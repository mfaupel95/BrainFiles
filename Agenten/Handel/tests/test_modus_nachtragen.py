"""Tests fuer modus_nachtragen.py (T-354).

Die Regeln, nicht die Zahlen: ein Test, der eine feste Positionenzahl
einfriert, meldet spaeter jede neue Spur statt jeden Fehler.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lade_modul():
    pfad = os.path.join(HANDEL, "modus_nachtragen.py")
    spec = importlib.util.spec_from_file_location("modus_nachtragen", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mn = lade_modul()


def spur_anlegen(basis, name, zustand, journal_zeilen=(), live_zeile=False):
    ordner = os.path.join(basis, name)
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "wachen.json"), "w", encoding="utf-8") as f:
        json.dump({"journal_zweitziel": "Q:\\Handel_Journal\\%s" % name}, f)
    with open(os.path.join(ordner, "handeln.py"), "w", encoding="utf-8") as f:
        f.write("import spur_buch\nbuch.zyklus()\n")
    with open(os.path.join(ordner, "zustand.json"), "w", encoding="utf-8") as f:
        json.dump(zustand, f)
    kopf = "zeit,modus,aktion,inst,preis,grund\n"
    zeilen = list(journal_zeilen)
    if live_zeile:
        zeilen.append("2026-10-01T00:00:00+00:00,live,kauf,ETH,1.0,test\n")
    with open(os.path.join(ordner, "handelsjournal.csv"), "w",
              encoding="utf-8") as f:
        f.write(kopf + "".join(zeilen))
    return ordner


def pos(inst="GENIUS", **rest):
    p = {"inst": inst, "seite": "long", "einstieg": 1.0, "stop": 0.9,
         "ziel": 1.2, "stop_pct": 7.0, "nominal": 100.0,
         "eroeffnet_zeit": "2026-09-20T20:19:22+00:00"}
    p.update(rest)
    return p


class TempWurzel(unittest.TestCase):
    def setUp(self):
        self.basis = tempfile.mkdtemp(prefix="t354_")
        self.addCleanup(shutil.rmtree, self.basis, True)
        self.alt_handel = mn.HANDEL
        mn.HANDEL = self.basis
        self.addCleanup(setattr, mn, "HANDEL", self.alt_handel)


class KandidatenTest(TempWurzel):
    def test_spuren_bestimmen_sich_aus_der_handeln_py(self):
        spur_anlegen(self.basis, "mit_buch", {"positionen": []})
        os.makedirs(os.path.join(self.basis, "ohne_buch"))
        with open(os.path.join(self.basis, "ohne_buch", "handeln.py"), "w",
                  encoding="utf-8") as f:
            f.write("x = 1\n")
        self.assertEqual(mn.spur_mit_buchkern(self.basis), ["mit_buch"])

    def test_zustand_dateien_der_drei_stufen(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": []})
        for name in ("zustand.mittel.json", "zustand.hoch.json"):
            with open(os.path.join(ordner, name), "w", encoding="utf-8") as f:
                json.dump({"positionen": []}, f)
        gefunden = [os.path.basename(p)
                    for p in mn.zustand_dateien("s", self.basis)]
        self.assertEqual(gefunden,
                         ["zustand.hoch.json", "zustand.json",
                          "zustand.mittel.json"])

    def test_journal_gehoert_zur_zustandsdatei(self):
        p = os.path.join(self.basis, "s", "zustand.mittel.json")
        self.assertTrue(mn.journal_zu(p).endswith("handelsjournal.mittel.csv"))
        p = os.path.join(self.basis, "s", "zustand.json")
        self.assertTrue(mn.journal_zu(p).endswith("handelsjournal.csv"))

    def test_position_ohne_modus_ist_ein_kandidat(self):
        self.assertEqual(len(mn.fehlende_modus([pos(), pos(modus="papier"),
                                                pos(modus="live")])), 1)


class BelegeTest(TempWurzel):
    """Die zwei Bedingungen, unter denen ueberhaupt angefasst wird."""

    def test_live_buch_wird_nicht_angefasst(self):
        ordner = spur_anlegen(self.basis, "s",
                              {"positionen": [pos()], "modus": "live"})
        b = mn.datei_lauf("s", os.path.join(ordner, "zustand.json"), False)
        self.assertEqual(b["geaendert"], 0)
        self.assertIn("live", b["grund"])

    def test_journal_mit_live_zeile_waere_ein_gegenbeweis(self):
        # Gegenprobe zum vorigen Test: derselbe Zustand, aber die Spur hat
        # einmal echt gekauft. Dann ist die Herkunft nicht belegbar.
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = os.path.join(ordner, "zustand.json")
        alt = os.path.getmtime(pfad) - mn.SCHONFRIST_S - 60
        os.utime(pfad, (alt, alt))
        b = mn.datei_lauf("s", pfad, False)
        self.assertEqual(b["grund"], "")
        with open(os.path.join(ordner, "handelsjournal.csv"), "a",
                  encoding="utf-8") as f:
            f.write("2026-10-01T00:00:00+00:00,live,kauf,ETH,1.0,t\n")
        b = mn.datei_lauf("s", pfad, False)
        self.assertEqual(b["geaendert"], 0)
        self.assertIn("live-Zeile", b["grund"])

    def test_juriger_zustand_wird_nicht_angefasst(self):
        # Frisch angelegt (Alter ~0 s < SCHONFRIST_S): dort laeuft ein Zyklus,
        # der Lauf darf die Datei nicht anfassen.
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = os.path.join(ordner, "zustand.json")
        b = mn.datei_lauf("s", pfad, True)
        self.assertEqual(b["geaendert"], 0)
        self.assertIn("laeuft ein Zyklus", b["grund"])
        z = json.load(open(pfad, encoding="utf-8"))
        self.assertIsNone(z["positionen"][0].get("modus"))

    def test_buch_modus_fehlt_heisst_papier(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = os.path.join(ordner, "zustand.json")
        alt = os.path.getmtime(pfad) - mn.SCHONFRIST_S - 60
        os.utime(pfad, (alt, alt))
        b = mn.datei_lauf("s", pfad, True)
        self.assertEqual(b["geaendert"], 1, "fehlender Buch-Modus ist Papier")


class SchreibenTest(TempWurzel):
    def _alt_machen(self, ordner):
        pfad = os.path.join(ordner, "zustand.json")
        alt = os.path.getmtime(pfad) - mn.SCHONFRIST_S - 60
        os.utime(pfad, (alt, alt))
        return pfad

    def test_anwenden_ergaenzt_nur_das_feld(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = self._alt_machen(ordner)
        vorher = list(json.load(open(pfad, encoding="utf-8"))["positionen"][0])
        mn.datei_lauf("s", pfad, True)
        z = json.load(open(pfad, encoding="utf-8"))
        p = z["positionen"][0]
        self.assertEqual(p["modus"], "papier")
        self.assertIn(mn.VERMERK, p)
        # Kein Feld verloren, kein Preis angefasst.
        for feld in vorher:
            self.assertEqual(p[feld], json.load(
                open(pfad, encoding="utf-8"))["positionen"][0][feld])
        self.assertEqual(p["einstieg"], 1.0)

    def test_anwenden_schreibt_keine_journalzeile(self):
        """Eine Ausstiegszeile waere eine Runde, die es nie gab."""
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = self._alt_machen(ordner)
        jrn = os.path.join(ordner, "handelsjournal.csv")
        vorher = open(jrn, encoding="utf-8").read()
        mn.datei_lauf("s", pfad, True)
        self.assertEqual(open(jrn, encoding="utf-8").read(), vorher)

    def test_sicherung_entsteht(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = self._alt_machen(ordner)
        b = mn.datei_lauf("s", pfad, True)
        self.assertTrue(os.path.isfile(b["sicherung"]))
        alt = json.load(open(b["sicherung"], encoding="utf-8"))
        self.assertIsNone(alt["positionen"][0].get("modus"))

    def test_idempotent(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = self._alt_machen(ordner)
        mn.datei_lauf("s", pfad, True)
        alt = os.path.getmtime(pfad) - mn.SCHONFRIST_S - 60
        os.utime(pfad, (alt, alt))
        b = mn.datei_lauf("s", pfad, True)
        self.assertEqual(b["fehlt"], 0)
        self.assertEqual(b["geaendert"], 0)

    def test_vorschau_schreibt_nichts(self):
        ordner = spur_anlegen(self.basis, "s", {"positionen": [pos()]})
        pfad = self._alt_machen(ordner)
        vorher = open(pfad, encoding="utf-8").read()
        b = mn.datei_lauf("s", pfad, False)
        self.assertEqual(b["fehlt"], 1)
        self.assertEqual(b["geaendert"], 0)
        self.assertEqual(open(pfad, encoding="utf-8").read(), vorher)


class EchtesBuchTest(unittest.TestCase):
    """Am echten Haus: das Werkzeug darf nur Positionen OHNE Live-Herkunft
    finden, und jede gefundene Spur muss den Beleg tragen."""

    def test_jedes_buch_ohne_herkunft_ist_papier_belegbar(self):
        befunde = [b for b in mn.lauf()
                   if b["fehlt"] and not b["grund"]]
        for b in befunde:
            self.assertNotEqual(b["spur"], "kraken",
                                "kraken nutzt kauf_txid, nicht modus")
            z = mn.lade(os.path.join(HANDEL, b["spur"], b["datei"]))
            self.assertNotEqual(z.get("modus"), "live")
            self.assertFalse(mn.journal_hat_live(
                os.path.join(HANDEL, b["spur"],
                             b["datei"].replace("zustand", "handelsjournal")
                             .replace(".json", ".csv"))))

    def test_die_zwei_benoannten_positionen_sind_nicht_mehr_kandidaten(self):
        """Der Befund der Karte: GENIUS (signalwelle) und BTC (marktlage) tragen
        jetzt modus=papier (belegt an der Boerse nicht offen) - sie duerfen in
        keinem Buch mehr als Kandidat ohne Herkunftsfeld auftauchen."""
        gefunden = set()
        for b in mn.lauf():
            for inst, _ in b.get("betroffen", []) or []:
                gefunden.add((b["spur"], inst))
        self.assertNotIn(("moondev_signalwelle", "GENIUS"), gefunden)
        self.assertNotIn(("moondev_marktlage", "BTC"), gefunden)


if __name__ == "__main__":
    unittest.main()