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


class TestSchwelleAusDerWachen(unittest.TestCase):
    """T-097: die Einstiegsschwelle steht in der Wachen, nicht im Quelltext.

    Geprueft wird die EIGENSCHAFT, nicht ein Wert: ohne das Feld verhaelt sich
    die Spur wie vorher (der Default ist der alte Code-Wert), ein gesetzter
    Wert weitet das Signal auf Zonen aus, die vorher nicht zaehlten, und nach
    Ruecknahme des Feldes ist der alte Stand wieder da. Ein Test gegen einen
    festen Zahlenwert wuerde nur die eine Konfiguration messen.
    """

    def setUp(self):
        self.alt = handeln.WACHEN
        self.tmp = tempfile.mkdtemp(prefix="wt-schwelle-")
        handeln.WACHEN = os.path.join(self.tmp, "wachen.json")
        with open(self.alt, encoding="utf-8") as f:
            self.wachen = json.load(f)

    def tearDown(self):
        handeln.WACHEN = self.alt
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _schreibe(self, wert):
        d = dict(self.wachen)
        d.pop("wt_ueberverkauft", None)
        if wert is not None:
            d["wt_ueberverkauft"] = wert
        with open(handeln.WACHEN, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)

    def _kreuzung_mitte(self, k):
        """Kerzen, deren Kreuzung zwischen -40 und +40 liegt."""
        wt1, wt2 = ti.wavetrend(k)
        return [i for i in range(1, len(k))
                if None not in (wt1[i - 1], wt2[i - 1], wt1[i], wt2[i])
                and wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i]
                and -40 <= wt1[i] <= 40]

    def test_ohne_feld_gilt_der_alte_wert(self):
        """Kein Feld -> kein Verhalten, das vorher nicht da war."""
        self._schreibe(None)
        k = kerzen_welle(N_LONG)
        mitte = self._kreuzung_mitte(k)
        self.assertTrue(mitte, "Fixture sollte Kreuzungen in der Mitte haben")
        for i in mitte:
            self.assertIsNone(handeln.signal(k, i))

    def test_engere_schwelle_nimmt_die_zonen_dazu(self):
        """Eine ENGERE Schwelle macht aus derselben Lage ein Signal.

        Richtung richtig herum: long verlangt `wt1 < -schwelle`. Je kleiner
        die Schwelle, desto mehr Lagen fallen darunter - eine engere Schwelle
        weitet das Signal also aus. Eine ENGERE im Wortsinn (hoeherer Wert)
        wuerde es nur schrumpfen; die Gegenprobe steht darunter.
        """
        k = kerzen_welle(N_LONG)
        wt1, wt2 = ti.wavetrend(k)
        # Kreuzungen von unten, die mit -5 (nicht mit -40) zaehlen
        nah = [i for i in range(1, len(k))
               if None not in (wt1[i - 1], wt2[i - 1], wt1[i], wt2[i])
               and wt1[i - 1] <= wt2[i - 1] and wt1[i] > wt2[i]
               and -40 <= wt1[i] < -5]
        self.assertTrue(nah, "Fixture braucht Kreuzungen zwischen -40 und -5")
        self._schreibe(None)
        for i in nah:
            self.assertIsNone(handeln.signal(k, i),
                             "bei -40 darf diese Lage kein Signal sein")
        self._schreibe(5.0)
        neue = [i for i in nah if handeln.signal(k, i) is not None]
        self.assertTrue(neue, "engere Schwelle muss die Lage zu einem Signal machen")
        self.assertEqual(len(neue), len(nah),
                         "alle Lagen zwischen -40 und -5 muessen jetzt zaehlen")

    def test_gegenprobe_wieder_urspruenglich(self):
        """Nach Ruecknahme des Feldes ist der alte Stand wieder da."""
        k = kerzen_welle(N_LONG)
        mitte = self._kreuzung_mitte(k)
        self._schreibe(100.0)
        vorher = [handeln.signal(k, i) for i in mitte]
        self._schreibe(None)
        nachher = [handeln.signal(k, i) for i in mitte]
        self.assertEqual(vorher, nachher)

    def test_echte_wachen_traegt_das_feld(self):
        """Die Wachen selbst fuehrt den Wert - sonst waere der Umbau stumm."""
        with open(self.alt, encoding="utf-8") as f:
            w = json.load(f)
        self.assertIn("wt_ueberverkauft", w)


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

    def test_zweitziel_gesetzt(self):
        self.assertTrue(self.w["journal_zweitziel"].endswith("wavetrend"))


if __name__ == "__main__":
    unittest.main()
