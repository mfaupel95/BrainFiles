"""Tests fuer den Wochenbericht."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import wochenbericht                                     # noqa: E402


class VerlaufTest(unittest.TestCase):
    def test_vier_fenster_vier_eintraege(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return {"n": 10, "ergebnis": 1.0, "treffer": 6}

        v = wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        self.assertEqual(len(v), 4)
        self.assertEqual(len(gerufen), 4)

    def test_fenster_liegen_hintereinander_und_ueberlappen_nicht(self):
        gerufen = []

        def fake(spur, von=None, bis=None):
            gerufen.append((von, bis))
            return None

        wochenbericht.verlauf("scanner", kennzahlen_fn=fake)
        for juenger, aelter in zip(gerufen, gerufen[1:]):
            self.assertLessEqual(aelter[1], juenger[0])


class SummenTest(unittest.TestCase):
    def test_waehrungen_werden_nicht_stumm_addiert(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "kraken", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "EUR", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("USD", text)
        self.assertIn("EUR", text)
        self.assertNotIn("+10.00", text)     # keine Summe ueber beide

    def test_papier_und_live_bleiben_getrennt(self):
        posten = [
            {"spur": "scanner", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": True, "belastbar": True},
            {"spur": "swap", "n": 10, "ergebnis": 5.0, "treffer": 6,
             "waehrung": "USD", "live": False, "belastbar": True},
        ]
        text = wochenbericht.bilanzteil(posten)
        self.assertIn("Live", text)
        self.assertIn("Papier", text)


if __name__ == "__main__":
    unittest.main()
