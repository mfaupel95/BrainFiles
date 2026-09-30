"""Tests fuer klassik_regeln - reine Funktionen, ohne Netz."""

import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import klassik_regeln as kr  # noqa: E402


def kerzen(closes, spanne=1.0):
    return [[i, c, c + spanne, c - spanne, c, 1.0] for i, c in enumerate(closes)]


class Indikatoren(unittest.TestCase):
    def test_sma_ema_laenge_und_start(self):
        w = list(range(1, 11))
        self.assertEqual(kr.sma(w, 3)[2], 2.0)
        self.assertIsNone(kr.sma(w, 3)[1])
        self.assertEqual(kr.ema(w, 3)[2], 2.0)

    def test_rsi_extreme(self):
        self.assertEqual(kr.rsi(list(range(1, 30)), 14)[-1], 100.0)
        self.assertLess(kr.rsi(list(range(30, 1, -1)), 14)[-1], 1.0)

    def test_bollinger_konstante_reihe_hat_null_breite(self):
        m, o, u = kr.bollinger([5.0] * 30, 20, 2.0)
        self.assertEqual(o[-1], 5.0)
        self.assertEqual(u[-1], 5.0)

    def test_kreuz_nur_auf_dem_wechsel(self):
        self.assertTrue(kr.kreuzt_auf([1, 1, 3], [2, 2, 2]))
        self.assertFalse(kr.kreuzt_auf([1, 3, 4], [2, 2, 2]))   # schon oben
        self.assertTrue(kr.kreuzt_ab([3, 3, 1], 2))


class Regeln(unittest.TestCase):
    W = {}

    def test_donchian_ausbruch_zaehlt_kanal_davor(self):
        # Vorlage-Fehler: mit der laufenden Kerze im Kanal waere das nie wahr.
        c = [100.0] * 25 + [110.0]
        self.assertEqual(kr.einstieg_donchian(kerzen(c), self.W), "long")
        c = [100.0] * 25 + [90.0]
        self.assertEqual(kr.einstieg_donchian(kerzen(c), self.W), "short")
        self.assertIsNone(kr.einstieg_donchian(kerzen([100.0] * 26), self.W))

    def test_donchian_ausstieg_zehnerkanal(self):
        c = [100.0] * 25 + [98.0]
        self.assertEqual(kr.ausstieg_donchian(kerzen(c), "long", self.W), "kanal")
        self.assertIsNone(kr.ausstieg_donchian(kerzen(c), "short", self.W))

    def test_sma_kreuz_long_und_gegensignal(self):
        c = [100.0] * 60 + [95.0] * 10 + [130.0] * 3
        k = kerzen(c)
        gefunden = [kr.einstieg_sma(k[:n], self.W) for n in range(55, len(k) + 1)]
        self.assertIn("long", gefunden)

    def test_rsi_rueckkehr_long_unter_30(self):
        c = [100.0 - i for i in range(25)] + [80.0, 84.0]
        k = kerzen(c)
        gef = [kr.einstieg_rsi(k[:n], self.W) for n in range(16, len(k) + 1)]
        self.assertIn("long", gef)

    def test_rsi2_verlangt_grossen_trend(self):
        # steigender Trend, dann scharfer Ruecksetzer -> long
        c = [100.0 + i * 0.5 for i in range(220)] + [190.0, 185.0, 180.0]
        self.assertEqual(kr.einstieg_rsi2_trend(kerzen(c), self.W), "long")
        # gleicher Ruecksetzer im Abwaertstrend -> kein Long
        c = [300.0 - i * 0.5 for i in range(220)] + [190.0, 185.0, 180.0]
        self.assertIsNone(kr.einstieg_rsi2_trend(kerzen(c), self.W))

    def test_donchian_trend_filtert_gegen_die_steigung(self):
        # Ausbruch nach oben, aber EMA200 faellt -> kein Long
        c = [300.0 - i * 0.5 for i in range(230)] + [200.0] * 5 + [400.0]
        self.assertIsNone(kr.einstieg_donchian_trend(kerzen(c), self.W))

    def test_alle_regeln_registriert_und_aufrufbar(self):
        k = kerzen([100.0 + (i % 7) for i in range(260)])
        for name, (ein, aus) in kr.REGELN.items():
            self.assertIn(ein(k, {}), (None, "long", "short"), name)
            self.assertIn(aus(k, "long", {}), (None, "gegensignal", "kanal",
                                               "mitte", "sma5"), name)

    def test_bauen_signal_zu_wenig_kerzen(self):
        _q, signal, _a = kr.bauen("klassik_sma")
        self.assertIsNone(signal({"kerzen": kerzen([100.0] * 30)}, {}))

    def test_quelle_meldet_fehler_statt_zu_raten(self):
        alt = kr._kerzen
        kr._kerzen = lambda *a: (_ for _ in ()).throw(RuntimeError("weg"))
        try:
            quelle, _s, _a = kr.bauen("klassik_ema")
            daten, kurse, fehler = quelle({"instrumente": ["BTC-USDT-SWAP"]})
        finally:
            kr._kerzen = alt
        self.assertEqual(daten, {})
        self.assertEqual(len(fehler), 1)


