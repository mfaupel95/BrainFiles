"""Tests fuer die Berichts-Schlankung der Kopie-Familie.

Die Familie (spiegel, spiegel_knapp, spiegel_weit, kopier)
erscheint im HOLER als EIN Holer und im Tagesbericht als EIN Block mit je
einer schlanken Zeile pro Buch - die Einzelpositionen bleiben fuer
Schnappschuss und Summe in `positionen`, werden aber nicht aufgezogen.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import lage                                              # noqa: E402

FAMILIE = ("spur_spiegel", "spur_spiegel_knapp", "spur_spiegel_weit",
           "spur_kopier")


class FamilienHolerTest(unittest.TestCase):
    def test_liefert_pflichtfelder_und_familie(self):
        s = lage.spur_kopier_familie()
        for feld in ("name", "waehrung", "w", "positionen", "familie"):
            self.assertIn(feld, s)
        self.assertIsInstance(s["positionen"], list)
        self.assertIsInstance(s["familie"], list)

    def test_offene_summe_stimmt_mit_positionen(self):
        s = lage.spur_kopier_familie()
        summe = sum(g["offen"] for g in s["familie"])
        self.assertEqual(summe, len(s["positionen"]))

    def test_holer_ersetzt_die_fuenf_einzelnen(self):
        namen = {getattr(h, "__name__", "?") for h in lage.HOLER}
        self.assertIn("spur_kopier_familie", namen)
        for n in FAMILIE:
            self.assertNotIn(n, namen)

    def test_kein_ordner_kein_spiegel_schluessel(self):
        # Bewusst: kein "ordner", sonst kaeme der Schluessel aus dem
        # Ordnernamen und kollidierte mit "spiegel" (_schluessel_von).
        s = lage.spur_kopier_familie()
        self.assertNotIn("ordner", s)


class FamilienBlockTest(unittest.TestCase):
    def test_block_rendert_eine_zeile_je_buch(self):
        import tagesbericht                                # noqa: PLC0415
        # Durch den ECHTEN Pfad (zu_lage): der erste Entwurf schickte eine
        # handgebaute dict an _block und verdeckte, dass zu_lage "familie"
        # selbst rausschmeisst.
        roh = {
            "name": "Kopie-Familie (Spiegel/Copy)", "waehrung": "USD",
            "w": {},
            "positionen": [{"wert": 50, "vh": 1.0}],
            "familie": [
                {"name": "Spiegel (Papier, Copy)", "offen": 2,
                 "bilanz": "Bilanz (10 Ausstiege), nach Kosten +1.2 %"},
                {"name": "Spiegel-knapp (Papier, Copy)", "offen": 3,
                 "bilanz": "Bilanz (5 Ausstiege), nach Kosten -3.0 %"},
            ],
            "bilanz": "Kopie-Familie: 5 offene Position ueber 2 Buecher",
        }
        spur = lage.zu_lage(roh, None)
        self.assertEqual(spur["familie"], roh["familie"])
        text = tagesbericht._block(spur, {})
        self.assertIn("Kopie-Familie", text)
        self.assertIn("Spiegel (Papier, Copy)", text)
        self.assertIn("Spiegel-knapp", text)
        self.assertIn("2 offen", text)
        self.assertIn("5 offene Position", text)
        # Die Einzelpositionen werden NICHT als Zeilen aufgezogen.
        self.assertNotIn("keine offene Position", text)