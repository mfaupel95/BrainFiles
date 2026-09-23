"""Tests fuer anpassen.py - der Amend-Weg zu einem LAUFENDEN OKX-Bot.

Kein Netz, keine echten Dateien: bots.sende wird gezaehlt, nicht ausgefuehrt.
Die Regel, die hier festgenagelt wird: ein Amend darf NICHTS erfinden - was
nicht ausdruecklich gewaehlt ist, bleibt wie es war (Leiter, Stop, Ziel).
"""
import argparse
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
if SPUR not in sys.path:
    sys.path.insert(0, SPUR)

import anpassen as an  # noqa: E402
import bots as bm  # noqa: E402

assert an.__file__.startswith(SPUR)

BOT = {
    "algoId": "3947610369740500992", "instId": "UNI-USD_UM_XPERP-310718",
    "maxSafetyOrds": "11", "pxSteps": "0.0072", "pxStepsMult": "1", "volMult": "1.1",
    "initOrdAmt": "5.4072", "safetyOrdAmt": "3.35557926", "tpPct": None, "slPct": None,
}
DETAILS = {
    "avgPx": "9.9454583333333334", "liqPx": "8.719328514679633", "notionalUsd": "437.42",
    "fillSafetyOrds": "11", "tpPx": "10.384", "slPx": "", "sz": "48", "initPx": "10.44075",
}
# Kerzen sind LISTEN, genau wie bots.kerzen sie liefert: [ts, o, h, l, c, v]
KERZEN = [[1000 * i, 100.0, 106.0, 94.0, 100.0, 1.0] for i in range(120)]
W = {"dca_max_steps": 12, "_vorschlag": {"dca_tp_pct": 0.05}}


def args(**kw):
    grund = dict(stufen=None, schritt=None, tp_pct=None, sl_pct=None, nur_schutz=False,
                 reserve=False, margin=None, nur=None, anwenden=False)
    grund.update(kw)
    return argparse.Namespace(**grund)


class KoerperTest(unittest.TestCase):
    def test_amend_koerper_hat_alle_pflichtfelder(self):
        k = an.koerper_amend("123", 0.02, 1, 1.1, 0.05, 0.2, 5.4, 3.35, 12, reserve=True)
        for feld in ("algoId", "pxSteps", "pxStepsMult", "volMult", "tpPct", "slPct",
                     "initOrdAmt", "safetyOrdAmt", "maxSafetyOrds", "reserveFunds",
                     "triggerParams"):
            self.assertIn(feld, k)
        self.assertEqual(k["algoId"], "123")
        self.assertEqual(k["maxSafetyOrds"], "12")
        self.assertIs(k["reserveFunds"], True)
        self.assertEqual(k["triggerParams"][0]["triggerAction"], "start")

    def test_margin_koerper(self):
        self.assertEqual(an.koerper_margin("123", 50), {"algoId": "123", "amt": "50"})


class MarginBedarfTest(unittest.TestCase):
    def test_wand_und_bedarf_werden_gerechnet(self):
        d = {"avgPx": "100", "liqPx": "90", "notionalUsd": "400", "fillSafetyOrds": "3"}
        b = {"initOrdAmt": "10", "safetyOrdAmt": "10"}
        m = an.margin_bedarf(d, b, 80.0)
        self.assertEqual(m["margin_ist"], 40.0)
        self.assertEqual(m["liq_abstand_prozent"], 10.0)
        self.assertEqual(m["rest_prozent"], 0.0)   # 10 % - 40/400
        self.assertEqual(m["ziel_abstand_prozent"], 20.0)
        self.assertEqual(m["noetige_margin_usdc"], 40.0)

    def test_ziel_ueber_der_liquidation_kostet_nichts(self):
        d = {"avgPx": "100", "liqPx": "90", "notionalUsd": "400", "fillSafetyOrds": "3"}
        b = {"initOrdAmt": "10", "safetyOrdAmt": "10"}
        self.assertEqual(an.margin_bedarf(d, b, 95.0)["noetige_margin_usdc"], 0.0)

    def test_ohne_zahlen_keine_rechnung(self):
        self.assertIsNone(an.margin_bedarf({"avgPx": "100"}, BOT, 80.0))


