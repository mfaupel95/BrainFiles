"""MAE/MFE - die Regel und ihr Nachweis (03.10.2026).

Die Kennzahl beantwortet die Frage, die keine Trefferquote beantwortet:
lief die Position erst ins Plus und drehte dann um (Stop zu eng), oder lief
sie sofort gegen den Einstieg (Signal falsch)?

Der Richtungsfaktor ist das Eigentliche hier: der scanner ist long-only und
braucht ihn nicht, die Indikatorspuren handeln auch short. Die Gegenprobe
laeuft deshalb ueber beide Richtungen mit DENSELEN Kursen - ohne Faktor
kaemen die beiden Seiten spiegelverkehrt heraus.
"""
import os
import sys
import unittest
from datetime import date

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import mae  # noqa: E402


class MaeTest(unittest.TestCase):

    def pos(self, seite="long", einstieg=100.0):
        return {"inst": "BTC", "seite": seite, "einstieg": einstieg,
                "eroeffnet_zeit": "2026-10-01"}

    def test_long_und_short_geben_dieselbe_auskunft(self):
        lang, kurz = self.pos("long"), self.pos("short")
        for k in (100.0, 108.0, 94.0, 96.0):
            mae.merke_extrem(lang, k)
        for k in (100.0, 92.0, 106.0, 97.0):
            mae.merke_extrem(kurz, k)
        self.assertAlmostEqual(lang["mfe_pct"], 8.0, places=6)
        self.assertAlmostEqual(lang["mae_pct"], -6.0, places=6)
        self.assertAlmostEqual(kurz["mfe_pct"], 8.0, places=6)
        self.assertAlmostEqual(kurz["mae_pct"], -6.0, places=6)

    def test_ohne_richtungsfaktor_waere_short_gespiegelt(self):
        """Die Gegenprobe selbst: dieselben Kurse ohne Faktor.

        Roh gerechnet meldet eine Short-Position bei 106 den HOECHSTWert +6 %
        - das ist in Wirklichkeit der groesste VERLUST. Der Faktor dreht das
        Vorzeichen, erst dadurch bedeutet MFE "Vorlauf" und MAE "Gegenlauf".
        """
        p = self.pos("short")
        roh = [(k - 100.0) for k in (100.0, 92.0, 106.0)]
        self.assertAlmostEqual(max(roh), 6.0, places=6)     # falsch ausgezeichnet
        self.assertAlmostEqual(min(roh), -8.0, places=6)
        for k in (92.0, 106.0):
            mae.merke_extrem(p, k)
        # mit Faktor: der Vorlauf ist +8 (Kurs 92), der Gegenlauf -6 (Kurs 106)
        self.assertAlmostEqual(p["mfe_pct"], 8.0, places=6)
        self.assertAlmostEqual(p["mae_pct"], -6.0, places=6)

    def test_vorlauf_nie_negativ_gegenlauf_nie_positiv(self):
        p = self.pos("long")
        mae.merke_extrem(p, 101.0)
        self.assertGreaterEqual(p["mfe_pct"], 0.0)
        self.assertLessEqual(p["mae_pct"], 0.0)

    def test_hoechstwert_bleibt_bestehen(self):
        p = self.pos("long")
        mae.merke_extrem(p, 110.0)
        mae.merke_extrem(p, 105.0)          # Rueckschritt darf MFE nicht loeschen
        self.assertAlmostEqual(p["mfe_pct"], 10.0, places=6)

    def test_altbestand_ohne_felder_faellt_nicht_um(self):
        p = {"inst": "BTC", "seite": "long", "einstieg": 100.0}
        mae.merke_extrem(p, 102.0)
        self.assertAlmostEqual(p["mfe_pct"], 2.0, places=6)

    def test_haltetage_zaehlt_kalendertage(self):
        p = self.pos()
        self.assertEqual(mae.haltetage(p, heute=date(2026, 10, 4)), 3)

    def test_unbekanntes_eroeffnet_bleibt_leer_statt_geraten(self):
        p = self.pos()
        del p["eroeffnet_zeit"]
        self.assertEqual(mae.haltetage(p, heute=date(2026, 10, 4)), "")

    def test_kopfzeile_bekommt_die_spalten_ohne_dopplung(self):
        spalten = mae.kopfzeile_ergaenzen(["zeit", "aktion", "mae_pct"])
        self.assertIn("mfe_pct", spalten)
        self.assertIn("haltetage", spalten)
        self.assertEqual(spalten.count("mae_pct"), 1)
        self.assertEqual(spalten[0], "zeit")


if __name__ == "__main__":
    unittest.main(verbosity=2)