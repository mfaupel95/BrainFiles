"""Tests fuer kosten_korrelation.py - reine Rechenhilfen, ohne Netz."""

import importlib.util
import math
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("kk_modul", os.path.join(HIER, "..", "kosten_korrelation.py"))
kk = importlib.util.module_from_spec(spec)
sys.modules["kk_modul"] = kk
spec.loader.exec_module(kk)


class SaetzeTest(unittest.TestCase):
    REIHE = [(1000, 0.01), (2000, 0.02), (3000, -0.005), (4000, 0.03)]

    def test_intervall_ist_links_offen_rechts_geschlossen(self):
        self.assertAlmostEqual(kk.summe_saetze(self.REIHE, 1000, 3000), 0.02 - 0.005)
        self.assertAlmostEqual(kk.summe_saetze(self.REIHE, 999, 1000), 0.01)

    def test_ausserhalb_und_leer(self):
        self.assertEqual(kk.summe_saetze(self.REIHE, 5000, 9000), 0.0)
        self.assertEqual(kk.summe_saetze([], 0, 10), 0.0)

    def test_negativer_satz_zaehlt_mit(self):
        self.assertAlmostEqual(kk.summe_saetze(self.REIHE, 2000, 3000), -0.005)


class KorrelationTest(unittest.TestCase):
    def test_perfekt_und_gegenlaeufig(self):
        self.assertAlmostEqual(kk.korr([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertAlmostEqual(kk.korr([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)

    def test_konstante_reihe_ist_nan(self):
        self.assertTrue(math.isnan(kk.korr([1, 1, 1, 1], [1, 2, 3, 4])))

    def test_zu_kurz_ist_nan(self):
        self.assertTrue(math.isnan(kk.korr([1, 2], [1, 2])))


class ZeitTest(unittest.TestCase):
    def test_woche_und_jahr(self):
        self.assertEqual(kk.wochen(7 * 86400 * 1000), 1)
        self.assertEqual(kk.wochen(7 * 86400 * 1000 - 1), 0)
        self.assertEqual(kk.jahr(1672531200000), 2023)           # 01.01.2023
        self.assertEqual(kk.jahr(1672531199000), 2022)


class BreakEvenTest(unittest.TestCase):
    def test_r_kosten_eines_trades(self):
        # 10 Stunden gehalten, Satz 0,01 %/h, Stop 2 % -> 0,1 % / 2 % = 0,05 R
        saetze = [(h * 3600000, 0.0001) for h in range(1, 11)]
        f = kk.summe_saetze(saetze, 0, 10 * 3600000)
        self.assertAlmostEqual(f / 0.02, 0.05)


if __name__ == "__main__":
    unittest.main()
