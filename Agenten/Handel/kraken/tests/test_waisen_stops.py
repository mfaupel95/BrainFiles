"""Waisen-Stops erkennen - reine Rechnung auf Attrappen, kein Netz.

Ein Stop ohne Position ist gefaehrlich: ein Margin-SELL-Stop verkauft, was nicht
da ist, und eroeffnet damit einen SHORT.
"""
import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
sys.path.insert(0, HIER)


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


w = _lade("waisen_stops", os.path.join(SPUR, "waisen_stops.py"))
_s = _lade("spot_stops_w", os.path.join(SPUR, "spot_stops.py"))
assert w.__file__.startswith(SPUR), w.__file__

PAARE = {
    "SUIEUR": {"base": "SUI", "quote": "ZEUR", "lot_decimals": 5,
               "ordermin": "1"},
    "ZECUSD": {"base": "ZEC", "quote": "ZUSD", "lot_decimals": 8,
               "ordermin": "0.00005"},
    "SOLEUR": {"base": "SOL", "quote": "ZEUR", "lot_decimals": 8,
               "ordermin": "0.02"},
}


class FalscherKraken:
    """Attrappe: liefert genau die drei Lesewege, die lage() braucht."""

    def __init__(self, guthaben=None, positionen=None, orders=None):
        self._bal = guthaben or {}
        self._pos = positionen or {}
        self._ord = orders or {}

    def _roh_privat(self, name, **kw):
        if name == "BalanceEx":
            return self._bal
        if name == "OpenPositions":
            return {"open": self._pos}
        if name == "OpenOrders":
            return {"open": self._ord}
        return {}

    # Paartabelle der echten Spur (kein Netz)
    def _paare_laden(self):
        return PAARE


def stop(txid, paar, vol, preis="1.0"):
    return {txid: {"vol": str(vol), "descr": {"pair": paar,
                                              "ordertype": "stop-loss",
                                              "price": str(preis)}}}


class LageTest(unittest.TestCase):
    def setUp(self):
        self._orig = _s._paare_laden
        _s._paare_laden = lambda: PAARE          # Paartabelle ohne Netz

    def tearDown(self):
        _s._paare_laden = self._orig

    def test_stop_ohne_position_ist_waise(self):
        k = FalscherKraken(guthaben={}, orders=stop("O1", "SUIEUR", 30.69))
        z = w.lage(k, _s)[0]
        self.assertTrue(z["waise"])
        self.assertIn("keine Position", z["lage"])

    def test_position_da_ist_geschuetzt(self):
        k = FalscherKraken(guthaben={},
                           positionen={"p1": {"pair": "SUIEUR", "vol": "30.69",
                                              "vol_closed": "0"}},
                           orders=stop("O1", "SUIEUR", 30.69))
        z = w.lage(k, _s)[0]
        self.assertFalse(z["waise"])
        self.assertIn("Position", z["lage"])

    def test_teilweise_geschlossene_position_zaehlt_den_rest(self):
        k = FalscherKraken(guthaben={},
                           positionen={"p1": {"pair": "SUIEUR", "vol": "30.69",
                                              "vol_closed": "30.69"}},
                           orders=stop("O1", "SUIEUR", 30.69))
        self.assertTrue(w.lage(k, _s)[0]["waise"])

    def test_spot_mit_reserviertem_guthaben_ist_geschuetzt(self):
        k = FalscherKraken(guthaben={"ZEUR": {"balance": "100",
                                              "hold_trade": "0"}},
                           orders=stop("O2", "SOLEUR", 0.5))
        k._bal["SOL"] = {"balance": "1.0", "hold_trade": "0.5"}
        self.assertFalse(w.lage(k, _s)[0]["waise"])

    def test_spot_ohne_guthaben_ist_waise(self):
        k = FalscherKraken(guthaben={"SOL": {"balance": "0.1",
                                             "hold_trade": "0.0"}},
                           orders=stop("O2", "SOLEUR", 0.5))
        self.assertTrue(w.lage(k, _s)[0]["waise"])

    def test_txid_kommt_aus_dem_schluessel(self):
        # Kraken legt die Kennung in den SCHLUESSEL, nicht in den Wert - mit
        # o.get('txid') war sie leer und das Storno endete mit 'Invalid order'.
        k = FalscherKraken(orders=stop("OU3PX6-4ITGR-NO2W5E", "SUIEUR", 1.0))
        self.assertEqual(w.lage(k, _s)[0]["txid"], "OU3PX6-4ITGR-NO2W5E")

    def test_andere_orderarten_werden_nicht_bewertet(self):
        k = FalscherKraken(orders={"O3": {"vol": "1", "descr": {
            "pair": "SUIEUR", "ordertype": "limit", "price": "9"}}})
        self.assertEqual(w.lage(k, _s), [])

    def test_lange_paarform_und_usd_paare(self):
        k = FalscherKraken(orders=stop("O4", "ZECUSD", 0.18336972, 1410.4))
        z = w.lage(k, _s)[0]
        self.assertEqual(z["muenze"], "ZEC")
        self.assertTrue(z["waise"])


if __name__ == "__main__":
    unittest.main()