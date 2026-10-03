"""Tests fuer die gemerkten Einstellungen (Schrift, Dichte, Fenster, Filter).

Reine Funktionen plus eine Schreibprobe in einem Temp-Ordner - es wird NIE in
die echte `einstellungen.json` des Werkzeugs geschrieben.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import einstellungen  # noqa: E402


class BereinigenTest(unittest.TestCase):
    def test_leere_eingabe_gibt_die_standards(self):
        self.assertEqual(einstellungen.bereinigen(None), einstellungen.STANDARD)
        self.assertEqual(einstellungen.bereinigen("kaputt"), einstellungen.STANDARD)

    def test_schrift_wird_auf_den_bereich_begrenzt(self):
        self.assertEqual(einstellungen.bereinigen({"schrift": 99})["schrift"],
                         einstellungen.SCHRIFT_MAX)
        self.assertEqual(einstellungen.bereinigen({"schrift": 1})["schrift"],
                         einstellungen.SCHRIFT_MIN)
        self.assertEqual(einstellungen.bereinigen({"schrift": 12})["schrift"], 12)

    def test_ein_wahrheitswert_ist_keine_schriftgroesse(self):
        """`True` ist in Python eine Zahl - als Schriftgroesse waere das 1 pt."""
        self.assertEqual(einstellungen.bereinigen({"schrift": True})["schrift"],
                         einstellungen.STANDARD["schrift"])

    def test_unbekannte_dichte_und_fenstergroesse_fallen_zurueck(self):
        sauber = einstellungen.bereinigen({"dichte": "riesig", "fenster": "wand"})
        self.assertEqual(sauber["dichte"], "normal")
        self.assertEqual(sauber["fenster"], "mittel")

    def test_unbekannte_filterkennzeichen_fallen_einzeln_weg(self):
        sauber = einstellungen.bereinigen({"filter": ["fremd", "quatsch", "scharf"]})
        self.assertEqual(sauber["filter"], ["fremd", "scharf"])

    def test_filterreihenfolge_ist_die_der_tabelle(self):
        sauber = einstellungen.bereinigen({"filter": ["scharf", "fremd"]})
        self.assertEqual(sauber["filter"], ["fremd", "scharf"])

    def test_doppelte_filter_werden_zusammengefasst(self):
        sauber = einstellungen.bereinigen({"filter": ["fremd", "fremd"]})
        self.assertEqual(sauber["filter"], ["fremd"])

    def test_spaltenbreiten_werden_geprueft(self):
        sauber = einstellungen.bereinigen({"spalten": {"#0": 300, "a": "breit", "b": 5}})
        self.assertEqual(sauber["spalten"], {"#0": 300})


class DateiTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.pfad = Path(self.t.name) / "einstellungen.json"

    def tearDown(self):
        self.t.cleanup()

    def test_fehlende_datei_gibt_die_standards(self):
        self.assertEqual(einstellungen.laden(self.pfad), einstellungen.STANDARD)

    def test_kaputte_datei_gibt_die_standards(self):
        self.pfad.write_text("{kaputt", encoding="utf-8")
        self.assertEqual(einstellungen.laden(self.pfad), einstellungen.STANDARD)

    def test_schreiben_und_wieder_lesen(self):
        werte = dict(einstellungen.STANDARD)
        werte.update({"schrift": 14, "dichte": "kompakt", "fenster": "gross",
                      "filter": ["scharf"], "text": "kraken"})
        self.assertTrue(einstellungen.speichern(self.pfad, werte))
        zurueck = einstellungen.laden(self.pfad)
        self.assertEqual(zurueck["schrift"], 14)
        self.assertEqual(zurueck["dichte"], "kompakt")
        self.assertEqual(zurueck["filter"], ["scharf"])
        self.assertEqual(zurueck["text"], "kraken")

    def test_geschriebene_datei_ist_gueltiges_json_mit_lf(self):
        einstellungen.speichern(self.pfad, einstellungen.STANDARD)
        roh = self.pfad.read_bytes()
        json.loads(roh.decode("utf-8"))
        self.assertNotIn(b"\r\n", roh, "die Datei ist Laufzeitstand, kein Windows-Text")

    def test_keine_nebendatei_bleibt_liegen(self):
        einstellungen.speichern(self.pfad, einstellungen.STANDARD)
        reste = [p.name for p in self.pfad.parent.iterdir() if p.name != self.pfad.name]
        self.assertEqual(reste, [], f"Nebendatei liegen geblieben: {reste}")


class VorgabenTest(unittest.TestCase):
    def test_dichte_faktor(self):
        self.assertLess(einstellungen.dichte_faktor("kompakt"), 1.0)
        self.assertEqual(einstellungen.dichte_faktor("normal"), 1.0)
        self.assertGreater(einstellungen.dichte_faktor("gross"), 1.0)
        self.assertEqual(einstellungen.dichte_faktor("gibtsnicht"), 1.0)

    def test_fenstergroesse_bildschirm_bleibt_im_bild(self):
        b, h = einstellungen.fenster_masse("bildschirm", (1920, 1080))
        self.assertLess(b, 1920)
        self.assertLess(h, 1080)
        self.assertGreaterEqual(b, 900)

    def test_unbekanntes_preset_gibt_mittel(self):
        self.assertEqual(einstellungen.fenster_masse("wand", (1920, 1080)),
                         einstellungen.FENSTERGROESSEN["mittel"])


if __name__ == "__main__":
    unittest.main()