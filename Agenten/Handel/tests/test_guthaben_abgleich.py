"""Tests fuer den Guthabenabgleich.

Kein Test geht ans Netz: der Kontostand wird uebergeben.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import auswertung_alle                                   # noqa: E402
import guthaben_abgleich                                 # noqa: E402


class AbgleichTest(unittest.TestCase):
    def test_rest_ist_konto_minus_bilanz_minus_gebunden(self):
        a = guthaben_abgleich.abgleich("scanner", konto=1050.0, bilanz=30.0,
                                       gebunden=1000.0)
        self.assertAlmostEqual(a["rest"], 20.0)
        self.assertIsNone(a["fehler"])

    def test_ausgefallener_abruf_traegt_den_grund_statt_einer_zahl(self):
        def kaputt():
            raise OSError("Netz weg")
        a = guthaben_abgleich.abgleich("scanner", konto=kaputt, bilanz=0.0,
                                       gebunden=0.0)
        self.assertIsNone(a["rest"])
        self.assertIn("Netz weg", a["fehler"])

    def test_fehlende_kennzahlen_ergeben_unbekannte_bilanz_statt_null(self):
        with patch.object(auswertung_alle, "kennzahlen_fuer", return_value=None):
            a = guthaben_abgleich.abgleich("scanner", konto=1000.0,
                                           gebunden=0.0)
        self.assertNotEqual(a["bilanz"], 0.0)
        self.assertTrue(a["bilanz_unbekannt"])
        self.assertIsNone(a["rest"])
        t = guthaben_abgleich.text(abgleiche=[a])
        self.assertIn("unbekannt", t)
        self.assertNotIn("Bilanz +0.00", t)

    def test_leere_boersenantwort_ergibt_unbekanntes_konto_statt_null(self):
        a = guthaben_abgleich.abgleich("scanner", konto=lambda: None,
                                       bilanz=0.0, gebunden=0.0)
        self.assertIsNone(a["fehler"])
        self.assertNotEqual(a["konto"], 0.0)
        self.assertTrue(a["konto_unbekannt"])
        self.assertIsNone(a["rest"])
        t = guthaben_abgleich.text(abgleiche=[a])
        self.assertIn("unbekannt", t)
        self.assertNotIn("Konto 0.00", t)

    def test_gebunden_bindet_das_eigene_hier_ohne_fremden_mantel(self):
        """Befund 3 der Schlusspruefung: _gebunden() rief lage.erhebe() bisher
        ohne eigenen HIER-Mantel auf und funktionierte nur zufaellig, weil es
        stets innerhalb von wochenbericht.baue() lief. Dieser Test ruft
        _gebunden() DIREKT, ohne einen fremden Mantel aktiv zu haben - waehrend
        lage.HIER auf einen unbeteiligten Ordner zeigt - und belegt, dass der
        Aufruf trotzdem im eigenen guthaben_abgleich.HIER erhebt und lage.HIER
        danach unveraendert laesst."""
        tmp = tempfile.mkdtemp(prefix="guthaben-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        # "fremd" hat KEIN merkmal.json - steht fuer lage.HIER ausserhalb
        # jedes Mantels (weder wochenbericht.baue() noch guthaben_abgleich
        # haben gerade gebunden).
        fremd = tempfile.mkdtemp(prefix="fremd-")
        self.addCleanup(shutil.rmtree, fremd, ignore_errors=True)
        with io.open(os.path.join(tmp, "merkmal.json"), "w",
                    encoding="utf-8") as f:
            json.dump({"spur": "scanner"}, f)

        def fake_holer():
            pfad = os.path.join(guthaben_abgleich.lage.HIER, "merkmal.json")
            with io.open(pfad, encoding="utf-8") as f:
                spur = json.load(f)["spur"]
            return {"name": spur, "waehrung": "USD",
                    "positionen": [{"wert": 42.0}], "w": {},
                    "ordner": os.path.join(guthaben_abgleich.lage.HIER, spur)}

        guthaben_abgleich.lage.HIER = fremd  # kein aktiver fremder Mantel
        try:
            with patch.object(guthaben_abgleich, "HIER", tmp), \
                    patch.object(guthaben_abgleich.lage, "HOLER",
                                (fake_holer,)):
                gebunden = guthaben_abgleich._gebunden("scanner")
            self.assertEqual(gebunden, 42.0)
            self.assertEqual(guthaben_abgleich.lage.HIER, fremd)
        finally:
            guthaben_abgleich.lage.HIER = HIER

    def test_papierspur_ist_nicht_dabei(self):
        self.assertNotIn("swap", guthaben_abgleich.LIVE)

    def test_text_nennt_papierbuch_fuer_die_uebrigen(self):
        t = guthaben_abgleich.text(abgleiche=[
            {"spur": "scanner", "konto": 1050.0, "bilanz": 30.0,
             "gebunden": 1000.0, "rest": 20.0, "waehrung": "USD",
             "fehler": None}])
        self.assertIn("scanner", t)
        self.assertIn("Papierbuch", t)


if __name__ == "__main__":
    unittest.main()
