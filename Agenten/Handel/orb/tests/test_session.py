import unittest
from datetime import date, datetime, timezone

import session

DE30 = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}
US30 = {"eroeffnung": "15:30", "zone": "Europe/Berlin", "cash_close": "22:00"}


class TestEroeffnung(unittest.TestCase):
    def test_de30_sommer_ist_0700_utc(self):
        # 15. Juli: Europe/Berlin = UTC+2 -> 09:00 lokal = 07:00 UTC
        e = session.eroeffnung(DE30, date(2025, 7, 15))
        self.assertEqual(e, datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc))

    def test_de30_winter_ist_0800_utc(self):
        # 15. Januar: Europe/Berlin = UTC+1 -> 09:00 lokal = 08:00 UTC
        e = session.eroeffnung(DE30, date(2025, 1, 15))
        self.assertEqual(e, datetime(2025, 1, 15, 8, 0, tzinfo=timezone.utc))

    def test_us30_sommer_ist_1330_utc(self):
        e = session.eroeffnung(US30, date(2025, 7, 15))
        self.assertEqual(e, datetime(2025, 7, 15, 13, 30, tzinfo=timezone.utc))


class TestFenster(unittest.TestCase):
    def test_opening_range_ist_erste_30_min(self):
        start, ende = session.opening_range_fenster(DE30, date(2025, 7, 15))
        self.assertEqual(start, datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc))
        self.assertEqual(ende, datetime(2025, 7, 15, 7, 30, tzinfo=timezone.utc))

    def test_zwangsschluss_de30_sommer(self):
        z = session.zwangsschluss(DE30, date(2025, 7, 15))
        self.assertEqual(z, datetime(2025, 7, 15, 15, 30, tzinfo=timezone.utc))

    def test_letzter_einstieg_90_min_vor_schluss(self):
        le = session.letzter_einstieg(DE30, date(2025, 7, 15), 90)
        self.assertEqual(le, datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc))


class TestInSession(unittest.TestCase):
    def test_vor_range_ende_nicht_in_session(self):
        m = datetime(2025, 7, 15, 7, 15, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(DE30, m))

    def test_nach_range_vor_schluss_in_session(self):
        m = datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(session.in_session(DE30, m))

    def test_nach_zwangsschluss_nicht_in_session(self):
        m = datetime(2025, 7, 15, 16, 0, tzinfo=timezone.utc)
        self.assertFalse(session.in_session(DE30, m))
