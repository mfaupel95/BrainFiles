"""Tests fuer signal_schema: Vertrag der Fremd-Signale (Skill fremdrepos-signal).

Geprueft wird die REGEL: Pflichtfelder, nie live, Stale-Verwurf, Stop-Pflicht
wo ein Stop mitkommt. Kein Netz, keine Uhr (jetzt wird uebergeben).
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))

import signal_schema as ss                                           # noqa: E402

JETZT = 1_728_432_100


def gut(**ueber):
    s = {"instrument": "BTC/USD", "venue": "okx", "direction": "long",
         "size_pct": 0.5, "source": "agent-trade-kit", "ts_utc": JETZT - 10,
         "expiry_s": 180, "mode": "demo"}
    s.update(ueber)
    return s


class SchemaTest(unittest.TestCase):

    def test_gutes_signal_ist_gueltig(self):
        self.assertEqual((True, "ok"), ss.pruefe(gut(), jetzt=JETZT))

    def test_fehlendes_pflichtfeld_wird_verworfen(self):
        for feld in ss.PFLICHT:
            s = gut()
            del s[feld]
            ok, grund = ss.pruefe(s, jetzt=JETZT)
            self.assertFalse(ok, feld)
            self.assertIn(feld, grund)

    def test_live_wird_nie_angenommen(self):
        ok, grund = ss.pruefe(gut(mode="live"), jetzt=JETZT)
        self.assertFalse(ok)
        self.assertIn("mode", grund)

    def test_unbekannter_modus_wird_verworfen(self):
        self.assertFalse(ss.pruefe(gut(mode="echt"), jetzt=JETZT)[0])

    def test_stale_signal_wird_verworfen_ohne_retry(self):
        ok, grund = ss.pruefe(gut(ts_utc=JETZT - 181), jetzt=JETZT)
        self.assertFalse(ok)
        self.assertIn("stale", grund)

    def test_genau_am_rand_gilt_noch(self):
        self.assertTrue(ss.pruefe(gut(ts_utc=JETZT - 180), jetzt=JETZT)[0])

    def test_zeitstempel_aus_der_zukunft_wird_verworfen(self):
        self.assertFalse(ss.pruefe(gut(ts_utc=JETZT + 600), jetzt=JETZT)[0])

    def test_richtung_und_venue_geschlossene_mengen(self):
        self.assertFalse(ss.pruefe(gut(direction="hoch"), jetzt=JETZT)[0])
        self.assertFalse(ss.pruefe(gut(venue="binance"), jetzt=JETZT)[0])

    def test_groesse_muss_zwischen_null_und_eins_liegen(self):
        for v in (0, -0.1, 1.01, "viel", True):
            self.assertFalse(ss.pruefe(gut(size_pct=v), jetzt=JETZT)[0], v)

    def test_expiry_muss_positive_zahl_sein(self):
        for v in (0, -5, "x", None):
            self.assertFalse(ss.pruefe(gut(expiry_s=v), jetzt=JETZT)[0], v)

    def test_flat_braucht_keine_groesse(self):
        s = gut(direction="flat")
        del s["size_pct"]
        self.assertTrue(ss.pruefe(s, jetzt=JETZT)[0])

    def test_kein_dict_wird_verworfen(self):
        self.assertFalse(ss.pruefe("long", jetzt=JETZT)[0])
        self.assertFalse(ss.pruefe(None, jetzt=JETZT)[0])


if __name__ == "__main__":
    unittest.main()
