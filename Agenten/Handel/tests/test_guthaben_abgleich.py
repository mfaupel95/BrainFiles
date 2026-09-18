"""Tests fuer den Guthabenabgleich.

Kein Test geht ans Netz: der Kontostand wird uebergeben.
"""
import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import auswertung_alle                                   # noqa: E402
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

    def test_fehlende_kennzahlen_ergeben_unbekannte_bilanz_statt_null(self):
        with patch.object(auswertung_alle, "kennzahlen_fuer", return_value=None):
            a = guthaben_abgleich.abgleich("scanner", konto=1000.0,
                                           gebunden=0.0)
        self.assertNotEqual(a["bilanz"], 0.0)
        self.assertTrue(a["bilanz_unbekannt"])
        self.assertIsNone(a["rest"])
        t = guthaben_abgleich.text(abgleiche=[a])
        self.assertIn("unbekannt", t)
        self.assertNotIn("Bilanz +0.00", t)

    def test_leere_boersenantwort_ergibt_unbekanntes_konto_statt_null(self):
        a = guthaben_abgleich.abgleich("scanner", konto=lambda: None,
                                       bilanz=0.0, gebunden=0.0)
        self.assertIsNone(a["fehler"])
        self.assertNotEqual(a["konto"], 0.0)
        self.assertTrue(a["konto_unbekannt"])
        self.assertIsNone(a["rest"])
        t = guthaben_abgleich.text(abgleiche=[a])
        self.assertIn("unbekannt", t)
        self.assertNotIn("Konto 0.00", t)

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
