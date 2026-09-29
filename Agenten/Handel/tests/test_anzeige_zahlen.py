"""Anzeige-Tests fuer den Tagesbericht (T-111): Zahlen lesbar, Token gekuerzt.

Befund 25.09.2026: Robinhood-Radar und Moon-Dev Sniper standen als
"0x48f413c32a7b... long 4.258775833450569e-05 (kein Kurs)" im Bericht - die
Zahl war richtig, aber niemand liest eine Exponentialschreibweise, und der
Token sprengte die Spalte. Geprueft wird die REGEL, nicht ein Tageswert.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..", "scanner")))

import tagesbericht as tb                                            # noqa: E402


class ZahlTest(unittest.TestCase):

    def test_keine_exponentialschreibweise(self):
        for x in (4.258775833450569e-05, 1e-9, 1234.5678, 0.000123456789):
            s = tb._zahl(x)
            self.assertNotIn("e", s.lower(), "%r wurde als %s ausgegeben" % (x, s))

    def test_kleine_preise_behalten_vier_ziffern(self):
        self.assertEqual("0.00004259", tb._zahl(4.258775833450569e-05))
        self.assertTrue(tb._zahl(1e-9).startswith("0.000000001"))

    def test_grosse_werte_werden_gerundet(self):
        self.assertEqual("75726.4", tb._zahl(75726.4))
        self.assertEqual("1234.57", tb._zahl(1234.5678))

    def test_null_und_none(self):
        self.assertEqual("0", tb._zahl(0))
        self.assertEqual("-", tb._zahl(None))


class KurzTest(unittest.TestCase):

    def test_langer_token_wird_gekuerzt(self):
        lang = "0x48f413c32a7b9e1f2a3b4c5d6e7f8a9b0c1d2e3f"
        s = tb._kurz(lang)
        self.assertLessEqual(len(s), 16)
        self.assertTrue(s.endswith("\u2026"))
        self.assertTrue(lang.startswith(s[:-1]))

    def test_kurzer_name_bleibt(self):
        self.assertEqual("BTC-USDC", tb._kurz("BTC-USDC"))


class ZeilePositionTest(unittest.TestCase):

    def test_zeile_ohne_kurs_ist_lesbar(self):
        p = {"name": "0x48f413c32a7b9e1f2a3b4c5d6e7f8a9b0c1d2e3f",
             "einstieg": 4.258775833450569e-05, "kurs": None}
        z = tb.zeile_position(p, "USD")
        self.assertNotIn("e", z.split("0x")[1].lower().split()[1],
                         "Exponentialschreibweise in der Zeile: %s" % z)
        self.assertIn("0.00004259", z)
        self.assertIn("(kein Kurs)", z)


if __name__ == "__main__":
    unittest.main()
