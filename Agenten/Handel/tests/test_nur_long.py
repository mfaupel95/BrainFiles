"""Tests: `nur_long` in den Klassik-Trendspuren (Auftrag Max 09.10.2026).

Short-Signale eroeffnen nichts; der Regelausstieg (Gegensignal) bleibt
unberuehrt. Ohne das Feld verhaelt sich jede Spur wie bisher.
"""

import importlib.util
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

spec = importlib.util.spec_from_file_location("kr_nur_long", os.path.join(HANDEL, "klassik_regeln.py"))
kr = importlib.util.module_from_spec(spec)
sys.modules["kr_nur_long"] = kr
spec.loader.exec_module(kr)

MIT = ("klassik_ema", "klassik_sma", "klassik_macd", "klassik_donchian_trend", "klassik_supertrend")
OHNE = ("klassik_rsi", "klassik_rsi2", "klassik_bollinger", "klassik_donchian", "klassik_pmax",
        "klassik_sr_breaks")


def wachen(name):
    with open(os.path.join(HANDEL, name, "wachen.json"), encoding="utf-8") as f:
        return json.load(f)


class SignalTest(unittest.TestCase):
    def setUp(self):
        self.alt = kr.REGELN["klassik_sma"]
        self.addCleanup(lambda: kr.REGELN.__setitem__("klassik_sma", self.alt))

    def _signal(self, regel_ergebnis, w):
        kr.REGELN["klassik_sma"] = (lambda k, w_: regel_ergebnis, self.alt[1])
        _quelle, signal, _aus, _preis = kr.bauen("klassik_sma")
        return signal({"kerzen": [[0, 1, 1, 1, 1, 1]] * 5}, dict(w, mindest_kerzen=1))

    def test_short_wird_mit_nur_long_verworfen(self):
        self.assertIsNone(self._signal("short", {"nur_long": True}))

    def test_long_geht_durch(self):
        self.assertEqual(self._signal("long", {"nur_long": True}), "long")

    def test_ohne_feld_oder_false_bleibt_short(self):
        self.assertEqual(self._signal("short", {}), "short")
        self.assertEqual(self._signal("short", {"nur_long": False}), "short")

    def test_kein_signal_bleibt_kein_signal(self):
        self.assertIsNone(self._signal(None, {"nur_long": True}))


class AusstiegBleibtTest(unittest.TestCase):
    def test_gegensignal_schliesst_long_trotz_nur_long(self):
        """Der Ausstieg liest nur_long nicht: ein Long wird am Short-Kreuz weiter beendet."""
        w = dict(wachen("klassik_sma"))
        self.assertTrue(w["nur_long"])
        ein, aus = kr.REGELN["klassik_sma"]
        schluesse = [100.0 + i for i in range(80)] + [180.0 - 2.0 * i for i in range(80)]
        k = [[i, c, c + 1, c - 1, c, 1.0] for i, c in enumerate(schluesse)]
        treffer = [n for n in range(60, len(k)) if ein(k[:n], w) == "short"]
        self.assertTrue(treffer, "Testdaten erzeugen kein Short-Kreuz")
        self.assertEqual(aus(k[:treffer[0]], "long", w), "gegensignal")


class WachenTest(unittest.TestCase):
    def test_trendspuren_nur_long_und_papier(self):
        for name in MIT:
            w = wachen(name)
            self.assertIs(w.get("nur_long"), True, name)
            self.assertFalse(w.get("handel_erlaubt"), name)
            self.assertIs(w.get("festes_ziel"), False, name)      # PR #16 bleibt gueltig

    def test_andere_klassik_spuren_unveraendert(self):
        for name in OHNE:
            self.assertNotIn("nur_long", wachen(name), name)


if __name__ == "__main__":
    unittest.main()
