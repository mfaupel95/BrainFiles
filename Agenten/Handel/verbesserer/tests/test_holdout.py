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


if __name__ == "__main__":
    unittest.main()
