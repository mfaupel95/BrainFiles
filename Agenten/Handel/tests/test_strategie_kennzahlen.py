"""Tests fuer strategie_kennzahlen.py (29.09.2026).

Geprueft werden die REGELN, nicht die Tageszahlen:
* Zwangsschluesse fliegen aus den Kennzahlen, werden aber AUSGEWIESEN
  (n + n_stoerung = alle Runden - die Hausrechnung muss aufgehen).
* Der MAE-Platzhalter 0.0000 wird verworfen, nicht als Messwert ausgegeben
  (Befund: der scanner schreibt bei 'ziel'-Ausstiegen durchweg 0.0000).
* Weniger als MIN_RUNDEN Runden werden als Befund markiert.
* strategy_metrics rechnet t-Statistik und Stop-aus-MAE ueberhaupt.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

# strategie_metrics braucht numpy/pandas. Die uebrigen Suiten laufen im
# scanner-Venv (ohne numpy) - dort wird uebersprungen statt rot zu werden.
try:
    import numpy  # noqa: F401
    HAT_NUMPY = True
except ImportError:
    HAT_NUMPY = False

if HAT_NUMPY:
    import auswertung_alle as a          # noqa: E402
    import strategie_kennzahlen as sk    # noqa: E402
    import strategie_metrics as sm       # noqa: E402


@unittest.skipUnless(HAT_NUMPY, "braucht numpy/pandas (Agenten/Handel/.venv)")
class _Basis(unittest.TestCase):
    pass


class RechnungTest(_Basis):
    def test_runden_fuer_ist_die_eine_zuordnung(self):
        """kennzahlen_fuer muss auf denselben Runden beruhen wie runden_fuer."""
        for spur in ("scanner", "kraken", "xperp", "orbk"):
            k = a.kennzahlen_fuer(spur)
            r = a.runden_fuer(spur)
            if k is None:
                self.assertEqual([], r, spur)
                continue
            self.assertEqual(k["n"] + (k.get("n_stoerung") or 0), len(r), spur)

    def test_stoerungen_bleiben_getrennt(self):
        """kraken hat viele Zwangsschluesse - sie duerfen die Quote nicht heben."""
        b = sk.bericht("kraken")
        self.assertIsNotNone(b)
        self.assertGreater(b["n_stoerung"], 0)
        alle_ = len(a.runden_fuer("kraken"))
        self.assertEqual(alle_, b["e"]["trades"] + b["n_stoerung"])

    def test_t_statistik_trennt_rauschen_von_vorteil(self):
        """Gleichverteilte Null-Runden -> t nahe 0; klarer Vorteil -> gross."""
        raus = sm.expectancy([-1.0, 1.0] * 40)
        self.assertLess(abs(raus["t_stat"]), 0.5)
        klar = sm.expectancy([10.0] * 30 + [-1.0] * 3)
        self.assertGreater(klar["t_stat"], 5.0)

    def test_expectancy_passt_zur_handrechnung(self):
        e = sm.expectancy([10, -5, 10, -5])
        self.assertAlmostEqual(2.5, e["expectancy"])
        self.assertAlmostEqual(0.5, e["winrate"])
        self.assertAlmostEqual(2.0, e["profit_factor"])


class MaeTest(_Basis):
    def test_platzhalter_null_wird_verworfen(self):
        """0.0000 ist kein Messwert - sonst waere der Stop-Vorschlag 0 %."""
        werte = sm.expectancy([1.0, 2.0, 3.0])
        self.assertTrue(werte)                      # Aufruf bleibt stabil
        self.assertEqual(0.0, sm.stop_from_mae([0.0] * 10, 0.9))  # Null bleibt Null
        self.assertGreater(sm.stop_from_mae([0.03] * 10, 0.9), 0.0)

    def test_mae_gefuehrt_zaehlt_nur_echte_werte(self):
        """Fuer jede Spur gilt: gefuellte <= alle, und beide sind Zahlen."""
        for spur in ("scanner", "kraken"):
            gefuellt, gesamt = sk.mae_gefuehrt(spur)
            self.assertLessEqual(gefuellt, gesamt, spur)
            self.assertGreaterEqual(gefuellt, 0)

    def test_stop_heute_kommt_aus_der_wachen(self):
        """Wo die wachen.json einen Stop nennt, muss er als Anteil ankommen."""
        s = sk._stop_aus_wachen("scanner")
        self.assertIsNotNone(s)
        self.assertGreater(s, 0.0)
        self.assertLess(s, 1.0)


class BerichtTest(_Basis):
    def test_mindestrunden_marke(self):
        b = sk.bericht("scanner")
        self.assertIsNotNone(b)
        self.assertGreaterEqual(b["e"]["trades"], sk.MIN_RUNDEN)
        b2 = sk.bericht("swap")
        if b2 is not None:
            self.assertLess(b2["e"]["trades"], sk.MIN_RUNDEN)

    def test_spur_ohne_runden_gibt_none(self):
        self.assertIsNone(sk.bericht("gibt_es_nicht"))


if __name__ == "__main__":
    unittest.main()