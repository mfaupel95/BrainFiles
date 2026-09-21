"""Slippage-Messung: die Rechnung und der Leser, ohne Netz.

Der Messwert selbst ist die Zahl, die das Buch bisher nur ANGENOMMEN hat
(slippage_pct 3.0 je Seite). Damit die Zahl belastbar bleibt, wird hier die
Rechnung festgehalten - nicht ein momentaner Messwert, der sich mit jedem
Marktlauf aendert.

Kein Netz: `pool_daten` wird ersetzt, `einstiege` liest ein Temp-Journal.
Direkt ausfuehrbar:  python tests/test_slippage_messen.py
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import slippage_messen as sm                                        # noqa: E402


class ImpactTest(unittest.TestCase):

    def test_roundtrip_ist_zweimal_der_einfluss(self):
        # Kauf + Verkauf belasten die Quote-Seite je einmal.
        self.assertAlmostEqual(sm.impact_pct(50.0, 10000.0), 1.0, places=6)
        self.assertAlmostEqual(sm.impact_pct(100.0, 10000.0), 2.0, places=6)

    def test_kleinere_order_kostet_weniger(self):
        self.assertLess(sm.impact_pct(50.0, 60000.0), sm.impact_pct(500.0, 60000.0))

    def test_leerer_pool_ist_unendlich(self):
        # Ein toter Pool ist kein "billiger" Pool: dort gibt es keinen Fill,
        # keine 3 % - deshalb unendlich und nicht 0.
        self.assertEqual(sm.impact_pct(50.0, 0.0), float("inf"))

    def test_tiefe_haelfte_der_liquiditaet(self):
        # Ein AMM-Kauf belastet die Quote-Seite; die ausgewiesene Liquiditaet
        # zaehlt beide Seiten. Die Naeherung nimmt deshalb die Haelfte.
        sm._hol = lambda url, versuche=3: {"pairs": [
            {"dexId": "pumpfun", "priceUsd": "0.001", "marketCap": "400000",
             "liquidity": {"usd": 20000.0}}]}
        d = sm.pool_daten("beliebig")
        self.assertEqual(d["tiefe_usd"], 20000.0)
        self.assertEqual(d["tiefe_quote_usd"], 10000.0)

    def test_liquideste_pool_gewinnt(self):
        sm._hol = lambda url, versuche=3: {"pairs": [
            {"dexId": "klein", "priceUsd": "1", "liquidity": {"usd": 100.0}},
            {"dexId": "gross", "priceUsd": "2", "liquidity": {"usd": 900.0}}]}
        self.assertEqual(sm.pool_daten("x")["dex"], "gross")


class LeserTest(unittest.TestCase):

    def test_nur_einstiege_und_juengste_anzahl(self):
        tmp = Path(tempfile.mkdtemp())
        alt = sm.JOURNAL
        sm.JOURNAL = tmp / "handelsjournal.csv"
        self.addCleanup(setattr, sm, "JOURNAL", alt)
        with sm.JOURNAL.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "aktion", "token", "symbol", "einsatz_usd"])
            w.writerow(["2026-09-21T00:00:00+00:00", "eroeffnen", "AAA", "A", "50"])
            w.writerow(["2026-09-21T00:00:01+00:00", "schliessen", "BBB", "B", "50"])
            w.writerow(["2026-09-21T00:00:02+00:00", "eroeffnen", "CCC", "C", "50"])
        zeilen = sm.einstiege(10)
        self.assertEqual([z["token"] for z in zeilen], ["AAA", "CCC"])
        self.assertEqual(len(sm.einstiege(1)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
