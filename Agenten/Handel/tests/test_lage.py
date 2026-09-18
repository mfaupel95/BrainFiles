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


class BuchlageTest(unittest.TestCase):
    def test_kategorie_kein_buch_wenn_journal_fehlt(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel="gibtesnicht", tage=7)
        self.assertEqual(e["buchlage"], "kein_buch")
        self.assertIsNone(e["kennzahlen"])

    def test_zu_wenige_runden_zeigt_keine_zahl(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel=None, tage=7,
                         kennzahlen={"n": 2, "ergebnis": 5.0, "treffer": 1})
        self.assertEqual(e["buchlage"], "zu_wenige_runden")

    def test_belastbar_ab_min_runden(self):
        roh = {"name": "Testspur", "waehrung": "USD", "w": {}, "z": {},
               "positionen": []}
        e = lage.zu_lage(roh, schluessel=None, tage=7,
                         kennzahlen={"n": 12, "ergebnis": 5.0, "treffer": 7})
        self.assertEqual(e["buchlage"], "belastbar")

    def test_ausfall_einer_spur_bleibt_eine_zeile(self):
        def kaputt():
            raise RuntimeError("Journal unlesbar")
        kaputt.__name__ = "spur_kaputt"
        ergebnis = lage.erhebe(holer=(kaputt,), mit_xperp=False)
        self.assertEqual(len(ergebnis), 1)
        self.assertIn("Journal unlesbar", ergebnis[0]["fehler"])


if __name__ == "__main__":
    unittest.main()
