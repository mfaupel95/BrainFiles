import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

W = {"trailing_stop_prozent": 0.4, "trailing_trigger_r": 1.0,
     "trailing_abstand_floor_pct": 0.25, "trailing_min_hub_r": 0.25,
     "trailing_max_halten_pct": 5.0}


def _long_pos(stop=90.0, ziel=110.0, liq=80.0):
    return {"inst": "AAA-X", "seite": "long", "einstieg": 100.0,
            "stop": stop, "ziel": ziel, "liq": liq, "stop_id": "ruecktest",
            "kontrakte": 1}


def _short_pos(stop=110.0, ziel=90.0, liq=120.0):
    return {"inst": "AAA-X", "seite": "short", "einstieg": 100.0,
            "stop": stop, "ziel": ziel, "liq": liq, "stop_id": "ruecktest",
            "kontrakte": 1}


class TestAusstiegsvorrang(unittest.TestCase):
    def test_docht_durch_stop_und_liq_ist_ein_stop_keine_liquidation(self):
        # Die Boerse loest den Stop beim Durchlaufen aus - bevor der Kurs die
        # Liquidationsmarke erreicht.
        p = _long_pos(stop=90.0, liq=80.0)
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 95.0, 96.0, 75.0, 94.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 90.0))

    def test_eroeffnung_hinter_der_liquidation_ist_liquidation(self):
        p = _long_pos(stop=90.0, liq=80.0)
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 78.0, 79.0, 70.0, 75.0, 1.0], W)
        self.assertEqual((grund, preis), ("LIQUIDATION", 78.0))

    def test_gap_durch_den_stop_fuellt_zum_eroeffnungskurs(self):
        p = _long_pos(stop=90.0, liq=80.0)
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 85.0, 86.0, 84.0, 85.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 85.0))

    def test_short_gap_durch_den_stop_fuellt_zum_eroeffnungskurs(self):
        p = _short_pos(stop=110.0, liq=120.0)
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 115.0, 116.0, 114.0, 115.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 115.0))

    def test_nachgezogener_stop_heisst_trailing_stop(self):
        p = _long_pos(ziel=200.0)
        rt.pruefe_ausstieg_1h(p, [0, 109.0, 111.0, 108.0, 110.0, 1.0], W)
        self.assertGreater(p["stop"], 90.0)
        grund, preis = rt.pruefe_ausstieg_1h(
            p, [0, 110.0, 110.5, 100.0, 101.0, 1.0], W)
        self.assertEqual(grund, "trailing_stop")
        self.assertEqual(preis, p["stop"])

    def test_stop_wenn_nur_stop_beruehrt(self):
        p = _long_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 95.0, 96.0, 85.0, 86.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 90.0))

    def test_ziel_wenn_nur_ziel_beruehrt(self):
        p = _long_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 105.0, 112.0, 104.0, 111.0, 1.0], W)
        self.assertEqual((grund, preis), ("ziel", 110.0))

    def test_stop_vor_ziel_wenn_beides_in_einer_kerze(self):
        p = _long_pos()
        grund, _ = rt.pruefe_ausstieg_1h(p, [0, 100.0, 115.0, 85.0, 100.0, 1.0], W)
        self.assertEqual(grund, "stop")

    def test_short_eroeffnung_hinter_der_liquidation(self):
        p = _short_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 125.0, 126.0, 110.0, 120.0, 1.0], W)
        self.assertEqual((grund, preis), ("LIQUIDATION", 125.0))

    def test_short_docht_durch_stop_und_liq_ist_ein_stop(self):
        p = _short_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 105.0, 125.0, 104.0, 120.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 110.0))

    def test_short_stop(self):
        p = _short_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 105.0, 111.0, 104.0, 106.0, 1.0], W)
        self.assertEqual((grund, preis), ("stop", 110.0))

    def test_short_ziel(self):
        p = _short_pos()
        grund, preis = rt.pruefe_ausstieg_1h(p, [0, 95.0, 96.0, 89.0, 91.0, 1.0], W)
        self.assertEqual((grund, preis), ("ziel", 90.0))

    def test_kein_ausstieg_zieht_long_trailing_nach(self):
        p = _long_pos(ziel=200.0)
        grund, _ = rt.pruefe_ausstieg_1h(p, [0, 109.0, 111.0, 108.0, 110.0, 1.0], W)
        self.assertIsNone(grund)
        self.assertGreater(p["stop"], 90.0)

    def test_kein_ausstieg_zieht_short_trailing_nach(self):
        p = _short_pos(ziel=10.0)
        grund, _ = rt.pruefe_ausstieg_1h(p, [0, 91.0, 92.0, 89.0, 90.0, 1.0], W)
        self.assertIsNone(grund)
        self.assertLess(p["stop"], 110.0)


if __name__ == "__main__":
    unittest.main()
