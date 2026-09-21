"""Tests der WaveTrend-Spur. Kein Netz: die Kerzen entstehen im Test.

Geprueft wird:
  (a) Das Signal feuert genau bei der gebauten Kreuzung und NICHT daneben.
  (b) Stop-Abstand und Ziel stehen im Verhaeltnis 1:2.
  (c) Die Positionsgroesse respektiert max_pro_trade_usd.
  (d) --vorschau schreibt keine Datei.
  (e) Ohne Kerzen kein Absturz.

Lauf (aus wavetrend/tests):
  ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_wavetrend -v
"""

import json
import math
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
# Rueckwaerts einfuegen: insert(0, ...) dreht die Reihenfolge um. HIER muss
# ganz vorne landen, sonst gewinnt scanner/handeln.py.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402
import ti_indikatoren as ti  # noqa: E402

# Laenge, bei der die letzte Kerze eine Kreuzung im ueberzogenen Bereich
# traegt - ausgemessen an der Welle unten, nicht geraten.
N_LONG = 339
N_SHORT = 307


def kerzen_welle(n, amp=8.0, periode=60, drift=0.01, rausch=2.0):
    """Sinuswelle mit Drift und einer schnelleren Ueberlagerung.

    Die langsame Welle traegt wt1 in die ueberzogenen Zonen, die schnelle
    erzeugt zusaetzlich Kreuzungen in der Mitte - beides wird gebraucht:
    das Signal soll in der Zone feuern und in der Mitte schweigen.
    """
    ts0 = 1700000000000
    k = []
    for i in range(n):
        schwung = (amp * math.sin(2 * math.pi * i / periode)
                   + rausch * math.sin(2 * math.pi * i / 7.0))
        o = 100.0 + i * drift + schwung
        h = o + abs(schwung * 0.3) + 0.05
        l = o - abs(schwung * 0.3) - 0.05
        c = o + schwung * 0.1
        k.append([ts0 + i * 3600000, o, h, l, c, 1000.0])
    return k


def kerzen_flach(n=340):
    """Kerzen ohne Schwung: keine Kreuzung, kein ueberzogener Bereich."""
    ts0 = 1700000000000
    return [[ts0 + i * 3600000, 100.0, 100.05, 99.95, 100.0, 1000.0]
            for i in range(n)]


def wachen_test(ziel):
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    w["journal_zweitziel"] = ziel
    return w


class TestSignal(unittest.TestCase):
    """(a) Das Signal feuert genau an der gebauten Kreuzung."""

    def test_long_bei_kreuzung_von_unten_im_ueberverkauften(self):
        k = kerzen_welle(N_LONG)
        i = len(k) - 1
        wt1, wt2 = ti.wavetrend(k)
        # Festgemacht am Indikator: wt1 war unter wt2, steht jetzt darueber,
        # und wt1 liegt unter -40.
        self.assertLessEqual(wt1[i - 1], wt2[i - 1])
        self.assertGreater(wt1[i], wt2[i])
        self.assertLess(wt1[i], -40)
        self.assertEqual(handeln.signal(k, i), "long")

    def test_short_bei_kreuzung_von_oben_im_ueberkauften(self):
        k = kerzen_welle(N_SHORT)
        i = len(k) - 1
        wt1, wt2 = ti.wavetrend(k)
        self.assertGreaterEqual(wt1[i - 1], wt2[i - 1])
        self.assertLess(wt1[i], wt2[i])
        self.assertGreater(wt1[i], 40)
        self.assertEqual(handeln.signal(k, i), "short")

    def test_kreuzung_ohne_uebertreibung_feuert_nicht(self):
        """Die Zone ist Teil des Signals: eine Kreuzung in der Mitte zaehlt nicht."""
        k = kerzen_welle(N_LONG)
        wt1, wt2 = ti.wavetrend(k)
        mitte = [i for i in range(1, len(k))
                 if None not in (wt1[i - 1], wt2[i - 1], wt1[i], wt2[i])
                 and wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i]
                 and -40 <= wt1[i] <= 40]
        self.assertTrue(mitte, "Fixture sollte Kreuzungen in der Mitte haben")
        for i in mitte:
            self.assertIsNone(handeln.signal(k, i))

    def test_flache_reihe_ohne_signal(self):
        k = kerzen_flach()
        treffer = [i for i in range(1, len(k)) if handeln.signal(k, i)]
        self.assertEqual(treffer, [])

    def test_index_null_ohne_absturz(self):
        self.assertIsNone(handeln.signal(kerzen_welle(N_LONG), 0))


