"""Tests der Squeeze-Spur. Kein Netz: die Kerzen entstehen im Test.

Geprueft wird:
  (a) Das Signal feuert genau bei der gebauten Gelegenheit und NICHT daneben.
  (b) Stop-Abstand und Ziel stehen im Verhaeltnis 1:2.
  (c) Die Positionsgroesse respektiert max_pro_trade_usd.
  (d) --vorschau schreibt keine Datei.
  (e) Ohne Kerzen kein Absturz.

Lauf (aus squeeze/tests):
  ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_squeeze -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
# Rueckwaerts einfuegen: insert(0, ...) dreht die Reihenfolge um. HIER muss
# ganz vorne landen, sonst gewinnt scanner/handeln.py gegen das handeln.py
# dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402
import ti_indikatoren as ti  # noqa: E402


def kerzen_squeeze(richtung="long", n=300, bruch=299):
    """Kerzen mit langer Volatilitaetskompression und Ausbruch bei 'bruch'.

    Bis 'bruch' ist die Spanne winzig (Squeeze an), danach bricht der Kurs
    aus. Die Drift waehrend der Kompression bestimmt das Vorzeichen des
    Moments: aufwaerts -> positives Moment, abwaerts -> negatives.
    """
    ts0 = 1700000000000
    k = []
    for i in range(n):
        ts = ts0 + i * 3600000
        if i < bruch:
            if richtung == "long":
                basis = 100.0 + i * 0.001
                o, h, l, c = basis, basis + 0.02, basis - 0.02, basis + 0.005
            else:
                basis = 100.0 - i * 0.001
                o, h, l, c = basis, basis + 0.02, basis - 0.02, basis - 0.005
        else:
            if richtung == "long":
                o = 100.0 + 0.28 + (i - bruch) * 0.5
                h, l, c = o + 3.0, o - 0.1, o + 2.5
            else:
                o = 100.0 - 0.28 - (i - bruch) * 0.5
                h, l, c = o + 0.1, o - 3.0, o - 2.5
        k.append([ts, o, h, l, c, 1000.0])
    return k


def wachen_test(ziel):
    """Wachen wie die echte Datei, aber mit Zweitziel in einem Temp-Ordner."""
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    w["journal_zweitziel"] = ziel
    return w


class TestSignal(unittest.TestCase):
    """(a) Das Signal feuert genau an der gebauten Stelle."""

    def test_long_genau_beim_ausbruch(self):
        k = kerzen_squeeze("long")
        # Festgemacht am Indikator selbst: an 280 loest der Squeeze sich,
        # und das Moment steigt und ist positiv.
        momentum, squeeze_an, _ = ti.squeeze_momentum(k)
        self.assertTrue(squeeze_an[298])
        self.assertFalse(squeeze_an[299])
        self.assertGreater(momentum[299], momentum[298])
        self.assertGreater(momentum[298], 0)
        self.assertEqual(handeln.signal(k, 299), "long")

    def test_short_genau_beim_ausbruch(self):
        k = kerzen_squeeze("short")
        momentum, squeeze_an, _ = ti.squeeze_momentum(k)
        self.assertTrue(squeeze_an[298])
        self.assertFalse(squeeze_an[299])
        self.assertLess(momentum[299], momentum[298])
        self.assertLess(momentum[298], 0)
        self.assertEqual(handeln.signal(k, 299), "short")

    def test_kein_signal_daneben(self):
        """Weder in der Kompression noch nach dem Ausbruch feuert es nochmal."""
        k = kerzen_squeeze("long")
        treffer = [i for i in range(1, len(k)) if handeln.signal(k, i)]
        self.assertEqual(treffer, [299])

    def test_kein_signal_in_der_ruhe(self):
        """Eine Reihe ohne Ausbruch liefert nirgends ein Signal."""
        k = kerzen_squeeze("long", n=299, bruch=999)
        treffer = [i for i in range(1, len(k)) if handeln.signal(k, i)]
        self.assertEqual(treffer, [])

    def test_index_null_ohne_absturz(self):
        k = kerzen_squeeze("long")
        self.assertIsNone(handeln.signal(k, 0))


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
        k = kerzen_squeeze("long")
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        stop_abstand = p["einstieg"] - p["stop"]
        ziel_abstand = p["ziel"] - p["einstieg"]
        self.assertGreater(stop_abstand, 0)
        self.assertAlmostEqual(ziel_abstand / stop_abstand, 2.0, places=6)

    def test_ziel_ist_doppelter_stopabstand_short(self):
        k = kerzen_squeeze("short")
        z = {"positionen": []}
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
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = True
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nominal_unter_dem_deckel(self):
        k = kerzen_squeeze("long")
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        p = z["positionen"][0]
        self.assertLessEqual(p["nominal"], self.w["max_pro_trade_usd"])

    def test_deckel_greift_bei_kleinem_stop(self):
        """Stop am unteren Rand (5 %) -> 5 / 0.05 = 100 USD, unter 150."""
        k = kerzen_squeeze("long")
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        p = z["positionen"][0]
        erwartet = self.w["risiko_je_position_usd"] / (p["stop_pct"] / 100.0)
        erwartet = min(erwartet, self.w["max_pro_trade_usd"])
        self.assertAlmostEqual(p["nominal"], erwartet, places=6)

    def test_ratsche_halbiert(self):
        """Faktor 0.5 aus der Drawdown-Ratsche halbiert das Nominal."""
        k = kerzen_squeeze("long")
        z_voll = {"positionen": []}
        z_halb = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", k, z_voll, self.w, 1.0)
        handeln.pruefe_einstieg("BTC-USDT", k, z_halb, self.w, 0.5)
        self.assertAlmostEqual(z_halb["positionen"][0]["nominal"],
                               z_voll["positionen"][0]["nominal"] / 2.0,
                               places=6)

    def test_stop_prozent_im_pflichtrahmen(self):
        k = kerzen_squeeze("long")
        z = {"positionen": []}
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        p = z["positionen"][0]
        self.assertGreaterEqual(p["stop_pct"], self.w["pflicht_stop_prozent_min"])
        self.assertLessEqual(p["stop_pct"], self.w["pflicht_stop_prozent_max"])

    def test_max_offene_positionen_deckelt(self):
        k = kerzen_squeeze("long")
        z = {"positionen": [{"inst": "X%d" % i} for i in
                            range(self.w["max_offene_positionen"])]}
        handeln.pruefe_einstieg("BTC-USDT", k, z, self.w, 1.0)
        self.assertEqual(len(z["positionen"]), self.w["max_offene_positionen"])


class TestVorschauSchreibtNicht(unittest.TestCase):
    """(d) --vorschau schreibt keine Datei."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.zustand_alt = handeln.ZUSTAND
        self.journal_alt = handeln.JOURNAL
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        self.wachen_alt = handeln.lade_wachen
        ziel = os.path.join(self.tmp, "zweitziel")
        handeln.lade_wachen = lambda: wachen_test(ziel)
        handeln.kerzen_quelle = lambda i, t, a: kerzen_squeeze("long")

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
        """Gegenprobe: im Papierlauf entstehen Zustand, Journal und Spiegel."""
        handeln.lauf("papier")
        self.assertTrue(os.path.exists(handeln.ZUSTAND))
        self.assertTrue(os.path.exists(handeln.JOURNAL))
        spiegel = os.path.join(self.tmp, "zweitziel")
        self.assertTrue(os.path.exists(os.path.join(spiegel, "zustand.json")))
        self.assertTrue(os.path.exists(
            os.path.join(spiegel, "handelsjournal.csv")))


