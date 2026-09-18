"""Tests fuer den Guthabenabgleich.

Kein Test geht ans Netz: der Kontostand wird uebergeben.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import guthaben_abgleich                                 # noqa: E402


class AbgleichTest(unittest.TestCase):
    def test_rest_ist_konto_minus_bilanz_minus_gebunden(self):
        a = guthaben_abgleich.abgleich("scanner", konto=1050.0, bilanz=30.0,
                                       gebunden=1000.0)
        self.assertAlmostEqual(a["rest"], 20.0)
        self.assertIsNone(a["fehler"])

    def test_ausgefallener_abruf_traegt_den_grund_statt_einer_zahl(self):
        def kaputt():
            raise OSError("Netz weg")
        a = guthaben_abgleich.abgleich("scanner", konto=kaputt, bilanz=0.0,
                                       gebunden=0.0)
        self.assertIsNone(a["rest"])
        self.assertIn("Netz weg", a["fehler"])

    def test_papierspur_ist_nicht_dabei(self):
        self.assertNotIn("swap", guthaben_abgleich.LIVE)

    def test_text_nennt_papierbuch_fuer_die_uebrigen(self):
        t = guthaben_abgleich.text(abgleiche=[
            {"spur": "scanner", "konto": 1050.0, "bilanz": 30.0,
             "gebunden": 1000.0, "rest": 20.0, "waehrung": "USD",
             "fehler": None}])
        self.assertIn("scanner", t)
        self.assertIn("Papierbuch", t)


if __name__ == "__main__":
    unittest.main()
