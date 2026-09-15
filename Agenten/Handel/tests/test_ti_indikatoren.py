"""Tests fuer ti_indikatoren -- vier TradingView-Familien-Indikatoren.

Pflicht-Konventionen:
  - sys.path enthaelt das Elternverzeichnis (Handel), damit importiert werden kann.
  - Alle Tests auf Deutsch, ASCII (ae/oe/ue/ss).
  - Laengengleichheit, None-Praefixe, synthetische Reihen, Echtdaten-Gegenprobe.
"""

import json
import math
import sys
import unittest
from pathlib import Path

# Pfad zum Elternverzeichnis, damit 'import ti_indikatoren' funktioniert
_DIR = Path(__file__).resolve().parent.parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

import ti_indikatoren as ti


# --------------------------------------------------------------------------- #
# Hilfen
# --------------------------------------------------------------------------- #

def _kerze(ts=0, offen=100, hoch=110, tief=90, schluss=105, volumen=1000):
    """Test-Kerze erzeugen."""
    return [ts, offen, hoch, tief, schluss, volumen]


def _reihe_erzeugen(start, end, schritte=60):
    """Einfache Preismenge als Kerzenreihen-Liste, monoton steigend."""
    schritt = (end - start) / schritte
    kerzen = []
    for i in range(schritte):
        preis = start + schritt * i
        kerzen.append(_kerze(
            ts=i * 3600000,
            offen=preis,
            hoch=preis + 5,
            tief=preis - 5,
            schluss=preis + 2,
            volumen=1000,
        ))
    return kerzen


# --------------------------------------------------------------------------- #
# TestKlassen
# --------------------------------------------------------------------------- #

