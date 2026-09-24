"""Tests fuer mosaic/stops_nachziehen.py - ohne Netz, ohne Order.

ANLASS: Der erste Lauf am 24.09.2026 fand nur EINE von drei Kennungen. Kraken
nennt dasselbe Paar in zwei Schreibweisen (Order-Anfrage XXBTZEUR/XETHZEUR,
offene Order XBTEUR/ETHEUR) - ein Vergleich der rohen Zeichenketten haette die
Positionen von BTC und ETH fuer ungeschuetzt gehalten, obwohl an der Boerse ein
Stop lag. Diese Tests frieren die Paar-Erkennung und die Mengen-Toleranz ein.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import stops_nachziehen as sn                                       # noqa: E402


class ZerlegeTest(unittest.TestCase):

    def test_beide_schreibweisen_ergeben_dasselbe(self):
        self.assertEqual(sn.zerlege("XXBTZEUR"), ("BTC", "EUR"))
        self.assertEqual(sn.zerlege("XBTEUR"), ("BTC", "EUR"))
        self.assertEqual(sn.zerlege("XETHZEUR"), ("ETH", "EUR"))
        self.assertEqual(sn.zerlege("ETHEUR"), ("ETH", "EUR"))
        self.assertEqual(sn.zerlege("SOLEUR"), ("SOL", "EUR"))

    def test_unbekannt_ist_none(self):
        self.assertEqual(sn.zerlege(""), (None, None))
        self.assertEqual(sn.zerlege(None), (None, None))
        self.assertEqual(sn.zerlege("EUR"), (None, None))


class PassenderStopTest(unittest.TestCase):

    def _orders(self):
        return {
            "OHNYTW-3LOCU-ZRRQ54": {"paar": "ETHEUR", "seite": "sell",
                                    "art": "stop-loss", "menge": "0.04072038",
                                    "preis": "2240.10"},
            "O3QKG4-P6QVQ-6SLH5V": {"paar": "XBTEUR", "seite": "sell",
                                    "art": "stop-loss", "menge": "0.00066027",
                                    "preis": "71940.1"},
            "OH4CHB-YTTBD-GK2NKT": {"paar": "SOLEUR", "seite": "sell",
                                    "art": "stop-loss", "menge": "0.48058439",
                                    "preis": "98.84"},
        }

    def test_findet_die_kennung_je_position(self):
        faelle = [("BTC-USDC", "0.00066027", "O3QKG4-P6QVQ-6SLH5V"),
                  ("ETH-USDC", "0.04072038", "OHNYTW-3LOCU-ZRRQ54"),
                  ("SOL-USDC", "0.48058439", "OH4CHB-YTTBD-GK2NKT")]
        for inst, menge, erwartet in faelle:
            with self.subTest(inst=inst):
                txid, order = sn.passender_stop(
                    {"inst": inst, "menge": menge}, self._orders())
                self.assertEqual(txid, erwartet)
                self.assertEqual(order["art"], "stop-loss")

    def test_fremde_menge_passt_nicht(self):
        # Ein Stop ueber eine ANDERE Menge ist nicht der Schutz DIESER Position.
        txid, _ = sn.passender_stop({"inst": "SOL-USDC", "menge": "0.9"},
                                    self._orders())
        self.assertIsNone(txid)

    def test_kleine_rundung_ist_erlaubt(self):
        # Boersen runden; 1 % Toleranz ist die vereinbarte Grenze.
        txid, _ = sn.passender_stop({"inst": "SOL-USDC", "menge": "0.4810"},
                                    self._orders())
        self.assertEqual(txid, "OH4CHB-YTTBD-GK2NKT")

    def test_nicht_stop_zaehlt_nicht(self):
        orders = {"X": {"paar": "SOLEUR", "seite": "buy",
                        "art": "limit", "menge": "0.48058439", "preis": "90"}}
        txid, _ = sn.passender_stop({"inst": "SOL-USDC", "menge": "0.48058439"},
                                    orders)
        self.assertIsNone(txid)

    def test_unbekanntes_instrument(self):
        txid, _ = sn.passender_stop({"inst": "FOO-USDC", "menge": "1"},
                                    self._orders())
        self.assertIsNone(txid)


if __name__ == "__main__":
    unittest.main()
