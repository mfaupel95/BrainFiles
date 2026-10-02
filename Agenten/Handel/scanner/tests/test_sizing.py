"""Risiko-normiertes Sizing: gleiches Verlustpotenzial je Position.

Vorher band jede Position denselben Betrag, waehrend ihr Stop schwankte -
wer mehr riskierte, belegte denselben Platz wie der, der weniger riskierte.
Die Tests halten fest, was dabei schiefgehen kann: eine Division durch einen
Stop nahe null, ein fehlender Konfigurationswert (Altbestand), und der
Deckel, der die Hausregel gegen das Sizing durchsetzt.
"""

import json
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                          # noqa: E402

W = {"max_pro_trade_usd": 100, "risiko_je_position_usd": 6.0}


class NominalTest(unittest.TestCase):
    def test_weiter_stop_bindet_weniger_kapital(self):
        eng = h.nominal_fuer(5.0, W)
        weit = h.nominal_fuer(10.0, W)
        self.assertLess(weit, eng)
        self.assertEqual(weit, 60.0)

    def test_risiko_ist_bei_jedem_stop_gleich(self):
        """Der Kern: dasselbe Verlustpotenzial, egal wie weit der Stop liegt."""
        for sp in (6.0, 7.5, 9.0, 12.0):
            nominal = h.nominal_fuer(sp, W)
            self.assertAlmostEqual(nominal * sp / 100.0,
                                   W["risiko_je_position_usd"], places=2,
                                   msg="Stop %.1f%% riskiert abweichend" % sp)

    def test_deckel_setzt_die_hausregel_durch(self):
        """Ein enger Stop darf die Position nicht ueber max_pro_trade_usd
        heben - sonst waere das Sizing staerker als die Hausregel."""
        self.assertEqual(h.nominal_fuer(1.0, W), W["max_pro_trade_usd"])
        self.assertEqual(h.nominal_fuer(5.0, W), W["max_pro_trade_usd"])

    def test_stop_null_gibt_keine_unendliche_position(self):
        for sp in (0.0, -1.0):
            self.assertEqual(h.nominal_fuer(sp, W), W["max_pro_trade_usd"])

    def test_altbestand_ohne_den_wert_behaelt_festes_nominal(self):
        """Fehlt der Wert (oder steht auf null), aendert sich gar nichts."""
        for w in ({"max_pro_trade_usd": 100},
                  {"max_pro_trade_usd": 100, "risiko_je_position_usd": None},
                  {"max_pro_trade_usd": 100, "risiko_je_position_usd": 0}):
            self.assertEqual(h.nominal_fuer(8.0, w), 100)


class VorschlaegeTest(unittest.TestCase):
    """Am ECHTEN Aufruf: reicht vorschlaege() das Sizing durch?

    Naht: vorschlaege() holt den Marktpreis (marktkurs), seit 03.10.2026.
    Ohne sie ginge der Aufruf ans Netz und OKX 51001 wuerde den Test
    statt des Sizing-Befunds fehlschlagen lassen."""

    def _bericht(self, vola):
        return {"werte": [{"inst": "X-USDT", "score": 70.0, "preis": 100.0,
                           "verhaeltnis": 2.0,
                           "kennzahlen": {"volatilitaet_pa": vola}}]}

    def setUp(self):
        self.abl = h.ABLEHNUNGEN
        self.schreiben = h.SCHREIBEN
        self.marktkurs = h.marktkurs
        h.marktkurs = lambda inst: 100.0
        h.SCHREIBEN = False

    def tearDown(self):
        h.ABLEHNUNGEN = self.abl
        h.SCHREIBEN = self.schreiben
        h.marktkurs = self.marktkurs

    def test_weiter_stop_kommt_mit_kleinerem_nominal_an(self):
        w = dict(W, mindest_score=60, max_volatilitaet_pa=1.20,
                 mindest_chance_risiko=1.5, pflicht_stop_prozent_min=5.0,
                 pflicht_stop_prozent_max=12.0)
        # Beide Volas muessen UNTER max_volatilitaet_pa liegen, sonst
        # lehnt das Tor den Kandidaten ab und die Liste ist leer.
        eng = h.vorschlaege(self._bericht(0.35), w)[0]    # Stop 5.1 %
        weit = h.vorschlaege(self._bericht(1.15), w)[0]   # Stop 9.9 %
        self.assertGreater(weit["stop_pct"], eng["stop_pct"])
        self.assertLess(weit["usd"], eng["usd"],
                        "das Sizing kommt im Vorschlag nicht an")
        self.assertAlmostEqual(weit["usd"] * weit["stop_pct"] / 100.0, 6.0,
                               places=2)


class DeckelHerleitungTest(unittest.TestCase):
    """Der Deckel ist kein freier Wert - er folgt aus Risiko und Mindest-Stop.

    Solange max_pro_trade_usd kleiner ist als risiko / pflicht_stop_prozent_min,
    kappt er genau die engen Stops: sie behalten ihr altes, ZU KLEINES Risiko,
    waehrend weite Stops normiert werden. Die Normierung wirkt dann nur nach
    unten und ist halb. Dieser Test faellt, wenn jemand risiko_je_position_usd
    aendert, ohne den Deckel mitzurechnen.
    """

    def setUp(self):
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))

    def test_deckel_kappt_den_engsten_erlaubten_stop_nicht(self):
        r = self.w["risiko_je_position_usd"]
        smin = self.w["pflicht_stop_prozent_min"]
        noetig = r / (smin / 100.0)
        self.assertGreaterEqual(
            self.w["max_pro_trade_usd"], noetig - 0.01,
            "Deckel %.2f kappt den %.1f%%-Stop; noetig waeren %.2f"
            % (self.w["max_pro_trade_usd"], smin, noetig))

    def test_engster_stop_erreicht_das_volle_risiko(self):
        smin = self.w["pflicht_stop_prozent_min"]
        nominal = h.nominal_fuer(smin, self.w)
        self.assertAlmostEqual(nominal * smin / 100.0,
                               self.w["risiko_je_position_usd"], places=2)


class WachenTest(unittest.TestCase):
    def test_wert_steht_in_der_echten_datei(self):
        w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        self.assertIn("risiko_je_position_usd", w)
        self.assertIn("_risiko_je_position_usd", w,
                      "jede Grenze braucht ihr Erklaerfeld")

    def test_risiko_passt_zum_bisherigen_durchschnitt(self):
        """6 USD ist der bisherige Schnitt (100 USD bei ~6 % Stop): die
        Risikosumme bleibt, nur ihre Verteilung aendert sich. Ein deutlich
        groesserer Wert waere eine stille Risikoerhoehung."""
        w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        r = w["risiko_je_position_usd"]
        deckel = w["max_pro_trade_usd"]
        self.assertLessEqual(r, deckel * w["pflicht_stop_prozent_max"] / 100.0)
        self.assertGreaterEqual(r, deckel * w["pflicht_stop_prozent_min"] / 100.0)


if __name__ == "__main__":
    unittest.main()
