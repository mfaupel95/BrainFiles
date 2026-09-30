"""Anzeige der Kraken-Waehrung: Tagesbericht und Handelszentrale.

Seit 30.09.2026 kann die Kraken-Spur in EUR, USDC und EURC handeln; jede
Position traegt ihre Waehrung. Zwei Leser zeigten sie fest als EUR an:

  - `lage.spur_kraken` haette eine USDC-Position im Bericht als EUR
    ausgewiesen (der Kurs kaeme richtig, das Vorzeichen der Bilanz nicht),
  - `handelszentrale._konto_im_thread` haette "0.00 ZEUR frei (unter 60)"
    gemeldet, waehrend die Spur in USDC haette handeln koennen.

Altbestand: Positionen von vor dem 30.09.2026 tragen kein Feld - damals war
EUR die einzige Waehrung der Spur, also ist EUR die richtige Antwort und
nicht "unbekannt".

Direkt ausfuehrbar (aus Agenten/Handel):  python -m unittest discover -s tests -t tests
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(HANDEL / "kraken"))

import handelszentrale as hz                                 # noqa: E402
import kraken                                                # noqa: E402
import lage                                                  # noqa: E402

assert lage.__file__.startswith(str(HANDEL)), lage.__file__
assert hz.__file__.startswith(str(HANDEL)), hz.__file__


def _z(positionen):
    return {"positionen": positionen, "letzte_stops": {}}


class BuchWaehrung(unittest.TestCase):

    def test_position_traegt_die_waehrung(self):
        self.assertEqual(lage._kraken_buch_waehrung(
            _z([{"paar": "XBTUSDC", "eur": 50.0, "waehrung": "USDC"}])), "USDC")
        self.assertEqual(lage._kraken_buch_waehrung(
            _z([{"paar": "XXBTZEUR", "eur": 50.0, "waehrung": "EURC"}])), "EURC")

    def test_altbestand_ohne_feld_ist_eur(self):
        # Vor dem 30.09.2026 gab es nur EUR - ein fehlendes Feld ist keine
        # unbekannte Waehrung.
        self.assertEqual(lage._kraken_buch_waehrung(
            _z([{"paar": "XXBTZEUR", "eur": 50.0}])), "EUR")

    def test_leeres_buch_ist_eur(self):
        self.assertEqual(lage._kraken_buch_waehrung(_z([])), "EUR")
        self.assertEqual(lage._kraken_buch_waehrung({}), "EUR")


class BerichtZeigtDieBuchwaehrung(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = lage.HIER
        lage.HIER = self.tmp.name
        ordner = Path(self.tmp.name) / "kraken"
        ordner.mkdir()
        (ordner / "wachen.json").write_text(json.dumps(
            {"handel_erlaubt": False}), encoding="utf-8")
        (ordner / "zustand.json").write_text(json.dumps(
            _z([{"paar": "XBTUSDC", "einstieg": 100.0, "eur": 50.0,
                 "waehrung": "USDC", "stop": 93.0, "eroeffnet": "2026-09-30"}])),
            encoding="utf-8")

    def tearDown(self):
        lage.HIER = self.alt
        self.tmp.cleanup()

    def test_spur_uebernimmt_die_waehrung_aus_dem_buch(self):
        spur = lage.spur_kraken()
        self.assertEqual(spur["waehrung"], "USDC")
        self.assertEqual(spur["positionen"][0]["name"], "XBTUSDC")

    def test_altbestand_meldet_eur(self):
        ordner = Path(self.tmp.name) / "kraken"
        (ordner / "zustand.json").write_text(json.dumps(
            _z([{"paar": "XXBTZEUR", "einstieg": 100.0, "eur": 50.0}])),
            encoding="utf-8")
        self.assertEqual(lage.spur_kraken()["waehrung"], "EUR")


class KontoFenster(unittest.TestCase):

    def _lauf(self, staende):
        with patch.object(kraken, "kontostaende", return_value=staende):
            hz._konto_im_thread()
        return hz._konto_cache["text"], hz._konto_cache["warnung"]

    def test_fenster_nennt_jede_waehrung(self):
        text, warnung = self._lauf({"ZEUR": 46.81, "USDC": 25.08, "EURC": 0.0})
        for name in ("ZEUR 46.81", "USDC 25.08", "EURC 0.00"):
            self.assertIn(name, text)
        # Keine Waehrung ueber 60 - hier ist die Warnung richtig.
        self.assertTrue(warnung)
        self.assertIn("keine Waehrung ueber 60", text)

    def test_eine_gedeckte_waehrung_genuegt(self):
        # Gegenprobe: vorher stand hier nur ZEUR und das Fenster warnte,
        # waehrend die Spur in USDC haette handeln koennen.
        text, warnung = self._lauf({"ZEUR": 46.81, "USDC": 500.0, "EURC": 0.0})
        self.assertFalse(warnung)
        self.assertNotIn("keine Waehrung ueber 60", text)

    def test_abruf_scheitert_bleibt_lesbar(self):
        with patch.object(kraken, "kontostaende",
                          side_effect=RuntimeError("kein Netz")):
            hz._konto_im_thread()
        self.assertEqual(hz._konto_cache["text"], "Kraken-Konto: nicht erreichbar")
        self.assertTrue(hz._konto_cache["warnung"])


if __name__ == "__main__":
    unittest.main(verbosity=2)