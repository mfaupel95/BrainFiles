"""Tests der SuperTrend-Spur. Kein Netz: die Kerzen entstehen im Test.

Geprueft wird:
  (a) Das Signal feuert genau beim Richtungswechsel und NICHT daneben.
  (b) Stop-Abstand und Ziel stehen im Verhaeltnis 1:2.
  (c) Die Positionsgroesse respektiert max_pro_trade_usd.
  (d) --vorschau schreibt keine Datei.
  (e) Ohne Kerzen kein Absturz.
  Dazu die Besonderheit dieser Spur: die SuperTrend-Linie ist der
  Trailing-Stop.

Lauf (aus supertrend/tests):
  ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_supertrend -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
# Rueckwaerts einfuegen: insert(0, ...) dreht die Reihenfolge um.
for p in (os.path.join(HANDEL, "scanner"), os.path.join(HANDEL, "xperp"),
          HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402
import indikatoren as xi  # noqa: E402

# Bei 303 Kerzen (Wende bei 300) liegt der Richtungswechsel des SuperTrend
# genau auf der letzten Kerze - ausgemessen, nicht geraten.
N_WECHSEL = 303
WENDE = 300


def kerzen_wende(n=N_WECHSEL, wende=WENDE, richtung="up", basis=1000.0,
                 schritt=2.0):
    """Ein Trend, der bei 'wende' scharf dreht.

    richtung='up': erst fallend, dann steigend -> SuperTrend dreht -1 auf +1.
    richtung='down': spiegelbildlich.
    """
    ts0 = 1700000000000
    k = []
    p = basis
    for i in range(n):
        if i < wende:
            p -= schritt if richtung == "up" else -schritt
        else:
            p += schritt * 4 if richtung == "up" else -schritt * 4
        k.append([ts0 + i * 14400000, p, p + 3.0, p - 3.0, p, 1000.0])
    return k


def kerzen_gerade(n=320, basis=1000.0, schritt=2.0):
    """Ein durchgehender Trend ohne Wende - kein Signal ausser am Anfang."""
    ts0 = 1700000000000
    return [[ts0 + i * 14400000, basis + i * schritt, basis + i * schritt + 3.0,
             basis + i * schritt - 3.0, basis + i * schritt, 1000.0]
            for i in range(n)]


def wachen_test(ziel):
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    w["journal_zweitziel"] = ziel
    return w


class TestSignal(unittest.TestCase):
    """(a) Das Signal feuert genau beim Richtungswechsel."""

    def test_long_beim_wechsel_minus_auf_plus(self):
        k = kerzen_wende(richtung="up")
        i = len(k) - 1
        _linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        # Festgemacht am Indikator: die Richtung springt von -1 auf +1.
        self.assertEqual(richtung[i - 1], -1)
        self.assertEqual(richtung[i], 1)
        treffer = handeln.signal(k, i)
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer[0], "long")

    def test_short_beim_wechsel_plus_auf_minus(self):
        k = kerzen_wende(richtung="down")
        i = len(k) - 1
        _linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        self.assertEqual(richtung[i - 1], 1)
        self.assertEqual(richtung[i], -1)
        treffer = handeln.signal(k, i)
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer[0], "short")

    def test_signal_gibt_die_linie_mit(self):
        """Der zweite Rueckgabewert ist der SuperTrend-Wert (= Trailing-Stop)."""
        k = kerzen_wende(richtung="up")
        i = len(k) - 1
        linie, _richtung = xi.supertrend(k, n=10, faktor=3.0)
        self.assertAlmostEqual(handeln.signal(k, i)[1], linie[i], places=9)

    def test_kein_signal_im_laufenden_trend(self):
        """Ohne Wechsel kein Signal: die Kerze davor traegt dieselbe Richtung."""
        k = kerzen_wende(richtung="up", n=320)
        _linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        i = len(k) - 1
        self.assertEqual(richtung[i], richtung[i - 1])
        self.assertIsNone(handeln.signal(k, i))

    def test_gerader_trend_feuert_nur_einmal(self):
        """Ein Trend ohne Wende dreht nur beim Einschwingen, danach nie."""
        k = kerzen_gerade()
        treffer = [i for i in range(2, len(k)) if handeln.signal(k, i)]
        self.assertLessEqual(len(treffer), 1)
        for i in treffer:
            self.assertLess(i, 30, "Signal nur beim Einschwingen erwartet")

    def test_index_null_ohne_absturz(self):
        self.assertIsNone(handeln.signal(kerzen_wende(), 0))


class TestTrailingStop(unittest.TestCase):
    """Besonderheit: die SuperTrend-Linie ist der Trailing-Stop."""

    def test_long_faellt_aus_wenn_richtung_kippt(self):
        k = kerzen_wende(richtung="down")
        linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        p = {"seite": "long", "einstieg": k[-1][4] * 1.1}
        self.assertEqual(handeln.trailing_ausstieg(p, k, linie, richtung),
                         "trailing")

    def test_short_faellt_aus_wenn_richtung_kippt(self):
        k = kerzen_wende(richtung="up")
        linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        p = {"seite": "short", "einstieg": k[-1][4] * 0.9}
        self.assertEqual(handeln.trailing_ausstieg(p, k, linie, richtung),
                         "trailing")

    def test_long_bleibt_solange_der_trend_traegt(self):
        k = kerzen_wende(richtung="up", n=320)
        linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
        self.assertEqual(richtung[-1], 1)
        self.assertGreater(k[-1][4], linie[-1])
        p = {"seite": "long", "einstieg": k[-1][4] * 0.9}
        self.assertIsNone(handeln.trailing_ausstieg(p, k, linie, richtung))


class TestStopUndZiel(unittest.TestCase):
    """(b) Stop-Abstand und Ziel stehen 1:2."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.w = wachen_test(os.path.join(self.tmp, "zweitziel"))
        self.w["mindest_kerzen"] = 300
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = True
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ziel_ist_doppelter_stopabstand(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT",
                                kerzen_wende(N_WECHSEL, WENDE, "up"),
                                z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        stop_abstand = p["einstieg"] - p["stop"]
        ziel_abstand = p["ziel"] - p["einstieg"]
        self.assertGreater(stop_abstand, 0)
        self.assertAlmostEqual(ziel_abstand / stop_abstand, 2.0, places=6)

    def test_ziel_ist_doppelter_stopabstand_short(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT",
                                kerzen_wende(N_WECHSEL, WENDE, "down"),
                                z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        stop_abstand = p["stop"] - p["einstieg"]
        ziel_abstand = p["einstieg"] - p["ziel"]
        self.assertGreater(stop_abstand, 0)
        self.assertAlmostEqual(ziel_abstand / stop_abstand, 2.0, places=6)


class TestGroesse(unittest.TestCase):
    """(c) Die Positionsgroesse respektiert max_pro_trade_usd."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.w = wachen_test(os.path.join(self.tmp, "zweitziel"))
        self.w["mindest_kerzen"] = 300
        self.k = kerzen_wende(N_WECHSEL, WENDE, "up")
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = True
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nominal_unter_dem_deckel(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", self.k, z, self.w, 1.0)
        self.assertLessEqual(z["positionen"][0]["nominal"],
                             self.w["max_pro_trade_usd"])

    def test_nominal_ist_risiko_durch_stopabstand(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", self.k, z, self.w, 1.0)
        p = z["positionen"][0]
        erwartet = min(self.w["risiko_je_position_usd"] / (p["stop_pct"] / 100.0),
                       self.w["max_pro_trade_usd"])
        self.assertAlmostEqual(p["nominal"], erwartet, places=6)

    def test_ratsche_halbiert(self):
        z_voll, z_halb = {"positionen": []}, {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", self.k, z_voll, self.w, 1.0)
        handeln.pruefe_einstieg("BTC-USDT", self.k, z_halb, self.w, 0.5)
        self.assertAlmostEqual(z_halb["positionen"][0]["nominal"],
                               z_voll["positionen"][0]["nominal"] / 2.0, places=6)

    def test_stop_prozent_im_pflichtrahmen(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", self.k, z, self.w, 1.0)
        p = z["positionen"][0]
        self.assertGreaterEqual(p["stop_pct"], self.w["pflicht_stop_prozent_min"])
        self.assertLessEqual(p["stop_pct"], self.w["pflicht_stop_prozent_max"])

    def test_max_offene_positionen_deckelt(self):
        z = {"positionen": [{"inst": "X%d" % i} for i in
                            range(self.w["max_offene_positionen"])]}
        handeln.pruefe_einstieg("BTC-USDT", self.k, z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), self.w["max_offene_positionen"])


class TestVorschauSchreibtNicht(unittest.TestCase):
    """(d) --vorschau schreibt keine Datei."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.zustand_alt = handeln.ZUSTAND
        self.journal_alt = handeln.JOURNAL
        self.wachen_alt = handeln.lade_wachen
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        ziel = os.path.join(self.tmp, "zweitziel")

        def wachen():
            w = wachen_test(ziel)
            w["mindest_kerzen"] = 300
            return w

        handeln.lade_wachen = wachen
        handeln.kerzen_quelle = lambda i, t, a: kerzen_wende(N_WECHSEL, WENDE, "up")

    def tearDown(self):
        handeln.ZUSTAND = self.zustand_alt
        handeln.JOURNAL = self.journal_alt
        handeln.lade_wachen = self.wachen_alt
        handeln.kerzen_quelle = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_vorschau_legt_keine_datei_an(self):
        handeln.lauf("vorschau")
        self.assertFalse(os.path.exists(handeln.ZUSTAND))
        self.assertFalse(os.path.exists(handeln.JOURNAL))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "zweitziel")))

    def test_papier_schreibt_zustand_und_spiegelt(self):
        handeln.lauf("papier")
        self.assertTrue(os.path.exists(handeln.ZUSTAND))
        self.assertTrue(os.path.exists(handeln.JOURNAL))
        spiegel = os.path.join(self.tmp, "zweitziel")
        self.assertTrue(os.path.exists(os.path.join(spiegel, "zustand.json")))


