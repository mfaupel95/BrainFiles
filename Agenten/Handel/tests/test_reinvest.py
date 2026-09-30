"""reinvest: Schwelle und Endwert - nur die eindeutigen Eigenschaften.

Bewusst NICHT festgeschrieben: was endwert() tut, wenn die Kosten einer
Reinvestition den Ertrag uebersteigen (siehe Hinweis im Test unten).
"""

import math
import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import dca  # noqa: E402
import reinvest as ri  # noqa: E402


class SchwelleTest(unittest.TestCase):
    def setUp(self):
        self.orig = dict(dca.KOSTEN)
        self.addCleanup(lambda: (dca.KOSTEN.clear(), dca.KOSTEN.update(self.orig)))
        dca.KOSTEN["t_gratis"] = (0.0, 0.0)
        dca.KOSTEN["t_fix"] = (0.001, 28.0)
        dca.KOSTEN["t_teuer"] = (0.10, 5.0)

    def test_ohne_fixkosten_lohnt_jeder_betrag(self):
        self.assertEqual(ri.schwelle(0.05, "t_gratis"), 0.0)

    def test_fixkosten_verschieben_die_schwelle_nach_oben(self):
        # nutzen je USD = 0.05*1 - 0.001 = 0.049 ; 28 / 0.049
        self.assertAlmostEqual(ri.schwelle(0.05, "t_fix"), 28 / 0.049)

    def test_hoehere_rendite_senkt_die_schwelle(self):
        self.assertLess(ri.schwelle(0.20, "t_fix"), ri.schwelle(0.05, "t_fix"))

    def test_laengere_restlaufzeit_senkt_die_schwelle(self):
        self.assertLess(ri.schwelle(0.05, "t_fix", 3.0),
                        ri.schwelle(0.05, "t_fix", 1.0))

    def test_anteil_ueber_rendite_lohnt_nie(self):
        self.assertEqual(ri.schwelle(0.05, "t_teuer"), math.inf)

    def test_unbekannte_kette_faellt_auf_keine_zurueck(self):
        self.assertEqual(ri.schwelle(0.05, "gibt_es_nicht"),
                         ri.schwelle(0.05, "keine"))


class EndwertTest(unittest.TestCase):
    def setUp(self):
        self.orig = dict(dca.KOSTEN)
        self.addCleanup(lambda: (dca.KOSTEN.clear(), dca.KOSTEN.update(self.orig)))
        dca.KOSTEN["t_gratis"] = (0.0, 0.0)

    def test_ohne_reinvestition_linear(self):
        self.assertAlmostEqual(ri.endwert(1000, 0.05, 3, 0, "t_gratis"), 1150.0)

    def test_kostenlos_entspricht_zinseszins(self):
        erwartet = 1000 * (1 + 0.06 / 12) ** 36
        self.assertAlmostEqual(ri.endwert(1000, 0.06, 3, 12, "t_gratis"),
                               erwartet, places=6)

    def test_kostenlose_reinvestition_schlaegt_liegenlassen(self):
        self.assertGreater(ri.endwert(1000, 0.06, 3, 12, "t_gratis"),
                           ri.endwert(1000, 0.06, 3, 0, "t_gratis"))

    def test_null_jahre_aendert_nichts(self):
        self.assertEqual(ri.endwert(1000, 0.06, 0, 12, "t_gratis"), 1000)

    def test_quellenliste_ist_wohlgeformt(self):
        for name, apy, tvl, art, warnung in ri.QUELLEN:
            self.assertTrue(name and art and warnung)
            self.assertGreater(apy, 0)
            self.assertGreater(tvl, 0)
        # DEX-Pools tragen den Hinweis auf impermanenten Verlust
        for name, apy, tvl, art, warnung in ri.QUELLEN:
            if art == "DEX-Pool":
                self.assertIn("IMPERMANENT LOSS", warnung)


if __name__ == "__main__":
    unittest.main()
