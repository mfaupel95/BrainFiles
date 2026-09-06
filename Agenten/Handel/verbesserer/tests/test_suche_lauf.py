"""TP3 Teil 2: Koordinatenabstieg und Overfitting-Sperre.

suche.suche() steigt von der Basis aus ueber die jeweils besten Nachbarn ab,
solange das OOS-Aggregat (netto_gv_je_runde) besser wird und das Suchbudget
reicht. Ein Kandidat gilt nur, wenn er die Basis im Aggregat schlaegt UND in
mindestens overfit_min_fenster Einzelfenstern UND >= overfit_min_runden
OOS-Runden hat. Der Fake bewerte() ersetzt ruecktest.walk_forward.
"""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import suche  # noqa: E402

WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5], "watchlist": "liste"}
KONF = {"such_budget": 50, "overfit_min_runden": 20, "overfit_min_fenster": 3}


def _wf(gv_je_runde, n=30, fenster_besser=0, basis_gv=0.0, fenster_anz=5):
    fenster = []
    for i in range(fenster_anz):
        g = gv_je_runde if i < fenster_besser else basis_gv
        fenster.append({"von_tag": 120 + 30 * i, "bis_tag": 150 + 30 * i,
                        "kennzahlen": {"n": n // fenster_anz,
                                       "netto_gv_je_runde": g,
                                       "max_drawdown": 1.0}})
    return {"fenster": fenster, "fenster_anzahl": fenster_anz,
            "gesamt": {"n": n, "netto_gv_je_runde": gv_je_runde,
                       "max_drawdown": 1.0}}


class TestLauf(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_nur_ein_fenster_besser_wird_abgelehnt(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=5, basis_gv=0.0)
            return _wf(1.0, n=30, fenster_besser=1, basis_gv=0.0)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNone(r["kandidat"])
        self.assertIn("Fenster", r["grund"])

    def test_genug_fenster_und_runden_wird_angenommen(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=0, basis_gv=0.0)
            return _wf(1.0, n=30, fenster_besser=4, basis_gv=0.0)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNotNone(r["kandidat"])

    def test_drei_von_sechs_fenstern_keine_mehrheit(self):
        # 3 von 6 Fenstern erreicht zwar overfit_min_fenster (3), ist aber
        # keine Mehrheit (> 3 noetig) -> abgelehnt. Genau der Fall, den die
        # feste Schwelle frueher durchgelassen haette.
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=60, fenster_besser=0, fenster_anz=6)
            return _wf(1.0, n=60, fenster_besser=3, fenster_anz=6)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNone(r["kandidat"])
        self.assertIn("Fenster", r["grund"])

    def test_vier_von_sechs_fenstern_ist_mehrheit(self):
        # 4 von 6 Fenstern > 3 -> Mehrheit erreicht und >= overfit_min_fenster.
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=60, fenster_besser=0, fenster_anz=6)
            return _wf(1.0, n=60, fenster_besser=4, fenster_anz=6)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNotNone(r["kandidat"])

    def test_budget_wird_eingehalten(self):
        ruf = {"n": 0}

        def fake(kerzen, kand, konf):
            ruf["n"] += 1
            return _wf(0.0)
        suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertLessEqual(ruf["n"], KONF["such_budget"] + 1)

    def test_zu_wenige_runden_wird_abgelehnt(self):
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=10)
            return _wf(1.0, n=10, fenster_besser=5)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNone(r["kandidat"])
        self.assertIn("Runden", r["grund"])

    def test_aenderungen_nennt_das_geaenderte_gate(self):
        # Nur der eine Nachbar mit mindest_score == 62.5 ist besser; er aendert
        # sonst nichts. aenderungen muss genau dieses wachen.json-Feld nennen.
        def fake(kerzen, kand, konf):
            if kand["gates"]["mindest_score"] == 62.5:
                return _wf(1.0, n=30, fenster_besser=4, basis_gv=0.0)
            return _wf(0.0, n=30, fenster_besser=0, basis_gv=0.0)
        r = suche.suche(self.basis, {}, KONF, GRENZEN, bewerte=fake)
        self.assertIsNotNone(r["kandidat"])
        self.assertEqual(r["aenderungen"], {"mindest_score": 62.5})
        self.assertEqual(r["kandidat_wf"]["gesamt"]["netto_gv_je_runde"], 1.0)


if __name__ == "__main__":
    unittest.main()
