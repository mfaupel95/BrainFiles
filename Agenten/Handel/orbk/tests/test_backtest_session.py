import unittest
from datetime import date, datetime, timezone, timedelta

import backtest

INST = {"eroeffnung": "00:00", "zone": "UTC", "session_ende": "24:00"}
W = {"letzter_einstieg_min_vor_schluss": 90,
     "mindest_range_punkte": {"X": 5}, "max_range_punkte": {"X": 500},
     "ziel_modus": "r_vielfaches", "ziel_k": 2.0,
     "ziel_punkte": {"X": 40},
     "instrumente": {"X": INST}}


def _k(hh, mm, o, h, l, c, tag=date(2025, 7, 15)):
    return {"zeit": datetime(tag.year, tag.month, tag.day, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c, "complete": True}


def _session_long_ziel():
    # Range 00:00-00:30 UTC (UTC-Tagesgrenze): hoch 18010, tief 17990
    return [
        _k(0, 0, 18000, 18008, 17992, 18004),
        _k(0, 15, 18004, 18010, 17990, 18006),
        _k(0, 30, 18006, 18012, 18004, 18011),   # schliesst > hoch 18010 -> Long-Einstieg
        _k(0, 45, 18011, 18040, 18009, 18035),   # laeuft Richtung Ziel
        _k(1, 0, 18035, 18055, 18033, 18052),    # Ziel 18011 + 2*(18011-17990)=18051 getroffen
    ]


def _session_short_ziel():
    # Spiegelbild: Range hoch 110, tief 90; Ausbruchskerze schliesst unter tief -> Short.
    return [
        _k(0, 0, 100, 105, 95, 100),
        _k(0, 15, 100, 110, 90, 100),            # Range hoch 110, tief 90
        _k(0, 30, 100, 101, 88, 89),             # schliesst < tief 90 -> Short-Einstieg bei 89
        _k(0, 45, 89, 90, 60, 65),               # laeuft Richtung Ziel
        _k(1, 0, 65, 66, 40, 45),                # Ziel 89 - 2*20 = 49 getroffen (Tief 45)
    ]


class TestOpeningRange(unittest.TestCase):
    def test_hoch_tief_aus_ersten_zwei(self):
        s = _session_long_ziel()
        hr = backtest.opening_range(s, INST, date(2025, 7, 15))
        self.assertEqual(hr, (18010.0, 17990.0))

    def test_none_bei_einer_kerze(self):
        self.assertIsNone(backtest.opening_range([_k(0, 0, 1, 2, 0, 1)], INST, date(2025, 7, 15)))


class TestSimuliere(unittest.TestCase):
    def test_long_bis_ziel(self):
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["richtung"], "long")
        self.assertEqual(r["einstieg"], 18011.0)      # Schlusskurs der Breakout-Kerze
        self.assertEqual(r["stop"], 17990.0)          # Gegenseite der Range
        self.assertEqual(r["ziel"], 18051.0)          # einstieg + k*range_hoehe
        self.assertEqual(r["ausgang"], "ziel")
        self.assertGreater(r["gv_punkte"], 0)

    def test_stop_vor_ziel_gleiche_kerze_ist_stop(self):
        s = [
            _k(0, 0, 100, 105, 95, 100),
            _k(0, 15, 100, 110, 90, 101),            # Range hoch 110, tief 90
            _k(0, 30, 101, 112, 99, 111),            # Long-Einstieg bei 111, Stop 90
            _k(0, 45, 111, 155, 85, 120),            # beruehrt Ziel 151 UND Stop 90 -> Stop
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["ausgang"], "stop")
        self.assertTrue(r["mehrdeutig"])
        self.assertLess(r["gv_punkte"], 0)

    def test_kein_breakout_gibt_none(self):
        s = [_k(0, 0, 100, 110, 90, 100), _k(0, 15, 100, 108, 92, 100),
             _k(0, 30, 100, 112, 88, 105), _k(0, 45, 105, 113, 87, 104)]
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))

    def test_range_zu_klein_gibt_none(self):
        w2 = dict(W, mindest_range_punkte={"X": 50})
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), w2, "schluss")
        self.assertIsNone(r)

    def test_breakout_nach_letztem_einstieg_gibt_none(self):
        # Zwangsschluss 24:00 UTC, letzter Einstieg 22:30 UTC (90 min vorher)
        s = [_k(0, 0, 100, 110, 90, 100), _k(0, 15, 100, 110, 90, 100),
             _k(23, 0, 100, 130, 99, 121)]   # Breakout erst 23:00 -> zu spaet
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))

    def test_short_bis_ziel(self):
        r = backtest.simuliere_session(_session_short_ziel(), INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["richtung"], "short")
        self.assertEqual(r["einstieg"], 89.0)         # Schlusskurs der Breakout-Kerze
        self.assertEqual(r["stop"], 110.0)            # Gegenseite der Range (hoch)
        self.assertEqual(r["ziel"], 49.0)            # einstieg - k*range_hoehe
        self.assertEqual(r["ausgang"], "ziel")
        self.assertGreater(r["gv_punkte"], 0)         # 89 - 49 = 40

    def test_short_stop(self):
        s = [
            _k(0, 0, 100, 105, 95, 100),
            _k(0, 15, 100, 110, 90, 100),            # Range hoch 110, tief 90
            _k(0, 30, 100, 101, 88, 89),             # Short-Einstieg bei 89, Stop 110
            _k(0, 45, 89, 130, 88, 125),             # laeuft hoch durch den Stop 110
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["richtung"], "short")
        self.assertEqual(r["ausgang"], "stop")
        self.assertEqual(r["ausstieg"], 110.0)
        self.assertLess(r["gv_punkte"], 0)            # 89 - 110 = -21


class TestPruefKerzenGrenze(unittest.TestCase):
    """Nur gehaltene Kerzen zaehlen: schluss ab der Kerze NACH dem Ausbruch,
    naechste_eroeffnung ab der Fuellkerze selbst."""

    def test_schluss_ignoriert_docht_der_ausbruchskerze(self):
        s = [
            _k(0, 0, 100, 105, 95, 100),
            _k(0, 15, 100, 110, 90, 100),           # Range hoch 110, tief 90
            _k(0, 30, 100, 112, 85, 111),           # Long-Einstieg 111; eigenes Tief 85
            _k(0, 45, 111, 160, 111, 155),          # Hoch 160 >= Ziel 151
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["einstieg"], 111.0)
        self.assertEqual(r["ziel"], 151.0)
        self.assertEqual(r["ausgang"], "ziel")       # Docht der Ausbruchskerze zaehlt nicht
        self.assertGreater(r["gv_punkte"], 0)

    def test_naechste_eroeffnung_prueft_die_fuellkerze(self):
        s = [
            _k(0, 0, 100, 105, 95, 100),
            _k(0, 15, 100, 110, 90, 100),           # Range hoch 110, tief 90
            _k(0, 30, 100, 112, 99, 111),           # Long-Ausbruch (Schluss 111)
            _k(0, 45, 111, 112, 80, 95),            # Fuellkerze: Open 111, Tief 80 <= Stop 90
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "naechste_eroeffnung")
        self.assertEqual(r["einstieg"], 111.0)       # Open der Fuellkerze
        self.assertEqual(r["ausgang"], "stop")       # Fuellkerze wird geprueft
        self.assertEqual(r["ausstieg"], 90.0)
        self.assertLess(r["gv_punkte"], 0)           # 90 - 111 = -21


if __name__ == "__main__":
    unittest.main()