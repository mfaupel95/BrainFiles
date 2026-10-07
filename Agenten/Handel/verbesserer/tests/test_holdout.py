"""F4: holdout() misst einen Kandidaten auf einem einzelnen Endblock, und
suche() lehnt einen Sieger ab, der den Holdout nicht besteht."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import ruecktest  # noqa: E402
import suche  # noqa: E402


def _kerzen(n):
    """Saegezahn wie test_ruecktest_wf, lueckenlose Tage."""
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


class TestHoldoutFunktion(unittest.TestCase):
    def test_holdout_liefert_kennzahlen_des_endblocks(self):
        kz = ruecktest.holdout({"AAA": _kerzen(240)}, KAND, 60)
        # kennzahlen()-Form: n und netto_gv_je_runde sind vorhanden.
        self.assertIn("n", kz)
        self.assertIn("netto_gv_je_runde", kz)

    def test_holdout_block_ist_nur_die_letzten_H_tage(self):
        # Ein Kandidat ohne moeglichen Einstieg (mindest_score unerreichbar)
        # liefert n == 0 - der Block rechnet, wirft nicht.
        stumm = {**KAND, "gates": {**KAND["gates"], "mindest_score": 999.0}}
        kz = ruecktest.holdout({"AAA": _kerzen(240)}, stumm, 60)
        self.assertEqual(kz["n"], 0)


WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5], "watchlist": "liste"}
# Holdout aktiv; Historie reicht (240 - 60 = 180 >= 120 + 3*30 = 210? nein ->
# darum oos_test_tage klein halten fuer den Historie-Test unten gesondert).
KONF_HOLDOUT = {"such_budget": 50, "overfit_min_runden": 20,
                "overfit_min_fenster": 3, "oos_training_tage": 120,
                "oos_test_tage": 30, "oos_schritt_tage": 30,
                "holdout_tage": 60, "holdout_min_runden": 8}


def _wf(gv_je_runde, n=30, fenster_besser=0, basis_gv=0.0, fenster_anz=5):
    fenster = []
    for i in range(fenster_anz):
        g = gv_je_runde if i < fenster_besser else basis_gv
        fenster.append({"von_tag": 120 + 30 * i, "bis_tag": 150 + 30 * i,
                        "kennzahlen": {"n": n // fenster_anz,
                                       "netto_gv_je_runde": g}})
    return {"fenster": fenster, "fenster_anzahl": fenster_anz,
            "gesamt": {"n": n, "netto_gv_je_runde": gv_je_runde}}


def _kz(netto, n):
    return {"n": n, "netto_gv_je_runde": netto}


class TestHoldoutInSuche(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)
        # Genug Historie: ein Instrument, L = 400 Tage > 60 + 210.
        self.kerzen = {"AAA": _kerzen(400)}

    def _sieger_fake(self):
        """bewerte: Basis schlecht, jeder Nachbar schlaegt sie in 4/5 Fenstern
        und hat >= 20 Runden -> ein Sieger kommt durch alle Altsperren."""
        def fake(kerzen, kand, konf):
            if kand == self.basis:
                return _wf(0.0, n=30, fenster_besser=0)
            return _wf(1.0, n=30, fenster_besser=4)
        return fake

    def test_holdout_verlust_wird_abgelehnt_fast_kandidat_gesetzt(self):
        # Sieger gewinnt die Suche, verliert aber im Holdout (Kandidat <= Basis).
        def hold(kerzen, kand, h):
            return _kz(-0.5, 12) if kand != self.basis else _kz(0.0, 12)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "Holdout nicht bestanden")
        self.assertIsNotNone(r["fast_kandidat"])
        self.assertIsNone(r["kandidat_wf"])

    def test_echter_gewinn_laeuft_durch(self):
        def hold(kerzen, kand, h):
            return _kz(2.0, 12) if kand != self.basis else _kz(0.0, 12)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNotNone(r["kandidat"])
        self.assertIsNone(r["fast_kandidat"])
        self.assertEqual(r["holdout_kandidat"]["netto_gv_je_runde"], 2.0)

    def test_zu_wenige_runden_im_holdout_wird_abgelehnt(self):
        # Kandidat besser, aber n < holdout_min_runden (8).
        def hold(kerzen, kand, h):
            return _kz(2.0, 7) if kand != self.basis else _kz(0.0, 7)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "Holdout nicht bestanden")

    def test_grenze_genau_min_runden_besteht(self):
        def hold(kerzen, kand, h):
            return _kz(2.0, 8) if kand != self.basis else _kz(0.0, 8)
        r = suche.suche(self.basis, self.kerzen, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=hold)
        self.assertIsNotNone(r["kandidat"])

    def test_zu_wenig_historie(self):
        # L = 150 Tage: 150 - 60 = 90 < 120 + 3*30 = 210 noetig.
        r = suche.suche(self.basis, {"AAA": _kerzen(150)}, KONF_HOLDOUT, GRENZEN,
                        bewerte=self._sieger_fake(), holdout_fn=lambda *a: _kz(0, 0))
        self.assertIsNone(r["kandidat"])
        self.assertEqual(r["grund"], "zu wenig Historie fuer Holdout")


if __name__ == "__main__":
    unittest.main()
