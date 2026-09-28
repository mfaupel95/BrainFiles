"""Tests der MACD-MTF-Spur. Kein Netz: die Kerzen entstehen im Test.

Geprueft wird:
  (a) Das Signal feuert nur bei Einigkeit ueber alle drei Zeitrahmen UND
      drehendem Histogramm - und NICHT daneben.
  (b) Stop-Abstand und Ziel stehen im Verhaeltnis 1:2.
  (c) Die Positionsgroesse respektiert max_pro_trade_usd.
  (d) --vorschau schreibt keine Datei.
  (e) Ohne Kerzen kein Absturz.

Lauf (aus macd_mtf/tests):
  ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_macd_mtf -v
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
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402
import ti_indikatoren as ti  # noqa: E402

# 16er-Zeitrahmen braucht 16 * (26 + 9) Basiskerzen, bevor er eine
# Ausrichtung nennt. Darunter steht dort None und "einig" ist False.
N = 800
AB = 780


def kerzen_trend(n=N, steigung=0.25, beschleunigung=0.0, ab=AB,
                 basis=1000.0):
    """Gerader Trend, ab 'ab' quadratisch beschleunigt.

    Der gerade Teil bringt alle drei Zeitrahmen auf dieselbe Ausrichtung;
    die Beschleunigung am Ende dreht das Histogramm des 1er-Zeitrahmens.
    Der Basispreis liegt bei 1000, damit auch 800 fallende Kerzen den Kurs
    nicht unter null druecken - ein negativer Kurs macht jede
    Prozentrechnung sinnlos.
    """
    ts0 = 1700000000000
    k = []
    for i in range(n):
        p = basis + i * steigung
        if i >= ab:
            p += beschleunigung * (i - ab) ** 2
        c = p + (0.12 if steigung > 0 else -0.12)
        k.append([ts0 + i * 3600000, p, max(p, c) + 0.6, min(p, c) - 0.6,
                  c, 1000.0])
    return k


def wachen_test(ziel):
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    w["journal_zweitziel"] = ziel
    return w


class TestSignal(unittest.TestCase):
    """(a) Das Signal feuert nur bei Einigkeit plus drehendem Histogramm."""

    def test_long_bei_einigkeit_und_steigendem_histogramm(self):
        k = kerzen_trend(steigung=0.25, beschleunigung=0.01)
        i = len(k) - 1
        e = ti.macd_mtf(k, faktoren=(1, 4, 16))
        # Festgemacht am Indikator: alle drei auf +1, Histogramm steigt.
        self.assertTrue(e["einig"])
        self.assertEqual([e[f]["ausrichtung"] for f in (1, 4, 16)], [1, 1, 1])
        h = e[1]["hist"]
        self.assertGreater(h[i], h[i - 1])
        self.assertEqual(handeln.signal(k, i), "long")

    def test_short_bei_einigkeit_und_fallendem_histogramm(self):
        k = kerzen_trend(steigung=-0.25, beschleunigung=-0.01)
        i = len(k) - 1
        e = ti.macd_mtf(k, faktoren=(1, 4, 16))
        self.assertTrue(e["einig"])
        self.assertEqual([e[f]["ausrichtung"] for f in (1, 4, 16)], [-1, -1, -1])
        h = e[1]["hist"]
        self.assertLess(h[i], h[i - 1])
        self.assertEqual(handeln.signal(k, i), "short")

    def test_einigkeit_ohne_histogrammdrehung_feuert_nicht(self):
        """Gerader Trend: alle einig, aber das Histogramm dreht nicht."""
        k = kerzen_trend(steigung=0.25, beschleunigung=0.0)
        i = len(k) - 1
        e = ti.macd_mtf(k, faktoren=(1, 4, 16))
        h = e[1]["hist"]
        self.assertFalse(h[i] > h[i - 1] and e[1]["ausrichtung"] == 1)
        self.assertIsNone(handeln.signal(k, i))

    def test_flacher_markt_ohne_signal(self):
        """Ausrichtung 0 auf allen Ebenen ist keine Ausrichtung +1/-1."""
        k = kerzen_trend(steigung=0.0, beschleunigung=0.0)
        i = len(k) - 1
        e = ti.macd_mtf(k, faktoren=(1, 4, 16))
        self.assertEqual([e[f]["ausrichtung"] for f in (1, 4, 16)], [0, 0, 0])
        self.assertIsNone(handeln.signal(k, i))

    def test_zu_kurze_reihe_ohne_signal(self):
        """Unter 16 * 35 Kerzen kennt der 16er-Rahmen keine Ausrichtung."""
        k = kerzen_trend(n=400, steigung=0.25, beschleunigung=0.01, ab=380)
        e = ti.macd_mtf(k, faktoren=(1, 4, 16))
        self.assertIsNone(e[16]["ausrichtung"])
        self.assertFalse(e["einig"])
        self.assertIsNone(handeln.signal(k, len(k) - 1))

    def test_index_null_ohne_absturz(self):
        self.assertIsNone(handeln.signal(kerzen_trend(), 0))


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
        k = kerzen_trend(steigung=0.25, beschleunigung=0.01)
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        stop_abstand = p["einstieg"] - p["stop"]
        ziel_abstand = p["ziel"] - p["einstieg"]
        self.assertGreater(stop_abstand, 0)
        self.assertAlmostEqual(ziel_abstand / stop_abstand, 2.0, places=6)

    def test_ziel_ist_doppelter_stopabstand_short(self):
        z = {"positionen": []}
        k = kerzen_trend(steigung=-0.25, beschleunigung=-0.01)
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
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
        self.k = kerzen_trend(steigung=0.25, beschleunigung=0.01)
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
        handeln.lade_wachen = lambda: wachen_test(ziel)
        handeln.kerzen_quelle = lambda i, t, a: kerzen_trend(
            steigung=0.25, beschleunigung=0.01)

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
        handeln.kerzen_quelle = lambda i, t, a: kerzen_trend(n=50, ab=45)
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

    def test_deckel_traegt_das_risiko(self):
        noetig = (self.w["risiko_je_position_usd"]
                  / (self.w["pflicht_stop_prozent_min"] / 100.0))
        self.assertGreaterEqual(self.w["max_pro_trade_usd"], noetig)

    def test_zwei_instrumente(self):
        # USDC seit 21.09.2026 (Auftrag Max: die OKX-Spuren mit der Waehrung
        # bedienen, in der das Geld liegt - USDT ist auf dem Konto nicht
        # vorhanden). Der Test prueft die LISTE, nicht die Waehrung: er soll
        # auffallen, wenn ein Instrument still verschwindet.
        self.assertEqual(self.w["instrumente"], ["BTC-USDC", "ETH-USDC"])

    def test_zweitziel_gesetzt(self):
        self.assertTrue(self.w["journal_zweitziel"].endswith("macd_mtf"))


if __name__ == "__main__":
    unittest.main()
