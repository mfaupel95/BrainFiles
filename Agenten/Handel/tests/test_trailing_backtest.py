"""Tests fuer trailing_backtest.py - Simulationskern, synthetische Kerzen, ohne Netz."""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("trail_bt_modul", os.path.join(HIER, "..", "trailing_backtest.py"))
tb = importlib.util.module_from_spec(spec)
sys.modules["trail_bt_modul"] = tb
spec.loader.exec_module(tb)


def k(zeilen):
    return [[i, o, h, l, c, 1.0] for i, (o, h, l, c) in enumerate(zeilen)]


KEINE = lambda j, s: None


class TrailingTest(unittest.TestCase):
    # Einstieg 100, Stop 95 (5 R-Einheiten = 5 Punkte), stop_frac 0.05
    def test_ohne_trailing_bleibt_der_stop_fest(self):
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 112), (112, 112, 94, 96)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05)
        self.assertEqual(t["grund"], "stop")
        self.assertAlmostEqual(t["r"], -1.0)

    def test_trailing_sichert_gewinn(self):
        # Kerze 1: Schluss 110 (= 2R), Hoch 112 -> Stop 112 - 1 % = 110,88; Kerze 2 faellt darunter
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 112), (111.5, 111.6, 105, 106)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=1.0, floor_pct=0.0, min_hub_r=0.0)
        self.assertEqual(t["grund"], "trail")
        self.assertAlmostEqual(t["r"], (112 * 0.99 - 100) / 100 / 0.05)

    def test_stop_gilt_erst_ab_naechster_kerze(self):
        # Trigger und Ruecksetzer in derselben Kerze 1 duerfen den neuen Stop nicht treffen
        kerzen = k([(100, 100, 100, 100), (100, 112, 98, 110), (110, 110, 109, 109)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=1.0, floor_pct=0.0, min_hub_r=0.0)
        self.assertNotEqual(t["bars"], 1)

    def test_gap_ueber_den_nachgezogenen_stop_fuellt_zum_open(self):
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 110), (110, 111, 105, 106)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=1.0, floor_pct=0.0, min_hub_r=0.0)
        self.assertAlmostEqual(t["r"], 2.0)          # Open 110 < Stop 110,88

    def test_dokumentierte_kappung_halten_klein_bleibt_klein(self):
        # halten 0,4 % darf NICHT auf max_halten (5 %) aufgeweitet werden
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 112), (111.9, 112, 108, 108)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=0.4, floor_pct=0.0, min_hub_r=0.0)
        self.assertEqual(t["grund"], "trail")
        self.assertAlmostEqual(t["r"], (112 * 0.996 - 100) / 100 / 0.05)

    def test_stop_geht_nie_zurueck(self):
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 111), (111, 111, 108, 108),
                    (108, 108, 90, 90)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=1.0, floor_pct=0.0, min_hub_r=0.0)
        self.assertGreater(t["r"], 0)            # Stop blieb bei ~110,9, nicht zurueck bei 95

    def test_short_gespiegelt(self):
        kerzen = k([(100, 100, 100, 100), (100, 100, 88, 88), (88.5, 95, 88.4, 94)])
        t = tb.laufe_trailing(kerzen, 0, "short", 100, 105, None, KEINE, 0.0, 0.05,
                              trigger_r=1.0, halten_pct=1.0, floor_pct=0.0, min_hub_r=0.0)
        self.assertEqual(t["grund"], "trail")
        self.assertAlmostEqual(t["r"], (100 - 88 * 1.01) / 100 / 0.05)

    def test_breakeven(self):
        kerzen = k([(100, 100, 100, 100), (100, 106, 100, 106), (106, 106, 99, 100)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None, KEINE, 0.0, 0.05, breakeven_r=1.0)
        self.assertAlmostEqual(t["r"], 0.0)

    def test_ziel_bleibt_wirksam(self):
        kerzen = k([(100, 100, 100, 100), (100, 111, 100, 105)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, 110, KEINE, 0.0, 0.05)
        self.assertEqual(t["grund"], "ziel")
        self.assertAlmostEqual(t["r"], 2.0)

    def test_regelausstieg(self):
        kerzen = k([(100, 100, 100, 100), (100, 101, 99, 101), (101, 103, 100, 103)])
        t = tb.laufe_trailing(kerzen, 0, "long", 100, 95, None,
                              lambda j, s: "gegensignal" if j == 2 else None, 0.0, 0.05)
        self.assertEqual(t["grund"], "gegensignal")


if __name__ == "__main__":
    unittest.main()