class PlanTest(unittest.TestCase):
    def test_ohne_wahl_bleibt_alles_wie_es_ist(self):
        p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args())
        k = p["koerper"]
        self.assertEqual(k["maxSafetyOrds"], "11")
        self.assertEqual(float(k["pxSteps"]), 0.0072)
        self.assertEqual(float(k["slPct"]), 0.0)
        self.assertEqual(p["neu"]["tiefe_prozent"], p["alt"]["tiefe_prozent"])

    def test_tp_kommt_aus_dem_preis_wenn_das_feld_fehlt(self):
        p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args())
        self.assertAlmostEqual(p["alt"]["tpPct"], 10.384 / 9.9454583333333334 - 1, places=6)
        self.assertIn("tpPx", p["alt"]["tp_quelle"])

    def test_stufen_erhoehen_aendert_die_leiter_und_die_tiefe(self):
        p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args(stufen=20, schritt=2.5))
        self.assertEqual(p["koerper"]["maxSafetyOrds"], "20")
        self.assertAlmostEqual(float(p["koerper"]["pxSteps"]), 0.025, places=6)
        self.assertEqual(p["neu"]["tiefe_prozent"], 50.0)
        # genug Geld da (Attrappe) -> keine Guthaben-Warnung, aber die
        # Reichweiten-Warnung bleibt: die Leiter endet unter der Liquidation
        self.assertTrue(any("Liquidation" in x for x in p["warnungen"]))

    def test_nur_schutz_laesst_die_leiter_in_ruhe(self):
        p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args(nur_schutz=True, sl_pct=0.21))
        self.assertEqual(p["koerper"]["maxSafetyOrds"], "11")
        self.assertEqual(p["koerper"]["pxSteps"], "0.0072")
        self.assertAlmostEqual(float(p["koerper"]["slPct"]), 0.21, places=6)

    def test_ohne_freies_guthaben_wird_gewarnt(self):
        alt_frei = an.freies_guthaben
        an.freies_guthaben = lambda ccy="USDC": 1.0
        try:
            p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args(stufen=20, schritt=2.5))
        finally:
            an.freies_guthaben = alt_frei
        self.assertTrue(any("aber nicht fuellen" in x for x in p["warnungen"]))

    def test_stop_wird_nicht_erfunden(self):
        # ohne --sl-pct darf kein Stop entstehen, auch wenn die Analyse einen vorschlaegt
        p = an.plan_fuer_bot(BOT, DETAILS, [], 9.1, KERZEN, W, args())
        self.assertEqual(float(p["koerper"]["slPct"]), 0.0)
        self.assertTrue((p["empfehlung_atr"] or {}).get("sl_pct"))


class TorTest(unittest.TestCase):
    def setUp(self):
        self.gesendet = []
        self.alt_laufend = bm.dca_laufend
        self.alt_details = bm.dca_details
        self.alt_zyklen = bm.dca_zyklen
        self.alt_orders = bm.dca_orders
        self.alt_kurs = bm.kurs
        self.alt_kerzen = bm.kerzen
        self.alt_sende = bm.sende
        bm.dca_laufend = lambda: [dict(BOT)]
        bm.dca_details = lambda aid: dict(DETAILS)
        bm.dca_zyklen = lambda aid: [{"cycleId": "1", "currentCycle": True}]
        bm.dca_orders = lambda aid, cid: []
        bm.kurs = lambda inst: 9.1
        bm.kerzen = lambda inst, bar="1D", anzahl=365: list(KERZEN)
        bm.sende = lambda pfad, koerper: self.gesendet.append((pfad, koerper)) or {"code": "0"}
        # kein Netz im Test: das freie Guthaben kommt aus der Attrappe
        self.alt_frei = an.freies_guthaben
        an.freies_guthaben = lambda ccy="USDC": 1000.0

    def tearDown(self):
        bm.dca_laufend, bm.dca_details, bm.dca_zyklen = (self.alt_laufend, self.alt_details,
                                                         self.alt_zyklen)
        bm.dca_orders, bm.kurs, bm.kerzen, bm.sende = (self.alt_orders, self.alt_kurs,
                                                       self.alt_kerzen, self.alt_sende)
        an.freies_guthaben = self.alt_frei

    def _wachen(self, anpassen=False):
        alt = an.waechter.lade_wachen
        an.waechter.lade_wachen = lambda: {"anpassen_erlaubt": anpassen,
                                           "_vorschlag": W["_vorschlag"]}
        self.addCleanup(setattr, an.waechter, "lade_wachen", alt)

    def test_anwenden_ohne_tor_sendet_nichts(self):
        self._wachen(False)
        self.assertEqual(an.main(["--stufen", "20", "--anwenden"]), 2)
        self.assertEqual(self.gesendet, [])

    def test_anwenden_ohne_wahl_sendet_nichts(self):
        self._wachen(True)
        self.assertEqual(an.main(["--anwenden"]), 2)
        self.assertEqual(self.gesendet, [])

    def test_anwenden_mit_tor_und_wahl_sendet_genau_einmal(self):
        self._wachen(True)
        self.assertEqual(an.main(["--stufen", "20", "--schritt", "2.5", "--anwenden"]), 0)
        self.assertEqual(len(self.gesendet), 1)
        pfad, koerper = self.gesendet[0]
        self.assertEqual(pfad, "/api/v5/tradingBot/dca/amend-order-algo")
        self.assertEqual(koerper["maxSafetyOrds"], "20")

    def test_zaehler_des_trockenlaufs_sendet_nichts(self):
        self._wachen(True)
        self.assertEqual(an.main([]), 0)
        self.assertEqual(self.gesendet, [])

    def test_margin_geht_ueber_den_eigenen_weg(self):
        self._wachen(True)
        self.assertEqual(an.main(["--margin", "50", "--anwenden"]), 0)
        self.assertEqual(self.gesendet[0][0], "/api/v5/tradingBot/dca/margin/add")
        self.assertEqual(self.gesendet[0][1]["amt"], "50")


if __name__ == "__main__":
    unittest.main()