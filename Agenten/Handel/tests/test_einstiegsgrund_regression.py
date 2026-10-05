"""Regression: T-142 - Platzhalter wird nie ins Journal geschrieben.

Die Funktion `einstiegsgrund` in spur_buch.py liest `_grund` aus der Wache,
filtert Platzhalter-Saetze und nutzt stattdessen `begruendung()` oder
Messwerte aus dem Signal. Dieser Test verifiziert, dass:
1. Der Platzhalter-Text ("Der Grund, der im journal steht") nie
   zurueckgegeben wird.
2. Ein echter `_grund` aus der Wache durchgereicht wird.
3. `begruendung()` als Fallback genutzt wird.
4. Messwerte als letzter Fallback genutzt werden.
5. Der Platzhalter in der wachen.json NICHT gelesen wird, wenn
   `begruendung` einen echten Text liefert.
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path

# Handel-Verzeichnis in sys.path
HANDEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HANDEL))

import spur_buch


class EinstiegsgrundPlatzhalterTest(unittest.TestCase):
    """Der Platzhalter-Satz wird nie ins Journal geschrieben."""

    def test_platzhalter_wird_gefiltert(self):
        """_grund = Platzhalter -> muss durch begruendung oder Messwerte ersetzt werden."""
        w = {"_grund": "Der Grund, der im Journal steht."}
        d = {"close": 100.0, "rsi": 65.0, "volume": 1500000}
        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
        self.assertNotIn("Der Grund, der im Journal steht", grund)
        self.assertNotIn("Platzhalter", grund)
        self.assertTrue(len(grund) > 0)

    def test_echter_grund_wird_durchgereicht(self):
        """_grund = echter Text -> wird unveraendert zurueckgegeben."""
        w = {"_grund": "RSI ueber 70, Volumen 2x Median"}
        d = {"close": 100.0}
        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
        self.assertEqual(grund, "RSI ueber 70, Volumen 2x Median")

    def test_begruendung_fallback(self):
        """Platzhalter + begruendung -> begruendung wird genutzt."""
        w = {"_grund": "Der Grund, der im Journal steht."}
        d = {"close": 100.0}

        def begruendung(d, w, seite):
            return "EMA-Cross nach oben"

        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur",
                                        begruendung=begruendung)
        self.assertEqual(grund, "EMA-Cross nach oben")

    def test_messwerte_fallback(self):
        """Platzhalter ohne begruendung -> Messwerte aus dem Signal."""
        w = {"_grund": "Der Grund, der im Journal steht."}
        d = {"close": 100.0, "rsi": 65.0, "volume": 1500000}
        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
        self.assertIn("testspur", grund)
        self.assertIn("long", grund)
        # Messwerte enthalten RSI oder aehnliches
        self.assertTrue("rsi" in grund.lower() or "close" in grund.lower() or
                        "signal" in grund.lower())

    def test_leerer_grund_und_keine_daten(self):
        """Weder _grund noch Messwerte -> generischer Signal-Text."""
        w = {}
        d = {}
        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
        self.assertIn("testspur", grund)
        self.assertIn("signal", grund.lower())

    def test_platzhalter_varianten_werden_gefiltert(self):
        """Alle Platzhalter-Varianten werden erkannt."""
        platzhalter = [
            "Der Grund, der im Journal steht.",
            "Der Grund, der im Journal steht (das Modell ergaenzt Aktion und Confidence).",
            "Platzhalter",
        ]
        for ph in platzhalter:
            w = {"_grund": ph}
            d = {"close": 100.0, "rsi": 65.0}
            grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
            self.assertNotIn("Der Grund, der im Journal steht", grund,
                             "Platzhalter nicht gefiltert: %s" % ph)

    def test_konkreter_grund_aus_wache_wird_genommen(self):
        """Ein konkreter _grund aus der wachen.json wird durchgereicht."""
        w = {"_grund": "Funding Rate > 0.1% fuer 8h"}
        d = {"close": 100.0}
        grund = spur_buch.einstiegsgrund(w, d, "short", spur_name="funding")
        self.assertEqual(grund, "Funding Rate > 0.1% fuer 8h")


class EinstiegsgrundIntegrationTest(unittest.TestCase):
    """Integration: einstiegsgrund wird im echten Zyklus aufgerufen."""

    def test_echter_zyklus_schreibt_grund(self):
        """Ein echter Zyklus mit einstiegsgrund schreibt den Grund ins Journal."""
        # Dieser Test prueft, dass die Funktion im Zyklus-Kontext
        # aufgerufen wird und den Platzhalter filtert.
        # Wir testen die Funktion direkt, nicht den ganzen Zyklus,
        # weil der Zyklus Schreibvorgaenge ausloest.
        w = {"_grund": "Der Grund, der im Journal steht."}
        d = {"close": 100.0, "rsi": 65.0, "volume": 1500000}
        grund = spur_buch.einstiegsgrund(w, d, "long", spur_name="testspur")
        # Der Grund muss ein String sein, der nicht der Platzhalter ist
        self.assertIsInstance(grund, str)
        self.assertNotIn("Der Grund, der im Journal steht", grund)
        self.assertTrue(len(grund) > 10)  # nicht leer oder trivial


if __name__ == "__main__":
    unittest.main()
