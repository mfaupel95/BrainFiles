r"""Tests fuer omnitrade_bridge und den omnitrade-Reiter der Handelszentrale.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_omnitrade_bridge
"""

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import omnitrade_bridge as ob  # noqa: E402
import handelszentrale as hz  # noqa: E402

JETZT = 1_800_000_000_000
STATUS = {"schema": 1, "state": "running", "exchange": "okx", "symbol": "BTCUSDT", "network": "testnet",
          "script": "strategien/rsi30_stop2.omni", "initial_capital": 1000.0,
          "pid": 1, "started_ms": JETZT - 60_000, "updated_ms": JETZT - 10_000,
          "candles_seen": 7, "last_close": 64000.5, "last_candle_ms": JETZT - 60_000,
          "last_signal": "buy", "orders_placed": 2, "orders_rejected": 1,
          "net_quantity": 0.01, "last_error": "",
          "recent_orders": [
              {"time_ms": JETZT - 30_000, "side": "buy", "quantity": 0.01,
               "price": 64000.0, "outcome": "filled", "detail": ""},
              {"time_ms": JETZT - 20_000, "side": "buy", "quantity": 0.01,
               "price": 64010.0, "outcome": "rejected", "detail": "max position"}]}


class BrueckeTest(unittest.TestCase):

    def setUp(self):
        self.ordner = tempfile.mkdtemp()
        self.datei = os.path.join(self.ordner, "live.json")

    def tearDown(self):
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _schreibe(self, daten):
        with open(self.datei, "w", encoding="utf-8") as f:
            f.write(daten if isinstance(daten, str) else json.dumps(daten))

    def test_frische_datei_ist_ok(self):
        self._schreibe(STATUS)
        lage = ob.lage(self.datei, jetzt_ms=JETZT)
        self.assertTrue(lage["ok"], lage["fehler"])
        self.assertEqual(lage["alter_s"], 10.0)
        self.assertEqual(lage["symbol"], "BTCUSDT")

    def test_fehlende_datei(self):
        lage = ob.lage(self.datei, jetzt_ms=JETZT)
        self.assertFalse(lage["ok"])
        self.assertIn("keine Statusdatei", lage["fehler"])

    def test_kaputte_datei_wirft_nicht(self):
        for inhalt in ("{halb", "[1, 2]", json.dumps(dict(STATUS, schema=2)),
                       json.dumps(dict(STATUS, updated_ms=None))):
            self._schreibe(inhalt)
            lage = ob.lage(self.datei, jetzt_ms=JETZT)
            self.assertFalse(lage["ok"], inhalt)
            self.assertTrue(lage["fehler"])

    def test_veraltet_nur_solange_er_laufen_sollte(self):
        self._schreibe(dict(STATUS, updated_ms=JETZT - 600_000))
        lage = ob.lage(self.datei, jetzt_ms=JETZT)
        self.assertFalse(lage["ok"])
        self.assertIn("veraltet", lage["fehler"])
        self._schreibe(dict(STATUS, state="stopped", updated_ms=JETZT - 600_000))
        self.assertTrue(ob.lage(self.datei, jetzt_ms=JETZT)["ok"])

    def test_stuendlicher_lauf_ist_nicht_veraltet(self):
        """30.09.2026: ein Lauf mit --interval 1h schreibt die Datei nur
        stuendlich. Die feste 5-Minuten-Grenze hat ihn fuer tot erklaert,
        waehrend die Handelszentrale zusah. Die Grenze kommt jetzt aus dem
        Kerzenabstand der Datei selbst."""
        kerzen = [{"time_ms": JETZT - 3_600_000, "close": 1.0},
                  {"time_ms": JETZT - 7_200_000, "close": 1.0}]
        self._schreibe(dict(STATUS, recent_candles=kerzen, updated_ms=JETZT - 1_560_000))
        lage = ob.lage(self.datei, jetzt_ms=JETZT)
        self.assertTrue(lage["ok"], lage["fehler"])
        self.assertEqual(lage["altersgrenze_s"], 9000.0)

    def test_kerzenabstand_aus_der_datei(self):
        self.assertIsNone(ob.intervall_s({}))
        self.assertIsNone(ob.intervall_s({"recent_candles": [{"time_ms": 1}]}))
        self.assertIsNone(ob.intervall_s({"recent_candles": "kaputt"}))
        self.assertEqual(ob.intervall_s({"recent_candles": [{"time_ms": 0}, {"time_ms": 60_000}]}), 60.0)
        # Median: eine Luecke (hier 10 min) verschiebt die Grenze nicht
        self.assertEqual(ob.intervall_s({"recent_candles": [
            {"time_ms": 0}, {"time_ms": 60_000}, {"time_ms": 120_000}, {"time_ms": 720_000}]}), 60.0)
        self.assertEqual(ob.altersgrenze_s({"recent_candles": [{"time_ms": 0}, {"time_ms": 60_000}]}),
                         ob.VERALTET_S)
        self.assertEqual(ob.altersgrenze_s({}), float(ob.VERALTET_S))

    def test_pfad_aus_umgebung(self):
        with mock.patch.dict(os.environ, {"OMNITRADE_STATUS": self.datei}):
            self.assertEqual(ob.pfad(), self.datei)
        with mock.patch.dict(os.environ, {"OMNITRADE_STATUS": ""}):
            self.assertTrue(ob.pfad().endswith(os.path.join("omnitrade", "status",
                                                            "live.json")))


