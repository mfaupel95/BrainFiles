"""Die Tore der Prognose.

Geprueft wird die Auswahl, nicht die Bewertung: bewertung.py hat eigene
Zahlen und wird hier durch feste Kennzahlen ersetzt, damit jeder Test genau
ein Tor prueft. Das ist der Punkt - bei den ersten, aus dem Bauch gesetzten
Schwellen fand der Lauf ueber 41 Maerkte nichts, und niemand haette gemerkt,
welches Tor zu eng war.

Kein Netz: bewertung.bewerten wird je Test ersetzt und in addCleanup
zurueckgestellt.
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))            # Handel/ - prognose
sys.path.insert(0, str(HIER.parent / "scanner"))  # scanner/ - bewertung, okx

import prognose  # noqa: E402

TOR = {
    "mindest_score": 60, "mindest_score_short": 45, "hoechst_rsi": 55,
    "ruecksetzer_von_pct": -25.0, "ruecksetzer_bis_pct": -4.0,
    "mindest_rsi": 45, "erholung_von_pct": 4.0, "erholung_bis_pct": 25.0,
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


def _bewertung(score=63.0, rsi=50.7, hoch_pct=-7.2, vola=0.57, tief_pct=8.0):
    """Doppel fuer bewertung.bewerten - jetzt mit richtung-Parameter, weil
    lage() ihn durchreicht. Die Kennzahlen tragen beide Abstaende."""
    return {
        "preis": 128.0, "chance": 70.0, "risiko": 30.0, "score": score,
        "verhaeltnis": 2.3,
        "kennzahlen": {
            "trend_ueber_sma": 1.0, "rendite_30t_pct": 3.0, "rsi14": rsi,
            "abstand_60t_hoch_pct": hoch_pct,
            "abstand_60t_tief_pct": tief_pct, "volatilitaet_pa": vola,
            "max_drawdown_90t_pct": 8.0, "volumen_bestaetigung": 1.0,
        },
    }


class TestStopUndZiel(unittest.TestCase):
    def test_short_stop_ueber_dem_preis_und_ziel_darunter(self):
        # Spiegelbild: Stop ueber dem 20-Tage-Hoch, Ziel das 60-Tage-Tief
        s = prognose.stopp_und_ziel(_kerzen(preis=128.0, tief=118.0,
                                            hoch=130.0, steigend=False),
                                    TOR, "short")
        self.assertAlmostEqual(s["stop"], 128.0 * 1.05, places=6)
        self.assertAlmostEqual(s["ziel"], 118.0, places=6)
        self.assertAlmostEqual(s["risiko_pct"], 5.0, places=6)
        # (128 - 118) / (134,4 - 128) = 1,5625
        self.assertAlmostEqual(s["cr"], 1.5625, places=4)

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

    def _lage(self, richtung="long", **over):
        prognose.bewertung.bewerten = lambda k, richtung="long": _bewertung(**over)
        return prognose.lage("TEST-USDT", _kerzen(), TOR, richtung)

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
        prognose.bewertung.bewerten = lambda k, richtung="long": _bewertung()
        z = prognose.lage("TEST-USDT", _kerzen(preis=100.0, steigend=False), TOR)
        self.assertTrue(any("Trend" in t for t in z["offene_tore"]),
                        z["offene_tore"])

    def test_zu_wenig_volumen_ist_ein_tor(self):
        prognose.bewertung.bewerten = lambda k, richtung="long": _bewertung()
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
        z = {"inst": "LINK-USDT", "richtung": "long", "preis": 11.8,
             "stop": 11.06, "ziel": 13.3,
             "risiko_prozent": 6.2, "cr": 2.86, "score": 63.1,
             "kennzahlen": {"rsi14": 50.7, "abstand_60t_hoch_pct": -15.0,
                            "abstand_60t_tief_pct": 15.0,
                            "volatilitaet_pa": 0.57}}
        t = prognose.meldung([z], 41, 5)
        self.assertIn("LINK-USDT", t)
        self.assertIn("LONG", t)
        self.assertIn("keine Order", t)

    def test_short_wird_als_short_gemeldet(self):
        z = {"inst": "SUI-USDT", "richtung": "short", "preis": 11.8,
             "stop": 12.39, "ziel": 10.2,
             "risiko_prozent": 5.0, "cr": 2.86, "score": 63.1,
             "kennzahlen": {"rsi14": 50.7, "abstand_60t_hoch_pct": -15.0,
                            "abstand_60t_tief_pct": 8.5,
                            "volatilitaet_pa": 0.57}}
        t = prognose.meldung([z], 41, 5)
        self.assertIn("SHORT", t)
        self.assertIn("+5.0%", t)
        self.assertIn("Erholung", t)


class TestShortTore(unittest.TestCase):
    """Die Tore der gespiegelten Richtung pruefen einzeln."""

    def setUp(self):
        self.addCleanup(setattr, prognose.bewertung, "bewerten",
                        prognose.bewertung.bewerten)

    def _short(self, kerzen=None, **over):
        prognose.bewertung.bewerten = lambda k, richtung="long": _bewertung(**over)
        return prognose.lage("TEST-USDT", kerzen or _kerzen(preis=128.0, tief=118.0,
                                                             hoch=130.0, steigend=False),
                             TOR, "short")

    def test_short_lage_kann_guenstig_sein(self):
        z = self._short()
        self.assertEqual(z["richtung"], "short")
        self.assertEqual(z["offene_tore"], [])
        self.assertTrue(z["guenstig"])

    def test_short_rsi_zu_tief_ist_ein_tor(self):
        z = self._short(rsi=40.0)
        self.assertFalse(z["guenstig"])
        self.assertTrue(any("RSI" in t for t in z["offene_tore"]), z["offene_tore"])

    def test_short_trend_aufwaerts_ist_ein_tor(self):
        z = self._short(kerzen=_kerzen(preis=128.0, tief=118.0, hoch=130.0))
        self.assertTrue(any("Trend" in t for t in z["offene_tore"]),
                        z["offene_tore"])

    def test_short_abstand_zum_tief_ist_ein_tor(self):
        z = self._short(tief_pct=1.0)
        self.assertTrue(any("Abstand zum Tief" in t for t in z["offene_tore"]),
                        z["offene_tore"])

    def test_short_hat_eine_eigene_score_schwelle(self):
        # 47 reisst das Long-Tor (60), nicht das Short-Tor (45) - der Score
        # ist long-kalibriert, die Schwellen sind es nicht.
        z = self._short(score=47.0)
        self.assertEqual(z["offene_tore"], [])
        self.assertTrue(z["guenstig"])

    def test_short_unter_der_eigenen_schwelle_ist_ein_tor(self):
        z = self._short(score=44.0)
        self.assertFalse(z["guenstig"])
        self.assertTrue(any("Score" in t for t in z["offene_tore"]),
                        z["offene_tore"])


class TestTabelle(unittest.TestCase):
    def test_richtung_steht_in_der_tabelle(self):
        zeile = {"inst": "LINK-USDT", "richtung": "short", "score": 63.0,
                 "kennzahlen": {"rsi14": 50.7, "abstand_60t_hoch_pct": -7.2,
                                "abstand_60t_tief_pct": 8.0,
                                "volatilitaet_pa": 0.57},
                 "volumen_verhaeltnis": 1.0, "risiko_prozent": 5.0, "cr": 1.56,
                 "guenstig": True, "offene_tore": []}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            prognose.zeige("--- Test ---", [zeile])
        aus = buf.getvalue()
        self.assertIn("Richt", aus)
        self.assertIn("SHORT", aus)
        self.assertIn("8.0", aus)          # Short zeigt den Abstand zum Tief


if __name__ == "__main__":
    unittest.main()
