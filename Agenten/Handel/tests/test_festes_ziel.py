"""Tests: `festes_ziel` in spur_buch.pruefe_ausstiege (Auftrag Max 08.10.2026).

Ohne das Feld (oder mit true) loest das Ziel aus wie bisher. Mit
`festes_ziel: false` ist das Ziel nur Richtmarke: es loest nicht aus, der
Stop weiterhin. spur_buch wird ueber den Pfad geladen (Hausregel aus tests/).
"""

import csv
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

spec = importlib.util.spec_from_file_location("spur_buch_festes_ziel", os.path.join(HANDEL, "spur_buch.py"))
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)


def position(seite="long"):
    vz = 1 if seite == "long" else -1
    return {"inst": "BTC-USDT-SWAP", "seite": seite, "einstieg": 100.0,
            "stop": 100.0 - vz * 5.0, "ziel": 100.0 + vz * 10.0, "stop_pct": 5.0,
            "nominal": 1000.0, "modus": "papier", "pos_id": "t-1"}


class FestesZielTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="festes-ziel-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.journal = os.path.join(self.tmp, "handelsjournal.csv")
        self.zustand = os.path.join(self.tmp, "zustand.json")
        sb.lege_journal_an(self.journal)

    def _lauf(self, seite, kurs, w):
        z = {"positionen": [position(seite)]}
        sb.pruefe_ausstiege(z, {"BTC-USDT-SWAP": kurs}, w, self.journal,
                            zustand_pfad=self.zustand)
        with open(self.journal, encoding="utf-8", newline="") as f:
            gruende = [r.get("grund") for r in csv.DictReader(f) if r.get("aktion") == "verkauf"]
        return z["positionen"], gruende

    def test_standard_ziel_loest_aus(self):
        for w in ({}, {"festes_ziel": True}):
            offen, gruende = self._lauf("long", 111.0, w)
            self.assertEqual(offen, [], w)
            self.assertEqual(gruende, ["ziel"], w)
            self.setUp()

    def test_ohne_festes_ziel_loest_das_ziel_nicht_aus_long(self):
        offen, gruende = self._lauf("long", 111.0, {"festes_ziel": False})
        self.assertEqual(len(offen), 1)
        self.assertEqual(gruende, [])

    def test_ohne_festes_ziel_loest_das_ziel_nicht_aus_short(self):
        offen, gruende = self._lauf("short", 89.0, {"festes_ziel": False})
        self.assertEqual(len(offen), 1)
        self.assertEqual(gruende, [])

    def test_stop_gilt_weiter_ohne_festes_ziel(self):
        for seite, kurs in (("long", 94.0), ("short", 106.0)):
            offen, gruende = self._lauf(seite, kurs, {"festes_ziel": False})
            self.assertEqual(offen, [], seite)
            self.assertEqual(gruende, ["stop"], seite)
            self.setUp()


class WachenTest(unittest.TestCase):
    """Die fuenf getesteten Trendspuren tragen das Flag; alle anderen nicht."""

    MIT = ("klassik_ema", "klassik_sma", "klassik_macd", "klassik_donchian_trend",
           "klassik_supertrend")

    def test_trendspuren_ohne_festes_ziel(self):
        for name in self.MIT:
            with open(os.path.join(HANDEL, name, "wachen.json"), encoding="utf-8") as f:
                w = json.load(f)
            self.assertIs(w.get("festes_ziel"), False, name)
            self.assertIn("ziel_r_vielfaches", w, name)     # Richtmarke bleibt
            self.assertFalse(w.get("handel_erlaubt"), name)  # nur Papier

    def test_andere_klassik_spuren_unveraendert(self):
        for name in ("klassik_rsi", "klassik_rsi2", "klassik_bollinger", "klassik_donchian",
                     "klassik_pmax", "klassik_sr_breaks"):
            with open(os.path.join(HANDEL, name, "wachen.json"), encoding="utf-8") as f:
                w = json.load(f)
            self.assertNotIn("festes_ziel", w, name)


if __name__ == "__main__":
    unittest.main()