class RegelnFein(unittest.TestCase):
    """Die Regeln, die in der ersten Fassung fehlten - je Richtung eine Probe."""

    W = {}

    @staticmethod
    def irgendwann(fn, closes):
        """Den Wechsel suchen: ueber alle Kerzenpraefixe, in denen er auftritt."""
        k = kerzen(closes)
        return [fn(k[:n], RegelnFein.W) for n in range(30, len(k) + 1)]

    def test_ema_kreuz_long_und_short(self):
        gef = self.irgendwann(kr.einstieg_ema, [100.0] * 40 + [120.0] * 6)
        self.assertIn("long", gef)
        gef = self.irgendwann(kr.einstieg_ema, [100.0] * 40 + [80.0] * 6)
        self.assertIn("short", gef)

    def test_macd_kreuz_long_und_short(self):
        gef = self.irgendwann(kr.einstieg_macd, [100.0] * 60 + [130.0] * 10)
        self.assertIn("long", gef)
        gef = self.irgendwann(kr.einstieg_macd, [100.0] * 60 + [70.0] * 10)
        self.assertIn("short", gef)

    def test_macd_signal_ist_auf_die_linie_ausgerichtet(self):
        """Das Signal ist ein EMA der Linie und beginnt `signal_n - 1` Kerzen
        nach ihr. Eine falsch versetzte Reihe wuerde nie einen Wechsel finden -
        die Ausrichtung ist die Eigenschaft, nicht der Startwert."""
        n = 9
        linie, sig = kr.macd([100.0 + (i % 5) for i in range(60)], signal=n)
        start = next(i for i, x in enumerate(linie) if x is not None)
        self.assertTrue(all(x is None for x in sig[:start + n - 1]))
        self.assertIsNotNone(sig[start + n - 1])

    def test_macd_findet_den_wechsel_auf_der_ganzen_reihe(self):
        """Gegenprobe zur Ausrichtung: auf einer Reihe mit Kreuz gibt es ein Signal."""
        gef = self.irgendwann(kr.einstieg_macd, [100.0] * 60 + [130.0] * 10)
        self.assertIn("long", gef)

    def test_bollinger_band_kreuz_long_und_short(self):
        # EIN Sprung: das Kreuz entsteht auf der letzten Kerze. Bei mehreren
        # Sprungkerzen ist der Schluss schon vorher ueber dem Band - dann ist es
        # kein Kreuz mehr, sondern ein Zustand.
        self.assertEqual(kr.einstieg_bollinger(kerzen([100.0] * 40 + [130.0]), self.W), "long")
        self.assertEqual(kr.einstieg_bollinger(kerzen([100.0] * 40 + [70.0]), self.W), "short")
        self.assertIsNone(kr.einstieg_bollinger(kerzen([100.0] * 40), self.W))

    def test_rsi_ausstieg_mitte(self):
        c = [100.0 - i for i in range(25)] + [80.0 + i for i in range(10)]
        gef = self.irgendwann(lambda k, w: kr.ausstieg_rsi(k, "long", w), c)
        self.assertIn("mitte", gef)

    def test_rsi2_ausstieg_sma5(self):
        self.assertEqual(kr.ausstieg_rsi2(kerzen([100.0] * 30 + [120.0] * 2), "long", self.W), "sma5")
        self.assertIsNone(kr.ausstieg_rsi2(kerzen([100.0] * 32), "long", self.W))

    def test_rsi2_short_braucht_trend_nach_unten(self):
        c = [300.0 - i * 0.5 for i in range(220)] + [210.0, 215.0, 230.0]
        self.assertEqual(kr.einstieg_rsi2_trend(kerzen(c), self.W), "short")

    def test_donchian_trend_laesst_den_ausbruch_im_aufwaertstrend_durch(self):
        c = [100.0 + i * 0.5 for i in range(230)] + [230.0, 240.0]
        self.assertEqual(kr.einstieg_donchian_trend(kerzen(c), self.W), "long")

    def test_gegenkreuz_kennt_beide_seiten(self):
        f = kr._gegen_kreuz(lambda k, w: "long")
        k = kerzen([100.0] * 5)
        self.assertIsNone(f(k, "long", self.W), "die eigene Seite ist kein Gegensignal")
        self.assertEqual(f(k, "short", self.W), "gegensignal")

    def test_kreuz_mit_none_ist_kein_kreuz(self):
        """Vor dem ersten Indikatorwert darf kein Signal entstehen."""
        self.assertFalse(kr.kreuzt_auf([None, 3.0], [2.0, 2.0]))
        self.assertFalse(kr.kreuzt_auf([1.0], [2.0]))

    def test_kanal_ohne_vorgeschichte_ist_none(self):
        k = kerzen([1.0, 2.0])
        self.assertIsNone(kr.kanal_hoch(k, 5, 1))
        self.assertIsNone(kr.kanal_tief(k, 5, 1))


