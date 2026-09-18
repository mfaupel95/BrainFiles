"""Tests fuer die Erhebungsschicht."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import lage                                              # noqa: E402


class FormTest(unittest.TestCase):
    def test_jeder_holer_liefert_die_pflichtfelder(self):
        for hole in lage.HOLER:
            with self.subTest(spur=hole.__name__):
                try:
                    s = hole()
                except Exception as e:                   # noqa: BLE001
                    self.fail("%s ist ausgefallen: %s" % (hole.__name__, e))
                for feld in ("name", "waehrung", "w", "positionen"):
                    self.assertIn(feld, s, hole.__name__)
                self.assertIsInstance(s["positionen"], list)

    def test_holer_sind_vollzaehlig(self):
        self.assertEqual(len(lage.HOLER), 24)


if __name__ == "__main__":
    unittest.main()
