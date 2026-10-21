#!/usr/bin/env python3
"""Test des richtungs-agnostischen Positionierungs-Filters in liq_wand.

KEIN Netzzugriff: `pos.stuetzt_richtung` wird ersetzt. Der Test beweist die
FILTER-Logik: fuer "long" und "short" wird die jeweilige Richtung geprueft,
und fail-soft bei fehlender Quelle.
"""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for o in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if o in sys.path:
        sys.path.remove(o)
    sys.path.insert(0, o)


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


H = _lade(os.path.join(SPUR, "handeln.py"), "handeln_liq_test")


def _d(seite, preis=100.0):
    """Daten, die ein Signal ausloesen: eine Wand nahe am Spot, >=20 Liqs."""
    return {
        "spot": preis,
        "liqs": [
            {"seite": seite, "preis": preis, "kontrakte": 100.0, "usd": 1.0, "ts": i}
            for i in range(25)
        ],
    }


class LiqFilter(unittest.TestCase):
    def setUp(self):
        self.w = {"mindest_liquidationen": 20, "bandbreite_prozent": 0.25,
                  "mindest_anteil": 0.30, "max_abstand_prozent": 2.0,
                  "hinter_dem_spot_prozent": 0.5, "kerzen_zeitrahmen": "1H"}
        self._pos = H.pos.stuetzt_richtung

    def tearDown(self):
        H.pos.stuetzt_richtung = self._pos

    def test_short_wand_gibt_long(self):
        """Short-Liquidationen = Kaufdruck = long-Signal (ohne Filter)."""
        H.pos.stuetzt_richtung = lambda *a, **kw: self.fail("darf nicht rufen")
        self.assertEqual(H.signal(_d("short"), dict(self.w)), "long")

    def test_long_wand_gibt_short(self):
        H.pos.stuetzt_richtung = lambda *a, **kw: self.fail("darf nicht rufen")
        self.assertEqual(H.signal(_d("long"), dict(self.w)), "short")

    def test_filter_aus_ruft_quelle_nicht(self):
        gerufen = []
        H.pos.stuetzt_richtung = lambda *a, **kw: gerufen.append(1)
        w = {**self.w, "positionierung_filter": False}
        self.assertEqual(H.signal(_d("short"), w), "long")
        self.assertEqual(gerufen, [])

    def test_long_stuetzt_nicht_blockiert(self):
        H.pos.stuetzt_richtung = lambda *a, **kw: {"quellen": 3, "stuetzt": False}
        w = {**self.w, "positionierung_filter": True}
        self.assertIsNone(H.signal(_d("short"), w))

    def test_long_stuetzt_laesst_durch(self):
        H.pos.stuetzt_richtung = lambda *a, **kw: {"quellen": 3, "stuetzt": True}
        w = {**self.w, "positionierung_filter": True}
        self.assertEqual(H.signal(_d("short"), w), "long")

    def test_keine_quelle_blockiert_nicht(self):
        H.pos.stuetzt_richtung = lambda *a, **kw: {"quellen": 0, "stuetzt": False}
        w = {**self.w, "positionierung_filter": True}
        self.assertEqual(H.signal(_d("short"), w), "long")


if __name__ == "__main__":
    unittest.main(verbosity=2)
