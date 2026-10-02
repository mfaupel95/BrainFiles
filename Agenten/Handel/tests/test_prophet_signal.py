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

class VerdrahtungTest(unittest.TestCase):
    """Die LISTEN, die eine Spur nennen muessen - nicht der Code, der sie liest.

    Eine frische Spur laeuft im Dauerlauf, taucht aber im Bericht, in der
    Auswertung und in der Ratschenpruefung nicht auf, wenn eine dieser Listen
    sie vergessen hat. Genau das war der Rest der abgebrochenen Crypto-Sitzung
    (02.10.2026): `dauerlauf.SPUREN` kannte die Spur, der Rest nicht.

    Geprueft wird die REGEL (die Spur steht in der Liste), nicht eine Zahl -
    eine Zahl geht bei der naechsten Spur kaputt und sagt nichts aus.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SPUR.parent))
        sys.path.insert(0, str(HIER))

    def test_in_dauerlauf_spuren(self):
        import dauerlauf
        self.assertIn("prophet_signal", dauerlauf.SPUREN,
                      "prophet_signal fehlt in dauerlauf.SPUREN")

    def test_lage_holer_liefert_die_pflichtfelder(self):
        import lage
        self.assertIn("prophet_signal", [f.__name__.replace("spur_", "")
                                         for f in lage.HOLER],
                      "kein Holer fuer prophet_signal in lage.HOLER")
        bericht = lage.spur_prophet_signal()
        # Die Form, die `lage.HOLER` liefert (nicht geraten - siehe
        # `FormTest.test_jeder_holer_liefert_die_pflichtfelder`): Wachen, Name,
        # Zustand, Positionen, Journal und das Papier-Kennzeichen.
        for feld in ("name", "w", "z", "positionen", "journal", "papierfest"):
            self.assertIn(feld, bericht)
        self.assertEqual(bericht["papierfest"], True,
                         "prophet_signal hat keinen Live-Zweig - muss papierfest sein")
        self.assertEqual(bericht["name"], "Prophet-Signal (EMA30+Saisonalitaet)")

    def test_befehle_familie_und_indikatorenliste(self):
        import befehle
        self.assertIn("prophet_signal", befehle.FAMILIE,
                      "keine Strategie-Familie fuer prophet_signal")
        self.assertIn("prophet_signal", befehle.INDIKATOREN,
                      "prophet_signal fehlt in befehle.INDIKATOREN")

    def test_auswertung_hat_einen_rechenweg(self):
        import auswertung_alle as aa
        self.assertIn("prophet_signal", aa.INDIKATOR_SPUREN,
                      "prophet_signal fehlt in auswertung_alle.INDIKATOR_SPUREN")

    def test_ratschenbetrag_ist_buchrisiko(self):
        """Der Betrag muss 1.0x Buchrisiko sein (5.0 USD x 2 Plaetze = 10.0)."""
        import pruefe_ratschen as pr
        eintraege = [e for e in pr.SPUREN if e[0] == "prophet_signal"]
        self.assertEqual(len(eintraege), 1,
                         "prophet_signal nicht genau einmal in der Ratschenliste")
        spur, ordner, provider, modul = eintraege[0]
        self.assertEqual((ordner, provider, modul),
                         ("prophet_signal", "scanner", "wachen_pruefung"))
        import json
        w = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
        buchrisiko = (float(w["risiko_je_position_usd"])
                      * int(w["max_offene_positionen"]))
        self.assertAlmostEqual(float(w["drawdown_halbierung_usd"]), buchrisiko,
                               places=2,
                               msg="drawdown_halbierung_usd != Buchrisiko")

    def test_wachen_stellt_papierfest(self):
        import json
        w = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
        self.assertFalse(w["handel_erlaubt"],
                         "Papierspur darf handel_erlaubt nicht gesetzt haben")
        self.assertEqual(w["journal_zweitziel"],
                         r"Q:\Handel_Journal\prophet_signal")



if __name__ == "__main__":
    unittest.main()
