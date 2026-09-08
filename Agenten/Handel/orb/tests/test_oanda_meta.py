import json
import unittest
from pathlib import Path

import oanda

FIX = Path(__file__).resolve().parent / "fixtures"


class TestMeta(unittest.TestCase):
    def setUp(self):
        self._alt = oanda._roh_json
        oanda.token = lambda: "tok"
        oanda.konto_id = lambda: "kid"

    def tearDown(self):
        oanda._roh_json = self._alt

    def _mock(self, name):
        d = json.loads((FIX / name).read_text())
        oanda._roh_json = lambda url, *, method="GET", body=None: d

    def test_preis_liefert_bid_ask_spread(self):
        self._mock("pricing.json")
        p = oanda.preis("DE30_EUR")
        self.assertAlmostEqual(p["bid"], 18004.5)
        self.assertAlmostEqual(p["ask"], 18005.7)
        self.assertAlmostEqual(p["spread_punkte"], 1.2, places=1)

    def test_instrument_details(self):
        self._mock("instrument.json")
        d = oanda.instrument_details("DE30_EUR")
        self.assertEqual(d["minimumTradeSize"], 1.0)
        self.assertEqual(d["displayPrecision"], 1)
        self.assertAlmostEqual(d["marginRate"], 0.05)

    def test_konto_marge_frei(self):
        self._mock("account.json")
        self.assertAlmostEqual(oanda.konto_marge_frei(), 1234.56)

    def test_instrument_handelbar_true_bei_antwort(self):
        self._mock("instrument.json")
        self.assertTrue(oanda.instrument_handelbar("DE30_EUR"))

    def test_instrument_handelbar_false_bei_fehler(self):
        def boom(url, *, method="GET", body=None):
            raise oanda.OandaFehler("HTTP 400")
        oanda._roh_json = boom
        self.assertFalse(oanda.instrument_handelbar("DE30_EUR"))