class TestStopUndZiel(unittest.TestCase):
    """(b) Stop-Abstand und Ziel stehen 1:2."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.w = wachen_test(os.path.join(self.tmp, "zweitziel"))
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = True
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ziel_ist_doppelter_stopabstand(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_LONG), z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        stop_abstand = p["einstieg"] - p["stop"]
        ziel_abstand = p["ziel"] - p["einstieg"]
        self.assertGreater(stop_abstand, 0)
        self.assertAlmostEqual(ziel_abstand / stop_abstand, 2.0, places=6)

    def test_ziel_ist_doppelter_stopabstand_short(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_SHORT), z, self.w, 1.0)
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
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = True
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nominal_unter_dem_deckel(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_LONG), z, self.w, 1.0)
        self.assertLessEqual(z["positionen"][0]["nominal"],
                             self.w["max_pro_trade_usd"])

    def test_nominal_ist_risiko_durch_stopabstand(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_LONG), z, self.w, 1.0)
        p = z["positionen"][0]
        erwartet = min(self.w["risiko_je_position_usd"] / (p["stop_pct"] / 100.0),
                       self.w["max_pro_trade_usd"])
        self.assertAlmostEqual(p["nominal"], erwartet, places=6)

    def test_ratsche_halbiert(self):
        z_voll, z_halb = {"positionen": []}, {"positionen": []}
        k = kerzen_welle(N_LONG)
        handeln.pruefe_einstieg("BTC-USDT", k, z_voll, self.w, 1.0)
        handeln.pruefe_einstieg("BTC-USDT", k, z_halb, self.w, 0.5)
        self.assertAlmostEqual(z_halb["positionen"][0]["nominal"],
                               z_voll["positionen"][0]["nominal"] / 2.0, places=6)

    def test_stop_prozent_im_pflichtrahmen(self):
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_LONG), z, self.w, 1.0)
        p = z["positionen"][0]
        self.assertGreaterEqual(p["stop_pct"], self.w["pflicht_stop_prozent_min"])
        self.assertLessEqual(p["stop_pct"], self.w["pflicht_stop_prozent_max"])

    def test_max_offene_positionen_deckelt(self):
        z = {"positionen": [{"inst": "X%d" % i} for i in
                            range(self.w["max_offene_positionen"])]}
        handeln.pruefe_einstieg("BTC-USDT", kerzen_welle(N_LONG), z, self.w, 1.0)
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
        handeln.lade_wachen = lambda: wachen_test(ziel)
        handeln.kerzen_quelle = lambda i, t, a: kerzen_welle(N_LONG)

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
        handeln.kerzen_quelle = lambda i, t, a: kerzen_welle(50)
        handeln.lauf("papier")
        self.assertEqual(handeln.lade_zustand()["positionen"], [])


class TestWachenDatei(unittest.TestCase):
    """Die Tore stehen in wachen.json, nicht im Code."""

    def setUp(self):
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)

    def test_papier_und_pflichtfelder(self):
                # handel_erlaubt steht seit dem 21.09.2026 auf True (Auftrag Max:
        # "alle weiteren spuren live offen und handel erlaubt"). Die Spur
        # hat aber KEINEN Orderaufruf im Code - der Schalter allein handelt
        # nicht. Der Test prueft weiter, dass der Wert gesetzt ist und
        # niemand ihn still auf None/Text umstellt.
        self.assertTrue(self.w["handel_erlaubt"])
        self.assertEqual(self.w["waehrung"], "USD")
        self.assertEqual(self.w["herzschlag_max_minuten"], 180)
        self.assertEqual(self.w["ziel_r_vielfaches"], 2.0)
        self.assertNotIn("drawdown_halbierung_prozent", self.w)

    def test_deckel_traegt_das_risiko(self):
        noetig = (self.w["risiko_je_position_usd"]
                  / (self.w["pflicht_stop_prozent_min"] / 100.0))
        self.assertGreaterEqual(self.w["max_pro_trade_usd"], noetig)

    def test_zweitziel_gesetzt(self):
        self.assertTrue(self.w["journal_zweitziel"].endswith("wavetrend"))


if __name__ == "__main__":
    unittest.main()
