"""modell-Parameter in simuliere()/walk_forward()/holdout(): SPOT_MODELL
reproduziert das Bestandsverhalten exakt (Regression), ein Fake-Modell
zeigt, dass alle vier Hooks tatsaechlich aufgerufen werden."""

import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import ruecktest  # noqa: E402


def _flat_dann_hoch(n):
    k = []
    for i in range(n):
        p = 100.0 if i < 122 else 100.0 + (i - 122) * 6.0
        k.append([i * 86400000, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


KAND = {
    "gates": {"mindest_score": 0.0, "max_volatilitaet_pa": 9.0,
              "mindest_chance_risiko": 0.0, "stop_min": 4.0, "stop_max": 12.0,
              "abklingzeit_tage": 3, "max_offene_positionen": 4,
              "max_gesamt_usd": 200.0, "max_pro_trade_usd": 50.0},
    "gewichte": None, "watchlist": ["AAA"], "sizing": "flach",
}


class TestModellDefault(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)

    def test_ohne_modell_gleich_mit_spot_modell(self):
        a = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125)
        b = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)

    def test_spot_modell_gebuehr_ist_kosten_konstante(self):
        self.assertEqual(ruecktest.SPOT_MODELL["gebuehr_pct"]("AAA", 120),
                         ruecktest.GEBUEHR_PCT)

    def test_spot_modell_laufende_kosten_null(self):
        self.assertEqual(
            ruecktest.SPOT_MODELL["laufende_kosten"]({"einstieg_tag": 120}, 124),
            0.0)

    def test_spot_modell_in_basiswaehrung_identitaet(self):
        self.assertEqual(
            ruecktest.SPOT_MODELL["in_basiswaehrung"](42.0, "AAA", 120), 42.0)


class TestModellHooksWerdenAufgerufen(unittest.TestCase):
    def setUp(self):
        self.kerzen = {"AAA": _flat_dann_hoch(140)}
        self.m = ruecktest.merkmals_matrix(self.kerzen)
        self.gerufen = {"gebuehr_pct": 0, "pruefe_ausstieg": 0,
                        "laufende_kosten": 0, "in_basiswaehrung": 0}

    def _fake_modell(self, gebuehr=0.0005):
        def _gebuehr(inst, tag):
            self.gerufen["gebuehr_pct"] += 1
            return gebuehr

        def _pruefe(position, kerze):
            self.gerufen["pruefe_ausstieg"] += 1
            hoch, tief = kerze[2], kerze[3]
            if tief <= position["stop"]:
                return "stop", position["stop"]
            if hoch >= position["ziel"]:
                return "ziel", position["ziel"]
            return None

        def _laufend(position, tag):
            self.gerufen["laufende_kosten"] += 1
            return 0.0

        def _basis(betrag, inst, tag):
            self.gerufen["in_basiswaehrung"] += 1
            return betrag * 2.0  # erkennbare, falsche "Umrechnung"

        return {"gebuehr_pct": _gebuehr, "pruefe_ausstieg": _pruefe,
                "laufende_kosten": _laufend, "in_basiswaehrung": _basis}

    def test_alle_vier_hooks_werden_gerufen(self):
        modell = self._fake_modell()
        runden = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                     modell=modell)
        self.assertEqual(len(runden), 1)
        self.assertGreater(self.gerufen["gebuehr_pct"], 0)
        self.assertGreater(self.gerufen["pruefe_ausstieg"], 0)
        self.assertGreater(self.gerufen["laufende_kosten"], 0)
        self.assertGreater(self.gerufen["in_basiswaehrung"], 0)

    def test_in_basiswaehrung_wirkt_auf_gv_einsatz_und_erloes(self):
        modell = self._fake_modell()
        ohne = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125)[0]
        mit = ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125,
                                  modell=modell)[0]
        self.assertAlmostEqual(mit["gv"], ohne["gv"] * 2.0, places=6)
        self.assertAlmostEqual(mit["einsatz"], ohne["einsatz"] * 2.0, places=6)
        self.assertAlmostEqual(mit["erloes"], ohne["erloes"] * 2.0, places=6)

    def test_gebuehr_pct_wird_mit_ausstiegstag_gerufen(self):
        gesehen = []

        def _gebuehr(inst, tag):
            gesehen.append(tag)
            return 0.0005

        modell = self._fake_modell()
        modell["gebuehr_pct"] = _gebuehr
        ruecktest.simuliere(self.m, self.kerzen, KAND, 120, 125, modell=modell)
        # Ziel-Treffer liegt bei Tag 124 (siehe Fixture) - der Hook sieht den
        # Ausstiegstag, nicht den Einstiegstag (120).
        self.assertIn(124, gesehen)
        self.assertNotIn(120, gesehen)


