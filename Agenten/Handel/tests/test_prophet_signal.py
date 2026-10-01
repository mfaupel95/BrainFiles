"""Tests fuer prophet_signal-Spur."""
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parent.parent / "prophet_signal"
HIER = Path(__file__).resolve().parent

# sys.path.insert wird in Test-Klassenmethode gemacht


class PropertiesTest(unittest.TestCase):
    """Pruefungen auf den Ordner und die Struktur."""
    
    def test_ordner_existiert(self):
        """prophet_signal-Ordner muss existieren."""
        self.assertTrue(SPUR.is_dir(), f"{SPUR} ist kein Ordner")
    
    def test_handeln_py_existiert(self):
        """handeln.py muss im Ordner sein."""
        handeln = SPUR / "handeln.py"
        self.assertTrue(handeln.is_file(), f"{handeln} fehlt")
    
    def test_wachen_json_existiert(self):
        """wachen.json muss im Ordner sein."""
        wachen = SPUR / "wachen.json"
        self.assertTrue(wachen.is_file(), f"{wachen} fehlt")
    
    def test_readme_existiert(self):
        """README.md muss im Ordner sein."""
        readme = SPUR / "README.md"
        self.assertTrue(readme.is_file(), f"{readme} fehlt")


class RulesTest(unittest.TestCase):
    """Tests der Indikator-Funktionen."""
    
    @classmethod
    def setUpClass(cls):
        """Lade prophet_regeln."""
        sys.path.insert(0, str(SPUR.parent))
        global prophet_regeln
        import prophet_regeln as pr
        prophet_regeln = pr
    
    def test_ema_basisch(self):
        """EMA mit einfachen Daten."""
        daten = [1.0, 2.0, 3.0, 4.0, 5.0]
        ema = prophet_regeln.ema(daten, 2)
        self.assertEqual(len(ema), 5)
        # Erste 1 sind None
        self.assertIsNone(ema[0])
        # Ab Index 1 sollten Werte sein
        self.assertIsNotNone(ema[1])
        # Wert sollte zwischen Min und Max sein
        self.assertGreater(ema[1], 1.0)
        self.assertLess(ema[1], 5.0)
    
    def test_ema_konstant(self):
        """EMA bei konstanten Daten = konstanter Wert."""
        daten = [3.0] * 10
        ema = prophet_regeln.ema(daten, 3)
        # Ab Index 2 sollte die EMA 3.0 sein
        for i in range(2, len(ema)):
            self.assertAlmostEqual(ema[i], 3.0, places=5)
    
    def test_trend_richtung_aufwaerts(self):
        """Aufwaertstrend erkannt bei steigenden Kursen."""
        # Synthetische Kerzen: kontinuierlich steigende Schlusse
        kerzen = [[i, i, i+0.1, i-0.1, float(i), 100] for i in range(1, 100)]
        richtung = prophet_regeln.trend_richtung(kerzen, trend_n=10, min_kerzen=60)
        self.assertEqual(richtung, 1, "Aufwaertstrend sollte 1 sein")
    
    def test_trend_richtung_abwaerts(self):
        """Abwaertstrend erkannt bei fallenden Kursen."""
        # Synthetische Kerzen: kontinuierlich fallende Schlusse
        kerzen = [[i, 100-i, 100-i+0.1, 100-i-0.1, float(100-i), 100] 
                  for i in range(1, 100)]
        richtung = prophet_regeln.trend_richtung(kerzen, trend_n=10, min_kerzen=60)
        self.assertEqual(richtung, -1, "Abwaertstrend sollte -1 sein")
    
    def test_saisonalitaet_staerke_berechnet(self):
        """Saisonalitaets-Staerke ist zwischen 0 und 1."""
        kerzen = [[i, 100 + 5*((i % 7) - 3.5), 
                  100 + 5*((i % 7) - 3.5) + 1,
                  100 + 5*((i % 7) - 3.5) - 1,
                  float(100 + 5*((i % 7) - 3.5)), 100]
                  for i in range(1, 100)]
        staerke = prophet_regeln.saisonalitaet_staerke(kerzen, trend_n=10, min_kerzen=60)
        self.assertIsNotNone(staerke)
        self.assertGreaterEqual(staerke, 0.0)
        self.assertLessEqual(staerke, 1.0)


class VerificationTest(unittest.TestCase):
    """Gesamtpruefer: kann die Spur ueberhaupt starten?"""
    
    def test_importiert_prophet_regeln(self):
        """Spur-Regelwerk muss importierbar sein."""
        sys.path.insert(0, str(SPUR.parent))
        try:
            import prophet_regeln as pr  # noqa: F401
        except Exception as e:
            self.fail(f"prophet_regeln.py Fehler: {e}")


if __name__ == "__main__":
    unittest.main()
