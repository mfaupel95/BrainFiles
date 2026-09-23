"""Nach einem fehlgeschlagenen Verkauf muss der Schutz-Stop zurueckkommen.

Hintergrund (22./23.09.2026): `_live_verkauf` bestellt ZUERST den Notausstieg
ab - sonst blockiert er den Bestand. Der Verkauf scheiterte danach jede Runde
(OKX 50119, falscher Host), und die Position stand ohne Stop an der Boerse.
Der Test haelt die Regel fest, ohne Netz und ohne echte Dateien.
"""
import os
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import handeln  # noqa: E402

assert handeln.__file__.startswith(SPUR), handeln.__file__


class FakeOKX:
    """Antwortet wie okx.py, ohne Netz."""

    def __init__(self, verkauf_fehler=True, details_fehler=False):
        self.verkauf_fehler = verkauf_fehler
        self.details_fehler = details_fehler
        self.verkaeufe = []
        self.stops = []

    def order_details(self, inst, ord_id):
        if self.details_fehler:
            raise RuntimeError("kein Netz")
        return {"accFillSz": "0.04076"}

    def markt_verkauf(self, inst, menge):
        if self.verkauf_fehler:
            raise RuntimeError("OKX 50119: API key doesn't exist")
        self.verkaeufe.append((inst, menge))
        return "ord-1"

    def stop_setzen(self, inst, menge, preis):
        self.stops.append((inst, menge, preis))
        return "algo-neu"

    def stop_stornieren(self, algo_id, inst=None):
        return algo_id

    def stop_inst(self, algo_id):
        return "ZEC-USDC"


def position(**abweichend):
    p = {"inst": "ZEC-USDC", "usd": 65.96, "einstieg": 1619.38,
         "stop": 1472.01642, "ziel": 1914.10, "kauf_ord_id": "3947",
         "stop_ord_id": "algo-alt", "modus": "live"}
    p.update(abweichend)
    return p


class SchutzZurueckTest(unittest.TestCase):
    def setUp(self):
        self.echt = handeln.okx
        self.fake = FakeOKX()
        handeln.okx = self.fake

    def tearDown(self):
        handeln.okx = self.echt

    def test_alte_stop_kennung_bleibt_unberuehrt(self):
        # Der Storno scheiterte, der Stop schuetzt also noch - nichts tun.
        p = position()
        self.assertFalse(handeln._schutz_zurueck(p, 0.04076))
        self.assertEqual(self.fake.stops, [])
        self.assertEqual(p["stop_ord_id"], "algo-alt")

    def test_ohne_stop_preis_wird_nicht_geraten(self):
        p = position(stop_ord_id=None, stop=None)
        self.assertFalse(handeln._schutz_zurueck(p, 0.04076))
        self.assertEqual(self.fake.stops, [])

    def test_stop_wird_mit_der_menge_zurueckgelegt(self):
        p = position(stop_ord_id=None)
        self.assertTrue(handeln._schutz_zurueck(p, 0.04076))
        self.assertEqual(self.fake.stops, [("ZEC-USDC", 0.04076, 1472.01642)])
        self.assertEqual(p["stop_ord_id"], "algo-neu")

    def test_menge_wird_selbst_geholt(self):
        p = position(stop_ord_id=None)
        self.assertTrue(handeln._schutz_zurueck(p))
        self.assertEqual(self.fake.stops[0][1], 0.04076)

    def test_unlesbare_menge_meldet_statt_zu_raten(self):
        self.fake.details_fehler = True
        p = position(stop_ord_id=None)
        self.assertFalse(handeln._schutz_zurueck(p))
        self.assertEqual(self.fake.stops, [])

    def test_fehlgeschlagener_verkauf_legt_den_schutz_zurueck(self):
        p = position(stop_ord_id=None)
        z = {}
        self.assertEqual(handeln._live_verkauf(p, z), "fehler")
        self.assertEqual(self.fake.stops, [("ZEC-USDC", 0.04076, 1472.01642)])

    def test_geglueckter_verkauf_legt_keinen_schutz_an(self):
        self.fake.verkauf_fehler = False
        p = position()
        self.assertEqual(handeln._live_verkauf(p, {}), "ok")
        self.assertEqual(self.fake.stops, [])
        self.assertEqual(self.fake.verkaeufe, [("ZEC-USDC", 0.04076)])


if __name__ == "__main__":
    unittest.main()