"""Papier-Altlasten im Mosaic-Buch blockieren keinen Live-Platz.

Anlass 25.09.2026: Das Buch fuehrt Live und Papier in EINER Liste, die
Platzzahl von live_einstiege zaehlt beide. Eine Papier-Position ohne Order
nimmt einem echten Kauf den Platz weg.

Geprueft wird die REGEL (Papier raus, Live bleibt, Aufraeumen vor dem
Handeln) - nicht ein Tagesstand.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
sys.path.insert(0, SPUR)

import handeln as h                                                  # noqa: E402


class BuchbereinigungTest(unittest.TestCase):

    def setUp(self):
        # Nur fuer diese Klasse stilllegen - ein Modul-weites SCHREIBEN=False
        # legt die Journale der Nachbar-Testmodule still, wenn die Suite per
        # discover laeuft.
        self.schreiben = h.SCHREIBEN
        h.SCHREIBEN = False
        import okx
        self.okx = okx
        self.echt = okx.letzter_kurs
        okx.letzter_kurs = lambda inst: 84000.0
        # Modulwaechter: der echte Spurenordner darf sich nicht aendern.
        self.vorher = {n: os.path.getsize(os.path.join(SPUR, n))
                       for n in os.listdir(SPUR)
                       if os.path.isfile(os.path.join(SPUR, n))}

    def tearDown(self):
        h.SCHREIBEN = self.schreiben
        self.okx.letzter_kurs = self.echt
        self.assertEqual(
            self.vorher,
            {n: os.path.getsize(os.path.join(SPUR, n))
             for n in os.listdir(SPUR)
             if os.path.isfile(os.path.join(SPUR, n))},
            "Test hat in den echten Spurenordner geschrieben")

    def _papier(self, inst="BTC-USDC"):
        return {"inst": inst, "seite": "long", "einstieg": 84000.0,
                "stop": 80000.0, "ziel": 92000.0, "stop_pct": 5.0,
                "nominal": 100.0}

    def _live(self):
        p = self._papier("ETH-USDC")
        p["modus"] = "live"
        p["boerse"] = "kraken"
        p["kauf_ord_id"] = "OERWDB-Y3YVF-MAJGOF"
        return p

    def test_papier_raus_live_bleibt(self):
        z = {"positionen": [self._live(), self._papier()]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 1)
        self.assertEqual([p["modus"] for p in z["positionen"]], ["live"])

    def test_live_position_mit_boerse_unangetastet(self):
        p = self._live()
        z = {"positionen": [p]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 0)
        self.assertIs(z["positionen"][0], p)

    def test_leeres_buch_und_idempotenz(self):
        z = {"positionen": []}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 0)
        z = {"positionen": [self._papier()]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 1)
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 0)

    def test_ohne_kurs_bleibt_stehen(self):
        self.okx.letzter_kurs = lambda inst: None
        z = {"positionen": [self._papier()]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)


class LiveLaufRaeumtVorDemHandelnTest(unittest.TestCase):

    def test_quelle(self):
        quelle = open(os.path.join(SPUR, "handeln.py"), encoding="utf-8").read()
        aufraeumen = quelle.index("n_alt = bueche_papier_altlasten_aus(z, w)")
        kaufen = quelle.index("live_ausstiege(z, w)",
                              quelle.index("def lauf(modus)"))
        self.assertLess(aufraeumen, kaufen)

    def test_nur_papier_verwerfen_bleibt_erhalten(self):
        """Der Kill-Pfad hat seine eigene, stille Fassung - sie darf nicht
        durch die buchhaltende ersetzt werden (dort gibt es keine Order)."""
        quelle = open(os.path.join(SPUR, "handeln.py"), encoding="utf-8").read()
        self.assertIn("def nur_papier_verwerfen(z):", quelle)
        self.assertIn("nur_papier_verwerfen(z)", quelle)


if __name__ == "__main__":
    unittest.main()