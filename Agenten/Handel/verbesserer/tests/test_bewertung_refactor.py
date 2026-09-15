import sys
import unittest
from pathlib import Path

SCANNER = Path(__file__).resolve().parents[2] / "scanner"
sys.path.insert(0, str(SCANNER))
import bewertung  # noqa: E402


def _kerzen(n=160):
    # sanft steigende Reihe mit etwas Zappeln, deterministisch
    k = []
    p = 100.0
    for i in range(n):
        p *= 1.0 + (0.004 if i % 3 else -0.003)
        hoch, tief = p * 1.01, p * 0.99
        k.append([i * 86400000, p * 0.999, hoch, tief, p, 1000.0 + i])
    return k


class TestRefactor(unittest.TestCase):
    def setUp(self):
        self.k = _kerzen()

    def test_gewichte_none_ist_wie_vorher(self):
        self.assertEqual(bewertung.bewerten(self.k),
                         bewertung.bewerten(self.k, gewichte=None))

    def test_konstanten_summieren_auf_eins(self):
        self.assertAlmostEqual(sum(bewertung.CHANCE_GEWICHTE.values()), 1.0, 9)
        self.assertAlmostEqual(sum(bewertung.RISIKO_GEWICHTE.values()), 1.0, 9)

    def test_roh_komponenten_rekombinieren_zum_score(self):
        r = bewertung.roh_komponenten(self.k)
        cg, rg = bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE
        chance = 100.0 * (cg["trend"] * r["c_trend"]
                          + cg["momentum"] * r["c_momentum"]
                          + cg["ruecksetzer"] * r["c_ruecksetzer"]
                          + cg["nicht_ueberkauft"] * r["c_nicht_ueberkauft"]
                          + cg["volumen"] * r["c_volumen"])
        risiko = 100.0 * (rg["vola"] * r["r_vola"]
                          + rg["drawdown"] * r["r_drawdown"]
                          + rg["extrem_rsi"] * r["r_extrem_rsi"]
                          + rg["absturz_momentum"] * r["r_absturz_momentum"])
        score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
        self.assertAlmostEqual(score, bewertung.bewerten(self.k)["score"], 1)

    def test_andere_gewichte_aendern_score(self):
        # `gewichte` ist das DRITTE Argument. Positionell uebergeben landete
        # das dict in `richtung` und die Gewichte kamen nie an - der Test war
        # deshalb gruen, obwohl er nichts geprueft hat.
        g = {"chance": {"trend": 1.0, "momentum": 0.0, "ruecksetzer": 0.0,
                        "nicht_ueberkauft": 0.0, "volumen": 0.0},
             "risiko": dict(bewertung.RISIKO_GEWICHTE)}
        nur_trend = bewertung.bewerten(self.k, gewichte=g)["score"]
        standard = bewertung.bewerten(self.k)["score"]
        self.assertNotEqual(nur_trend, standard)
        # Richtung pruefen, damit der Score sich messbar bewegt: die
        # Chance-Komponenten dieser Reihe stehen bei 0,30 bis 1,00, das
        # Gewicht 1,0 auf `trend` muss den Chance-Wert also heben.
        self.assertGreater(nur_trend, standard)

    def test_dict_als_richtung_wird_abgelehnt(self):
        # Der stille Fehler, der diesen Test rot machte: ein dict als zweites
        # Argument ist die Richtung. Er darf nicht als "long" durchgehen.
        with self.assertRaises(ValueError):
            bewertung.bewerten(self.k, {"chance": {}})
