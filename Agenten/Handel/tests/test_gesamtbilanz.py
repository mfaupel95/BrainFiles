"""Tests fuer die Gesamtbilanz.

Der gefaehrlichste Fehler dieses Umbaus ist eine Zahl, die stimmt aussieht
und nicht stimmt: EUR zu USD addiert, oder Papiergewinn mit echtem Geld
verrechnet. Beides steht hier als Test.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import gesamtbilanz as gb                                      # noqa: E402

POSTEN = [
    {"spur": "scanner", "n": 10, "ergebnis": 100.0, "treffer": 6,
     "waehrung": "USD", "live": True, "belastbar": True},
    {"spur": "swap", "n": 8, "ergebnis": -20.0, "treffer": 3,
     "waehrung": "USD", "live": False, "belastbar": True},
    {"spur": "kraken", "n": 12, "ergebnis": 50.0, "treffer": 7,
     "waehrung": "EUR", "live": False, "belastbar": True},
]


def _kennzahlen_fuer_stub(spur, von=None, bis=None):
    """Ersetzt auswertung_alle.kennzahlen_fuer() fuer die posten()-Tests.

    Bildet genau die drei Faelle ab, um die es geht: kein Buch mit
    geschlossener Runde (None), zu wenige Runden (unter MIN_RUNDEN=8), und
    eine belastbare Spur.
    """
    return {
        "keinrunde": None,
        "wenig": {"n": 3, "ergebnis": -5.0, "treffer": 1},
        "reichlich": {"n": 10, "ergebnis": 25.0, "treffer": 6},
    }.get(spur)


class TestSumme(unittest.TestCase):

    def test_waehrungen_bleiben_getrennt(self):
        s = gb.summe(POSTEN)
        self.assertIn(("EUR", False), s)
        self.assertIn(("USD", False), s)
        self.assertEqual(s[("EUR", False)]["ergebnis"], 50.0)
        self.assertEqual(s[("USD", False)]["ergebnis"], -20.0)

    def test_papier_und_live_bleiben_getrennt(self):
        s = gb.summe(POSTEN)
        self.assertEqual(s[("USD", True)]["ergebnis"], 100.0)
        self.assertEqual(s[("USD", False)]["ergebnis"], -20.0)

    def test_keine_gemeinsame_summe_ueber_alles(self):
        # Es darf keinen Schluessel geben, der alles zusammenwirft.
        s = gb.summe(POSTEN)
        self.assertEqual(len(s), 3)
        for schluessel in s:
            self.assertIsInstance(schluessel, tuple)
            self.assertEqual(len(schluessel), 2)

    def test_runden_und_treffer_werden_mitgezaehlt(self):
        s = gb.summe(POSTEN)
        self.assertEqual(s[("USD", True)]["n"], 10)
        self.assertEqual(s[("USD", True)]["treffer"], 6)

    def test_leere_eingabe_ist_leere_summe(self):
        self.assertEqual(gb.summe([]), {})


class TestBerichtstext(unittest.TestCase):

    def test_text_nennt_papier_und_live_getrennt(self):
        t = gb.zeilen_text(gb.summe(POSTEN))
        self.assertIn("Live", t)
        self.assertIn("Papier", t)
        self.assertIn("EUR", t)
        self.assertIn("USD", t)

    def test_text_wirft_keine_gesamtzahl_aus(self):
        # 100 - 20 + 50 = 130 waere die verbotene Zahl.
        t = gb.zeilen_text(gb.summe(POSTEN))
        self.assertNotIn("130", t)


class TestSummeSchwelle(unittest.TestCase):
    """Ein Posten mit zu wenigen Runden darf die Summe nicht erreichen -
    genau die stille Falschzahl, gegen die belastbar() geschrieben ist."""

    def test_nicht_belastbarer_posten_zaehlt_nicht_mit(self):
        posten_ = POSTEN + [
            {"spur": "wenig", "n": 2, "ergebnis": 999.0, "treffer": 2,
             "waehrung": "USD", "live": False, "belastbar": False},
        ]
        s = gb.summe(posten_)
        self.assertNotIn(999.0, [t["ergebnis"] for t in s.values()])
        self.assertEqual(s[("USD", False)]["ergebnis"], -20.0)


class TestPosten(unittest.TestCase):
    """posten() selbst treffen, nicht nur eine von Hand gebaute Liste
    fuettern - siehe Modul-Docstring: das ist die gefaehrlichste
    Fehlerquelle dieses Umbaus."""

    def _mit_stub(self, spuren):
        return patch.multiple(
            gb,
            EIGENE=(),  # die fuenf eigenen Module bleiben hier aussen vor
        ), patch.object(gb.auswertung_alle, "SPUREN", spuren), \
            patch.object(gb.auswertung_alle, "kennzahlen_fuer",
                         side_effect=_kennzahlen_fuer_stub)

    def test_spur_ohne_geschlossene_runde_fehlt_ganz(self):
        m1, m2, m3 = self._mit_stub(("keinrunde",))
        with m1, m2, m3:
            p = gb.posten()
        self.assertEqual(p, [])

    def test_spur_unter_der_schwelle_bleibt_drin_aber_nicht_belastbar(self):
        m1, m2, m3 = self._mit_stub(("wenig",))
        with m1, m2, m3:
            p = gb.posten()
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["spur"], "wenig")
        self.assertEqual(p[0]["n"], 3)
        self.assertFalse(p[0]["belastbar"])

    def test_belastbare_spur_kommt_mit_belastbar_true(self):
        m1, m2, m3 = self._mit_stub(("reichlich",))
        with m1, m2, m3:
            p = gb.posten()
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["spur"], "reichlich")
        self.assertTrue(p[0]["belastbar"])


class TestLiveMerker(unittest.TestCase):
    """_live() darf nie werfen - genau wie die fuenf Eigen-Module.

    Der Aufruf steht in posten() ausserhalb jedes try: eine kaputte
    wachen.json EINER Spur wuerde sonst die ganze Gesamtbilanz mitreissen.
    Gueltiges JSON, das kein Objekt ist ([], 42, null, "x"), hat kein .get().
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        (self.wurzel / "spur").mkdir()
        self.datei = self.wurzel / "spur" / "wachen.json"
        self._alt = gb.HIER
        gb.HIER = self.wurzel

    def tearDown(self):
        gb.HIER = self._alt
        self.tmp.cleanup()

    def _merker(self, inhalt):
        if inhalt is None:
            if self.datei.exists():
                self.datei.unlink()
        else:
            self.datei.write_text(inhalt, encoding="utf-8")
        return gb._live("spur")

    def test_papier_bei_jedem_fehlschlag(self):
        # None heisst: Datei fehlt ganz.
        for inhalt in (None, "kein JSON {", "[]", "42", "null", '"x"', "{}",
                       '{"handel_erlaubt": false}'):
            with self.subTest(inhalt=inhalt):
                self.assertFalse(self._merker(inhalt))

    def test_true_wird_erkannt(self):
        self.assertTrue(self._merker('{"handel_erlaubt": true}'))


