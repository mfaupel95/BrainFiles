"""hausspur_regeln: eine Schnittstelle fuer alle Haus-Spuren (Freqtrade-Adapter).

Geprueft wird die Zusage, auf der der ganze Adapter steht: dieselbe Kerze gibt
dasselbe Signal wie die Spur selbst - fuer klassik_* ueber REGELN, fuer die
Indikatorspuren ueber ihr handeln.signal(k, idx, w).

Direkt ausfuehrbar:  python tests/test_hausspur_regeln.py
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hausspur_regeln as hr                                   # noqa: E402
import klassik_regeln as kr                                    # noqa: E402


def reihe(n=900, start=100.0):
    """Deterministische Kerzen mit Trends und Wenden, 1h-Abstand."""
    k, c = [], start
    for i in range(n):
        o = c
        c = start * (1 + 0.15 * math.sin(i / 37.0) + 0.05 * math.sin(i / 7.0))
        h = max(o, c) * 1.004
        l = min(o, c) * 0.996
        k.append([1_700_000_000_000 + i * 3_600_000, o, h, l, c, 1000 + i % 50])
    return k


class Register(unittest.TestCase):
    def test_alle_siebzehn(self):
        self.assertEqual(len(hr.ALLE), 17)
        for name in hr.ALLE:
            self.assertEqual(hr.spur(name).name, name)

    def test_unbekannt_nennt_namen(self):
        with self.assertRaises(KeyError) as cm:
            hr.spur("gibtsnicht")
        self.assertIn("gibtsnicht", str(cm.exception))

    def test_zeitrahmen_und_paare(self):
        self.assertEqual(hr.zeitrahmen("klassik_ema"), "4h")
        self.assertEqual(hr.zeitrahmen("macd_mtf"), "1h")
        self.assertEqual(hr.zeitrahmen("supertrend"), "4h")
        self.assertEqual(hr.zeitrahmen("orb"), "15m")
        self.assertEqual(hr.paare("klassik_ema"),
                         ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"])
        self.assertEqual(hr.paare("macd_mtf"), ["BTC/USDT:USDT", "ETH/USDT:USDT"])
        self.assertEqual(hr.paare("trendwende_btc"), ["BTC/USDT:USDT"])
        self.assertEqual(hr.paare("orb"), ["BTC/USDT:USDT", "ETH/USDT:USDT"])


class GleichesSignal(unittest.TestCase):
    def test_klassik_wie_regeln(self):
        k = reihe()
        for name in hr.KLASSIK:
            w = hr.wachen(name)
            ein, _aus = kr.REGELN[name]
            fe = hr.fenster(w)
            s = hr.signale(k, name, w)
            for i in range(len(k)):
                fenster = k[max(0, i + 1 - fe):i + 1]
                if len(fenster) < int(w.get("mindest_kerzen", 210)):
                    self.assertIsNone(s[i], (name, i))
                    continue
                erwartet = ein(fenster, w)
                if erwartet == "short" and w.get("nur_long"):
                    erwartet = None
                self.assertEqual(s[i]["einstieg"], erwartet, (name, i))

    def test_indikator_wie_handeln(self):
        k = reihe()
        for name in hr.INDIKATOR:
            w = hr.wachen(name)
            modul = hr._modul(name)
            fe = hr.fenster(w)
            s = hr.signale(k, name, w, ab=len(k) - 60)
            for i in range(len(k) - 60, len(k)):
                fenster = k[max(0, i + 1 - fe):i + 1]
                roh = modul.signal(fenster, len(fenster) - 1, w)
                erwartet = roh[0] if isinstance(roh, tuple) else roh
                self.assertEqual(s[i]["einstieg"], erwartet, (name, i))


class Grenzen(unittest.TestCase):
    def test_zu_wenig_kerzen_kein_signal(self):
        k = reihe(30)
        for name in hr.ALLE:
            self.assertTrue(all(x is None for x in hr.signale(k, name)), name)

    def test_regel_wirft_kein_absturz(self):
        flach = [[1_700_000_000_000 + i * 3_600_000, 1.0, 1.0, 1.0, 1.0, 0.0]
                 for i in range(700)]
        for name in hr.ALLE:
            s = hr.signale(flach, name, paar="BTC/USDT:USDT", ab=650)
            self.assertEqual(len(s), 700, name)

    def test_ab_spart_rechnung(self):
        s = hr.signale(reihe(), "klassik_ema", ab=890)
        self.assertTrue(all(x is None for x in s[:890]))
        self.assertTrue(all(x is not None for x in s[890:]))

    def test_stop_und_ziel(self):
        k = reihe()
        s = hr.signale(k, "klassik_ema", ab=len(k) - 1)[-1]
        self.assertEqual(s["stop"], 2.5)
        self.assertEqual(s["ziel"], 5.0)          # ziel_r_vielfaches 2.0 x 2.5
        m = hr.signale(k, "macd_mtf", ab=len(k) - 1)[-1]
        self.assertGreaterEqual(m["stop"], 5.0)   # ATR, in [5, 12] gezwungen
        self.assertLessEqual(m["stop"], 12.0)


if __name__ == "__main__":
    unittest.main()
