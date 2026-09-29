"""Verwaiste Instrumente: Ausstiege muessen ALLE offenen Positionen pruefen.

BEFUND 28.09.2026
-----------------
macd_mtf, squeeze, wavetrend (und supertrend, dieselbe Schleife) prueften ihre
Ausstiege nur ueber `w["instrumente"]`. Als die Liste von USDT- auf USDC-Paare
umgestellt wurde, blieben je Spur vier Positionen auf ETH-USDT/SOL-USDT/BTC-USDT
im Buch stehen: sie wurden nie wieder geprueft, nie geschlossen und belegten
alle vier Plaetze. Folge: das Journal fror ein (letzte Zeile 20./21.09.), kein
Einstieg war mehr moeglich, und die Auswertung meldete "keine geschlossene
Runde". Genau das sah aus wie "die Spur verbessert sich nicht".

Geprueft wird hier zweierlei:
  1. die gemeinsame Regel in wachen_pruefung (pruef_instrumente) - Reihenfolge,
     Doppelungen, fehlende Felder;
  2. dass die vier Spuren sie auch WIRKLICH benutzen (Quelltext-Regel) und dass
     der Einstieg auf die Plan-Instrumente begrenzt bleibt - sonst wuerde die
     Spur auf einem Instrument handeln, das sie nicht mehr fuehren soll.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
if os.path.join(HANDEL, "scanner") not in sys.path:
    sys.path.insert(0, os.path.join(HANDEL, "scanner"))

import wachen_pruefung as wp  # noqa: E402

SPUREN = ("macd_mtf", "squeeze", "wavetrend", "supertrend", "mosaic")


class RegelTest(unittest.TestCase):
    def test_plan_zuerst_dann_verwaiste_alphabetisch(self):
        w = {"instrumente": ["ETH-USDC", "BTC-USDC"]}
        z = {"positionen": [{"inst": "SOL-USDT"}, {"inst": "BTC-USDC"},
                            {"inst": "ETH-USDT"}]}
        self.assertEqual(wp.pruef_instrumente(w, z),
                         ["ETH-USDC", "BTC-USDC", "ETH-USDT", "SOL-USDT"])

    def test_ohne_verwaiste_bleibt_der_plan(self):
        w = {"instrumente": ["BTC-USDC"]}
        z = {"positionen": [{"inst": "BTC-USDC"}]}
        self.assertEqual(wp.pruef_instrumente(w, z), ["BTC-USDC"])
        self.assertEqual(wp.verwaiste_instrumente(w, z), [])

    def test_doppelte_position_macht_kein_doppeltes_instrument(self):
        w = {"instrumente": ["BTC-USDC"]}
        z = {"positionen": [{"inst": "SOL-USDT"}, {"inst": "SOL-USDT"}]}
        self.assertEqual(wp.pruef_instrumente(w, z), ["BTC-USDC", "SOL-USDT"])

    def test_fehlende_felder_werfen_nicht(self):
        self.assertEqual(wp.pruef_instrumente({}, {}), [])
        self.assertEqual(wp.pruef_instrumente({"instrumente": None}, {}), [])
        self.assertEqual(wp.plan_instrumente({"instrumente": ["", None]}), [])

    def test_position_ohne_instrument_wird_ignoriert(self):
        # Eine Position ohne 'inst' kann nicht geprueft werden - sie darf aber
        # auch keine None in die Liste schreiben.
        self.assertEqual(wp.pruef_instrumente({"instrumente": []},
                                              {"positionen": [{"x": 1}]}), [])


class QuelltextTest(unittest.TestCase):
    """Die vier Spuren MUESSEN die Regel benutzen - sonst hilft sie nichts."""

    def _quelle(self, spur):
        with open(os.path.join(HANDEL, spur, "handeln.py"),
                  encoding="utf-8") as f:
            return f.read()

    def test_ausstiegsschleife_nimmt_pruef_instrumente(self):
        for spur in SPUREN:
            t = self._quelle(spur)
            self.assertIn("for inst in wp.pruef_instrumente(w, z):", t, spur)
            self.assertIn("plan = wp.plan_instrumente(w)", t, spur)
            self.assertIn("verwaist = wp.verwaiste_instrumente(w, z)", t, spur)

    def test_kein_ausstieg_mehr_ueber_die_wachenliste(self):
        # Nur fuer die vier Indikatorspuren: bei ihnen war die Liste die
        # AUSSTIEGS-Schleife. mosaic fuehrt daneben eine Einstiegs-Schleife ueber
        # den Plan - Einstiege SOLLEN dort begrenzt bleiben.
        for spur in ("macd_mtf", "squeeze", "wavetrend", "supertrend"):
            self.assertNotIn('for inst in w.get("instrumente", []):',
                             self._quelle(spur), spur)

    def test_einstieg_bleibt_auf_die_plan_instrumente_begrenzt(self):
        # Die Bedingung ist die EIGENSCHAFT, nicht die Zeile: nach
        # "if inst in plan:" muss der Einstieg kommen, gleich wie er heisst und
        # wie er eingerueckt ist (mosaic prueft mit vier Kerzenreihen).
        import re
        muster = re.compile(r"if inst in plan:\s*\n\s+pruefe_einstieg\(")
        for spur in SPUREN:
            t = self._quelle(spur)
            self.assertIsNotNone(muster.search(t), spur)

    def test_verwaiste_werden_gemeldet(self):
        # Ohne Meldung sieht niemand, dass eine Position ausserhalb des Plans
        # liegt - sie liefe still weiter.
        for spur in SPUREN:
            self.assertIn("Verwaiste Instrumente", self._quelle(spur), spur)


if __name__ == "__main__":
    unittest.main(verbosity=2)