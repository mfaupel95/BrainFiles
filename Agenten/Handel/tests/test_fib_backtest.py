"""Tests fuer fib_backtest.py - Simulationskern mit synthetischen Kerzen, ohne Netz."""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fib_bt_modul", os.path.join(HIER, "..", "fib_backtest.py"))
bt = importlib.util.module_from_spec(spec)
sys.modules["fib_bt_modul"] = bt
spec.loader.exec_module(bt)


def k(zeilen):
    """zeilen: (open, high, low, close) -> Kerzenliste."""
    return [[i, o, h, l, c, 1.0] for i, (o, h, l, c) in enumerate(zeilen)]


KEINE_REGEL = lambda j, seite: None


class LaufeTest(unittest.TestCase):
    def test_stop_vor_ziel_im_selben_balken(self):
        kerzen = k([(100, 100, 100, 100), (100, 110, 90, 100)])   # beide Marken im Balken
        t = bt.laufe(kerzen, 0, "long", 100, 95, 105, KEINE_REGEL, 0.0, 0.05)
        self.assertEqual(t["grund"], "stop")
        self.assertAlmostEqual(t["r"], -1.0)

    def test_ziel_in_r(self):
        kerzen = k([(100, 100, 100, 100), (100, 106, 99, 105)])
        t = bt.laufe(kerzen, 0, "long", 100, 95, 105, KEINE_REGEL, 0.0, 0.05)
        self.assertEqual(t["grund"], "ziel")
        self.assertAlmostEqual(t["r"], 1.0)

    def test_gebuehr_je_seite(self):
        kerzen = k([(100, 100, 100, 100), (100, 106, 99, 105)])
        t = bt.laufe(kerzen, 0, "long", 100, 95, 105, KEINE_REGEL, 0.001, 0.05)
        self.assertAlmostEqual(t["r"], (0.05 - 0.002) / 0.05)

    def test_gap_ueber_den_stop_fuellt_zum_open(self):
        kerzen = k([(100, 100, 100, 100), (90, 92, 88, 91)])
        t = bt.laufe(kerzen, 0, "long", 100, 95, 105, KEINE_REGEL, 0.0, 0.05)
        self.assertAlmostEqual(t["r"], -2.0)                       # -10 % bei 5 % Stop

    def test_short_gespiegelt(self):
        kerzen = k([(100, 100, 100, 100), (100, 101, 94, 95)])
        t = bt.laufe(kerzen, 0, "short", 100, 105, 95, KEINE_REGEL, 0.0, 0.05)
        self.assertEqual(t["grund"], "ziel")
        self.assertAlmostEqual(t["r"], 1.0)

    def test_regelausstieg(self):
        kerzen = k([(100, 100, 100, 100), (100, 101, 99, 101), (101, 102, 100, 102)])
        t = bt.laufe(kerzen, 0, "long", 100, 95, 110, lambda j, s: "gegensignal" if j == 2 else None,
                     0.0, 0.05)
        self.assertEqual(t["grund"], "gegensignal")
        self.assertAlmostEqual(t["r"], 0.4)


class SimuliereTest(unittest.TestCase):
    def test_signal_in_laufender_position_entfaellt(self):
        kerzen = k([(100, 100, 100, 100)] * 3 + [(100, 106, 99, 105)] + [(105, 105, 105, 105)] * 3)
        var = lambda i, s, kurs: (kurs * 0.95, kurs * 1.05, 0.05, 0.0)
        tr = bt.simuliere(kerzen, [(0, "long"), (1, "long"), (4, "long")], var, KEINE_REGEL)
        self.assertEqual([t["i"] for t in tr], [0, 4])

    def test_abgelehnt_zaehlt_nicht(self):
        kerzen = k([(100, 100, 100, 100)] * 3)
        self.assertEqual(bt.simuliere(kerzen, [(0, "long")], lambda *a: None, KEINE_REGEL), [])


class KennzahlTest(unittest.TestCase):
    def test_haelften_seiten_drawdown(self):
        tr = [{"i": 1, "seite": "long", "r": 2.0}, {"i": 2, "seite": "short", "r": -1.0},
              {"i": 8, "seite": "long", "r": -1.0}, {"i": 9, "seite": "long", "r": 3.0}]
        z = bt.kennzahlen(tr, 10)
        self.assertEqual(z["n"], 4)
        self.assertAlmostEqual(z["summe_r"], 3.0)
        self.assertAlmostEqual(z["h1"], 1.0)
        self.assertAlmostEqual(z["h2"], 2.0)
        self.assertAlmostEqual(z["short"], -1.0)
        self.assertAlmostEqual(z["dd"], 2.0)
        self.assertAlmostEqual(z["winrate"], 0.5)

    def test_leer(self):
        self.assertEqual(bt.kennzahlen([], 10)["n"], 0)


class BasisTest(unittest.TestCase):
    def test_basis_variante(self):
        f = bt.basis_variante({"stop_prozent": 2.0, "ziel_r_vielfaches": 2.0, "gebuehr_taker": 0.0005})
        stop, ziel, frac, gb = f(0, "long", 100.0)
        self.assertAlmostEqual(stop, 98.0)
        self.assertAlmostEqual(ziel, 104.0)
        self.assertAlmostEqual(frac, 0.02)
        stop, ziel, *_ = f(0, "short", 100.0)
        self.assertAlmostEqual((stop, ziel), (102.0, 96.0))


if __name__ == "__main__":
    unittest.main()
