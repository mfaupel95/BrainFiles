"""Tests fuer die Analyse der Nachkauf-Barrieren - ohne Netz.

Geprueft wird die REGEL, nicht ein Zahlenstand: eine Leiter muss tiefer reichen
als das Instrument laeuft, die Stufen duerfen dabei nicht zu grob werden, und
die Liquidation muss unter dem Planboden liegen.

Aufruf (aus diesem Ordner):  python -m unittest test_okx_bot_analyse
"""
import os
import sys
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
HIER = os.path.dirname(TESTS)
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import analyse  # noqa: E402

assert analyse.__file__.startswith(HIER), analyse.__file__


def kerzen(werte, spanne_prozent=None):
    """Kerzen bauen: [ts, open, high, low, close, vol].

    `werte` sind Schlusskurse; `spanne_prozent` setzt die Tagesspanne
    (high/low um den Schluss) - daraus ergibt sich der ATR.
    """
    raus = []
    for i, c in enumerate(werte):
        if spanne_prozent:
            halb = c * spanne_prozent / 200.0
            raus.append([1000 + i, c, c + halb, c - halb, c, 1])
        else:
            raus.append([1000 + i, c, c * 1.001, c * 0.999, c, 1])
    return raus


class MessungTest(unittest.TestCase):
    def test_atr_ist_die_mittlere_tagesspanne(self):
        k = kerzen([100.0] * 20, spanne_prozent=2.0)
        self.assertAlmostEqual(analyse.atr_prozent(k, 14), 2.0, places=6)

    def test_atr_ohne_genug_kerzen_ist_none(self):
        self.assertIsNone(analyse.atr_prozent(kerzen([100.0] * 5), 14))

    def test_max_rueckgang_vom_hoch(self):
        # 100 -> 120 -> 90: tiefster Rueckgang vom Hoch 120 auf 90 = -25 %
        self.assertAlmostEqual(analyse.max_rueckgang(kerzen([100, 120, 90]), 3), -25.0, places=6)

    def test_max_rueckgang_ohne_ruecksetzer_ist_null(self):
        self.assertAlmostEqual(analyse.max_rueckgang(kerzen([1, 2, 3, 4]), 4), 0.0, places=6)

    def test_letzter_boden_ist_das_tiefste_tief(self):
        k = kerzen([100, 90, 80])
        k[1][3] = 55.0                       # ein Tief tiefer als alle Schlusskurse
        self.assertEqual(analyse.letzter_boden(k, 90), 55.0)

    def test_zu_wenige_kerzen_geben_keine_empfehlung(self):
        self.assertIn("fehler", analyse.empfehlung({"kurs": 100.0}))


class WochenTrendTest(unittest.TestCase):
    def test_steigende_reihe_ist_aufwaerts(self):
        tr = analyse.wochen_trend(kerzen([100.0 + i for i in range(60)]), fenster=30, vergleich=4)
        self.assertEqual(tr["lage"], "aufwaerts")
        self.assertTrue(tr["sma_steigt"])

    def test_fallende_reihe_ist_abwaerts(self):
        tr = analyse.wochen_trend(kerzen([200.0 - i for i in range(60)]), fenster=30, vergleich=4)
        self.assertEqual(tr["lage"], "abwaerts")

    def test_widerspruch_ist_seitwaerts(self):
        """Kurs ueber dem Durchschnitt, aber der Durchschnitt faellt."""
        reihe = [300.0 - i for i in range(59)] + [290.0]
        tr = analyse.wochen_trend(kerzen(reihe), fenster=30, vergleich=4)
        self.assertFalse(tr["sma_steigt"])
        self.assertTrue(tr["kurs_ueber_sma"])
        self.assertEqual(tr["lage"], "seitwaerts")

    def test_zu_kurze_reihe_ist_unbekannt(self):
        tr = analyse.wochen_trend(kerzen([1.0] * 10))
        self.assertEqual(tr["lage"], "unbekannt")
        self.assertIn("zu wenig", tr["hinweis"])

    def test_abstand_zum_durchschnitt_wird_gerechnet(self):
        tr = analyse.wochen_trend(kerzen([100.0 + i for i in range(60)]))
        self.assertAlmostEqual(tr["kurs_ueber_sma_prozent"],
                               round((159.0 / tr["sma"] - 1.0) * 100.0, 2), places=2)


