"""Tests fuer ausstieg_studie.py - Simulationskern und Hilfsreihen, ohne Netz."""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("studie_modul", os.path.join(HIER, "..", "ausstieg_studie.py"))
st = importlib.util.module_from_spec(spec)
sys.modules["studie_modul"] = st
spec.loader.exec_module(st)

KEINE = lambda j, s: None


def k(zeilen):
    return [[i * 14400000, o, h, l, c, 1.0] for i, (o, h, l, c) in enumerate(zeilen)]


class HilfsreihenTest(unittest.TestCase):
    def test_atr_nur_vergangenheit(self):
        kerzen = k([(10, 11, 9, 10)] * 20)
        a = st.atr_reihe(kerzen, 14)
        self.assertIsNone(a[12])
        self.assertAlmostEqual(a[13], 2.0)
        self.assertAlmostEqual(a[19], 2.0)

    def test_regime(self):
        kerzen = k([(1, 1, 1, float(i + 1)) for i in range(30)])           # steigend
        r = st.regime_reihe(kerzen, 10)
        self.assertIsNone(r[8])
        self.assertTrue(r[9] and r[29])
        fallend = k([(1, 1, 1, float(30 - i)) for i in range(30)])
        self.assertFalse(st.regime_reihe(fallend, 10)[29])

    def test_halbjahr(self):
        self.assertEqual(st.halbjahr(1672531200000), "2023-H1")      # 01.01.2023
        self.assertEqual(st.halbjahr(1688169600000), "2023-H2")      # 01.07.2023


class SicherungTest(unittest.TestCase):
    # Einstieg 100, Stop 95 (5 Punkte = 1R), Gebuehr 0 -> Boden = Einstand
    def lauf(self, kerzen, seite="long", **kw):
        einstieg = 100.0
        stop = 95.0 if seite == "long" else 105.0
        atr = st.atr_reihe(kerzen, 3)
        return st.laufe(kerzen, 0, seite, einstieg, stop, KEINE, 0.0, 0.05, atr, **kw)

    def test_kontrolle_wird_ausgestoppt(self):
        t = self.lauf(k([(100, 100, 100, 100), (100, 108, 100, 108), (108, 108, 94, 95)]))
        self.assertEqual(t["grund"], "stop")
        self.assertAlmostEqual(t["r"], -1.0)

    def test_boden_verhindert_verlust_nach_plus(self):
        # Kerze 1 schliesst bei 106 (>= 1R) -> Boden auf 100; Kerze 2 faellt auf 90
        t = self.lauf(k([(100, 100, 100, 100), (100, 106, 100, 106), (105, 105, 90, 92)]),
                      modus="boden", trigger_r=1.0)
        self.assertEqual(t["grund"], "sicherung")
        self.assertAlmostEqual(t["r"], 0.0)

    def test_boden_beruecksichtigt_gebuehr(self):
        kerzen = k([(100, 100, 100, 100), (100, 106, 100, 106), (105, 105, 90, 92)])
        atr = st.atr_reihe(kerzen, 3)
        t = st.laufe(kerzen, 0, "long", 100.0, 95.0, KEINE, 0.001, 0.05, atr,
                     modus="boden", trigger_r=1.0)
        self.assertAlmostEqual(t["r"], 0.0, places=6)                 # Boden = Einstand + 2 Gebuehren

    def test_ohne_plus_kein_trailing(self):
        # Schluss nie ueber 1R -> nicht scharf -> normaler Stop
        t = self.lauf(k([(100, 100, 100, 100), (100, 103, 99, 103), (103, 103, 94, 95)]),
                      modus="boden", trigger_r=1.0)
        self.assertEqual(t["grund"], "stop")
        self.assertAlmostEqual(t["r"], -1.0)

    def test_giveback_haelt_bruchteil(self):
        # Hoch 112, f=0.5 -> Stop 106; Kerze 2 faellt auf 104 -> Ausstieg bei 106 = +1.2R
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 112), (111, 111, 104, 105)])
        t = self.lauf(kerzen, modus="giveback", trigger_r=1.0, param=0.5)
        self.assertEqual(t["grund"], "sicherung")
        self.assertAlmostEqual(t["r"], (106 - 100) / 100 / 0.05)

    def test_stop_gilt_erst_ab_naechster_kerze(self):
        # Kerze 1 macht scharf UND faellt tief -> darf den neuen Stop nicht treffen
        t = self.lauf(k([(100, 100, 100, 100), (100, 112, 96, 112), (112, 113, 111, 112)]),
                      modus="giveback", trigger_r=1.0, param=0.5)
        self.assertNotEqual(t["bars"], 1)

    def test_stop_geht_nie_zurueck(self):
        kerzen = k([(100, 100, 100, 100), (100, 112, 100, 112), (112, 112, 110, 110),
                    (110, 110, 100, 101)])
        t = self.lauf(kerzen, modus="giveback", trigger_r=1.0, param=0.5)
        self.assertGreater(t["r"], 0.5)

    def test_short_gespiegelt(self):
        t = self.lauf(k([(100, 100, 100, 100), (100, 100, 94, 94), (95, 110, 95, 108)]),
                      seite="short", modus="boden", trigger_r=1.0)
        self.assertEqual(t["grund"], "sicherung")
        self.assertAlmostEqual(t["r"], 0.0)

    def test_atr_trail_folgt_dem_hoch(self):
        kerzen = k([(100, 101, 99, 100)] * 4 + [(100, 115, 100, 115), (115, 116, 100, 101)])
        atr = [None, None, 2.0, 2.0, 2.0, 2.0]
        t = st.laufe(kerzen, 3, "long", 100.0, 95.0, KEINE, 0.0, 0.05, atr,
                     modus="atr", trigger_r=1.0, param=3.0)
        # Hoch 115, Stop 115-3*2=109 -> Ausstieg bei 109
        self.assertAlmostEqual(t["r"], (109 - 100) / 100 / 0.05)


if __name__ == "__main__":
    unittest.main()
