"""Tests fuer den Spiegelstand der Spuren (Bedingung 4) und seine Berichtszeile.

Der Spiegelstand vergleicht die Originale byte-genau mit der Kopie ausser Haus
(`Q:\\Handel_Journal\\...`) und liest daneben den Vermerk im Zustand. Beides wird
hier durch einen Datenordner ersetzt - kein Netz, kein Q:, kein Lauf.

Was hier belegt wird:
  1. Byte-gleiche Kopie ergibt keine Abweichung, die Zeile sagt es auch so.
  2. Eine abweichende Kopie wird MIT Spurnamen gemeldet (nicht als "0 Spuren").
  3. Ein fehlendes Ziel (Platte nicht angeschlossen) ist kein stiller Fall.
  4. Eine Spur ohne Ziel (`journal_zweitziel: null`) meldet "kein Ziel".
  5. Eine Spur ausserhalb von `dauerlauf.SPUREN` wird geprueft, aber nicht
     als Fehler gezaehlt.
  6. Geprueft wird nur gelesen: Dateiliste und Aenderungszeiten bleiben gleich.
  7. Die Zeile im Tagesbericht wird im Fehlerfall hervorgehoben.

Nachsehen statt glauben:
    python tests/test_tagesbericht_spiegelstand.py
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import spiegelstand                                          # noqa: E402
import tagesbericht                                          # noqa: E402

JOURNAL = "zeit,modus,aktion,inst,preis,usd\n2026-09-13T10:00:00Z,papier,kauf,ETH-USDT,1,20\n"
ZUSTAND = {"modus": "papier", "letzter_lauf": "2026-09-13T18:00:00+00:00"}


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="spiegel-stand-")
        self.handel = os.path.join(self.tmp, "Handel")
        os.makedirs(self.handel)
        self.ziel = os.path.join(self.tmp, "Q", "Handel_Journal")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- Bauhilfen ---------------------------------------------------------

    def spur(self, name, zweitziel=..., gleich=True, ziel_da=True, zeilen=JOURNAL):
        """Eine Spur mit Ziel, Kopie und Zustand anlegen."""
        ordner = os.path.join(self.handel, name)
        os.makedirs(ordner, exist_ok=True)
        w = {"handel_erlaubt": False}
        if zweitziel is ...:
            w["journal_zweitziel"] = os.path.join(self.ziel, name)
        elif zweitziel is not None:
            w["journal_zweitziel"] = zweitziel
        with open(os.path.join(ordner, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f)
        with open(os.path.join(ordner, "handelsjournal.csv"), "w",
                  encoding="utf-8", newline="") as f:
            f.write(zeilen)
        with open(os.path.join(ordner, "zustand.json"), "w", encoding="utf-8") as f:
            json.dump(dict(ZUSTAND, journal_zweitziel_ok=True), f)
        if w.get("journal_zweitziel") and ziel_da:
            zielordner = w["journal_zweitziel"]
            os.makedirs(zielordner, exist_ok=True)
            with open(os.path.join(zielordner, "handelsjournal.csv"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(zeilen if gleich else zeilen.replace("20", "99"))
            with open(os.path.join(zielordner, "zustand.json"), "w",
                      encoding="utf-8") as f:
                json.dump(dict(ZUSTAND, journal_zweitziel_ok=True), f)
        return ordner

    def dauerlauf(self, *spuren):
        """Ein dauerlauf.py-Stummel, damit spuren_im_lauf() etwas liest."""
        with open(os.path.join(self.handel, "dauerlauf.py"), "w",
                  encoding="utf-8") as f:
            f.write("SPUREN = {\n")
            for s in spuren:
                f.write("    %r: {\"skript\": \"handeln.py\",\n"
                        "           \"python\": os.path.join(HIER, \"%s\")},\n" % (s, s))
            f.write("}\n")

    def zustand_aller_dateien(self):
        stand = []
        for wurzel, _, dateien in os.walk(self.tmp):
            for d in sorted(dateien):
                p = os.path.join(wurzel, d)
                st = os.stat(p)
                stand.append((p, st.st_size, st.st_mtime_ns))
        return sorted(stand)


class SpiegelstandTest(Basis):
    def test_gleiche_kopie_ist_keine_abweichung(self):
        self.spur("swap")
        self.dauerlauf("swap")
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["geprueft"], 1)
        self.assertEqual(e["abweichend"], [])
        self.assertEqual(spiegelstand.kurz(e), "1 von 1 Spuren byte-gleich (Q:)")

    def test_abweichende_kopie_wird_mit_namen_gemeldet(self):
        self.spur("swap", gleich=False)
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["abweichend"], ["swap"])
        self.assertIn("swap", spiegelstand.kurz(e))
        self.assertIn("ABWEICHEND", spiegelstand.kurz(e))

    def test_fehlendes_ziel_ist_kein_stiller_fall(self):
        self.spur("spiegel", ziel_da=False)
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["spuren"][0]["stand"], "Ziel fehlt")
        self.assertEqual(e["abweichend"], ["spiegel"])

    def test_spur_ohne_ziel_meldet_kein_ziel(self):
        self.spur("orb", zweitziel=None, ziel_da=False)
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["spuren"][0]["stand"], "kein Ziel")
        self.assertEqual(e["spuren"][0]["grund"], "journal_zweitziel leer")

    def test_spur_ausserhalb_des_dauerlaufs_zaehlt_nicht_als_fehler(self):
        self.spur("swap")
        self.spur("kraken", gleich=False)          # abweichend, aber ohne Dienst
        self.dauerlauf("swap")
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["geprueft"], 1)
        self.assertEqual(e["abweichend"], [])
        self.assertEqual(e["ausserhalb"], ["kraken"])
        k = [x for x in e["spuren"] if x["spur"] == "kraken"][0]
        self.assertIn("nicht in dauerlauf.SPUREN", k["grund"])
        self.assertEqual(spiegelstand.kurz(e), "1 von 1 Spuren byte-gleich (Q:)")

    def test_pruefung_schreibt_nichts(self):
        self.spur("swap")
        self.spur("nautilus")
        vorher = self.zustand_aller_dateien()
        spiegelstand.stand(self.handel)
        self.assertEqual(vorher, self.zustand_aller_dateien())

    def test_zusatzdatei_der_spiegel_spur_wird_mitgeprueft(self):
        """Das Ablehnungsprotokoll gehoert ausser Haus wie das Journal.

        Eine Zusatzdatei nur EINER Spur darf die anderen nicht abweichend
        machen - und fuer ihre eigene Spur muss sie mitgeprueft werden, sonst
        ist die Kopie ein ungeprueftes Versprechen.
        """
        ordner = self.spur("spiegel")
        ordner_anders = self.spur("swap")
        self.dauerlauf("spiegel", "swap")
        protokoll = ("zeit,art,grund,anzahl\n"
                     "2026-09-14T17:00:00Z,zyklus,Signale gesehen,695\n")
        for p in (os.path.join(ordner, "ablehnungen.csv"),
                  os.path.join(ordner_anders, "ablehnungen.csv")):
            # Nur spiegel fuehrt das Protokoll; swap hat keine Zusatzdatei.
            if "spiegel" in p:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(protokoll)
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["abweichend"], ["spiegel"], e["spuren"])
        grund = [x for x in e["spuren"] if x["spur"] == "spiegel"][0]["grund"]
        self.assertIn("ablehnungen.csv", grund)

    def test_zusatzdatei_gleich_ist_keine_abweichung(self):
        ordner = self.spur("spiegel")
        ziel = os.path.join(self.ziel, "spiegel")
        self.dauerlauf("spiegel")
        protokoll = ("zeit,art,grund,anzahl\n"
                     "2026-09-14T17:00:00Z,zyklus,Signale gesehen,695\n")
        for p in (os.path.join(ordner, "ablehnungen.csv"),
                  os.path.join(ziel, "ablehnungen.csv")):
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(protokoll)
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["abweichend"], [], e["spuren"])
        self.assertEqual(e["spuren"][0]["stand"], "gleich")

    def test_ohne_lesbare_spurenliste_ist_die_zeile_vorsichtig(self):
        # Ohne dauerlauf.py ist nicht entscheidbar, welche Spur im Dienst ist.
        # Dann darf die Zeile keine Zahl behaupten, die sie nicht decken kann.
        self.spur("swap")
        e = spiegelstand.stand(self.handel)
        self.assertFalse(e["im_lauf_lesbar"])
        self.assertIn("SPUREN nicht lesbar", spiegelstand.kurz(e))

    def test_unerreichbarer_ordner_ist_eine_meldung_kein_absturz(self):
        e = spiegelstand.stand(os.path.join(self.tmp, "gibtsnicht"))
        self.assertEqual(e["geprueft"], 0)
        self.assertIn("nicht geprueft", spiegelstand.kurz(e))


class BerichtszeileTest(Basis):
    def test_zeile_im_bericht_ist_ruhig_wenn_alles_gleich_ist(self):
        self.spur("swap")
        self.dauerlauf("swap")
        # HIER umbiegen: die Zeile liest den Datenordner, nicht den echten Baum.
        alt = tagesbericht.HIER
        tagesbericht.HIER = self.handel
        try:
            zeile = tagesbericht.spiegelzeile()
        finally:
            tagesbericht.HIER = alt
        self.assertEqual(zeile, "Journal ausser Haus: 1 von 1 Spuren byte-gleich (Q:)")

    def test_zeile_wird_im_fehlerfall_hervorgehoben(self):
        self.spur("swap", gleich=False)
        alt = tagesbericht.HIER
        tagesbericht.HIER = self.handel
        try:
            zeile = tagesbericht.spiegelzeile()
        finally:
            tagesbericht.HIER = alt
        self.assertIn("<b>", zeile)
        self.assertIn("ABWEICHEND", zeile)


class GleichTest(unittest.TestCase):
    """Der Byte-Vergleich selbst - die beidseitig fehlende Datei zaehlt.

    Eine neue Spur hat bis zur ersten Buchung kein Journal; fehlt die Datei
    auf BEIDEN Seiten, ist der Stand gleich (kein Fehlalarm). Fehlt sie nur
    auf einer Seite, haengt die Kopie hinterher.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="spiegel-gleich-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_beidseitig_fehlend_ist_gleich(self):
        a = os.path.join(self.tmp, "a.csv")
        b = os.path.join(self.tmp, "b.csv")
        self.assertTrue(spiegelstand.gleich(a, b))

    def test_einseitig_fehlend_ist_abweichung(self):
        a = os.path.join(self.tmp, "a.csv")
        b = os.path.join(self.tmp, "b.csv")
        with open(a, "w", encoding="utf-8") as f:
            f.write("x")
        self.assertFalse(spiegelstand.gleich(a, b))

    def test_inhalt_unterschied_zaehlt(self):
        a = os.path.join(self.tmp, "a.csv")
        b = os.path.join(self.tmp, "b.csv")
        with open(a, "w", encoding="utf-8") as f:
            f.write("x")
        with open(b, "w", encoding="utf-8") as f:
            f.write("y")
        self.assertFalse(spiegelstand.gleich(a, b))
        with open(b, "w", encoding="utf-8") as f:
            f.write("x")
        self.assertTrue(spiegelstand.gleich(a, b))