class TestGezaehlteBuecher(unittest.TestCase):
    """Die Schlusszeile muss die Buecher nennen, die in der Summe stehen.

    Bis zum 18.09.2026 stand dort `len(p)` - alle Posten. summe() laesst
    aber jeden unbelastbaren Posten weg. Die Zeile behauptete damit eine
    Grundlage, die breiter war als die Rechnung: "5 Buecher gezaehlt" unter
    einer Summe aus drei. Genau die Sorte Zahl, die stimmt aussieht.
    """

    GEMISCHT = [
        {"spur": "a", "n": 10, "ergebnis": 10.0, "treffer": 5,
         "waehrung": "USD", "live": False, "belastbar": True},
        {"spur": "b", "n": 9, "ergebnis": -5.0, "treffer": 4,
         "waehrung": "USD", "live": False, "belastbar": True},
        {"spur": "c", "n": 2, "ergebnis": 99.0, "treffer": 2,
         "waehrung": "USD", "live": False, "belastbar": False},
    ]

    def test_nur_die_summierten_werden_gezaehlt(self):
        with patch.object(gb, "posten", return_value=self.GEMISCHT):
            letzte = gb.bericht().splitlines()[-1]
        self.assertIn("2 Buecher", letzte)
        self.assertNotIn("3 Buecher", letzte)

    def test_die_zeile_sagt_worauf_sie_sich_bezieht(self):
        # "gezaehlt" liess offen, was gezaehlt wurde. Die Zeile steht
        # direkt unter der Summe und muss sich auf sie beziehen.
        with patch.object(gb, "posten", return_value=self.GEMISCHT):
            letzte = gb.bericht().splitlines()[-1]
        self.assertIn("in der Summe", letzte)

    def test_ohne_belastbaren_posten_steht_null(self):
        nur_schwach = [dict(self.GEMISCHT[2])]
        with patch.object(gb, "posten", return_value=nur_schwach):
            letzte = gb.bericht().splitlines()[-1]
        self.assertIn("0 Buecher", letzte)


if __name__ == "__main__":
    unittest.main()
