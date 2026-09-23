"""okx.stop_stornieren: instId muss mit, "schon erledigt" ist kein Fehler.

Befund 23.09.2026: der scanner meldete jede Runde
"SCHUTZ 50014: Parameter instId can not be empty". Gemessen an der Boerse:

    cancel-algos OHNE instId  -> OKX 50014 (Parameter instId can not be empty)
    cancel-algos MIT  instId  -> OKX 51400 (gefuellt, storniert oder nicht da)

Ohne instId liess sich der Stop also NIE abbestellen. Und 51400 ist keine
Stoerung, sondern die Auskunft "da ist nichts mehr" - wird sie als Fehler
behandelt, bleibt der Eintrag fuer immer liegen.

Kein Netz: ``_roh`` wird ersetzt, die Signatur ist hier nicht Gegenstand.
"""
import os
import sys
import unittest
from unittest.mock import patch

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import okx  # noqa: E402

assert okx.__file__.startswith(SPUR), okx.__file__


def _antwort(body, code="0"):
    return [{"algoId": body[0].get("algoId"), "sCode": code}]


class StopStornierenTest(unittest.TestCase):
    def setUp(self):
        self.body = None

    def _fake_roh(self, *a, **kw):
        self.pfad, self.methode, self.body, self.sig = a[0], a[1], a[2], kw
        return _antwort(self.body)

    def test_instid_geht_mit(self):
        with patch.object(okx, "_roh", self._fake_roh):
            okx.stop_stornieren("ALGO1", "ZEC-USDC")
        self.assertEqual(self.pfad, "/api/v5/trade/cancel-algos")
        self.assertEqual(self.methode, "POST")
        self.assertEqual(self.body, [{"algoId": "ALGO1", "instId": "ZEC-USDC"}])
        self.assertTrue(self.sig.get("signiert"))

    def test_ohne_inst_bleibt_der_body_schmal(self):
        # Gegenprobe zum Befund: ohne inst ist noch kein instId drin.
        with patch.object(okx, "_roh", self._fake_roh):
            okx.stop_stornieren("ALGO1")
        self.assertEqual(self.body, [{"algoId": "ALGO1"}])

    def test_51400_gilt_als_erledigt(self):
        def wirft(*a, **kw):
            raise okx.OKXFehler("OKX 51400: Order cancellation failed as the "
                                "order has been filled, canceled or does not exist.")
        with patch.object(okx, "_roh", wirft):
            self.assertIsNone(okx.stop_stornieren("ALGO1", "ZEC-USDC"))

    def test_andere_fehler_bleiben_fehler(self):
        def wirft(*a, **kw):
            raise okx.OKXFehler("OKX 50014: Parameter instId can not be empty.")
        with patch.object(okx, "_roh", wirft):
            with self.assertRaises(okx.OKXFehler):
                okx.stop_stornieren("ALGO1")

    def test_stop_inst_liest_das_instrument(self):
        with patch.object(okx, "stop_details",
                          lambda algo: {"state": "canceled",
                                        "instId": "ZEC-USDC"}):
            self.assertEqual(okx.stop_inst("ALGO1"), "ZEC-USDC")

    def test_stop_inst_ist_bei_fehler_still(self):
        def kaputt(algo):
            raise RuntimeError("kein Netz")
        with patch.object(okx, "stop_details", kaputt):
            self.assertIsNone(okx.stop_inst("ALGO1"))


if __name__ == "__main__":
    unittest.main()