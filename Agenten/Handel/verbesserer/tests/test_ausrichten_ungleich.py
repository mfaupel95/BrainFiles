"""ausrichten_ungleich(): junge Listings bleiben im Test, Vorlauf wird uebersprungen."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _reihe(tage, kurs=100.0, wellig=False):
    def c(t):
        return kurs * (1.0 + (0.12 * ((t % 10) - 5) / 5.0 if wellig else 0.0))
    return [[t * 86400000, c(t), c(t) * 1.03, c(t) * 0.97, c(t), 1000.0]
            for t in tage]


class TestAusrichtenUngleich(unittest.TestCase):
    def test_junges_listing_bleibt_und_ist_vorn_aufgefuellt(self):
        alt = _reihe(range(300))
        jung = _reihe(range(200, 300))
        aus, hinweise = ruecktest.ausrichten_ungleich(
            {"ALT": alt, "JUNG": jung}, min_tage=100)
        self.assertEqual(len(aus["ALT"]), 300)
        self.assertEqual(len(aus["JUNG"]), 300)
        self.assertEqual([k[0] for k in aus["ALT"]], [k[0] for k in aus["JUNG"]])
        self.assertTrue(all(k[5] is None for k in aus["JUNG"][:200]))
        self.assertEqual(aus["JUNG"][200][5], 1000.0)
        self.assertTrue(any("Vorlauf" in h for h in hinweise))

    def test_zu_kurzes_wird_verworfen(self):
        aus, hinweise = ruecktest.ausrichten_ungleich(
            {"ALT": _reihe(range(300)), "WINZIG": _reihe(range(290, 300))},
            min_tage=100)
        self.assertNotIn("WINZIG", aus)
        self.assertTrue(any("WINZIG" in h for h in hinweise))

    def test_luecke_nach_start_wird_flach_gefuellt(self):
        lueck = _reihe([t for t in range(300) if t != 150])
        aus, hinweise = ruecktest.ausrichten_ungleich(
            {"ALT": _reihe(range(300)), "LUECK": lueck}, min_tage=100)
        k = aus["LUECK"][150]
        self.assertEqual(k[1:5], [100.0] * 4)
        self.assertEqual(k[5], 0.0)
        self.assertTrue(any("Luecken" in h for h in hinweise))

    def test_alte_ausrichten_laesst_ergebnis_unveraendert(self):
        aus, _ = ruecktest.ausrichten_ungleich(
            {"ALT": _reihe(range(300)), "JUNG": _reihe(range(200, 300))},
            min_tage=100)
        nochmal, hinweise = ruecktest.ausrichten(aus)
        self.assertEqual(nochmal, aus)
        self.assertEqual(hinweise, [])

    def test_matrix_beginnt_beim_jungen_nach_eigenem_warmup(self):
        aus, _ = ruecktest.ausrichten_ungleich(
            {"ALT": _reihe(range(400)), "JUNG": _reihe(range(150, 400))},
            min_tage=100)
        m = ruecktest.merkmals_matrix(aus)
        self.assertEqual(min(m["ALT"]), ruecktest.MINDEST_KERZEN)
        self.assertEqual(min(m["JUNG"]), 150 + ruecktest.MINDEST_KERZEN)
        self.assertEqual(max(m["JUNG"]), 399)

    def test_gleich_lange_reihen_geben_gleiche_matrix_wie_vorher(self):
        reihen = {"A": _reihe(range(200)), "B": _reihe(range(200), 50.0)}
        m = ruecktest.merkmals_matrix(reihen)
        self.assertEqual(min(m["A"]), ruecktest.MINDEST_KERZEN)
        self.assertEqual(max(m["B"]), 199)

    def test_walk_forward_laeuft_mit_jungem_listing(self):
        aus, _ = ruecktest.ausrichten_ungleich(
            {"ALT": _reihe(range(400), wellig=True),
             "JUNG": _reihe(range(150, 400), wellig=True),
             "MITTEL": _reihe(range(50, 400), wellig=True)}, min_tage=100)
        kand = {"gates": {"mindest_score": 0, "max_volatilitaet_pa": 99,
                          "mindest_chance_risiko": 0, "abklingzeit_tage": 2,
                          "max_offene_positionen": 3, "max_pro_trade_usd": 100,
                          "max_gesamt_usd": 300, "stop_min": 4, "stop_max": 15},
                "watchlist": ["ALT", "JUNG", "MITTEL"]}
        konf = {"oos_training_tage": 120, "oos_test_tage": 30,
                "oos_schritt_tage": 30}
        erg = ruecktest.walk_forward(aus, kand, konf)
        self.assertGreater(erg["fenster_anzahl"], 0)
        # Einstiege des jungen Listings erst nach dessen eigenem Warmup.
        matrix = ruecktest.merkmals_matrix(aus)
        runden = ruecktest.simuliere(matrix, aus, kand, 120, 400)
        jung = [r for r in runden if r["inst"] == "JUNG"]
        self.assertTrue(jung)
        self.assertTrue(all(r["einstieg_tag"] >= 150 + ruecktest.MINDEST_KERZEN
                            for r in jung))


if __name__ == "__main__":
    unittest.main()