class TestOhneKerzen(unittest.TestCase):
    """(e) Ohne Kerzen kein Absturz."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.zustand_alt = handeln.ZUSTAND
        self.journal_alt = handeln.JOURNAL
        self.wachen_alt = handeln.lade_wachen
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        ziel = os.path.join(self.tmp, "zweitziel")
        handeln.lade_wachen = lambda: wachen_test(ziel)

    def tearDown(self):
        handeln.ZUSTAND = self.zustand_alt
        handeln.JOURNAL = self.journal_alt
        handeln.lade_wachen = self.wachen_alt
        handeln.kerzen_quelle = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_leere_kerzenliste(self):
        handeln.kerzen_quelle = lambda i, t, a: []
        handeln.lauf("papier")
        self.assertTrue(os.path.exists(handeln.ZUSTAND))

    def test_netzfehler_wird_abgefangen(self):
        def kaputt(inst, takt, anzahl):
            raise OSError("keine Verbindung")
        handeln.kerzen_quelle = kaputt
        handeln.lauf("papier")
        self.assertTrue(os.path.exists(handeln.ZUSTAND))

    def test_zu_wenige_kerzen(self):
        handeln.kerzen_quelle = lambda i, t, a: kerzen_wende(50, 40, "up")
        handeln.lauf("papier")
        self.assertEqual(handeln.lade_zustand()["positionen"], [])


class TestWachenDatei(unittest.TestCase):
    """Die Tore stehen in wachen.json, nicht im Code."""

    def setUp(self):
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)

    def test_papier_und_pflichtfelder(self):
        # handel_erlaubt ist ein SCHALTER, kein Zustand der Strategie: Max hat
        # ihn am 21.09.2026 auf die Spuren mit Orderweg begrenzt (Commit
        # f8f269d) - diese Spur hat keinen. Der Test prueft deshalb die REGEL
        # statt eines Tageswerts; ein Test gegen den Tageswert ist bei jeder
        # Umstellung rot, ohne dass etwas kaputt ist (Befund 29.09.2026).
        self.assertIsInstance(self.w["handel_erlaubt"], bool)
        if not self.w["handel_erlaubt"]:
            self.assertIn("_handel_erlaubt_vermerk", self.w)
        self.assertEqual(self.w["waehrung"], "USD")
        self.assertEqual(self.w["herzschlag_max_minuten"], 180)
        self.assertEqual(self.w["ziel_r_vielfaches"], 2.0)
        self.assertNotIn("drawdown_halbierung_prozent", self.w)

    def test_vier_stunden_takt(self):
        self.assertEqual(self.w["kerzen_takt"], "4H")

    def test_deckel_traegt_das_risiko(self):
        noetig = (self.w["risiko_je_position_usd"]
                  / (self.w["pflicht_stop_prozent_min"] / 100.0))
        self.assertGreaterEqual(self.w["max_pro_trade_usd"], noetig)

    def test_zweitziel_gesetzt(self):
        self.assertTrue(self.w["journal_zweitziel"].endswith("supertrend"))


if __name__ == "__main__":
    unittest.main()
