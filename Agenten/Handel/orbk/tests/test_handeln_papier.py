import unittest
from datetime import date, datetime, timezone, timedelta

import handeln
import wachen_orb as wp

INST = {"kraken": "ETHUSD", "zone": "UTC", "eroeffnung": "00:00",
        "session_ende": "24:00", "spread_punkte": 0.1, "punkt_wert_usd": 1.0}
W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USD": 1.0},
     "max_range_punkte":     {"ETH_USD": 40.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "ziel_punkte": {"ETH_USD": 30},
     "instrument_aktiv": "ETH_USD",
     "instrumente": {"ETH_USD": INST}}


def _k(hh, mm, o, h, l, c):
    return {"zeit": datetime(2026, 9, 13, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c}


def _range_kerzen():
    # Range 00:00-00:30: hoch 100, tief 98
    return [_k(0, 0, 99, 100, 98, 99.5),
            _k(0, 15, 99.5, 100, 98, 99.8)]


class TestOpeningRange(unittest.TestCase):
    def test_hoch_tief_aus_ersten_zwei(self):
        hr = handeln.opening_range(_range_kerzen(), W, "ETH_USD", date(2026, 9, 13))
        self.assertEqual(hr, (100.0, 98.0))

    def test_none_bei_einer_kerze(self):
        self.assertIsNone(handeln.opening_range(
            [_k(0, 0, 99, 100, 98, 99.5)], W, "ETH_USD", date(2026, 9, 13)))


class TestBreakout(unittest.TestCase):
    def test_long_ueber_hoch(self):
        kerzen = _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertEqual(r, "long")
        self.assertEqual(kurs, 100.4)

    def test_short_unter_tief(self):
        kerzen = _range_kerzen() + [_k(0, 30, 97.8, 98.1, 97.5, 97.6)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertEqual(r, "short")
        self.assertEqual(kurs, 97.6)

    def test_kein_breakout(self):
        kerzen = _range_kerzen() + [_k(0, 30, 99.5, 99.9, 98.5, 99.6)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertIsNone(r)


class TestEinstieg(unittest.TestCase):
    def setUp(self):
        self.z = {"position": None, "letzter_lauf": None}
        handeln.kerzen_quelle = (
            lambda w, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])

    def tearDown(self):
        handeln.kerzen_quelle = None

    def test_kein_instrument_aktiv(self):
        w2 = dict(W, instrument_aktiv=None)
        m = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, w2, m)
        self.assertIsNone(e)
        self.assertIn("instrument_aktiv", meldung)

    def test_range_laeuft_noch(self):
        m = datetime(2026, 9, 13, 0, 15, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, W, m)
        self.assertIsNone(e)
        self.assertIn("Range laeuft", meldung)

    def test_long_einstieg(self):
        m = datetime(2026, 9, 13, 0, 45, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, W, m)
        self.assertEqual(e, "papier")
        p = self.z["position"]
        self.assertEqual(p["richtung"], "long")
        self.assertEqual(p["stop"], 98.0)
        self.assertEqual(p["ziel"], 100.4 + 1.5 * 2.0)


class TestAusstiege(unittest.TestCase):
    def test_stop_long(self):
        z = {"position": {"inst": "ETH_USD", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 97.5}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop")
        self.assertEqual(z["position"]["ausgang"], "stop")

    def test_ziel_long(self):
        z = {"position": {"inst": "ETH_USD", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 103.5}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W)
        self.assertEqual(grund, "ziel")

    def test_offen_bleibt(self):
        z = {"position": {"inst": "ETH_USD", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 101.0}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W)
        self.assertFalse(veraendert)
        self.assertIsNone(grund)

    def test_tag_als_iso_string_aus_zustand(self):
        # zustand.json speichert tag als ISO-String - pruefe_ausstiege muss
        # das parsen (der Fehler vom 13.09.2026: TypeError im Dauerlauf).
        z = {"position": {"inst": "ETH_USD", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": "2026-09-13", "letzter_kurs": 101.0}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W)
        self.assertFalse(veraendert)
        self.assertIsNone(grund)


if __name__ == "__main__":
    unittest.main()