class NurLesendTest(unittest.TestCase):

    def test_kein_open_im_schreibmodus(self):
        with open(ob.__file__, encoding="utf-8") as f:
            baum = ast.parse(f.read())
        for knoten in ast.walk(baum):
            if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                    and knoten.func.id == "open"):
                self.assertEqual(knoten.args[1].value, "r")


class ReiterFunktionenTest(unittest.TestCase):

    def _lage(self, **extra):
        return dict(STATUS, ok=True, alter_s=10.0, fehler="", **extra)

    def test_kopf(self):
        self.assertEqual(hz.omnitrade_kopf(None)[1], "matt")
        text, marke = hz.omnitrade_kopf({"ok": False, "fehler": "weg"})
        self.assertEqual(marke, "schlecht")
        self.assertIn("weg", text)
        text, marke = hz.omnitrade_kopf(self._lage())
        self.assertEqual(marke, "gut")
        for teil in ("running", "okx testnet", "BTCUSDT", "Kerzen 7", "Signal buy",
                     "abgelehnt 1"):
            self.assertIn(teil, text)
        self.assertEqual(hz.omnitrade_kopf(self._lage(network="mainnet"))[1], "schlecht")
        self.assertEqual(hz.omnitrade_kopf(self._lage(state="error"))[1], "schlecht")

    def test_orderzeilen_neueste_zuerst(self):
        zeilen = hz.omnitrade_order_zeilen(self._lage())
        self.assertEqual([z[4] for z in zeilen], ["rejected", "filled"])
        self.assertEqual(zeilen[0][5], "max position")
        self.assertEqual(hz.omnitrade_order_zeilen({"recent_orders": None}), [])
        self.assertEqual(hz.omnitrade_order_zeilen(None), [])

    def test_reiter_wird_gefuellt(self):
        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            with mock.patch.object(hz.Handelszentrale, "_starte_freqtrade_worker"):
                app = hz.Handelszentrale(root)
            app._zeige_omnitrade(self._lage())
            self.assertEqual(len(app.t_omni.get_children()), 2)
            self.assertIn("BTCUSDT", app.l_omni.cget("text"))
            app._zeige_omnitrade({"ok": False, "fehler": "keine Statusdatei"})
            self.assertEqual(app.t_omni.get_children(), ())
            self.assertIn("⚠", app.l_omni.cget("text"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
