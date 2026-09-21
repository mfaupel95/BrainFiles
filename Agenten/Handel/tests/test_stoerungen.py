"""Die Trennung "Handelsrunde oder Betriebsstoerung" - eine Fassung, alle Spuren.

Warum: ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung. Er entsteht,
weil der Dauerlauf stand, und wird im Journal trotzdem wie eine Runde gezaehlt.
Wer ihn mitzaehlt, zaehlt gegen die Freigabebedingung (50 Runden) Stoerungen
statt Strategie - und die Verzerrung kann in BEIDE Richtungen gehen.

Geprueft wird hier:
  1. das Merkmal (`ist_stoerung`) - inklusive der Faelle, die NICHT als
     Stoerung gelten duerfen (`stop`, `ziel`, `LIQUIDATION`)
  2. die Trennung `teile_runden` (eine Fassung, auch von `auswertung_alle`)
  3. dass JEDE Wachenfassung die Trennung liefert und die Kontrollzeile
     aufgeht (echt + Stoerung = Buchungen)
  4. dass die Kapitalkurve UNGEFILTERT bleibt: Drawdown und Kill rechnen auf
     allen Buchungen, weil eine Stoerung gebucht ist und Geld bewegt hat
  5. die gedruckten Zeilen (Wachen-Status und Tagesbericht) - gerendert, nicht
     im Quelltext gelesen

Die Journale sind synthetisch, die Wachen kommen als Kopie mit ausdruecklich
gesetzten Werten: kein Test behauptet einen Konfigurationswert, und kein Test
schreibt in einen echten Zielpfad.
"""

import ast
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent


def lade(name, pfad):
    """Ein Modul ueber den DATEIPFAD laden - nicht ueber den Modulnamen.

    `import handeln`/`import wachen_pruefung` holt das erste gleichnamige Modul
    aus dem Suchpfad; im Handel-Baum liegen mehrere Spuren mit denselben
    Dateinamen.
    """
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


ST = lade("test_stoerungen_modul", HANDEL / "stoerungen.py")
WP = lade("test_wachen_pruefung", HANDEL / "scanner" / "wachen_pruefung.py")

# Die Journale je Spur in ihrer ECHTEN Schreibweise (Kopfzeile wie im
# Spurordner). Eine erfundene Spaltenform wuerde eine andere Zahl messen.
KOEPFE = {
    "xperp": "zeit,modus,aktion,inst,seite,familie,preis,kontrakte,nominal_usd,"
             "margin_usd,hebel,stop,ziel,liq,liq_abstand,funding_pct,"
             "gebuehr_pct,quote_noetig,quote_beob,grund",
    "kraken": "zeit,modus,aktion,paar,preis,eur,menge,stop,ziel,grund",
    "scanner": "zeit,modus,aktion,inst,preis,usd,stop,ziel,grund,mfe_pct,"
               "mae_pct,haltetage",
    "orbk": "zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,"
            "gv_punkte,gv_usd",
}
ZEIT = "2026-09-10T10:00:00+00:00"


def xperp_zeilen(gruende):
    """(Kopf, Zeilen) - je Grund ein Paar aus eroeffnen und schliessen."""
    z = []
    for i, grund in enumerate(gruende):
        inst = "ABC-USD_UM_XPERP-%d" % (310000 + i)
        z.append("%s,papier,eroeffnen,%s,long,xperp,100,1,100,50,2,,,,,,,,,"
                 % (ZEIT, inst))
        z.append("%s,papier,schliessen,%s,long,xperp,100,1,100,55,2,,,,,,,,,%s"
                 % (ZEIT, inst, grund))
    return KOEPFE["xperp"], z


def scanner_zeilen(gruende, einstieg=100, ausstieg=110):
    """scanner-Journal: kauf/verkauf, Spalte usd (12 Spalten)."""
    z = []
    for i, grund in enumerate(gruende):
        inst = "ABC-USDT-%d" % i
        z.append("%s,papier,kauf,%s,1,%d,,,%s,,,"
                 % (ZEIT, inst, einstieg, grund))
        z.append("%s,papier,verkauf,%s,1,%d,,,%s,,,"
                 % (ZEIT, inst, ausstieg, grund))
    return KOEPFE["scanner"], z