class TestOhneKerzen(unittest.TestCase):
    """(e) Ohne Kerzen kein Absturz."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.zustand_alt = handeln.ZUSTAND
        self.journal_alt = handeln.JOURNAL
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        self.wachen_alt = handeln.lade_wachen
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
        """Ein Zyklus ohne Verbindung meldet 'uebersprungen' statt zu sterben."""
        def kaputt(inst, takt, anzahl):
            raise OSError("keine Verbindung")
        handeln.kerzen_quelle = kaputt
        handeln.lauf("papier")
        self.assertTrue(os.path.exists(handeln.ZUSTAND))

    def test_zu_wenige_kerzen(self):
        handeln.kerzen_quelle = lambda i, t, a: kerzen_squeeze("long", n=50)
        handeln.lauf("papier")
        z = handeln.lade_zustand()
        self.assertEqual(z["positionen"], [])


class TestWachenDatei(unittest.TestCase):
    """Die Tore stehen in wachen.json, nicht im Code."""

    def setUp(self):
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            self.w = json.load(f)

    def test_papier_und_pflichtfelder(self):
        self.assertFalse(self.w["handel_erlaubt"])
        self.assertEqual(self.w["waehrung"], "USD")
        self.assertEqual(self.w["herzschlag_max_minuten"], 180)
        self.assertEqual(self.w["ziel_r_vielfaches"], 2.0)
        self.assertNotIn("drawdown_halbierung_prozent", self.w)

    def test_deckel_traegt_das_risiko(self):
        """max_pro_trade_usd >= risiko / kleinstem Stop."""
        noetig = (self.w["risiko_je_position_usd"]
                  / (self.w["pflicht_stop_prozent_min"] / 100.0))
        self.assertGreaterEqual(self.w["max_pro_trade_usd"], noetig)

    def test_zweitziel_gesetzt(self):
        self.assertTrue(self.w["journal_zweitziel"].endswith("squeeze"))


if __name__ == "__main__":
    unittest.main()
