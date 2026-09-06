"""TP2 Teil 3: walk_forward() aggregiert die OOS-Runden aller Testfenster.

Die Fixture ist eine simple Saegezahn-Reihe (fuenf Tage rauf, fuenf runter),
lang genug fuer mehrere Fenster bei Training 120 / Test 30 / Schritt 30.
"""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _kerzen(n):
    k, p = [], 100.0
    for i in range(n):
        p *= 1.0 + (0.01 if (i // 5) % 2 else -0.009)
        k.append([i * 86400000, p, p * 1.03, p * 0.97, p, 1000.0])
    return k


KAND = {
    "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
              "mindest_chance_risiko": 0.0, "stop_min": 4.0, "stop_max": 12.0,
              "abklingzeit_tage": 3, "max_offene_positionen": 4,
              "max_gesamt_usd": 200.0, "max_pro_trade_usd": 50.0},
    "gewichte": None, "watchlist": ["AAA"], "sizing": "flach",
}
KONF = {"oos_training_tage": 120, "oos_test_tage": 30, "oos_schritt_tage": 30}


class TestWF(unittest.TestCase):
    def test_fensteranzahl(self):
        wf = ruecktest.walk_forward({"AAA": _kerzen(240)}, KAND, KONF)
        # Testfenster starten bei 120, 150, 180, 210 -> letztes endet 240
        self.assertEqual(wf["fenster_anzahl"], 4)

    def test_gesamt_ist_summe_der_fensterrunden(self):
        wf = ruecktest.walk_forward({"AAA": _kerzen(240)}, KAND, KONF)
        n_fenster = sum(f["kennzahlen"]["n"] for f in wf["fenster"])
        self.assertEqual(wf["gesamt"]["n"], n_fenster)

    def test_kennzahlen_leere_runden(self):
        kz = ruecktest.kennzahlen([])
        self.assertEqual(kz["n"], 0)
        self.assertIsNone(kz["liquidationsabstand"])

    def test_fenstergrenzen(self):
        wf = ruecktest.walk_forward({"AAA": _kerzen(240)}, KAND, KONF)
        grenzen = [(f["von_tag"], f["bis_tag"]) for f in wf["fenster"]]
        self.assertEqual(grenzen, [(120, 150), (150, 180), (180, 210), (210, 240)])

    def test_kennzahlen_gefuellt(self):
        runden = [
            {"einstieg_tag": 1, "gv": 10.0},
            {"einstieg_tag": 2, "gv": -4.0},
            {"einstieg_tag": 3, "gv": 6.0},
        ]
        kz = ruecktest.kennzahlen(runden)
        self.assertEqual(kz["n"], 3)
        self.assertAlmostEqual(kz["summe_gv"], 12.0)
        self.assertAlmostEqual(kz["netto_gv_je_runde"], 4.0)
        self.assertAlmostEqual(kz["trefferquote"], 2 / 3)
        self.assertAlmostEqual(kz["beobachtete_trefferquote"], 2 / 3)
        self.assertAlmostEqual(kz["gebuehr_runde_pct"], 2 * ruecktest.GEBUEHR_PCT)
        # mittlerer Gewinn 8, mittlerer Verlustbetrag 4 -> 4 / (8 + 4)
        self.assertAlmostEqual(kz["noetige_trefferquote"], 4.0 / 12.0)
        # Kurve: 10, 6, 12 -> Hoch 10 dann Stand 6 -> Drawdown 4
        self.assertAlmostEqual(kz["max_drawdown"], 4.0)
        self.assertIsNone(kz["liquidationsabstand"])
        self.assertIsNone(kz["funding_pct"])

    def test_noetige_trefferquote_none_ohne_verlust(self):
        kz = ruecktest.kennzahlen([{"einstieg_tag": 1, "gv": 3.0}])
        self.assertIsNone(kz["noetige_trefferquote"])


if __name__ == "__main__":
    unittest.main()
