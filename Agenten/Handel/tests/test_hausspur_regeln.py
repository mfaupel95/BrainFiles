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

    def test_ohne_atr_kein_einstieg(self):
        # Review M4: das Haus handelt bei ATR <= 0 nicht, der Adapter auch nicht.
        import dataclasses
        import types
        k = reihe()
        name = "macd_mtf"
        null = types.SimpleNamespace(atr_abs=lambda *_a: 0.0)
        ersatz = dataclasses.replace(hr.spur(name), einstieg=lambda _k, _w: "long",
                                     stop_prozent=hr._atr_stop(null))
        alt = hr.spur
        hr.spur = lambda n: ersatz if n == name else alt(n)
        try:
            s = hr.signale(k, name, ab=len(k) - 1)[-1]
        finally:
            hr.spur = alt
        self.assertIsNone(s["einstieg"])
        self.assertEqual(s["stop"], hr.STOP_VORGABE)

    def test_stop_und_ziel(self):
        k = reihe()
        w = dict(hr.wachen("klassik_ema"), festes_ziel=True)
        s = hr.signale(k, "klassik_ema", w, ab=len(k) - 1)[-1]
        self.assertEqual(s["stop"], 2.5)
        self.assertEqual(s["ziel"], 5.0)          # ziel_r_vielfaches 2.0 x 2.5

    def test_ohne_festes_ziel_kein_ziel(self):
        """festes_ziel false (Auftrag Max 08.10.2026, spur_buch.py): das Haus
        steigt nur ueber Stop und Regel aus - der Adapter darf kein Ziel setzen."""
        k = reihe()
        w = hr.wachen("klassik_ema")
        self.assertIs(w.get("festes_ziel"), False)
        s = hr.signale(k, "klassik_ema", ab=len(k) - 1)[-1]
        self.assertEqual(s["ziel"], hr.OHNE_ZIEL)
        self.assertEqual(s["stop"], 2.5)
        ohne_feld = {x: y for x, y in w.items() if x != "festes_ziel"}
        self.assertEqual(hr.signale(k, "klassik_ema", ohne_feld, ab=len(k) - 1)[-1]["ziel"], 5.0)
        m = hr.signale(k, "macd_mtf", ab=len(k) - 1)[-1]
        self.assertGreaterEqual(m["stop"], 5.0)   # ATR, in [5, 12] gezwungen
        self.assertLessEqual(m["stop"], 12.0)


class Sicher(unittest.TestCase):
    def test_gleicher_fehler_nur_einmal(self):
        # Review M9: ein Fehlertext je Lauf, nicht je Kerze.
        import contextlib
        import io
        hr._GEMELDET.clear()
        puffer = io.StringIO()

        def wirft():
            raise ValueError("kaputt")
        with contextlib.redirect_stderr(puffer):
            for _ in range(5):
                self.assertIsNone(hr._sicher(wirft))
        self.assertEqual(puffer.getvalue().count("kaputt"), 1)


def orb_tag(ausbruch_bei=5, richtung=1, tag_ms=1_760_054_400_000):
    """Ein UTC-Tag in 15-min-Kerzen; Range 100..110, Ausbruch an Kerze `ausbruch_bei`.

    tag_ms = 2025-10-10 00:00 UTC. Vorlauf: 300 Kerzen vom Vortag, damit
    mindest_kerzen erfuellt ist.
    """
    k = []
    for i in range(-300, 96):
        ts = tag_ms + i * 900_000
        o, h, l, c = 105.0, 110.0, 100.0, 105.0
        if i == ausbruch_bei:
            c = 112.0 if richtung > 0 else 98.0
            h, l = max(h, c), min(l, c)
        k.append([ts, o, h, l, c, 10.0])
    return k


class Orb(unittest.TestCase):
    PAAR = "ETH/USDT:USDT"

    def test_erster_ausbruch_long(self):
        k = orb_tag(5, +1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        idx = 300 + 5
        self.assertEqual(s[idx]["einstieg"], "long")
        self.assertTrue(all(x["einstieg"] is None for x in s[300:idx]))
        self.assertAlmostEqual(s[idx]["stop"], (112.0 - 100.0) / 112.0 * 100.0)
        w = hr.wachen("orb")
        self.assertAlmostEqual(s[idx]["ziel"], w["ziel_k"] * 10.0 / 112.0 * 100.0)

    def test_short(self):
        k = orb_tag(7, -1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertEqual(s[307]["einstieg"], "short")

    def test_nur_ein_einstieg_je_tag(self):
        k = orb_tag(5, +1)
        k[300 + 9][4] = 113.0                     # zweiter Ausbruch spaeter
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertIsNone(s[309]["einstieg"])

    def test_kein_einstieg_kurz_vor_schluss(self):
        k = orb_tag(93, +1)                       # 23:15 UTC
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertIsNone(s[393]["einstieg"])

    def test_letzte_kerze_vor_schluss_zaehlt_nach_ende(self):
        # Review M3: 22:45 schliesst um 23:00 = Schluss, das Haus lehnt dort ab.
        k = orb_tag(91, +1)                       # 22:45 UTC
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertIsNone(s[391]["einstieg"])
        k = orb_tag(90, +1)                       # 22:30 UTC, Ende 22:45
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertEqual(s[390]["einstieg"], "long")

    def test_session_ende(self):
        k = orb_tag(5, +1)
        s = hr.signale(k, "orb", paar=self.PAAR, ab=300)
        self.assertEqual(s[-1]["aus_long"], "session_ende")
        self.assertIsNone(s[-2]["aus_long"])


if __name__ == "__main__":
    unittest.main()
