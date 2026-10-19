"""Ansatz B (Spec 10.10.2026, Phase 2): vektorisierte Spur gegen den Adapter.

Der Adapter (hausspur_regeln.signale) ist die Referenz. Die B-Fassung muss
JEDE Kerze gleich entscheiden - Einstieg, beide Ausstiege, Stop und Ziel.

Direkt ausfuehrbar:  python tests/test_hausspur_vektor.py
"""

import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import hausspur_regeln as hr                                   # noqa: E402
import hausspur_vektor as hv                                   # noqa: E402
from test_hausspur_regeln import reihe                         # noqa: E402


def zufall(n=1600, saat=7):
    """Irrfahrt mit wechselnder Drift: Ausbrueche, Trendwechsel, Seitwaerts."""
    rnd = random.Random(saat)
    k, c = [], 100.0
    for i in range(n):
        drift = 0.004 * math.sin(i / 150.0)
        o = c
        c = max(1.0, c * (1 + drift + rnd.gauss(0, 0.012)))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.004)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.004)))
        k.append([1_700_000_000_000 + i * 14_400_000, o, h, l, c, 1000.0])
    return k


def abweichungen(k, name, w=None):
    a = hr.signale(k, name, w)
    b = hv.signale(k, name, w)
    aus = []
    for i, x in enumerate(a):
        soll = (None, False, False, None, None) if x is None else (
            x["einstieg"], bool(x["aus_long"]), bool(x["aus_short"]), x["stop"], x["ziel"])
        ist = (b["einstieg"][i], bool(b["aus_long"][i]), bool(b["aus_short"][i]),
               None if math.isnan(b["stop"][i]) else float(b["stop"][i]),
               None if math.isnan(b["ziel"][i]) else float(b["ziel"][i]))
        if soll != ist:
            aus.append((i, soll, ist))
    return aus


class DonchianTrend(unittest.TestCase):
    NAME = "klassik_donchian_trend"

    def test_register(self):
        self.assertTrue(hv.hat(self.NAME))
        self.assertFalse(hv.hat("klassik_ema"))

    def test_gleich_auf_sinusreihe(self):
        self.assertEqual(abweichungen(reihe(), self.NAME), [])

    def test_gleich_auf_irrfahrt_mit_signalen(self):
        k = zufall()
        self.assertEqual(abweichungen(k, self.NAME), [])
        a = [x["einstieg"] for x in hr.signale(k, self.NAME) if x]
        self.assertGreater(a.count("long"), 5, "Reihe ohne Einstiege prueft nichts")

    def test_short_seite_ohne_nur_long(self):
        # Saaten 3/13/14 bei n=2000: dort entscheidet eine EMA ueber die ganze
        # Reihe 2-6 Kerzen anders als die Fenster-EMA (Mutantenprobe 12.10.2026)
        # - der Test faellt also, wenn die Fenstertreue verloren geht.
        w = dict(hr.wachen(self.NAME), nur_long=False)
        for saat in (3, 13, 14):
            k = zufall(n=2000, saat=saat)
            self.assertEqual(abweichungen(k, self.NAME, w), [], saat)
        a = [x["einstieg"] for x in hr.signale(zufall(saat=3), self.NAME, w) if x]
        self.assertIn("short", a)

    def test_kurze_reihe_ohne_signal(self):
        k = zufall(n=200)
        b = hv.signale(k, self.NAME)
        self.assertEqual(set(b["einstieg"]), {None})
        self.assertTrue(all(math.isnan(x) for x in b["stop"]))

    def test_unbekannte_spur(self):
        with self.assertRaises(KeyError):
            hv.signale(reihe(), "klassik_ema")


if __name__ == "__main__":
    unittest.main()
