"""maker_preis: Limit kreuzt nie den Spread (11.10.2026)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import okxf  # noqa: E402


class MakerPreis(unittest.TestCase):
    def test_kauf_ueber_ask_wird_bid(self):
        self.assertEqual(okxf.maker_preis("buy", 101.0, 99.9, 100.0), 99.9)

    def test_kauf_unter_ask_bleibt(self):
        self.assertEqual(okxf.maker_preis("buy", 99.5, 99.9, 100.0), 99.5)

    def test_verkauf_unter_bid_wird_ask(self):
        self.assertEqual(okxf.maker_preis("sell", 99.0, 99.9, 100.0), 100.0)

    def test_verkauf_ueber_bid_bleibt(self):
        self.assertEqual(okxf.maker_preis("sell", 100.5, 99.9, 100.0), 100.5)

    def test_ohne_spanne_unveraendert(self):
        self.assertEqual(okxf.maker_preis("buy", 101.0, None, None), 101.0)

    def test_nie_schlechter_als_zone(self):
        for p in (98.0, 99.95, 100.0, 103.0):
            self.assertLessEqual(okxf.maker_preis("buy", p, 99.9, 100.0), p)
            self.assertGreaterEqual(okxf.maker_preis("sell", p, 99.9, 100.0), p)


if __name__ == "__main__":
    unittest.main()
