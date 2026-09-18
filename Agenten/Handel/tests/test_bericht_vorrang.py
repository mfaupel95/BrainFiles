"""Tests fuer die Vorrangregel des Tagesberichts."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import tagesbericht                                      # noqa: E402


def _e(name, positionen=(), sperren=(), still=False, fehler=None, wachen=None):
    return {"schluessel": name, "name": name, "waehrung": "USD",
            "positionen": list(positionen), "sperren": list(sperren),
            "stillgelegt": still, "wachen": wachen, "kennzahlen": None,
            "buchlage": "kein_buch", "buch_seit": None, "bilanz": None,
            "fehler": fehler, "roh": {}}


class VorrangTest(unittest.TestCase):
    def test_ausfall_ist_rang_eins(self):
        self.assertEqual(tagesbericht.rang(_e("a", fehler="kaputt"), {}), 1)

    def test_neue_sperre_ist_rang_eins(self):
        diff = {"sperre_neu": ["KILL-SWITCH erreicht"]}
        self.assertEqual(tagesbericht.rang(_e("a"), diff), 1)

    def test_stillgelegt_ist_rang_eins(self):
        self.assertEqual(tagesbericht.rang(_e("a", still=True), {}), 1)

    def test_herzschlag_alt_ist_rang_eins(self):
        e = _e("a", wachen={"herzschlag_frisch": False, "freigabe_erfuellt": True,
                            "kill": False, "ev_negativ": False})
        self.assertEqual(tagesbericht.rang(e, {}), 1)

    def test_offene_position_ist_rang_zwei(self):
        e = _e("a", positionen=[{"name": "BTC", "wert": 100, "einstieg": 1.0,
                                 "kurs": None, "vh": None, "stop": None,
                                 "seit": None}])
        self.assertEqual(tagesbericht.rang(e, {}), 2)

    def test_geschlossene_runde_ist_rang_zwei(self):
        self.assertEqual(tagesbericht.rang(_e("a"), {"runden_mehr": 2}), 2)

    def test_stille_spur_ist_rang_drei(self):
        self.assertEqual(tagesbericht.rang(_e("a"), {}), 3)


class SammelzeileTest(unittest.TestCase):
    def test_zaehlt_und_benennt(self):
        zeile = tagesbericht.sammelzeile([_e("macd_mtf"), _e("squeeze")])
        self.assertIn("2 Spuren still", zeile)
        self.assertIn("macd_mtf", zeile)
        self.assertIn("squeeze", zeile)

    def test_leere_liste_gibt_leeren_text(self):
        self.assertEqual(tagesbericht.sammelzeile([]), "")


if __name__ == "__main__":
    unittest.main()
