"""Gleichheitsrahmen: B-Strategie gegen Adapter A, Kerze fuer Kerze.

Direkt ausfuehrbar:  python freqtrade/tests/test_gleichheit.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))

import gleichheit                                              # noqa: E402
import hausspur_regeln as hr                                   # noqa: E402
from test_hausspur_regeln import reihe                         # noqa: E402


class Gleichheit(unittest.TestCase):
    def test_a_gegen_sich_selbst_ist_gleich(self):
        k = reihe()
        a = [x["einstieg"] if x else None for x in hr.signale(k, "klassik_ema")]
        self.assertEqual(gleichheit.vergleiche(k, "klassik_ema", a), [])

    def test_abweichung_wird_gemeldet(self):
        k = reihe()
        a = [x["einstieg"] if x else None for x in hr.signale(k, "klassik_ema")]
        b = list(a)
        b[-1] = "short" if a[-1] != "short" else None
        self.assertEqual(gleichheit.vergleiche(k, "klassik_ema", b),
                         [(len(k) - 1, a[-1], b[-1])])

    def test_laenge_muss_passen(self):
        with self.assertRaises(ValueError):
            gleichheit.vergleiche(reihe(), "klassik_ema", [None])


if __name__ == "__main__":
    unittest.main()
