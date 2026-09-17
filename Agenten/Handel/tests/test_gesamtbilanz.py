"""Tests fuer die Gesamtbilanz.

Der gefaehrlichste Fehler dieses Umbaus ist eine Zahl, die stimmt aussieht
und nicht stimmt: EUR zu USD addiert, oder Papiergewinn mit echtem Geld
verrechnet. Beides steht hier als Test.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import gesamtbilanz as gb                                      # noqa: E402

POSTEN = [
    {"spur": "scanner", "n": 10, "ergebnis": 100.0, "treffer": 6,
     "waehrung": "USD", "live": True},
    {"spur": "swap", "n": 8, "ergebnis": -20.0, "treffer": 3,
     "waehrung": "USD", "live": False},
    {"spur": "kraken", "n": 12, "ergebnis": 50.0, "treffer": 7,
     "waehrung": "EUR", "live": False},
]


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


if __name__ == "__main__":
    unittest.main()
