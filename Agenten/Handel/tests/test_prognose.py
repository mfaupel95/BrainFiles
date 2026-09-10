"""Die Tore der Prognose.

Geprueft wird die Auswahl, nicht die Bewertung: bewertung.py hat eigene
Zahlen und wird hier durch feste Kennzahlen ersetzt, damit jeder Test genau
ein Tor prueft. Das ist der Punkt - bei den ersten, aus dem Bauch gesetzten
Schwellen fand der Lauf ueber 41 Maerkte nichts, und niemand haette gemerkt,
welches Tor zu eng war.

Kein Netz: bewertung.bewerten wird je Test ersetzt und in addCleanup
zurueckgestellt.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))            # Handel/ - prognose
sys.path.insert(0, str(HIER.parent / "scanner"))  # scanner/ - bewertung, okx

import prognose  # noqa: E402

TOR = {
    "mindest_score": 60, "hoechst_rsi": 55,
    "ruecksetzer_von_pct": -25.0, "ruecksetzer_bis_pct": -4.0,
    "max_volatilitaet_pa": 1.2, "trend_ueber_sma": 100,
    "mindest_volumen_verhaeltnis": 0.5, "mindest_cr": 1.5,
    "stop_min_pct": 5.0, "stop_max_pct": 12.0,
}


def _kerzen(preis=128.0, tief=127.0, hoch=138.0, tage=200, steigend=True):
    """Reihe, die auf ``preis`` endet: steigend (Standard) oder fallend.

    Preis 128, Tief 127, Hoch 138 -> Stop 121,6 (5 %), Ziel 138, C/R 1,56.
    Steigend liegt der 100-Tage-Schnitt unter dem Preis, fallend darueber -
    damit laesst sich das Trend-Tor einzeln pruefen. Das Hoch liegt bewusst
    10 Kerzen vor dem Ende, sonst faellt es aus dem 60-Tage-Fenster.
    """
    start = preis - 28.0 if steigend else preis + 28.0
    k = []
    for i in range(tage):
        p = start + (preis - start) * i / (tage - 1)
        k.append([i * 86400000, p,
                  hoch if i == tage - 10 else p + 0.5,
                  tief, p, 1000.0])
    return k


def _bewertung(score=63.0, rsi=50.7, hoch_pct=-7.2, vola=0.57):
    return {
        "preis": 128.0, "chance": 70.0, "risiko": 30.0, "score": score,
        "verhaeltnis": 2.3,
        "kennzahlen": {
            "trend_ueber_sma": 1.0, "rendite_30t_pct": 3.0, "rsi14": rsi,
            "abstand_60t_hoch_pct": hoch_pct, "volatilitaet_pa": vola,
            "max_drawdown_90t_pct": 8.0, "volumen_bestaetigung": 1.0,
        },
    }


class TestStopUndZiel(unittest.TestCase):
    def test_stop_haelt_die_obergrenze_ein(self):
        # Tief 60 weit unten: der Stop darf trotzdem nur stop_max_pct weg sein
        s = prognose.stopp_und_ziel(_kerzen(tief=60.0), TOR)
        self.assertAlmostEqual(s["stop"], 128.0 * 0.88, places=6)
        self.assertAlmostEqual(s["risiko_pct"], 12.0, places=6)

    def test_ziel_ist_das_hoch_und_nicht_hochgezogen(self):
        s = prognose.stopp_und_ziel(_kerzen(), TOR)
        self.assertAlmostEqual(s["ziel"], 138.0, places=6)
        # (138 - 128) / (128 - 121.6) = 1,5625
        self.assertAlmostEqual(s["cr"], 1.5625, places=4)

    def test_nah_am_hoch_bleibt_das_verhaeltnis_klein(self):
        # Genau der Fall, der vorher durch das hochgezogene Ziel verdeckt war
        s = prognose.stopp_und_ziel(_kerzen(hoch=130.0), TOR)
        self.assertLess(s["cr"], TOR["mindest_cr"])


class TestTore(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, prognose.bewertung, "bewerten",
                        prognose.bewertung.bewerten)

    def _lage(self, **over):
        prognose.bewertung.bewerten = lambda k: _bewertung(**over)
        return prognose.lage("TEST-USDT", _kerzen(), TOR)

    def test_guenstige_lage_hat_keine_offenen_tore(self):
        z = self._lage()
        self.assertEqual(z["offene_tore"], [])
        self.assertTrue(z["guenstig"])
        self.assertAlmostEqual(z["volumen_verhaeltnis"], 1.0, places=6)

    def test_jedes_tor_nennt_sich_beim_namen(self):
        faelle = [
            (dict(score=59.0), "Score"),
            (dict(rsi=60.0), "RSI"),
            (dict(hoch_pct=-30.0), "Abstand zum Hoch"),
            (dict(hoch_pct=-1.0), "Abstand zum Hoch"),
            (dict(vola=1.5), "Vola"),
        ]
        for over, wort in faelle:
            z = self._lage(**over)
            self.assertFalse(z["guenstig"], over)
            self.assertTrue(any(wort in t for t in z["offene_tore"]),
                            "%s fehlt in %s" % (wort, z["offene_tore"]))

    def test_trend_tor_steht_auf_dem_preis(self):
        # Preis unter dem 100-Tage-Schnitt: Abschwung, kein Ruecksetzer
        prognose.bewertung.bewerten = lambda k: _bewertung()
        z = prognose.lage("TEST-USDT", _kerzen(preis=100.0, steigend=False), TOR)
        self.assertTrue(any("Trend" in t for t in z["offene_tore"]),
                        z["offene_tore"])

    def test_zu_wenig_volumen_ist_ein_tor(self):
        prognose.bewertung.bewerten = lambda k: _bewertung()
        k = _kerzen()
        for i in range(1, 6):             # genau die letzten 5 Tage brechen ein
            k[-i][5] = 100.0
        z = prognose.lage("TEST-USDT", k, TOR)
        self.assertTrue(any("Volumen" in t for t in z["offene_tore"]),
                        z["offene_tore"])


class TestMeldung(unittest.TestCase):
    def test_ohne_treffer_wird_das_gesagt(self):
        t = prognose.meldung([], 41, 5)
        self.assertIn("kein guenstiger Einstieg", t)
        self.assertIn("41", t)

    def test_treffer_nennen_wert_und_keine_order(self):
        z = {"inst": "LINK-USDT", "preis": 11.8, "stop": 11.06, "ziel": 13.3,
             "risiko_prozent": 6.2, "cr": 2.86, "score": 63.1,
             "kennzahlen": {"rsi14": 50.7, "abstand_60t_hoch_pct": -15.0,
                            "volatilitaet_pa": 0.57}}
        t = prognose.meldung([z], 41, 5)
        self.assertIn("LINK-USDT", t)
        self.assertIn("keine Order", t)


if __name__ == "__main__":
    unittest.main()