class BauenVertrag(unittest.TestCase):
    """`bauen()` ist die Naht zu Buch und Replay - sie muss die Wachen lesen."""

    W = {"kerzen_anzahl": 400, "kerzen_zeitrahmen": "4H"}

    def test_ausstieg_ist_abschaltbar(self):
        _q, _s, ausstieg = kr.bauen("klassik_ema")
        p = {"inst": "BTC-USDT-SWAP", "seite": "long"}
        self.assertIsNone(ausstieg(p, {"ausstieg_bei_regel": False}))

    def test_ausstieg_ohne_seite_fragt_die_boerse_nicht(self):
        """Ohne long/short gibt es nichts zu pruefen - und keinen Abruf."""
        alt = kr._kerzen
        kr._kerzen = lambda *a, **k: kerzen([100.0] * 60)
        try:
            _q, _s, ausstieg = kr.bauen("klassik_ema")
            self.assertIsNone(ausstieg({"inst": "BTC-USDT-SWAP"}, self.W))
        finally:
            kr._kerzen = alt

    def test_ausstieg_wartet_auf_genug_kerzen(self):
        alt = kr._kerzen
        kr._kerzen = lambda *a, **k: kerzen([100.0] * 10)
        try:
            _q, _s, ausstieg = kr.bauen("klassik_ema")
            p = {"inst": "BTC-USDT-SWAP", "seite": "long"}
            self.assertIsNone(ausstieg(p, self.W))
        finally:
            kr._kerzen = alt

    def test_signal_und_ausstieg_kommen_aus_derselben_regel(self):
        for name in kr.REGELN:
            with self.subTest(spur=name):
                quelle, signal, ausstieg = kr.bauen(name)
                self.assertTrue(callable(quelle))
                self.assertTrue(callable(signal))
                self.assertTrue(callable(ausstieg))

    def test_quelle_verwirft_die_laufende_kerze(self):
        """OKX liefert die laufende Kerze mit - sie darf nie in die Rechnung."""
        roh = [[i, 1.0, 1.0, 1.0, 100.0 + i, 1.0] for i in range(5)]
        alt = kr._kerzen
        kr._cache.clear()
        try:
            quelle, _s, _a = kr.bauen("klassik_ema")
            kr._kerzen = lambda *a, **k: roh[:-1]      # so liefert es der Kern
            daten, kurse, _f = quelle({"instrumente": ["BTC-USDT-SWAP"]})
        finally:
            kr._kerzen = alt
            kr._cache.clear()
        self.assertEqual(kurse["BTC-USDT-SWAP"], 103.0)   # nicht 104.0


if __name__ == "__main__":
    unittest.main(verbosity=2)