class LaeufeArmeTest(Basis):
    """Die laeufe-Arme (llm_stunde, 12.10.2026) werden als eigene Spuren geprueft.

    Der Hauptordner haelt nur die Basis-Wachen, die Straenge fahren eigene
    Buecher unter laeufe/<variante>-<arm>/ mit eigener wachen.json. Jeder Arm
    spiegelt in denselben Zielordner. Vor dem Fix meldete der Hauptordner
    faelschlich ABWEICHUNG, weil dort keine Quelldateien liegen.
    """

    def arm_spur(self, name, zweitziel, gleich=True):
            """Ein laeufe-Arm mit eigener Wachen, Buch und Kopie im Ziel."""
            # Der Hauptordner haelt die Basis-Wachen (wie in der echten Spur) -
            # ohne sie landet llm_stunde nicht in `alle` und wird nicht expandiert.
            haupt = os.path.join(self.handel, "llm_stunde")
            os.makedirs(haupt, exist_ok=True)
            if not os.path.isfile(os.path.join(haupt, "wachen.json")):
                with open(os.path.join(haupt, "wachen.json"), "w",
                          encoding="utf-8") as f:
                    json.dump({"handel_erlaubt": False}, f)
            ordner = os.path.join(haupt, "laeufe", name)
            os.makedirs(ordner, exist_ok=True)
            w = {"handel_erlaubt": False, "journal_zweitziel": zweitziel}
            with open(os.path.join(ordner, "wachen.json"), "w",
                      encoding="utf-8") as f:
                json.dump(w, f)
            with open(os.path.join(ordner, "handelsjournal.csv"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(JOURNAL)
            with open(os.path.join(ordner, "zustand.json"), "w",
                      encoding="utf-8") as f:
                json.dump(dict(ZUSTAND, journal_zweitziel_ok=True), f)
            zielordner = zweitziel
            os.makedirs(zielordner, exist_ok=True)
            with open(os.path.join(zielordner, "handelsjournal.csv"), "w",
                      encoding="utf-8", newline="") as f:
                f.write(JOURNAL if gleich else JOURNAL.replace("20", "99"))
            with open(os.path.join(zielordner, "zustand.json"), "w",
                      encoding="utf-8") as f:
                json.dump(dict(ZUSTAND, journal_zweitziel_ok=True), f)
            return ordner

    def test_arme_werden_als_eigene_spuren_geprueft(self):
        ziel = os.path.join(self.ziel, "llm_stunde")
        for arm in ("ema1h-L", "ema1h-R", "rsi1h-L", "rsi1h-R",
                    "st1h-L", "st1h-R"):
            self.arm_spur(arm, ziel)
        self.dauerlauf("llm_stunde")
        e = spiegelstand.stand(self.handel)
        namen = [x["spur"] for x in e["spuren"]]
        for arm in ("ema1h-L", "ema1h-R", "rsi1h-L", "rsi1h-R",
                    "st1h-L", "st1h-R"):
            self.assertIn("llm_stunde/%s" % arm, namen)
        # Der Hauptordner selbst wird NICHT als eigene Spur geprueft.
        self.assertNotIn("llm_stunde", namen)
        self.assertEqual(e["geprueft"], 6)
        self.assertEqual(e["abweichend"], [])
        self.assertEqual(e["ausserhalb"], [])
        for x in e["spuren"]:
            self.assertEqual(x["stand"], "gleich")
            self.assertEqual(x["ziel"], ziel)

    def test_abweichender_arm_wird_mit_namen_gemeldet(self):
        # Eigene Zielordner je Arm, damit die Abweichung des einen den anderen
        # nicht ueber den geteilten Zielordner mitreisst (im echten Lauf sind
        # die Arm-Dateien byte-gleich, der geteilte Ordner kollidiert nicht).
        ziel_l = os.path.join(self.ziel, "llm_stunde_l")
        ziel_r = os.path.join(self.ziel, "llm_stunde_r")
        self.arm_spur("ema1h-L", ziel_l)
        self.arm_spur("ema1h-R", ziel_r, gleich=False)
        self.dauerlauf("llm_stunde")
        e = spiegelstand.stand(self.handel)
        self.assertEqual(e["abweichend"], ["llm_stunde/ema1h-R"])
        self.assertEqual(e["geprueft"], 2)

    def test_ohne_laeufe_bleibt_die_spur_normal(self):
        # Eine Spur ohne laeufe-Unterordner wird wie vorher geprueft.
        self.spur("swap")
        self.dauerlauf("swap")
        e = spiegelstand.stand(self.handel)
        self.assertEqual([x["spur"] for x in e["spuren"]], ["swap"])
        self.assertEqual(e["geprueft"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