class EmpfehlungTest(unittest.TestCase):
    def _zeile(self, kurs=100.0, atr=12.0, r90=-25.0, r180=None, boden=None):
        return {"kurs": kurs, "atr_prozent_14": atr, "max_rueckgang_90": r90,
                "max_rueckgang_180": r180 if r180 is not None else r90,
                "max_rueckgang_365": r180 if r180 is not None else r90,
                "letzter_boden_90": boden, "leiter_tiefe_prozent": 8.0}

    def test_tiefe_folgt_dem_atr_wenn_er_groesser_ist(self):
        e = analyse.empfehlung(self._zeile(atr=12.0, r90=-25.0))
        self.assertAlmostEqual(e["ziel_tiefe_prozent"], 36.0, places=1)   # 3 x ATR
        self.assertAlmostEqual(e["schritt_prozent"], 3.0, places=1)

    def test_der_beobachtete_rueckgang_schlaegt_den_atr(self):
        e = analyse.empfehlung(self._zeile(atr=2.0, r90=-30.0))
        self.assertAlmostEqual(e["ziel_tiefe_prozent"], 30.0, places=1)

    def test_stufen_sind_der_engpass_und_werden_gemeldet(self):
        e = analyse.empfehlung(self._zeile(atr=12.0, r90=-25.0), max_stufen=4)
        self.assertEqual(e["stufen"], 4)
        self.assertTrue(any("Stufen" in w for w in e["warnungen"]))

    def test_stufen_werden_nicht_zu_grob(self):
        """Bei kleinem ATR deckelt der Abstand - die Tiefe wird zurueckgenommen."""
        e = analyse.empfehlung(self._zeile(atr=1.0, r90=-40.0))
        self.assertLessEqual(e["schritt_prozent"], 2.5 + 1e-9)
        self.assertTrue(any("Stufen" in w for w in e["warnungen"]))

    def test_liquidation_liegt_unter_dem_planboden(self):
        e = analyse.empfehlung(self._zeile())
        self.assertLess(e["liq_bei_hebel"], e["planboden"])
        self.assertLessEqual(e["hebel"], 10)

    def test_barriere_ueber_dem_markttief_wird_gemeldet(self):
        e = analyse.empfehlung(self._zeile(atr=12.0, r90=-25.0, boden=50.0))
        self.assertTrue(any("90-Tage-Tief" in w for w in e["warnungen"]))
        # Barriere UEBER dem Planboden (64 bei 36 % Fallraum) -> keine Meldung
        e2 = analyse.empfehlung(self._zeile(atr=12.0, r90=-25.0, boden=70.0))
        self.assertFalse(any("90-Tage-Tief" in w for w in e2["warnungen"]))

    def test_alte_leiter_wird_als_zu_kurz_erkannt(self):
        e = analyse.empfehlung(self._zeile())          # alte Leiter 8 %
        self.assertFalse(e["leiter_reicht"])
        self.assertIn("ZU KURZ", e["hinweis"])

    def test_tiefe_bleibt_im_rahmen(self):
        e = analyse.empfehlung(self._zeile(atr=40.0, r90=-80.0))
        self.assertLessEqual(e["ziel_tiefe_prozent"], 60.0)
        e2 = analyse.empfehlung(self._zeile(atr=0.2, r90=-1.0))
        self.assertGreaterEqual(e2["ziel_tiefe_prozent"], 10.0)   # nie enger als 10 %


class TiefeBestimmenTest(unittest.TestCase):
    def test_auto_rechnet_aus_dem_instrument(self):
        import vorschlag
        tiefe, basis = vorschlag.tiefe_bestimmen("auto", kerzen([100.0] * 40, 10.0), 100.0,
                                                 {"dca_fallraum_prozent": 15.0}, 12)
        self.assertAlmostEqual(tiefe, 30.0, places=1)     # 3 x ATR 10 %
        self.assertEqual(basis["atr_prozent_14"], 10.0)

    def test_feste_zahl_wird_genommen(self):
        import vorschlag
        tiefe, basis = vorschlag.tiefe_bestimmen("22.5", [], 100.0, {}, 12)
        self.assertAlmostEqual(tiefe, 22.5)
        self.assertIsNone(basis)

    def test_ohne_kerzen_gilt_der_rueckfall_mit_hinweis(self):
        import vorschlag
        tiefe, basis = vorschlag.tiefe_bestimmen("auto", [], 100.0,
                                                 {"dca_fallraum_prozent": 15.0}, 12)
        self.assertAlmostEqual(tiefe, 15.0)
        self.assertTrue(any("feste Wert" in w for w in basis["warnungen"]))


class WachenRegelTest(unittest.TestCase):
    def test_atr_vielfaches_steht_in_der_wachen_datei(self):
        import waechter
        w = waechter.lade_wachen()
        self.assertGreaterEqual(float(w.get("dca_atr_vielfaches") or 0), 1.0)

    def test_entschiedene_bots_sind_im_vermerk_ausgenommen(self):
        import waechter
        w = waechter.lade_wachen()
        bots = {k: v for k, v in (w.get("bots") or {}).items() if not k.startswith("_")}
        self.assertTrue(bots, "die Entscheidung zu UNI/ARB muss festgehalten sein")
        for algo, v in bots.items():
            self.assertFalse(v.get("scharf"), "%s darf nicht scharf sein" % algo)
            self.assertIn("Entscheidung Max", v.get("vermerk") or "")


if __name__ == "__main__":
    unittest.main()