def kraken_zeilen(gruende, einstieg=100, ausstieg=110):
    """kraken-Journal: kauf/verkauf, Spalte eur, Feld paar (10 Spalten)."""
    z = []
    for i, grund in enumerate(gruende):
        paar = "ABCEUR%d" % i
        z.append("%s,papier,kauf,%s,1,%d,1,,,," % (ZEIT, paar, einstieg))
        z.append("%s,papier,verkauf,%s,1,%d,1,,,%s"
                 % (ZEIT, paar, ausstieg, grund))
    return KOEPFE["kraken"], z


def orbk_zeilen(gruende):
    z = []
    for i, grund in enumerate(gruende):
        z.append("%s,ABC-USD_UM_XPERP-%d,long,100,95,110,%s,108,8,8"
                 % (ZEIT, 310000 + i, grund))
    return KOEPFE["orbk"], z


def schreibe_journal(tmp, spur, gruende):
    bauer = {"xperp": xperp_zeilen, "kraken": kraken_zeilen,
             "scanner": scanner_zeilen, "orbk": orbk_zeilen}[spur]
    kopf, zeilen_ = bauer(gruende)
    p = os.path.join(tmp, "handelsjournal.csv")
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        f.write(kopf + "\n" + "\n".join(zeilen_) + "\n")
    return p


def wachen_kopie(spur, tmp, **werte):
    """Die echte wachen.json als FORM, die Werte ausdruecklich gesetzt."""
    with io.open(HANDEL / spur / "wachen.json", encoding="utf-8") as f:
        w = json.load(f)
    w["journal_zweitziel"] = os.path.join(tmp, "zweitziel")   # nie Q:
    w.update(werte)
    return w


class MerkmalTest(unittest.TestCase):
    def test_merkmale_treffen(self):
        for grund in ("herzschlag_alt", "Herzschlag", "HERZSCHLAG_ALT",
                      "zwangsschluss", "Zwangsschluss (Frist)", "notaus"):
            self.assertTrue(ST.ist_stoerung(grund), grund)

    def test_echte_ausstiege_sind_keine_stoerung(self):
        # Wuerde eines davon treffen, verschwaenden echte Handelsrunden aus
        # jeder Kennzahl - der Fehler waere groesser als der Nutzen.
        for grund in ("stop", "ziel", "stop (boerse)", "frist", "trail",
                      "kopie", "vorbild_ausstieg", "1 Periode(n) a 8h",
                      "LIQUIDATION", "", None):
            self.assertFalse(ST.ist_stoerung(grund), grund)

    def test_liquidation_ist_bewusst_keine_stoerung(self):
        """Eine Liquidation ist ein Marktereignis der eigenen Position, kein
        Betriebsvorfall: sie gehoert in die Kennzahl, sonst verschwindet die
        riskanteste Runde aus der Trefferquote."""
        self.assertFalse(ST.ist_stoerung("LIQUIDATION"))

    def test_buchbereinigung_ist_keine_runde(self):
        """Eine Buchbereinigung ist eine Korrektur am Buch, keine Runde.

        Sie entsteht, wenn eine Position ohne echte Order im Live-Buch steht
        (Papier-Altlast) und ausgebucht wird. Fuer die Kennzahlen gilt dasselbe
        wie fuer einen Zwangsschluss - sonst zaehlt eine Korrektur als
        Handelsentscheidung. Eigene Klasse, eigene Schreibweisen:
        """
        for grund in ("buchbereinigung", "Buchbereinigung", "BUCHBEREINIGUNG"):
            self.assertTrue(ST.ist_stoerung(grund), grund)
        self.assertIn("buchbereinigung", ST.BUCHHALTUNG)
        self.assertNotIn("buchbereinigung", ST.STOERUNG_MERKMAL,
                         "die beiden Klassen bleiben unterscheidbar")

    def test_scanner_zaehlt_bereinigung_nicht_als_runde(self):
        """Der belegte Fall: scanner trug 10 Bereinigungs-Zeilen im Buch."""
        runden = [{"grund": g} for g in
                  ("ziel", "stop", "herzschlag_alt", "buchbereinigung",
                   "buchbereinigung", "trail")]
        echt, stoer = ST.teile_runden(runden)
        self.assertEqual([r["grund"] for r in echt],
                         ["ziel", "stop", "trail"])
        self.assertEqual(len(stoer), 3)


