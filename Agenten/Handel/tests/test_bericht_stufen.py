"""Tests fuer den Stufenbericht: tagesbericht.py --risiko.

Warum es diese Tests gibt
-------------------------
Der Bericht konnte eine Risikostufe nur ANKUENDIGEN. `stufenzeile()` nannte
sie, gelesen wurden aber immer `zustand.json` und `handelsjournal.csv` der
Basis - ein Bericht mit dem Kopf "Faktor 4" zeigte die Zahlen der Basis. Wer
das nicht nachmisst, haelt den Bericht fuer falsch, obwohl nur die Datei die
falsche war.

Gehalten wird hier die REGEL, nicht ein Bestand:
  1. `lage._buch` haengt das Suffix an Zustand und Journal - und ausdruecklich
     NICHT an wachen.json (die Wachen werden skaliert, nicht umbenannt; mit
     Suffix gelesen waere jede Sperre eines Stufenberichts leer).
  2. `_lies` liest wirklich die Stufendatei.
  3. Eine Spur holt im Stufenlauf ihre Wachen trotzdem aus `wachen.json`.
  4. Der Bericht nennt die Stufe am Kopf und am Buch.
  5. `--risiko alle` baut DREI Berichte in der Reihenfolge Basis, mittel, hoch.
  6. `baue(stufe_=...)` stellt die Umgebung danach zurueck - ein Bericht darf
     den aufrufenden Prozess (den Dauerlauf!) nicht umstellen.
"""
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.join(HIER, "scanner"))

import auswertung_alle                                       # noqa: E402
import lage                                                    # noqa: E402
import risikostufe                                             # noqa: E402
import tagesbericht                                            # noqa: E402


