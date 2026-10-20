"""Tests fuer itb_uebersetzer: ITB-Export -> Signal-Dict.

Geprueft wird die REGEL: buy wird long, sell ohne buy wird flat, Zweideutiges
wird verworfen, und ein uebersetztes Signal kommt durch das Tor nur mit
Freigabe. Die Tests lesen die echte wachen.json, keine Attrappe.
"""
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))

import fremd_tor as ft                                               # noqa: E402
import itb_uebersetzer as iu                                         # noqa: E402

WACHE = os.path.join(os.path.dirname(HIER), "fremd_signale", "wachen.json")
JETZT = 1_800_000_000


def zeile(buy, sell, ts=JETZT, instrument="BTC-USDT"):
    return {"instrument": instrument, "ts_utc": str(ts), "buy": str(buy), "sell": str(sell)}


class RegelnTest(unittest.TestCase):

    def test_buy_wird_long_mit_groesse_eins(self):
        s = iu.uebersetze_zeile(zeile(True, False))
        self.assertEqual(s["direction"], "long")
        self.assertEqual(s["size_pct"], 0.5)

    def test_sell_ohne_buy_wird_flat_ohne_groesse(self):
        s = iu.uebersetze_zeile(zeile(False, True))
        self.assertEqual(s["direction"], "flat")
        self.assertNotIn("size_pct", s)

    def test_beide_true_ist_kein_signal(self):
        self.assertIsNone(iu.uebersetze_zeile(zeile(True, True)))

    def test_beide_false_ist_kein_signal(self):
        self.assertIsNone(iu.uebersetze_zeile(zeile(False, False)))

    def test_feste_felder_stehen_im_dict(self):
        s = iu.uebersetze_zeile(zeile(True, False))
        self.assertEqual(s["venue"], "okx")
        self.assertEqual(s["mode"], "paper")
        self.assertEqual(s["source"], "intelligent-trading-bot")
        self.assertEqual(s["expiry_s"], 1800)
        self.assertEqual(s["instrument"], "BTC-USDT")
        self.assertEqual(s["ts_utc"], JETZT)

    def test_live_wird_nie_erzeugt(self):
        self.assertNotEqual(iu.uebersetze_zeile(zeile(True, False))["mode"], "live")

    def test_uebersetze_laesst_nichts_ungueltiges_weg_ausser_leer(self):
        zeilen = [zeile(True, False), zeile(True, True), zeile(False, True)]
        self.assertEqual([s["direction"] for s in iu.uebersetze(zeilen)], ["long", "flat"])


class ExportTest(unittest.TestCase):

    def test_export_einlesen_und_uebersetzen(self):
        inhalt = "instrument,ts_utc,buy,sell\nBTC-USDT,%d,True,False\n" % JETZT
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "signale.csv")
            with open(pfad, "w", encoding="utf-8", newline="") as f:
                f.write(inhalt)
            signale = iu.uebersetze(iu.lese_export(pfad))
        self.assertEqual(len(signale), 1)
        self.assertEqual(signale[0]["direction"], "long")

    def test_fehlende_spalte_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "kaputt.csv")
            with open(pfad, "w", encoding="utf-8", newline="") as f:
                f.write("instrument,buy\nBTC-USDT,True\n")
            with self.assertRaises(ValueError):
                iu.lese_export(pfad)


class TorTest(unittest.TestCase):
    """Das uebersetzte Signal muss das echte Tor passieren, nicht nur die Form."""

    def setUp(self):
        with open(WACHE, encoding="utf-8") as f:
            self.wache = json.load(f)

    def test_btc_usdt_long_kommt_durch(self):
        s = iu.uebersetze_zeile(zeile(True, False, ts=JETZT))
        ok, grund = ft.entscheide(s, self.wache, JETZT)
        self.assertTrue(ok, grund)

    def test_altes_signal_wird_verworfen(self):
        s = iu.uebersetze_zeile(zeile(True, False, ts=JETZT - 3600))
        ok, _ = ft.entscheide(s, self.wache, JETZT)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
