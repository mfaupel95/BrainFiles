"""Tests: Stop-Luecke sperrt neue Live-Einstiege (Variante A, 09.10.2026)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR.parent))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

assert h.__file__.startswith(str(SPUR)), "falsches handeln: %s" % h.__file__


class Stopluecke(unittest.TestCase):
    def setUp(self):
        p = patch.object(h.ereignis, "hinweis")
        self.hinweis = p.start()
        self.addCleanup(p.stop)

    def test_luecke_live_sperrt_und_meldet_einmal(self):
        z = {}
        stand = {"deckung": 2, "deckung_abfrage": True}
        self.assertTrue(h.stopluecken_sperre(z, stand, live=True))
        self.assertTrue(h.stopluecken_sperre(z, stand, live=True))
        self.assertEqual(self.hinweis.call_count, 1)

    def test_abfrage_nicht_lesbar_sperrt_nicht(self):
        z = {}
        stand = {"deckung": 0, "deckung_abfrage": False}
        self.assertFalse(h.stopluecken_sperre(z, stand, live=True))
        self.hinweis.assert_not_called()

    def test_papier_sperrt_nicht(self):
        stand = {"deckung": 3, "deckung_abfrage": True}
        self.assertFalse(h.stopluecken_sperre({}, stand, live=False))
        self.hinweis.assert_not_called()

    def test_luecke_geschlossen_gibt_frei_und_meldet(self):
        z = {"stopluecke_gemeldet": True}
        stand = {"deckung": 0, "deckung_abfrage": True}
        self.assertFalse(h.stopluecken_sperre(z, stand, live=True))
        self.assertFalse(z["stopluecke_gemeldet"])
        self.assertEqual(self.hinweis.call_count, 1)

    def test_abfragefehler_loescht_den_merker_nicht(self):
        z = {"stopluecke_gemeldet": True}
        stand = {"deckung": 0, "deckung_abfrage": False}
        self.assertFalse(h.stopluecken_sperre(z, stand, live=True))
        self.assertTrue(z["stopluecke_gemeldet"])
        self.hinweis.assert_not_called()


if __name__ == "__main__":
    unittest.main()
