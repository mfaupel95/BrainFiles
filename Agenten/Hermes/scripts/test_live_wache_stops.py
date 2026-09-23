#!/usr/bin/env python3
"""Test der Stop-Lage in der Live-Wache (ohne Netz, ohne echte Buecher).

Aufruf:  python test_live_wache_stops.py     (aus Agenten/Hermes/scripts)

Warum: am 23.09.2026 wuchs `scanner/zustand.json` unbemerkt auf 23 Kopien
desselben Stops, und der Live-Lauf meldete jede Runde "bleibt liegen". Eine
Wache, die das nicht meldet, ist keine. Geprueft wird deshalb: jede Abweichung
zwischen Buch, Boerse und Merker wird gemeldet - und dieselbe Lage nur EINMAL.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import live_wache  # noqa: E402

assert live_wache.__file__.startswith(str(HIER)), live_wache.__file__


class StopLageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wurzel = Path(self.tmp.name)
        (self.wurzel / "scanner").mkdir()
        self.zustand({"positionen": [{"inst": "ZEC-USDC",
                                      "stop_ord_id": "A1"}]})
        p = patch.object(live_wache, "HANDEL", self.wurzel)
        p.start()
        self.addCleanup(p.stop)

    def zustand(self, z):
        (self.wurzel / "scanner" / "zustand.json").write_text(
            json.dumps(z), encoding="utf-8")

    def boerse(self, kennungen):
        p = patch.object(live_wache, "boersenstops",
                         lambda: [{"algoId": k} for k in kennungen])
        p.start()
        self.addCleanup(p.stop)

    def test_alles_gleich_ist_leise(self):
        self.boerse(["A1"])
        meldungen, lage = live_wache.stop_lage("scanner")
        self.assertEqual(meldungen, [], "keine Neuigkeit, keine Nachricht")
        self.assertEqual((lage["boerse"], lage["buch"]), (1, 1))

    def test_waisenstop_wird_gemeldet(self):
        self.boerse(["A1", "ALT9"])
        meldungen, lage = live_wache.stop_lage("scanner")
        self.assertEqual(len(meldungen), 1)
        self.assertIn("ALT9", meldungen[0])
        self.assertIn("Waisenstop", meldungen[0])
        self.assertEqual(lage["waisen"], ["ALT9"])

    def test_position_ohne_boersenstop_wird_gemeldet(self):
        self.boerse([])
        meldungen, lage = live_wache.stop_lage("scanner")
        self.assertEqual(len(meldungen), 1)
        self.assertIn("Notausstieg", meldungen[0])
        self.assertEqual(lage["ohne_stop"], ["A1"])

    def test_merker_wird_gemeldet(self):
        self.zustand({"positionen": [{"inst": "ZEC-USDC", "stop_ord_id": "A1"}],
                      "offene_stops": [{"inst": "ZEC-USDC",
                                        "stop_ord_id": "ALT9",
                                        "seit": "2026-09-22"}]})
        self.boerse(["A1"])
        meldungen, lage = live_wache.stop_lage("scanner")
        self.assertEqual(lage["offene_stops"], 1)
        self.assertTrue(any("Merker" in m for m in meldungen))

    def test_dieselbe_lage_wird_nicht_wiederholt(self):
        self.boerse(["A1", "ALT9"])
        _, lage = live_wache.stop_lage("scanner")
        self.assertTrue(live_wache._lage_gleich(lage, dict(lage)),
                        "unveraendert -> nichts senden")
        self.assertFalse(live_wache._lage_gleich(
            lage, dict(lage, waisen=[])), "Waisen weg -> melden")
        self.assertFalse(live_wache._lage_gleich(
            {"offene_stops": 0}, {"offene_stops": 3}), "Merker waechst -> melden")

    def test_boersenabruf_tot_ist_kein_waisenfund(self):
        p = patch.object(live_wache, "boersenstops", lambda: None)
        p.start()
        self.addCleanup(p.stop)
        meldungen, lage = live_wache.stop_lage("scanner")
        self.assertEqual(meldungen, [], "kein Abruf, keine Behauptung")
        self.assertFalse(lage["abruf_ok"])

    def test_fremde_spur_ohne_okx_buch_wird_nicht_verglichen(self):
        (self.wurzel / "kraken").mkdir()
        (self.wurzel / "kraken" / "zustand.json").write_text(
            json.dumps({"positionen": [{"paar": "SOLEUR",
                                        "stop_txid": "TX1"}]}), encoding="utf-8")
        self.boerse(["A1"])
        meldungen, lage = live_wache.stop_lage("kraken")
        self.assertEqual(meldungen, [], "Kraken-Kennungen gehoeren nicht an "
                                       "den OKX-Vergleich")
        self.assertNotIn("boerse", lage)


if __name__ == "__main__":
    unittest.main(verbosity=2)