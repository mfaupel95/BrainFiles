import unittest
from datetime import date, datetime, timezone, timedelta

import backtest

INST = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}
W = {"letzter_einstieg_min_vor_schluss": 90,
     "mindest_range_punkte": {"X": 5}, "max_range_punkte": {"X": 500},
     "ziel_modus": "r_vielfaches", "ziel_k": 2.0,
     "ziel_punkte": {"X": 40},
     "instrumente": {"X": INST}}


def _k(hh, mm, o, h, l, c, tag=date(2025, 7, 15)):
    return {"zeit": datetime(tag.year, tag.month, tag.day, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c, "complete": True}


def _session_long_ziel():
    # Range 07:00-07:30 UTC (= 09:00 Berlin Sommer): hoch 18010, tief 17990
    return [
        _k(7, 0, 18000, 18008, 17992, 18004),
        _k(7, 15, 18004, 18010, 17990, 18006),
        _k(7, 30, 18006, 18012, 18004, 18011),   # schliesst > hoch 18010 -> Long-Einstieg
        _k(7, 45, 18011, 18040, 18009, 18035),   # laeuft Richtung Ziel
        _k(8, 0, 18035, 18055, 18033, 18052),    # Ziel 18010 + 2*(18010-17990)=18050 getroffen
    ]


class TestOpeningRange(unittest.TestCase):
    def test_hoch_tief_aus_ersten_zwei(self):
        s = _session_long_ziel()
        hr = backtest.opening_range(s, INST, date(2025, 7, 15))
        self.assertEqual(hr, (18010.0, 17990.0))

    def test_none_bei_einer_kerze(self):
        self.assertIsNone(backtest.opening_range([_k(7, 0, 1, 2, 0, 1)], INST, date(2025, 7, 15)))


class TestSimuliere(unittest.TestCase):
    def test_long_bis_ziel(self):
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["richtung"], "long")
        self.assertEqual(r["einstieg"], 18011.0)      # Schlusskurs der Breakout-Kerze
        self.assertEqual(r["stop"], 17990.0)          # Gegenseite der Range
        self.assertEqual(r["ziel"], 18051.0)          # 18011 + 2*(18011-17990)? nein: k*range ab Einstieg
        self.assertEqual(r["ausgang"], "ziel")
        self.assertGreater(r["gv_punkte"], 0)

    def test_stop_vor_ziel_gleiche_kerze_ist_stop(self):
        s = [
            _k(7, 0, 100, 105, 95, 100),
            _k(7, 15, 100, 110, 90, 101),            # Range hoch 110, tief 90
            _k(7, 30, 101, 112, 99, 111),            # Long-Einstieg bei 111, Stop 90
            _k(7, 45, 111, 155, 85, 120),            # beruehrt Ziel 151 UND Stop 90 -> Stop
        ]
        r = backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss")
        self.assertEqual(r["ausgang"], "stop")
        self.assertTrue(r["mehrdeutig"])
        self.assertLess(r["gv_punkte"], 0)

    def test_kein_breakout_gibt_none(self):
        s = [_k(7, 0, 100, 101, 99, 100), _k(7, 15, 100, 101, 99, 100),
             _k(7, 30, 100, 100.5, 99.5, 100), _k(7, 45, 100, 100.5, 99.5, 100)]
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))

    def test_range_zu_klein_gibt_none(self):
        w2 = dict(W, mindest_range_punkte={"X": 50})
        r = backtest.simuliere_session(_session_long_ziel(), INST, date(2025, 7, 15), w2, "schluss")
        self.assertIsNone(r)

    def test_breakout_nach_letztem_einstieg_gibt_none(self):
        # Zwangsschluss 15:30 UTC, letzter Einstieg 14:00 UTC
        s = [_k(7, 0, 100, 110, 90, 100), _k(7, 15, 100, 110, 90, 100),
             _k(14, 15, 100, 130, 99, 121)]   # Breakout erst 14:15 -> zu spaet
        self.assertIsNone(backtest.simuliere_session(s, INST, date(2025, 7, 15), W, "schluss"))


if __name__ == "__main__":
    unittest.main()
