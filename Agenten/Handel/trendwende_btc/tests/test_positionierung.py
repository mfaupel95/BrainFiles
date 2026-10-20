#!/usr/bin/env python3
"""Test des Positionierungs-Filters in trendwende_btc.

KEIN Netzzugriff: `pos.kipp_abwaerts` wird ersetzt. Der Test beweist die
FILTER-Logik, nicht den SuperTrend - deshalb werden xi.supertrend/xi.ema
gemockt, damit das Basissignal deterministisch ist. Drei Dinge:
  1. Filter AUS (Standard) -> das Signal bleibt unveraendert.
  2. Filter AN und Positionierung stuetzt NICHT -> kein Signal.
  3. Filter AN, aber KEINE Quelle erreichbar -> das Signal bleibt (fail-soft).
"""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for o in (SPUR, HANDEL, os.path.join(HANDEL, "xperp"), os.path.join(HANDEL, "scanner")):
    if o not in sys.path:
        sys.path.insert(0, o)


def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


H = _lade(os.path.join(SPUR, "handeln.py"), "handeln_trendwende_test")


def _basis_signal_kerzen(n=260):
    """Genug Kerzen, damit signal() die Laengenpruefung passiert. Der
    SuperTrend/EMA wird im Test gemockt, die Werte hier sind egal."""
    k = []
    for i in range(n):
        k.append([str(i), 100.0, 101.0, 99.0, 100.0, "1"])
    return k


class PositionierungsFilter(unittest.TestCase):
    def setUp(self):
        self.d = {"kerzen": _basis_signal_kerzen()}
        self.w = {"supertrend_n": 10, "supertrend_faktor": 3.0,
                  "ema_filter_n": 200, "kerzen_zeitrahmen": "1H"}
        # Deterministisches Basissignal: SuperTrend dreht 1 -> -1, unter EMA200.
        self._st = H.xi.supertrend
        self._ema = H.xi.ema
        H.xi.supertrend = lambda k, n=10, faktor=3.0: (None, [1] * (len(k) - 2) + [1, -1])
        H.xi.ema = lambda w, n=200: [200.0] * len(w)   # Schluss 100 < 200
        self._pos = H.pos.kipp_abwaerts

    def tearDown(self):
        H.xi.supertrend = self._st
        H.xi.ema = self._ema
        H.pos.kipp_abwaerts = self._pos

    def test_basissignal_steht(self):
        """Vorbedingung: ohne Filter liefert die Lage ueberhaupt ein short."""
        H.pos.kipp_abwaerts = lambda *a, **kw: self.fail("darf nicht rufen")
        self.assertEqual(H.signal(self.d, dict(self.w)), "short")

    def test_filter_aus_ruft_die_quelle_nicht(self):
        """Standard AUS: kein Aufruf der Fremdquelle, Signal unveraendert."""
        gerufen = []
        H.pos.kipp_abwaerts = lambda *a, **kw: gerufen.append(1)
        w = {**self.w, "positionierung_filter": False}
        self.assertEqual(H.signal(self.d, w), "short")
        self.assertEqual(gerufen, [])

    def test_stuetzt_nicht_unterdrueckt_das_signal(self):
        H.pos.kipp_abwaerts = lambda *a, **kw: {"quellen": 3, "stuetzt": False}
        w = {**self.w, "positionierung_filter": True}
        self.assertIsNone(H.signal(self.d, w))

    def test_stuetzt_laesst_das_signal_durch(self):
        H.pos.kipp_abwaerts = lambda *a, **kw: {"quellen": 3, "stuetzt": True}
        w = {**self.w, "positionierung_filter": True}
        self.assertEqual(H.signal(self.d, w), "short")

    def test_keine_quelle_blockiert_nicht(self):
        """Fail-soft: 0 Quellen = kein Urteil = das Signal bleibt."""
        H.pos.kipp_abwaerts = lambda *a, **kw: {"quellen": 0, "stuetzt": False}
        w = {**self.w, "positionierung_filter": True}
        self.assertEqual(H.signal(self.d, w), "short")


class ModulVertrag(unittest.TestCase):
    """Das Modul muss ohne Netz importierbar sein und None-tolerant bleiben."""

    def test_kipp_feldnamen(self):
        p = _lade(os.path.join(HANDEL, "okx_positionierung.py"), "pos_vertrag")
        p._hol = lambda pfad: None          # Netz aus
        u = p.kipp_abwaerts("BTC", "1H")
        self.assertEqual(u["quellen"], 0)
        self.assertFalse(u["stuetzt"])
        for feld in ("ls_faellt", "oi_faellt", "verkaufsdruck"):
            self.assertIsNone(u[feld])


if __name__ == "__main__":
    unittest.main(verbosity=2)