class TestWalkForwardUndHoldoutReichenModellDurch(unittest.TestCase):
    def test_walk_forward_ohne_modell_unveraendert(self):
        kerzen = {"AAA": _flat_dann_hoch(240)}
        konf = {"oos_training_tage": 120, "oos_test_tage": 30,
                "oos_schritt_tage": 30}
        a = ruecktest.walk_forward(kerzen, KAND, konf)
        b = ruecktest.walk_forward(kerzen, KAND, konf,
                                   modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)

    def test_holdout_ohne_modell_unveraendert(self):
        kerzen = {"AAA": _flat_dann_hoch(240)}
        a = ruecktest.holdout(kerzen, KAND, 60)
        b = ruecktest.holdout(kerzen, KAND, 60, modell=ruecktest.SPOT_MODELL)
        self.assertEqual(a, b)


def _flat_dann_hoch_ab_tag(n, start_epoch_tag):
    """Wie _flat_dann_hoch, aber die Kerzen beginnen an einem echten,
    von 0 verschiedenen Kalendertag - deckt auf, wenn ein Hook mit dem
    Array-Index statt dem echten Kalendertag aufgerufen wird (Review-Fund
    Critical #2: kraken_modell schluesselt FX-Kurse nach Kalendertag, nicht
    nach Index)."""
    k = []
    for i in range(n):
        p = 100.0 if i < 122 else 100.0 + (i - 122) * 6.0
        ts = (start_epoch_tag + i) * 86400000
        k.append([ts, p, p * 1.001, p * 0.999, p, 1000.0])
    return k


class TestModellBekommtKalendertagNichtIndex(unittest.TestCase):
    """Review-Fund Critical #2: der Hook muss den echten Kalendertag aus dem
    Kerzen-Zeitstempel sehen, nicht den Array-Index in simuliere()'s
    Fenster-Schleife - sonst schluesselt ein Modell wie kraken_modell, das
    FX-Kurse nach Kalendertag ablegt, ins Leere."""

    def test_gebuehr_pct_bekommt_kalendertag_nicht_index(self):
        start_epoch_tag = 20000
        kerzen = {"AAA": _flat_dann_hoch_ab_tag(140, start_epoch_tag)}
        m = ruecktest.merkmals_matrix(kerzen)
        gesehen = []

        def _gebuehr(inst, tag):
            gesehen.append(tag)
            return 0.0005

        modell = dict(ruecktest.SPOT_MODELL)
        modell["gebuehr_pct"] = _gebuehr
        ruecktest.simuliere(m, kerzen, KAND, 120, 125, modell=modell)
        # Ziel-Treffer bei Array-Index 124 - der echte Kalendertag ist
        # start_epoch_tag + 124, NICHT 124.
        self.assertIn(start_epoch_tag + 124, gesehen)
        self.assertNotIn(124, gesehen)

    def test_in_basiswaehrung_bekommt_kalendertag_nicht_index(self):
        start_epoch_tag = 20000
        kerzen = {"AAA": _flat_dann_hoch_ab_tag(140, start_epoch_tag)}
        m = ruecktest.merkmals_matrix(kerzen)
        gesehen = []

        def _basis(betrag, inst, tag):
            gesehen.append(tag)
            return betrag

        modell = dict(ruecktest.SPOT_MODELL)
        modell["in_basiswaehrung"] = _basis
        ruecktest.simuliere(m, kerzen, KAND, 120, 125, modell=modell)
        self.assertIn(start_epoch_tag + 124, gesehen)
        self.assertNotIn(124, gesehen)


if __name__ == "__main__":
    unittest.main()
