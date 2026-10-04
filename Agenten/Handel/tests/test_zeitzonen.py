"""Zeitzonen: UTC-Zeiten aus Journal/Datei werden UMGERECHNET, nie abgeschnitten.

Befund 30.09.2026: freigabefenster._zeit kappte "+00:00" auf naiv (UTC als
Ortszeit gelesen) und befehle zeigte die UTC-Uhrzeit des letzten Live-Vorgangs
neben Ortszeiten. Getestet mit gesetzter Zeitzone (tzset, nur POSIX) UND
plattformunabhaengig gegen die Umrechnung des Betriebssystems.
"""

import datetime as dt
import os
import sys
import time
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import befehle  # noqa: E402
import freigabefenster as fw  # noqa: E402


class _Zone:
    """Zeitzone fuer einen Test setzen (nur wo time.tzset existiert)."""

    def __init__(self, tz):
        self.tz = tz

    def __enter__(self):
        self.alt = os.environ.get("TZ")
        os.environ["TZ"] = self.tz
        time.tzset()

    def __exit__(self, *a):
        if self.alt is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = self.alt
        time.tzset()


def _ortszeit(iso):
    """Erwartung ueber die Betriebssystem-Umrechnung, ohne unsere Funktionen."""
    t = dt.datetime.fromisoformat(iso)
    return dt.datetime.fromtimestamp(t.timestamp())


class FreigabefensterZeitTest(unittest.TestCase):
    def test_utc_wird_umgerechnet_nicht_abgeschnitten(self):
        iso = "2026-07-01T08:15:00+00:00"
        self.assertEqual(fw._zeit(iso), _ortszeit(iso))

    def test_ergebnis_ist_naiv_und_vergleichbar(self):
        w = fw._zeit("2026-07-01T08:15:00+00:00")
        self.assertIsNone(w.tzinfo)
        self.assertIsInstance(w < fw._jetzt(), bool)      # kein TypeError

    def test_naive_zeit_bleibt_unveraendert(self):
        self.assertEqual(fw._zeit("2026-07-01T10:15:00"),
                         dt.datetime(2026, 7, 1, 10, 15))

    def test_kaputter_wert_wirft_nicht(self):
        for wert in (None, "", "gestern", 5):
            self.assertIsNone(fw._zeit(wert))

    @unittest.skipUnless(hasattr(time, "tzset"), "tzset gibt es nur auf POSIX")
    def test_berlin_sommer_plus_zwei_stunden(self):
        with _Zone("Europe/Berlin"):
            self.assertEqual(fw._zeit("2026-07-01T08:15:00+00:00"),
                             dt.datetime(2026, 7, 1, 10, 15))

    @unittest.skipUnless(hasattr(time, "tzset"), "tzset gibt es nur auf POSIX")
    def test_berlin_winter_plus_eine_stunde(self):
        with _Zone("Europe/Berlin"):
            self.assertEqual(fw._zeit("2026-01-15T08:15:00+00:00"),
                             dt.datetime(2026, 1, 15, 9, 15))


class BefehleAnzeigeTest(unittest.TestCase):
    def test_utc_journalzeit_wird_ortszeit(self):
        iso = "2026-07-01T08:15:00+00:00"
        self.assertEqual(befehle._zeit_ortszeit(iso),
                         _ortszeit(iso).strftime("%Y-%m-%d %H:%M"))

    def test_nur_datum_bekommt_keine_erfundene_uhrzeit(self):
        self.assertEqual(befehle._zeit_ortszeit("2026-07-01"), "2026-07-01")

    def test_unlesbar_faellt_auf_schneiden_zurueck(self):
        self.assertEqual(befehle._zeit_ortszeit("2026-07-01Z08:15:00"),
                         "2026-07-01 08:15")
        self.assertEqual(befehle._zeit_ortszeit("kaputt"), "kaputt")

    @unittest.skipUnless(hasattr(time, "tzset"), "tzset gibt es nur auf POSIX")
    def test_berlin_sommer(self):
        with _Zone("Europe/Berlin"):
            self.assertEqual(befehle._zeit_ortszeit("2026-07-01T08:15:00+00:00"),
                             "2026-07-01 10:15")


if __name__ == "__main__":
    unittest.main()
