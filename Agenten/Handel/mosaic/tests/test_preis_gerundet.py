"""Der Stop-Preis muss ein Vielfaches der Tick-Groesse (tickSz) sein.

Gegenstueck zu kraken/tests/test_preis_gerundet.py: derselbe Fehler ist
22.09.2026 live bei Kraken aufgetreten ("SOL/EUR price can only be specified
up to 2 decimals") und hat den Notausstieg einer frisch gekauften Position
ausfallen lassen. Bei OKX heisst die Regel tickSz; okx_spot sendete den rohen
Rechenwert als slTriggerPx.

Kein Netz: spot_instrument wird ersetzt. Direkt ausfuehrbar:
    python tests/test_preis_gerundet.py
"""

import importlib.util
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPUR))


def lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


osx = lade("mosaic_okx_spot_preis", SPUR / "okx_spot.py")

# tickSz der echten Instrumente, 22.09.2026 aus /api/v5/public/instruments.
TICK = {"SOL-USDC": "0.01", "BTC-USDC": "0.1", "ETH-USDC": "0.01",
        "XRP-USDC": "0.0001"}


class PreisGerundetTest(unittest.TestCase):

    def setUp(self):
        self.orig = osx.spot_instrument
        osx.spot_instrument = lambda inst: {"instId": inst,
                                            "tickSz": TICK.get(inst, "0.01")}

    def tearDown(self):
        osx.spot_instrument = self.orig

    def test_sol_auf_zwei_stellen(self):
        self.assertEqual(osx.preis_gerundet("SOL-USDC", 101.923456), "101.93")

    def test_sol_abwaerts(self):
        self.assertEqual(osx.preis_gerundet("SOL-USDC", 101.923456, "ab"),
                         "101.92")

    def test_bitcoin_eine_stelle(self):
        self.assertEqual(osx.preis_gerundet("BTC-USDC", 69123.456), "69123.5")

    def test_feine_tick_groesse_bleibt_genau(self):
        self.assertEqual(osx.preis_gerundet("XRP-USDC", 2.1234567), "2.1235")

    def test_preis_ist_nie_tiefer_als_gerechnet(self):
        for roh in (101.923456, 2.0000001, 69123.40001):
            g = float(osx.preis_gerundet("SOL-USDC", roh))
            self.assertGreaterEqual(g, roh)

    def test_ohne_tick_groesse_kein_stiller_ausfall(self):
        def kaputt(inst):
            raise osx.OKXFehler("Netz weg")
        osx.spot_instrument = kaputt
        # Verhalten wie vorher: roh senden (der alte Zustand), nicht werfen.
        self.assertEqual(osx.preis_gerundet("SOL-USDC", 101.923456),
                         "101.923456")

    def test_unbekannte_richtung_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            osx.preis_gerundet("SOL-USDC", 100.0, "schraeg")


class StopGehtGerundetRausTest(unittest.TestCase):
    """algo_stop_setzen gibt den gerundeten Preis in den Orderkoerper."""

    def setUp(self):
        self.orig_inst = osx.spot_instrument
        self.orig_roh = osx._roh
        osx.spot_instrument = lambda inst: {"instId": inst, "tickSz": "0.01"}
        self.body = None

        def attrappe(pfad, methode="GET", body=None, signiert=False):
            self.body = body
            return [{"algoId": "algo-1"}]

        osx._roh = attrappe

    def tearDown(self):
        osx.spot_instrument = self.orig_inst
        osx._roh = self.orig_roh

    def test_sl_trigger_ist_gerundet_und_schutzmarkt(self):
        osx.algo_stop_setzen("SOL-USDC", 0.2919, "long", 101.923456)
        self.assertEqual(self.body["slTriggerPx"], "101.93")
        self.assertEqual(self.body["slOrdPx"], "-1")
        self.assertEqual(self.body["side"], "sell")
        self.assertEqual(self.body["ordType"], "conditional")


if __name__ == "__main__":
    unittest.main(verbosity=2)