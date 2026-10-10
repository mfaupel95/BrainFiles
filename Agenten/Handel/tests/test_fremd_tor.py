"""Tests fuer fremd_tor: das wachen.json-Tor fuer Fremd-Signale.

Geprueft wird die REGEL: Tor zu ist der Normalzustand, Live kommt nie durch,
jede Liste ist eine Zulassungsliste, ein kaputtes Tor schliesst.
"""
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))

import fremd_tor as ft                                               # noqa: E402

JETZT = 1_728_432_100
OFFEN = {"fremd_signale_erlaubt": True, "modi_erlaubt": ["paper", "demo"],
         "quellen_erlaubt": ["kraken-cli"], "instrumente_erlaubt": ["BTC/USD"],
         "size_pct_max": 0.25}


def sig(**ueber):
    s = {"instrument": "BTC/USD", "venue": "kraken", "direction": "long",
         "size_pct": 0.2, "source": "kraken-cli", "ts_utc": JETZT - 5,
         "expiry_s": 180, "mode": "paper"}
    s.update(ueber)
    return s


class TorTest(unittest.TestCase):

    def test_offenes_tor_laesst_gutes_signal_durch(self):
        self.assertEqual((True, "ok"), ft.entscheide(sig(), OFFEN, JETZT))

    def test_tor_zu_ist_normalzustand(self):
        for w in ({}, dict(OFFEN, fremd_signale_erlaubt=False),
                  dict(OFFEN, fremd_signale_erlaubt="ja"), None, "kaputt"):
            ok, grund = ft.entscheide(sig(), w, JETZT)
            self.assertFalse(ok, w)
            self.assertIn("Tor", grund)

    def test_live_kommt_nie_durch_auch_wenn_die_liste_es_erlaubt(self):
        w = dict(OFFEN, modi_erlaubt=["paper", "demo", "live"])
        self.assertFalse(ft.entscheide(sig(mode="live"), w, JETZT)[0])

    def test_modus_muss_in_der_liste_stehen(self):
        w = dict(OFFEN, modi_erlaubt=["demo"])
        self.assertFalse(ft.entscheide(sig(mode="paper"), w, JETZT)[0])

    def test_quelle_und_instrument_sind_zulassungslisten(self):
        self.assertFalse(ft.entscheide(sig(source="moon-dev"), OFFEN, JETZT)[0])
        self.assertFalse(ft.entscheide(sig(instrument="DOGE/USD"), OFFEN, JETZT)[0])

    def test_fehlende_liste_heisst_nichts_erlaubt(self):
        w = {k: v for k, v in OFFEN.items() if k != "instrumente_erlaubt"}
        self.assertFalse(ft.entscheide(sig(), w, JETZT)[0])

    def test_groesse_ueber_deckel_wird_abgelehnt(self):
        self.assertFalse(ft.entscheide(sig(size_pct=0.26), OFFEN, JETZT)[0])
        self.assertTrue(ft.entscheide(sig(size_pct=0.25), OFFEN, JETZT)[0])

    def test_fehlender_deckel_heisst_kein_signal(self):
        w = {k: v for k, v in OFFEN.items() if k != "size_pct_max"}
        self.assertFalse(ft.entscheide(sig(), w, JETZT)[0])

    def test_flat_braucht_keinen_deckel_wert(self):
        s = sig(direction="flat")
        del s["size_pct"]
        self.assertTrue(ft.entscheide(s, OFFEN, JETZT)[0])

    def test_schemafehler_zaehlen_zuerst(self):
        ok, grund = ft.entscheide(sig(ts_utc=JETZT - 999), OFFEN, JETZT)
        self.assertFalse(ok)
        self.assertIn("stale", grund)

    def test_mitgelieferte_wachen_json_ist_sicher(self):
        # Tor am 11.10.2026 auf Max' Ansage geoeffnet; geprueft werden die Garantien, nicht der Zustand.
        p = os.path.join(HIER, "..", "fremd_signale", "wachen.json")
        with open(p, encoding="utf-8") as f:
            w = json.load(f)
        self.assertIsInstance(w["fremd_signale_erlaubt"], bool)
        self.assertNotIn("live", w["modi_erlaubt"])
        self.assertTrue(set(w["modi_erlaubt"]) <= {"paper", "demo"})
        self.assertTrue(0 < w["pflicht_stop_prozent_min"] <= w["stop_prozent"] <= w["pflicht_stop_prozent_max"])
        ok, _ = ft.entscheide(sig(mode="live"), w, JETZT)
        self.assertFalse(ok)

    def test_laden_schliesst_bei_kaputter_datei(self):
        self.assertIsNone(ft.lade(os.path.join(HIER, "gibt_es_nicht.json")))


if __name__ == "__main__":
    unittest.main()
