"""TP2 Teil 2: simuliere() bildet den Ein-/Ausstieg aus handeln.py nach.

Die Fixture ist bewusst simpel: 122 Tage flach bei 100, danach ein steiler
Anstieg, der Ziel-Treffer erzeugt. Damit laesst sich Gebuehr, Reihenfolge
(Ausstieg vor Einstieg), Stop-vor-Ziel und der Deckel fuer offene Positionen
einzeln pruefen.
"""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kosten  # noqa: E402
import ruecktest  # noqa: E402


def _flat_dann_hoch(n):
    """122 Tage flach bei 100, dann +6 je Tag - erzeugt kurz nach Tag 122
    einen Ziel-Treffer je Wert."""
    k = []
    for i in range(n):
        p = 100.0 if i < 122 else 100.0 + (i - 122) * 6.0
        k.append([i * 86400000, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


def _sanft_dann_hoch(n):
    """Leichter Aufwaertstrend bis Tag 122 (ab 60), dann dieselbe +6-Rampe.
    Der Vorlauf gibt diesem Wert einen hoeheren Score als der flachen Reihe."""
    k = []
    for i in range(n):
        p = 60.0 + i * 0.35 if i < 122 else 60.0 + 121 * 0.35 + (i - 122) * 6.0
        k.append([i * 86400000, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


def _basis_kandidat(watchlist):
    return {
        "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
                  "mindest_chance_risiko": 0.0, "stop_min": 4.0,
                  "stop_max": 12.0, "abklingzeit_tage": 3,
                  "max_offene_positionen": 4, "max_gesamt_usd": 200.0,
                  "max_pro_trade_usd": 50.0},
        "gewichte": None, "watchlist": watchlist, "sizing": "flach",
    }


class TestSim(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140), "BBB": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)

    def test_stop_prozent_klemmt(self):
        self.assertEqual(ruecktest.stop_prozent(5.0, 4.0, 12.0), 12.0)
        self.assertEqual(ruecktest.stop_prozent(0.0, 4.0, 12.0), 4.0)

    def test_gebuehr_aus_kosten(self):
        # Eine Gebuehrenzahl; test_kosten_gleich.py bindet kosten an handeln.
        self.assertEqual(ruecktest.GEBUEHR_PCT, kosten.GEBUEHR_PCT)

    def test_ziel_treffer_gibt_gewinn_nach_gebuehr(self):
        k = _basis_kandidat(["AAA"])
        # Fenster endet direkt nach dem ersten Ziel-Treffer (Tag 124): genau
        # eine geschlossene Runde. Der Wiedereinstieg am selben Tag bleibt
        # offen und wird - wie in runden_aus_journal - nicht gewertet.
        runden = ruecktest.simuliere(self.m, self.kerzen, k, 120, 125)
        self.assertEqual(len(runden), 1)
        r = runden[0]
        self.assertEqual(r["grund"], "ziel")
        # Gebuehrenfreier Gewinn zum Triggerpreis, ohne beide Gebuehrenseiten.
        gebuehrenfrei = (r["einsatz"] * r["ausstieg_kurs"] / r["einstieg_kurs"]
                         - r["einsatz"])
        self.assertGreater(r["gv"], 0.0)
        self.assertLess(r["gv"], gebuehrenfrei)

    def test_max_offene_positionen_begrenzt(self):
        k = _basis_kandidat(["AAA", "BBB"])
        k["gates"]["max_offene_positionen"] = 1
        runden = ruecktest.simuliere(self.m, self.kerzen, k, 120, 140)
        # nie mehr als eine Position gleichzeitig -> Einstiege serialisiert
        paare = [(r["einstieg_tag"], r["ausstieg_tag"]) for r in runden]
        for a in range(len(paare)):
            for b in range(a + 1, len(paare)):
                self.assertFalse(paare[a][0] < paare[b][1]
                                 and paare[b][0] < paare[a][1])

    def test_einstieg_in_score_reihenfolge(self):
        # Watchlist-Reihenfolge ist die Umkehrung der Score-Reihenfolge:
        # "AAA" (flach) bewertet niedriger als "BBB" (Vorlauf-Trend), steht
        # aber in der Watchlist zuerst. Bei max_offene_positionen = 1 muss der
        # Backtest wie der Livepfad den hoeher bewerteten Wert oeffnen (BBB),
        # nicht den in der Watchlist ersten (AAA).
        kerzen = {"AAA": _flat_dann_hoch(140), "BBB": _sanft_dann_hoch(140)}
        m = ruecktest.merkmals_matrix(kerzen)
        s_aaa = ruecktest._score(m["AAA"][120], None)[0]
        s_bbb = ruecktest._score(m["BBB"][120], None)[0]
        self.assertLess(s_aaa, s_bbb)  # Fixture-Annahme: BBB bewertet hoeher
        k = _basis_kandidat(["AAA", "BBB"])
        k["gates"]["max_offene_positionen"] = 1
        runden = ruecktest.simuliere(m, kerzen, k, 120, 125)
        self.assertEqual(len(runden), 1)
        self.assertEqual(runden[0]["inst"], "BBB")

    def test_stop_vor_ziel_am_selben_tag(self):
        # Tag mit tief <= stop UND hoch >= ziel -> grund muss "stop" sein
        kerzen = {"AAA": _flat_dann_hoch(140)}
        kerzen["AAA"][125] = [125 * 86400000, 100.0, 200.0, 1.0, 100.0, 1000.0]
        m = ruecktest.merkmals_matrix(kerzen)
        k = _basis_kandidat(["AAA"])
        runden = ruecktest.simuliere(m, kerzen, k, 120, 140)
        getroffen = [r for r in runden
                     if r["einstieg_tag"] <= 125 <= r["ausstieg_tag"]]
        self.assertTrue(getroffen)
        self.assertTrue(all(r["grund"] == "stop" for r in getroffen))


if __name__ == "__main__":
    unittest.main()
