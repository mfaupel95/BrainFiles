"""Kraken als zweiter Orderweg fuer mosaic.

Zwei Dinge werden geprueft:
  1. die Uebersetzung der Instrumente (OKX-Name -> Kraken-Paar) - ein unbekanntes
     Paar muss LAUT scheitern, nicht still im falschen Markt landen,
  2. die Bindung des Live-Wegs: `boerse` in der wachen.json waehlt das Modul, und
     die Sperrenkette fragt die gewaehlte Boerse (Schluessel, Demo, Guthaben in
     der richtigen Waehrung).

Kein Test stellt eine Order. Die Test-Seams von handeln.py (`op_*`) und die
Boersenmodule selbst werden ersetzt.
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parent.parent
HANDEL = SPUR.parent
sys.path.insert(0, str(SPUR))
assert (SPUR / "handeln.py").is_file()


def lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


handeln = lade("mosaic_handeln", SPUR / "handeln.py")
kraken_spot = lade("mosaic_kraken_spot", SPUR / "kraken_spot.py")


class PaarAbbildungTest(unittest.TestCase):

    def test_bekannte_instrumente(self):
        self.assertEqual(kraken_spot.paar_fuer("BTC-USDC"), "XXBTZEUR")
        self.assertEqual(kraken_spot.paar_fuer("eth-usdt"), "XETHZEUR")
        self.assertEqual(kraken_spot.paar_fuer(" SOL-USDC "), "SOLEUR")

    def test_unbekanntes_paar_scheitert_laut(self):
        """Sonst landet die Order im falschen Markt - schlimmer als ein Fehler."""
        with self.assertRaises(ValueError):
            kraken_spot.paar_fuer("DOGE-USDC")


class MengeTest(unittest.TestCase):

    def setUp(self):
        self.orig = kraken_spot.kraken.paar_info

    def tearDown(self):
        kraken_spot.kraken.paar_info = self.orig

    def test_mindestmenge_wird_gemeldet(self):
        kraken_spot.kraken.paar_info = lambda paar: {
            "name": "XBT/EUR", "preis_stellen": 1, "mengen_stellen": 8,
            "mindestmenge": 0.0001, "mindestwert": 5.0, "gegen": "ZEUR"}
        menge, fehler = kraken_spot.menge_fuer("BTC-USDC", 1.0, 80000.0)
        self.assertEqual(menge, 0.0)
        self.assertIsNotNone(fehler)

    def test_gute_menge_hat_keinen_fehler(self):
        kraken_spot.kraken.paar_info = lambda paar: {
            "name": "XBT/EUR", "preis_stellen": 1, "mengen_stellen": 8,
            "mindestmenge": 0.0001, "mindestwert": 5.0, "gegen": "ZEUR"}
        menge, fehler = kraken_spot.menge_fuer("BTC-USDC", 20.0, 80000.0)
        self.assertIsNone(fehler)
        self.assertAlmostEqual(menge, 20.0 / 80000.0, places=8)


class BindungTest(unittest.TestCase):

    def test_boerse_waehlt_das_modul(self):
        self.assertEqual(handeln.venue_binden({"boerse": "kraken"}), "kraken")
        # Ueber den Modulnamen vergleichen, nicht ueber die Objektidentitaet: der
        # Test laedt die Datei unter einem eigenen Namen, handeln.py importiert
        # sie als "kraken_spot" - dasselbe Modul, zwei Objekte.
        self.assertEqual(handeln.VENUE.__name__, "kraken_spot")
        self.assertEqual(handeln.op_kauf.__module__, "kraken_spot")
        self.assertEqual(handeln.op_stop.__module__, "kraken_spot")
        self.assertEqual(handeln.GUTHABEN_WAEHRUNG, "EUR")

    def test_ohne_feld_bleibt_okx(self):
        self.assertEqual(handeln.venue_binden({}), "okx")
        self.assertEqual(handeln.VENUE.__name__, "okx_spot")
        self.assertEqual(handeln.op_kauf.__module__, "okx_spot")
        self.assertEqual(handeln.GUTHABEN_WAEHRUNG, "USDC")

    def test_minimum_kommt_aus_der_wachen(self):
        handeln.venue_binden({"boerse": "kraken", "mindest_guthaben": 60})
        self.assertEqual(handeln.MINDEST_GUTHABEN, 60.0)
        handeln.venue_binden({"boerse": "kraken", "mindest_guthaben_eur": 42})
        self.assertEqual(handeln.MINDEST_GUTHABEN, 42.0)


class SperrenketteTest(unittest.TestCase):
    """Die Kette fragt die GEWAEHLTE Boerse - nicht immer OKX."""

    def setUp(self):
        self.merker = []
        handeln.venue_binden({"boerse": "kraken", "guthaben_waehrung": "EUR",
                              "mindest_guthaben": 60})
        self.alt = (handeln.VENUE, handeln.op_guthaben)
        handeln.VENUE = type("V", (), {
            "schluessel_vorhanden": staticmethod(lambda: True),
            "demo_modus": staticmethod(lambda: False),
            "__name__": "kraken_spot"})()
        handeln.op_guthaben = lambda ccy: (self.merker.append(ccy), 100.0)[1]

    def tearDown(self):
        handeln.VENUE, handeln.op_guthaben = self.alt

    def _sperren(self, frei=100.0):
        handeln.op_guthaben = lambda ccy: (self.merker.append(ccy), frei)[1]
        w = {"handel_erlaubt": True, "journal_zweitziel": "x",
             "guthaben_waehrung": "EUR", "mindest_guthaben": 60}
        s = {"freigabe_erfuellt": True, "herzschlag_frisch": True,
             "ev_negativ": False, "rollierender_ev": 1.0}
        return s

    def test_guthaben_wird_in_der_boersenwaehrung_gefragt(self):
        s = self._sperren()
        w = {"handel_erlaubt": True, "journal_zweitziel": "x",
             "guthaben_waehrung": "EUR", "mindest_guthaben": 60}
        handeln.live_sperren(w, s)
        self.assertIn("EUR", self.merker,
                      "die Kette muss das Guthaben in EUR abfragen, nicht in USDC")

    def test_zu_wenig_guthaben_ist_ein_grund(self):
        s = self._sperren(frei=5.0)
        w = {"handel_erlaubt": True, "journal_zweitziel": "x",
             "guthaben_waehrung": "EUR", "mindest_guthaben": 60}
        gruende = handeln.live_sperren(w, s)
        self.assertTrue(any("nur 5.00 EUR frei" in g for g in gruende), gruende)


if __name__ == "__main__":
    unittest.main()
