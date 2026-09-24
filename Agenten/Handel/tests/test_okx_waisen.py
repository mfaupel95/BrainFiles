"""Tests fuer okx_waisen.py - ohne Netz, ohne echten Schluessel.

Das okx-Modul wird durch eine Attrappe ersetzt: `_roh` liefert feste Antworten
(so wie OKX sie gibt), `stop_stornieren`/`stop_inst` zaehlen nur mit.
"""

import importlib.util
import io
import os
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))


def module():
    p = os.path.join(HIER, "..", "okx_waisen.py")
    spec = importlib.util.spec_from_file_location("okx_waisen_test", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


W = module()


def stop(algo_id, inst, menge, preis="1.0", art="cash", reduce_only=False):
    return {"algoId": algo_id, "instId": inst, "sz": str(menge),
            "slTriggerPx": preis, "tdMode": art, "side": "sell",
            "reduceOnly": reduce_only, "state": "live"}


class Attrappe:
    """Minimales okx-Modul: nur die drei Aufrufe, die okx_waisen macht."""

    def __init__(self, stops, positionen=None, bestand=None, fehler=None):
        self.stops = stops
        self.positionen = positionen or []
        self.bestand = bestand or []
        self.fehler = fehler or {}
        self.storniert = []
        self.inst_abgefragt = []

    def _roh(self, pfad, signiert=False, body=None, **kw):
        for teil, fehler in self.fehler.items():
            if teil in pfad:
                raise fehler
        if "orders-algo-pending" in pfad:
            return self.stops
        if "account/positions" in pfad:
            return self.positionen
        if "account/balance" in pfad:
            return [{"details": [{"ccy": c, "eq": str(v)} for c, v in self.bestand]}]
        return []

    def stop_inst(self, algo_id):
        self.inst_abgefragt.append(algo_id)
        return "GESUCHT-" + algo_id

    def stop_stornieren(self, algo_id, inst=None):
        self.storniert.append((algo_id, inst))
        return {"algoId": algo_id}


class LageTest(unittest.TestCase):
    def test_spot_voller_bestand_ist_in_ordnung(self):
        o = Attrappe([stop("A1", "SOL-USDC", 0.80283, art="cash")],
                     bestand=[("SOL", 0.80283)])
        z = W.lage(o)[0]
        self.assertEqual(z["lage"], "OK")
        self.assertFalse(z["waise"])

    def test_spot_ohne_bestand_ist_waise(self):
        o = Attrappe([stop("A2", "BTC-USDC", 0.00132754)], bestand=[("USDC", 52.6)])
        z = W.lage(o)[0]
        self.assertEqual(z["lage"], "WAISE")
        self.assertTrue(z["waise"])
        self.assertIn("kein Bestand BTC", z["grund"])

    def test_spot_mehr_als_bestand_ist_ueberdeckt_kein_alarm(self):
        o = Attrappe([stop("A3", "ETH-USDC", 0.5)], bestand=[("ETH", 0.037301)])
        z = W.lage(o)[0]
        self.assertEqual(z["lage"], "UEBERDECKT")
        self.assertFalse(z["waise"])

    def test_perp_ohne_position_ist_waise(self):
        o = Attrappe([stop("A4", "MON-USD_UM_XPERP-1", 10, art="isolated")])
        z = W.lage(o)[0]
        self.assertEqual(z["lage"], "WAISE")
        self.assertIn("kein Position", z["grund"])

    def test_perp_mit_position_ist_in_ordnung(self):
        o = Attrappe([stop("A5", "MON-USD_UM_XPERP-1", 4143, art="isolated")],
                     positionen=[{"instId": "MON-USD_UM_XPERP-1", "pos": "5000"}])
        zeile = [z for z in W.lage(o) if z["kennung"] == "A5"][0]
        self.assertEqual(zeile["lage"], "OK")

    def test_perp_ueber_deckung_traegt_reduceonly_im_grund(self):
        o = Attrappe([stop("A6", "MON-USD_UM_XPERP-1", 4143, art="isolated",
                           reduce_only=True)],
                     positionen=[{"instId": "MON-USD_UM_XPERP-1", "pos": "2985"}])
        z = [x for x in W.lage(o) if x["kennung"] == "A6"][0]
        self.assertEqual(z["lage"], "UEBERDECKT")
        self.assertIn("reduceOnly", z["grund"])

    def test_kurze_position_ist_nicht_gedeckt(self):
        """Eine SELL-Order deckt keine Short-Position (Betrag zaehlt)."""
        o = Attrappe([stop("A7", "MON-USD_UM_XPERP-1", 100, art="isolated")],
                     positionen=[{"instId": "MON-USD_UM_XPERP-1", "pos": "-2985"}])
        z = [x for x in W.lage(o) if x["kennung"] == "A7"][0]
        self.assertEqual(z["lage"], "OK")   # 100 <= 2985: gedeckt


class MainTest(unittest.TestCase):
    def _lauf(self, o, argv=()):
        alt = W._laden if hasattr(W, "_laden") else None
        W._laden = lambda name, pfad: o
        try:
            puffer = io.StringIO()
            with redirect_stdout(puffer):
                rc = W.main(list(argv))
            return rc, puffer.getvalue()
        finally:
            if alt is not None:
                W._laden = alt
            else:
                del W._laden

    def test_vorschau_storniert_nichts(self):
        o = Attrappe([stop("A1", "BTC-USDC", 1)], bestand=[])
        rc, text = self._lauf(o)
        self.assertEqual(rc, 0)
        self.assertEqual(o.storniert, [])
        self.assertIn("WAISEN", text)

    def test_stornieren_fasst_nur_waisen_an(self):
        o = Attrappe([stop("W1", "BTC-USDC", 1),
                      stop("U1", "ETH-USDC", 9)],
                     bestand=[("ETH", 0.5)])
        rc, text = self._lauf(o, ["--stornieren"])
        self.assertEqual([k for k, _ in o.storniert], ["W1"])
        self.assertIn("UEBERDECKT bleibt stehen", text)

    def test_storniere_holt_die_instid_wenn_sie_fehlt(self):
        o = Attrappe([stop("W2", "BTC-USDC", 1)])
        W.storniere(o, "W2")
        self.assertEqual(o.inst_abgefragt, ["W2"])
        self.assertEqual(o.storniert, [("W2", "GESUCHT-W2")])

    def test_fehler_einer_boerse_wird_gemeldet_nicht_verschluckt(self):
        o = Attrappe([], fehler={"account/balance": RuntimeError("OKX 50119: kaputt")})
        with self.assertRaises(RuntimeError):
            W.lage(o)


if __name__ == "__main__":
    unittest.main()