"""Tests fuer fremd_papier: Papier-Ausfuehrung zugelassener Fremd-Signale.

Geprueft wird die REGEL: Stop ist Pflicht, Grenzen der Wache gelten, kein
Signal wird doppelt ausgefuehrt, nichts geht an eine Boerse (Kurs wird
uebergeben, es gibt hier keinen Orderweg).
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))

import fremd_papier as fp                                            # noqa: E402

JETZT = 1_728_432_100
WACHE = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper", "demo"],
         "quellen_erlaubt": ["kraken-cli"], "instrumente_erlaubt": ["BTC/USD", "ETH/USD"],
         "size_pct_max": 0.5, "stop_prozent": 4.0, "pflicht_stop_prozent_min": 2.4,
         "pflicht_stop_prozent_max": 8.0, "risiko_je_position_usd": 5.0,
         "max_offene_positionen": 2, "max_pro_trade_usd": 250.0,
         "max_gesamt_usd": 300.0, "gebuehr_taker": 0.0005,
         "kill_switch_gesamt_usd": 20.0}


def sig(**u):
    s = {"instrument": "BTC/USD", "venue": "kraken", "direction": "long",
         "size_pct": 0.5, "source": "kraken-cli", "ts_utc": JETZT - 5,
         "expiry_s": 180, "mode": "paper"}
    s.update(u)
    return s


def zeile(sid, signal, was="signal"):
    import json
    return {"id": sid, "was": was, "wer": "fremd/kraken-cli",
            "text": json.dumps(signal)}


def kurs(p):
    return lambda inst: p


class EroeffnenTest(unittest.TestCase):

    def test_long_bekommt_stop_unter_einstieg(self):
        z = fp.leer()
        ok, g = fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        self.assertTrue(ok, g)
        p = z["offen"]["BTC/USD"]
        self.assertAlmostEqual(96.0, p["stop"])
        self.assertEqual("long", p["richtung"])

    def test_short_bekommt_stop_ueber_einstieg(self):
        z = fp.leer()
        fp.eroeffne(z, sig(direction="short"), 100.0, WACHE, "a", JETZT)
        self.assertAlmostEqual(104.0, z["offen"]["BTC/USD"]["stop"])

    def test_groesse_aus_risiko_und_deckel(self):
        z = fp.leer()
        fp.eroeffne(z, sig(size_pct=0.5), 100.0, WACHE, "a", JETZT)
        # Risiko 5 USD bei 4 % Stop = 125 USD; size_pct 0.5 * 250 = 125
        self.assertAlmostEqual(125.0, z["offen"]["BTC/USD"]["menge_usd"])
        z = fp.leer()
        fp.eroeffne(z, sig(size_pct=0.1), 100.0, WACHE, "a", JETZT)
        self.assertAlmostEqual(25.0, z["offen"]["BTC/USD"]["menge_usd"])

    def test_ohne_stop_regel_keine_position(self):
        for w in (dict(WACHE, stop_prozent=None), dict(WACHE, stop_prozent=1.0),
                  dict(WACHE, stop_prozent=9.0),
                  {k: v for k, v in WACHE.items() if k != "stop_prozent"}):
            z = fp.leer()
            ok, g = fp.eroeffne(z, sig(), 100.0, w, "a", JETZT)
            self.assertFalse(ok)
            self.assertIn("Stop", g)
            self.assertEqual({}, z["offen"])

    def test_grenzen_der_wache(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        ok, g = fp.eroeffne(z, sig(), 100.0, WACHE, "b", JETZT)
        self.assertFalse(ok)                      # gleiches Instrument schon offen
        fp.eroeffne(z, sig(instrument="ETH/USD"), 50.0, WACHE, "c", JETZT)
        w = dict(WACHE, max_offene_positionen=2)
        ok, g = fp.eroeffne(z, sig(instrument="BTC/USD", direction="short"), 1.0, w, "d", JETZT)
        self.assertFalse(ok)

    def test_gesamtdeckel(self):
        z = fp.leer()
        w = dict(WACHE, max_gesamt_usd=100.0)
        ok, g = fp.eroeffne(z, sig(), 100.0, w, "a", JETZT)   # 125 > 100
        self.assertFalse(ok)
        self.assertIn("gesamt", g)

    def test_kill_switch_nach_zu_viel_verlust(self):
        z = fp.leer()
        z["pnl_usd"] = -20.0
        ok, g = fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        self.assertFalse(ok)
        self.assertIn("Kill", g)

    def test_kein_preis_keine_position(self):
        for p in (None, 0, -1, float("nan"), "x"):
            ok, _ = fp.eroeffne(fp.leer(), sig(), p, WACHE, "a", JETZT)
            self.assertFalse(ok, p)


class SchliessenTest(unittest.TestCase):

    def test_stop_long_schliesst_mit_verlust_und_gebuehr(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        fp.stops_pruefen(z, kurs(96.0), WACHE, JETZT + 60)   # genau am Stop
        self.assertEqual({}, z["offen"])
        g = z["geschlossen"][0]
        self.assertEqual("stop", g["grund"])
        # 125 USD * (-4 %) = -5.0 ; Gebuehr 2 * 125 * 0.0005 = 0.125
        self.assertAlmostEqual(-5.0 - 0.125, g["pnl_usd"], places=3)
        self.assertAlmostEqual(g["pnl_usd"], z["pnl_usd"], places=6)

    def test_luecke_ueber_den_stop_wird_zum_marktpreis_geschlossen(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        fp.stops_pruefen(z, kurs(95.0), WACHE, JETZT + 60)
        self.assertAlmostEqual(-6.25 - 0.125, z["geschlossen"][0]["pnl_usd"], places=3)

    def test_stop_short(self):
        z = fp.leer()
        fp.eroeffne(z, sig(direction="short"), 100.0, WACHE, "a", JETZT)
        fp.stops_pruefen(z, kurs(105.0), WACHE, JETZT + 60)
        self.assertEqual({}, z["offen"])

    def test_kurs_im_korridor_laesst_offen(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        fp.stops_pruefen(z, kurs(99.0), WACHE, JETZT + 60)
        self.assertIn("BTC/USD", z["offen"])

    def test_kursausfall_haelt_position_und_wirft_nicht(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        def kaputt(inst):
            raise OSError("netz")
        fp.stops_pruefen(z, kaputt, WACHE, JETZT + 60)
        self.assertIn("BTC/USD", z["offen"])

    def test_flat_signal_schliesst(self):
        z = fp.leer()
        fp.eroeffne(z, sig(), 100.0, WACHE, "a", JETZT)
        s = sig(direction="flat")
        del s["size_pct"]
        ok, g = fp.eroeffne(z, s, 110.0, WACHE, "b", JETZT)
        self.assertTrue(ok, g)
        self.assertEqual({}, z["offen"])
        self.assertGreater(z["geschlossen"][0]["pnl_usd"], 0)


class VerarbeitenTest(unittest.TestCase):

    def test_signal_wird_einmal_ausgefuehrt(self):
        z = fp.leer()
        zl = [zeile("id1", sig())]
        fp.verarbeite(z, zl, kurs(100.0), WACHE, JETZT)
        fp.verarbeite(z, zl, kurs(100.0), WACHE, JETZT)
        self.assertEqual(1, len(z["offen"]))
        self.assertIn("id1", z["verarbeitet"])

    def test_verworfene_und_fremde_zeilen_werden_ignoriert(self):
        z = fp.leer()
        zl = [zeile("v", sig(), was="signal_verworfen"),
              {"id": "e", "was": "ende", "text": ""},
              {"id": "k", "was": "signal", "text": "kein json"}]
        fp.verarbeite(z, zl, kurs(100.0), WACHE, JETZT)
        self.assertEqual({}, z["offen"])

    def test_tor_wird_bei_der_ausfuehrung_erneut_geprueft(self):
        z = fp.leer()
        zu = dict(WACHE, fremd_signale_erlaubt=False)
        fp.verarbeite(z, [zeile("id1", sig())], kurs(100.0), zu, JETZT)
        self.assertEqual({}, z["offen"])

    def test_zu_altes_signal_wird_nicht_mehr_ausgefuehrt(self):
        z = fp.leer()
        fp.verarbeite(z, [zeile("id1", sig())], kurs(100.0), WACHE, JETZT + 500)
        self.assertEqual({}, z["offen"])

    def test_live_signal_wird_nie_ausgefuehrt(self):
        z = fp.leer()
        w = dict(WACHE, modi_erlaubt=["paper", "demo", "live"])
        fp.verarbeite(z, [zeile("id1", sig(mode="live"))], kurs(100.0), w, JETZT)
        self.assertEqual({}, z["offen"])


if __name__ == "__main__":
    unittest.main()