class TeilRundenTest(unittest.TestCase):
    def test_trennt_nach_grund(self):
        runden = [{"grund": "ziel"}, {"grund": "herzschlag_alt"},
                  {"grund": "stop"}, {"grund": "zwangsschluss"}]
        echt, stoer = ST.teile_runden(runden)
        self.assertEqual([r["grund"] for r in echt], ["ziel", "stop"])
        self.assertEqual([r["grund"] for r in stoer],
                         ["herzschlag_alt", "zwangsschluss"])

    def test_ohne_grund_ist_echt(self):
        echt, stoer = ST.teile_runden([{"grund": ""}, {}])
        self.assertEqual((len(echt), len(stoer)), (2, 0))

    def test_leere_eingabe(self):
        self.assertEqual(ST.teile_runden([]), ([], []))
        self.assertEqual(ST.teile_runden(None), ([], []))

    def test_wachenmodul_nutzt_dieselbe_fassung(self):
        """Die geteilte Fassung liegt in stoerungen.py - das Wachenmodul reicht
        sie durch, statt das Merkmal noch einmal zu schreiben."""
        runden = [{"grund": "ziel"}, {"grund": "notaus"}]
        echt, stoer = WP.teile_runden(runden)
        self.assertEqual([r["grund"] for r in echt], ["ziel"])
        self.assertEqual([r["grund"] for r in stoer], ["notaus"])
        self.assertFalse(hasattr(WP, "STOERUNG_MERKMAL"),
                         "das Merkmal gehoert nur nach stoerungen.py")
        modul = WP.stoerungen_modul()
        self.assertIs(modul, WP.stoerungen_modul())      # einmal geladen
        self.assertEqual(Path(modul.__file__).resolve(),
                         (HANDEL / "stoerungen.py").resolve())
        self.assertEqual(modul.STOERUNG_MERKMAL, ST.STOERUNG_MERKMAL)