class BuchpfadTest(unittest.TestCase):
    """Die Regel an einer Stelle - unabhaengig von jeder Spur."""

    def test_zustand_und_journal_bekommen_das_suffix(self):
        alt = os.environ.pop("HANDEL_RISIKO", None)
        os.environ["HANDEL_RISIKO"] = "mittel"
        try:
            self.assertTrue(lage._buch("/x/scanner/zustand.json")
                            .endswith("zustand.mittel.json"))
            self.assertTrue(lage._buch("/x/kopier/zustand.knapp.json")
                            .endswith("zustand.knapp.mittel.json"))
            self.assertTrue(lage._buch("/x/gitter/handelsjournal.csv")
                            .endswith("handelsjournal.mittel.csv"))
        finally:
            os.environ.pop("HANDEL_RISIKO", None)
            if alt is not None:
                os.environ["HANDEL_RISIKO"] = alt

    def test_wachen_bleiben_ohne_suffix(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        try:
            self.assertTrue(lage._buch("/x/scanner/wachen.json")
                            .endswith("wachen.json"))
            self.assertFalse("hoch" in lage._buch("/x/spiegel/wachen.weit.json"))
        finally:
            os.environ.pop("HANDEL_RISIKO", None)

    def test_ohne_stufe_aendert_sich_nichts(self):
        os.environ.pop("HANDEL_RISIKO", None)
        self.assertEqual(lage._buch("/x/scanner/zustand.json"),
                         "/x/scanner/zustand.json")

    def test_pfadtyp_bleibt(self):
        from pathlib import PurePath
        os.environ["HANDEL_RISIKO"] = "mittel"
        try:
            p = lage._buch(PurePath("/x/scanner/zustand.json"))
            self.assertIsInstance(p, PurePath)
        finally:
            os.environ.pop("HANDEL_RISIKO", None)


class LiesTest(unittest.TestCase):
    """`_lies` ist der eine Weg zu Zustandsdateien - er muss die Stufe treffen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = os.path.join(self.tmp.name, "scanner")
        os.makedirs(self.ordner)
        self._schreibe("zustand.json", {"marker": "basis"})
        self._schreibe("zustand.mittel.json", {"marker": "mittel"})
        self.alt = os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        os.environ.pop("HANDEL_RISIKO", None)
        if self.alt is not None:
            os.environ["HANDEL_RISIKO"] = self.alt
        self.tmp.cleanup()

    def _schreibe(self, name, inhalt):
        with open(os.path.join(self.ordner, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    def test_basis_liest_die_basisdatei(self):
        self.assertEqual(lage._lies(os.path.join(self.ordner, "zustand.json")),
                         {"marker": "basis"})

    def test_stufe_liest_die_stufendatei(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        self.assertEqual(lage._lies(os.path.join(self.ordner, "zustand.json")),
                         {"marker": "mittel"})

    def test_fehlende_stufendatei_gibt_die_vorgabe(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        self.assertEqual(lage._lies(os.path.join(self.ordner, "zustand.json"),
                                    {"marker": "vorgabe"}),
                         {"marker": "vorgabe"})


class SpurImStufenlaufTest(unittest.TestCase):
    """Der Nachweis an einer echten Spur: Zustand aus der Stufe, Wachen aus der Basis."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = os.path.join(self.tmp.name, "scanner")
        os.makedirs(self.ordner)
        self._schreibe("wachen.json", {"budget_usd": 600, "max_pro_trade_usd": 120,
                                       "herzschlag_max_minuten": 180})
        self._schreibe("zustand.json", {"positionen": [], "marker": "basis"})
        self._schreibe("zustand.mittel.json", {"positionen": [],
                                               "marker": "mittel"})
        self.alt_hier = lage.HIER
        self.alt_env = os.environ.pop("HANDEL_RISIKO", None)
        lage.HIER = self.tmp.name

    def tearDown(self):
        lage.HIER = self.alt_hier
        os.environ.pop("HANDEL_RISIKO", None)
        if self.alt_env is not None:
            os.environ["HANDEL_RISIKO"] = self.alt_env
        self.tmp.cleanup()

    def _schreibe(self, name, inhalt):
        with open(os.path.join(self.ordner, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    def test_basis_liest_basiszustand(self):
        self.assertEqual(lage.spur_scanner()["z"]["marker"], "basis")

    def test_stufe_liest_stufenzustand_und_die_wachen(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        roh = lage.spur_scanner()
        self.assertEqual(roh["z"]["marker"], "mittel")
        # Und die Wachen kommen weiter aus wachen.json - waeren sie mit Suffix
        # gelesen, stuende hier {} und jede Sperre des Berichts waere falsch.
        self.assertEqual(roh["w"].get("budget_usd"), 600)


class BerichtTest(unittest.TestCase):
    """Kopf, Buchzeile und Reihenfolge - ohne Netz und ohne echte Buecher."""

    def setUp(self):
        self.alt_erhebe = lage.erhebe
        lage.erhebe = lambda mit_xperp=True, **k: []
        self.alt_env = os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        lage.erhebe = self.alt_erhebe
        os.environ.pop("HANDEL_RISIKO", None)
        if self.alt_env is not None:
            os.environ["HANDEL_RISIKO"] = self.alt_env

    def test_basisbericht_nennt_keine_stufe(self):
        # Die Stufenuebersicht am Fuss gehoert zum Basisbericht (sie sagt, dass
        # es die Stufen gibt). Der KOPF darf keine nennen, und die Buchzeile
        # eines Stufenberichts fehlt hier.
        text = tagesbericht.baue(mit_xperp=False)
        self.assertNotIn("Risikostufe", text.split("\n")[0])
        self.assertNotIn("Buch: zustand", text)

    def test_stufenbericht_nennt_stufe_und_buch(self):
        text = tagesbericht.baue(mit_xperp=False, stufe_="mittel")
        self.assertIn("Risikostufe mittel (Faktor 2)", text)
        self.assertIn("zustand.mittel.json", text)
        self.assertIn("handelsjournal.mittel.csv", text)

    def test_stufenbericht_wiederholt_die_stufenuebersicht_nicht(self):
        text = tagesbericht.baue(mit_xperp=False, stufe_="mittel")
        self.assertNotIn("Details: auswertung_alle.py", text)

    def test_umgebung_wird_zurueckgestellt(self):
        os.environ.pop("HANDEL_RISIKO", None)
        tagesbericht.baue(mit_xperp=False, stufe_="hoch")
        self.assertIsNone(os.environ.get("HANDEL_RISIKO"))
        os.environ["HANDEL_RISIKO"] = "mittel"
        tagesbericht.baue(mit_xperp=False, stufe_="hoch")
        self.assertEqual(os.environ.get("HANDEL_RISIKO"), "mittel")

    def test_reihenfolge_ist_basis_zuerst(self):
        self.assertEqual(tagesbericht.STUFEN_ALLE,
                         ("niedrig", "mittel", "hoch"))

    def test_alle_baut_drei_berichte(self):
        gerufen = []
        alt_baue = tagesbericht.baue
        tagesbericht.baue = lambda mit_xperp=True, stufe_=None, **k: (
            gerufen.append(stufe_) or "Bericht %s" % stufe_)
        alt_argv = sys.argv
        sys.argv = ["tagesbericht.py", "--risiko", "alle", "--ohne-xperp"]
        try:
            rc = tagesbericht.main()
        finally:
            tagesbericht.baue = alt_baue
            sys.argv = alt_argv
        self.assertEqual(gerufen, ["niedrig", "mittel", "hoch"])
        self.assertEqual(rc, 0)


class KennzahlenStufeTest(unittest.TestCase):
    """Auch die Runden- und 7-Tage-Zahlen muessen aus der Stufe kommen.

    `auswertung_alle.STUFE` ist eine MODULVARIABLE (Vorgabe None = Basis).
    Wird sie nicht mitgestellt, zeigt ein Stufenbericht die Positionen der
    Stufe und die Runden der Basis - zwei Zahlen aus zwei Buechern in einer
    Zeile.
    """

    def setUp(self):
        self.alt_env = os.environ.pop("HANDEL_RISIKO", None)
        self.gesehen = []
        self.alt_k = auswertung_alle.kennzahlen_fuer
        self.alt_h = auswertung_alle.hat_buch
        self.alt_s = auswertung_alle.STUFE
        auswertung_alle.kennzahlen_fuer = lambda spur, von=None, bis=None: (
            self.gesehen.append(auswertung_alle.STUFE)
            or {"n": 3, "ergebnis": 1.0})
        auswertung_alle.hat_buch = lambda spur: True

    def tearDown(self):
        auswertung_alle.kennzahlen_fuer = self.alt_k
        auswertung_alle.hat_buch = self.alt_h
        auswertung_alle.STUFE = self.alt_s
        os.environ.pop("HANDEL_RISIKO", None)
        if self.alt_env is not None:
            os.environ["HANDEL_RISIKO"] = self.alt_env

    def test_basis_fragt_die_basis(self):
        lage.zu_lage({"name": "X", "waehrung": "USD"}, "scanner")
        self.assertEqual(self.gesehen, [None])

    def test_stufe_fragt_die_stufe(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        lage.zu_lage({"name": "X", "waehrung": "USD"}, "scanner")
        self.assertEqual(self.gesehen, ["mittel"])
        self.assertIsNone(auswertung_alle.STUFE)

    def test_stufe_bleibt_auch_bei_einem_fehler_nicht_stehen(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        auswertung_alle.kennzahlen_fuer = self._kaputt
        with self.assertRaises(ValueError):
            lage.zu_lage({"name": "X", "waehrung": "USD"}, "scanner")
        self.assertIsNone(auswertung_alle.STUFE)

    @staticmethod
    def _kaputt(*a, **k):
        raise ValueError("kaputt")


if __name__ == "__main__":
    unittest.main()