class TestLaengen(unittest.TestCase):
    """Kernkonvention: Ausgabe muss gleiche Laenge wie Eingabe haben."""

    def test_squeeze_momentum(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        m, s, r = ti.squeeze_momentum(kerzen)
        self.assertEqual(len(m), len(kerzen))
        self.assertEqual(len(s), len(kerzen))
        self.assertEqual(len(r), len(kerzen))

    def test_macd(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        schliesse = [k[4] for k in kerzen]
        ml, sl, h = ti.macd(schliesse)
        self.assertEqual(len(ml), len(kerzen))
        self.assertEqual(len(sl), len(kerzen))
        self.assertEqual(len(h), len(kerzen))

    def test_zu_hoeherem_zeitrahmen(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=10)
        tf = ti.zu_hoeherem_zeitrahmen(kerzen, 3)
        self.assertEqual(len(tf), 3)

    def test_wavetrend(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        w1, w2 = ti.wavetrend(kerzen)
        self.assertEqual(len(w1), len(kerzen))
        self.assertEqual(len(w2), len(kerzen))


class TestNonePraefix(unittest.TestCase):
    """Am Anfang muessen die Werte None sein, nicht 0.0 oder autre."""

    def test_macd_none_am_anfang(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        schliesse = [k[4] for k in kerzen]
        ml, sl, h = ti.macd(schliesse)
        # Die ersten 25 Werte muessen None sein (langsam=26, Index 0-24)
        for i in range(25):
            self.assertIsNone(ml[i], f"ml[{i}] sollte None sein")
        # Signal: index 25 + 8 = 33
        for i in range(33):
            self.assertIsNone(sl[i], f"sl[{i}] sollte None sein")

    def test_squeeze_momentum_none_am_anfang(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        m, s, r = ti.squeeze_momentum(kerzen, laenge=20)
        # Index 0-18 muessen None sein
        for i in range(19):
            self.assertIsNone(s[i], f"squeeze_an[{i}] sollte None sein")

    def test_wavetrend_none_am_anfang(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        w1, w2 = ti.wavetrend(kerzen, n1=10, n2=21)
        # n2-1 = 20 ist der erste gueltige Index fuer wt1
        for i in range(20):
            self.assertIsNone(w1[i], f"wt1[{i}] sollte None sein")


class TestSynthetischeReihe(unittest.TestCase):
    """Squeeze-Verhalten anhand einer synthetischen Reihe pruefen."""

    def test_squeeze_ausbruch(self):
        """Erst eng seitwaerts, dann Ausbruch: squeeze_an = True im engen Teil."""
        kerzen = []
        # 30 Kerzen Seitwaerts bei 100
        for i in range(30):
            kerzen.append(_kerze(ts=i * 3600000, offen=100, hoch=101,
                                 tief=99, schluss=100, volumen=1000))
        # 30 Kerzen Ausbruch nach oben
        for i in range(30):
            kerzen.append(_kerze(ts=(30 + i) * 3600000, offen=100 + i,
                                 hoch=102 + i, tief=99 + i,
                                 schluss=101 + i, volumen=5000))

        m, s, r = ti.squeeze_momentum(kerzen, laenge=20)
        # Im engen Teil (Index 19-29) sollte squeeze_an meist True sein
        eng_indices = [i for i in range(19, 30) if s[i] is not None]
        if eng_indices:
            anteil_true = sum(1 for i in eng_indices if s[i] is True)
            self.assertGreater(anteil_true, 0,
                               "Im engen Teil sollte mindestens ein squeeze_an=True sein")

        # Nach dem Ausbruch (Index 40+) sollte squeeze_an False sein
        ausbruch_indices = [i for i in range(39, 60) if s[i] is not None]
        if ausbruch_indices:
            anteil_false = sum(1 for i in ausbruch_indices if s[i] is False)
            self.assertGreater(anteil_false, 0,
                               "Nach Ausbruch sollte squeeze_an=False sein")


class TestWaveTrend(unittest.TestCase):
    """WaveTrend bei monoton steigender Reihe muss positiv sein."""

    def test_wt1_positiv_bei_steigung(self):
        kerzen = _reihe_erzeugen(100, 500, schritte=60)
        w1, w2 = ti.wavetrend(kerzen)
        # Ab Index n2-1 = 20 muessen die Werte nicht None sein
        gueltige = [w for w in w1 if w is not None]
        self.assertTrue(len(gueltige) > 0, "Keine gueltigen wt1-Werte")
        # Bei monoton steigendem Markt sollte wt1 im Durchschnitt positiv sein
        durchschnitt = sum(gueltige) / len(gueltige)
        self.assertGreater(durchschnitt, 0,
                           "wt1 sollte bei monoton steigend positiv sein")


class TestDivisionDurchNull(unittest.TestCase):
    """Konstante Kurse duerfen keinen ZeroDivisionError ausloesen."""

    def test_wavetrend_konstant(self):
        kerzen = [_kerze(ts=i * 3600000, offen=100, hoch=100,
                         tief=100, schluss=100, volumen=1000)
                  for i in range(60)]
        w1, w2 = ti.wavetrend(kerzen)
        # Kein Absturz. Alle Werte muessen None oder eine Zahl sein.
        for v in w1 + w2:
            if v is not None:
                self.assertFalse(math.isnan(v), "Kein NaN erlaubt")

    def test_squeeze_momentum_konstant(self):
        kerzen = [_kerze(ts=i * 3600000, offen=100, hoch=100,
                         tief=100, schluss=100, volumen=1000)
                  for i in range(60)]
        m, s, r = ti.squeeze_momentum(kerzen)
        for v in m:
            if v is not None:
                self.assertFalse(math.isnan(v), "Kein NaN erlaubt")


class TestZuHoeheremZeitrahmen(unittest.TestCase):
    """Aggregation mit faktor=2 auf 3 Kerzen ergibt 1 Kerze."""

    def test_aggregation(self):
        kerzen = [
            _kerze(ts=0, offen=10, hoch=15, tief=8, schluss=12, volumen=100),
            _kerze(ts=1, offen=12, hoch=18, tief=11, schluss=14, volumen=200),
            _kerze(ts=2, offen=14, hoch=16, tief=13, schluss=15, volumen=300),
        ]
        tf = ti.zu_hoeherem_zeitrahmen(kerzen, 2)
        self.assertEqual(len(tf), 1)
        t = tf[0]
        self.assertEqual(t[0], 0)       # ts = erste Kerze
        self.assertEqual(t[1], 10)      # offen = erste offen
        self.assertEqual(t[2], 18)      # hoch = max(15, 18)
        self.assertEqual(t[3], 8)       # tief = min(8, 11)
        self.assertEqual(t[4], 14)      # schluss = letzte schluss
        self.assertEqual(t[5], 300)     # volumen = 100 + 200


class TestMacdMtf(unittest.TestCase):
    """macd_mtf mit verschiedenen Faktoren."""

    def test_faktor_1(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=60)
        ergebnis = ti.macd_mtf(kerzen, faktoren=(1,))
        self.assertIn(1, ergebnis)
        self.assertIn("einig", ergebnis)
        self.assertIsInstance(ergebnis["einig"], bool)

    def test_faktor_1_4(self):
        kerzen = _reihe_erzeugen(100, 200, schritte=100)
        ergebnis = ti.macd_mtf(kerzen, faktoren=(1, 4))
        self.assertIn(1, ergebnis)
        self.assertIn(4, ergebnis)
        self.assertIn("einig", ergebnis)
        self.assertIsInstance(ergebnis["einig"], bool)
        # Laengen muessen passen
        self.assertEqual(len(ergebnis[1]["macd"]), 100)
        self.assertEqual(len(ergebnis[4]["macd"]), 25)


class TestEchtdatenGegenprobe(unittest.TestCase):
    """BTC-1H-Kerzen: alle Indikatoren durchlaufen, Laengen pruefen, Plausibilitaet."""

    @classmethod
    def setUpClass(cls):
        datenpfad = _DIR / "kerzen_BTC-USDT_1H_8760.json"
        if not datenpfad.exists():
            raise unittest.SkipTest("Echtdaten-Datei nicht vorhanden")
        with open(datenpfad, "r") as f:
            roh = json.load(f)
        # JSON enthaelt 5-Element-Kerzen [ts, offen, hoch, tief, schluss]
        # ohne Volumen. Fuer ti_indikatoren (6 Elemente) normieren:
        cls.kerzen = [k + [0.0] if len(k) == 5 else k for k in roh]

    def test_squeeze_momentum_laeuft(self):
        m, s, r = ti.squeeze_momentum(self.kerzen)
        self.assertEqual(len(m), len(self.kerzen))
        self.assertEqual(len(s), len(self.kerzen))
        self.assertEqual(len(r), len(self.kerzen))
        # Kein NaN, kein inf
        for i, v in enumerate(m):
            if v is not None:
                self.assertFalse(math.isnan(v), f"momentum[{i}] = NaN")
                self.assertFalse(math.isinf(v), f"momentum[{i}] = inf")
                self.assertLess(abs(v), 1000000,
                                f"momentum[{i}] = {v} -- absurd gross")

    def test_macd_laeuft(self):
        schliesse = [k[4] for k in self.kerzen]
        ml, sl, h = ti.macd(schliesse)
        self.assertEqual(len(ml), len(self.kerzen))
        self.assertEqual(len(sl), len(self.kerzen))
        self.assertEqual(len(h), len(self.kerzen))
        for i, v in enumerate(ml):
            if v is not None:
                self.assertFalse(math.isnan(v), f"macd[{i}] = NaN")
                self.assertFalse(math.isinf(v), f"macd[{i}] = inf")

    def test_wavetrend_laeuft(self):
        w1, w2 = ti.wavetrend(self.kerzen)
        self.assertEqual(len(w1), len(self.kerzen))
        self.assertEqual(len(w2), len(self.kerzen))
        for i, v in enumerate(w1):
            if v is not None:
                self.assertFalse(math.isnan(v), f"wt1[{i}] = NaN")
                self.assertFalse(math.isinf(v), f"wt1[{i}] = inf")

    def test_macd_mtf_laeuft(self):
        ergebnis = ti.macd_mtf(self.kerzen, faktoren=(1, 4, 16))
        self.assertIn("einig", ergebnis)
        self.assertIsInstance(ergebnis["einig"], bool)
        for faktor in (1, 4, 16):
            self.assertIn(faktor, ergebnis)
            for schluessel in ("macd", "signal", "hist", "ausrichtung"):
                self.assertIn(schluessel, ergebnis[faktor])


if __name__ == "__main__":
    unittest.main()