class TrennungImLagebildTest(unittest.TestCase):
    """Je Wachenfassung ein Fall: alle vier 'lage()' muessen die Trennung
    liefern - eine vergessene Fassung sieht nicht wie ein Fehler aus, sondern
    wie eine Spur ohne Stoerungen."""

    FAELLE = [
        ("scanner", HANDEL / "scanner" / "wachen_pruefung.py"),
        ("xperp", HANDEL / "xperp" / "wachen_xperp.py"),
        ("kraken", HANDEL / "kraken" / "wachen_kraken.py"),
        ("orbk", HANDEL / "orbk" / "wachen_orb.py"),
    ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zustand = {"letzter_lauf": "2026-09-10T10:00:00+00:00"}

    def tearDown(self):
        self.tmp.cleanup()

    def _lage(self, spur, pfad, gruende):
        modul = lade("w_test_" + spur, pfad)
        journal = schreibe_journal(self.tmp.name, spur, gruende)
        w = wachen_kopie(spur, self.tmp.name)
        s = modul.lage(w, journal, self.dict_zustand())
        return modul, journal, s

    def dict_zustand(self):
        return dict(self.zustand)

    def test_alle_vier_trennen(self):
        for spur, pfad in self.FAELLE:
            with self.subTest(spur=spur):
                _m, _j, s = self._lage(spur, pfad, ["ziel", "herzschlag_alt",
                                                    "stop"])
                self.assertEqual(s["runden_gesamt"], 3)
                self.assertEqual(s["runden_echt"], 2)
                self.assertEqual(s["runden_stoerung"], 1)
                self.assertEqual(s["runden_echt"] + s["runden_stoerung"],
                                 s["runden_gesamt"])
                self.assertLessEqual(s["runden_papier_echt"], s["runden_papier"])
                self.assertIn("rollierender_ev_alle", s)

    def test_ohne_stoerung_ist_beides_gleich(self):
        for spur, pfad in self.FAELLE:
            with self.subTest(spur=spur):
                _m, _j, s = self._lage(spur, pfad, ["ziel", "stop", "frist"])
                self.assertEqual(s["runden_stoerung"], 0)
                self.assertEqual(s["runden_echt"], s["runden_gesamt"])

    def test_kapitalkurve_bleibt_ungefiltert(self):
        """Die Stoerung ist gebucht - Drawdown und Kill duerfen sie NICHT
        wegnehmen. Geprueft ueber die echte Rechnung des Wachenmoduls: die
        Kurve ueber alle Runden muss dieselbe sein wie ohne Filter."""
        _m, journal, s = self._lage("scanner", HANDEL / "scanner" /
                                    "wachen_pruefung.py",
                                    ["ziel", "herzschlag_alt", "stop"])
        modul = lade("w_scanner_2", HANDEL / "scanner" / "wachen_pruefung.py")
        alle = modul.runden_aus_journal(journal)
        echt, _stoer = modul.teile_runden(alle)
        hoch_alle, rueck_alle = modul.drawdown(alle)
        hoch_echt, _r = modul.drawdown(echt)
        self.assertEqual(s["hoechststand_usd"], hoch_alle)
        self.assertEqual(s["ruecklauf_usd"], rueck_alle)
        self.assertEqual(len(alle), 3)
        self.assertEqual(len(echt), 2)
        self.assertNotEqual(hoch_alle, hoch_echt)   # der Filter wuerde wirken
        self.assertEqual(s.get("halbierungsschwelle_usd"),
                         modul.halbierungsschwelle(
                             wachen_kopie("scanner", self.tmp.name)))

    def test_erwartungswert_der_echten_runden_existiert_erst_ab_fuenf(self):
        _m, _j, s = self._lage("xperp", HANDEL / "xperp" / "wachen_xperp.py",
                               ["ziel", "herzschlag_alt"])
        self.assertIsNone(s["rollierender_ev"])
        self.assertIsNone(s["rollierender_ev_alle"])

    def test_bedingung_5_rechnet_nur_auf_handelsrunden(self):
        """Die Sperrzahl kommt aus den HANDELSRUNDEN.

        Ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung. Rechnete
        Bedingung 5 weiter auf allen Buchungen, sperrte die Spur wegen eines
        Betriebsvorfalls - hier: fuenf echte Runden mit +10 USD gegen drei
        Zwangsschluesse mit -50 USD. Die alte Rechnung war negativ (-12,50),
        die Handelsrunden sind es nicht (+10,00).
        """
        z = []
        for i in range(5):
            z.append("%s,papier,kauf,ECH-%d,1,100,,,,,," % (ZEIT, i))
            z.append("%s,papier,verkauf,ECH-%d,1,110,,,ziel,,," % (ZEIT, i))
        for i in range(3):
            z.append("%s,papier,kauf,STO-%d,1,100,,,,,," % (ZEIT, i))
            z.append("%s,papier,verkauf,STO-%d,1,50,,,herzschlag_alt,,," % (ZEIT, i))
        journal = os.path.join(self.tmp.name, "handelsjournal.csv")
        with io.open(journal, "w", encoding="utf-8", newline="") as f:
            f.write(KOEPFE["scanner"] + "\n" + "\n".join(z) + "\n")

        modul = lade("w_b5", HANDEL / "scanner" / "wachen_pruefung.py")
        s = modul.lage(wachen_kopie("scanner", self.tmp.name), journal,
                       self.dict_zustand())

        self.assertEqual(s["runden_gesamt"], 8)
        self.assertEqual(s["runden_echt"], 5)
        self.assertEqual(s["runden_stoerung"], 3)
        self.assertEqual(s["rollierender_ev"], 10.0)          # Handelsrunden
        self.assertEqual(s["rollierender_ev_alle"], -12.5)    # alle Buchungen
        self.assertFalse(s["ev_negativ"],
                         "Bedingung 5 darf nicht auf Zwangsschluesse sperren")
        # Gegenprobe: die ALTE Rechnung war negativ - der Test wuerde ohne die
        # Umstellung fehlschlagen, nicht stillschweigend gruen bleiben.
        self.assertLess(s["rollierender_ev_alle"], 0)


class AnzeigeTest(unittest.TestCase):
    """Die Zeilen werden AUSGEFUEHRT, nicht im Quelltext gelesen - eine
    Formatpruefung im Kopf ist kein Nachweis."""

    def rendere(self, rel, marke, ns):
        p = HANDEL / rel
        quelle = p.read_text(encoding="utf-8")
        baum = ast.parse(quelle)
        treffer = [k for k in ast.walk(baum)
                   if isinstance(k, ast.Expr)
                   and marke in (ast.get_source_segment(quelle, k.value) or "")]
        self.assertEqual(len(treffer), 1,
                         "%s: %d Fundstellen fuer %r" % (rel, len(treffer), marke))
        modul = ast.Module(body=[treffer[0]], type_ignores=[])
        ast.fix_missing_locations(modul)
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            exec(compile(modul, str(p), "exec"), ns)
        return puffer.getvalue()

    WACHEN = {"freigabe_erfuellt": True, "runden_echt": 11,
              "runden_papier_echt": 11, "runden_stoerung": 12,
              "erste_runde": "2026-09-01"}

    def test_wachenzeile_nennt_handelsrunden_und_stoerungen(self):
        for rel in ("scanner/handeln.py", "xperp/handeln.py",
                    "kraken/handeln.py"):
            with self.subTest(datei=rel):
                aus = self.rendere(rel, "Freigabe erfuellt", {"s": dict(self.WACHEN)})
                self.assertIn("Handelsrunden 11", aus)
                self.assertIn("12 Betriebsstoerung(en)", aus)
                self.assertNotIn("Runden gesamt", aus)

    def test_wachenzeile_ohne_stoerung_bleibt_lesbar(self):
        s = dict(self.WACHEN, runden_stoerung=0, runden_echt=39,
                 runden_papier_echt=39)
        aus = self.rendere("scanner/handeln.py", "Freigabe erfuellt", {"s": s})
        self.assertIn("Handelsrunden 39", aus)
        self.assertIn("0 Betriebsstoerung(en)", aus)

    def test_tagesbericht_zeigt_beides(self):
        ns = {"t": [], "s": {"waehrung": "USD"}, "rueck": 12.5,
              "lage_": {"runden_gesamt": 23, "runden_papier": 23,
                       "runden_echt": 11, "runden_papier_echt": 11,
                       "runden_stoerung": 12, "ruecklauf_usd": 12.5,
                       "groessenfaktor": 1.0}}
        self.rendere("tagesbericht.py", "Handelsrunden %d (Papier", ns)
        zeile = ns["t"][0]
        self.assertIn("Handelsrunden 11", zeile)
        self.assertIn("12 Betriebsstoerung", zeile)
        self.assertIn("12.50 USD", zeile)

    def test_tagesbericht_faellt_auf_die_alten_felder_zurueck(self):
        """Ein Wachenmodul ohne die Trennung darf die Zeile nicht sprengen:
        get() mit Rueckfall, sonst waere der Bericht fuer die Spuren stumm,
        die noch nicht mitgezogen sind."""
        ns = {"t": [], "s": {"waehrung": "USD"}, "rueck": 1.0,
              "lage_": {"runden_gesamt": 9, "runden_papier": 9,
                       "ruecklauf_eur": 1.0, "groessenfaktor": 1.0}}
        self.rendere("tagesbericht.py", "Handelsrunden %d (Papier", ns)
        self.assertIn("Handelsrunden 9", ns["t"][0])
        self.assertIn("0 Betriebsstoerung", ns["t"][0])


class AuswertungNimmtDieselbeFassungTest(unittest.TestCase):
    def test_auswertung_alle_importiert_stoerungen(self):
        """Zwei Fassungen des Merkmals laufen auseinander - die Auswertung
        muss dieselbe Funktion benutzen wie die Wachen."""
        quelle = (HANDEL / "auswertung_alle.py").read_text(encoding="utf-8")
        baum = ast.parse(quelle)
        namen = {a.name for k in ast.walk(baum) if isinstance(k, ast.Import)
                 for a in k.names}
        self.assertIn("stoerungen", namen)
        self.assertIn("stoerungen.ist_stoerung", quelle)


if __name__ == "__main__":
    unittest.main()