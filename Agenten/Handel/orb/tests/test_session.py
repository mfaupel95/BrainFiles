import unittest
from datetime import date, datetime, timezone

import session

OKX = {"eroeffnung": "00:00", "zone": "UTC", "session_ende": "24:00"}


class TestEroeffnung(unittest.TestCase):
    def test_eroeffnung_ist_0000_utc(self):
        e = session.eroeffnung(OKX, date(2025, 7, 15))
        self.assertEqual(e, datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc))

    def test_eroeffnung_ist_dst_frei(self):
        e = session.eroeffnung(OKX, date(2025, 1, 15))
        self.assertEqual(e, datetime(2025, 1, 15, 0, 0, tzinfo=timezone.utc))


class TestFenster(unittest.TestCase):
    def test_opening_range_ist_erste_30_min(self):
        start, ende = session.opening_range_fenster(OKX, date(2025, 7, 15))
        self.assertEqual(start, datetime(2025, 7, 15, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(ende, datetime(2025, 7, 15, 0, 30, tzinfo=timezone.utc))

    def test_zwangsschluss_ist_naechster_tag_0000(self):
        z = session.zwangsschluss(OKX, date(2025, 7, 15))
        self.assertEqual(z, datetime(2025, 7, 16, 0, 0, tzinfo=timezone.utc))

    def test_letzter_einstieg_60_min_vor_schluss(self):
        le = session.letzter_einstieg(OKX, date(2025, 7, 15), 60)
        self.assertEqual(le, datetime(2025, 7, 15, 23, 0, tzinfo=timezone.utc))


class TestInSession(unittest.TestCase):
    def test_vor_range_ende_nicht_in_session(self):
        m = datetime(2025, 7, 15, 0, 15, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(OKX, m))

    def test_nach_range_vor_schluss_in_session(self):
        m = datetime(2025, 7, 15, 12, 0, tzinfo=timezone.utc)
        self.assertTrue(session.in_session(OKX, m))

    def test_waehrend_range_nicht_in_session(self):
        # Kurz vor Range-Ende (00:29) zaehlt noch nicht als Session.
        m = datetime(2025, 7, 15, 0, 29, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(OKX, m))


if __name__ == "__main__":
    unittest.main()