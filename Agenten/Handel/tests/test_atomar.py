"""Tests fuer atomar.py: Zustand atomar schreiben, laut lesen."""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import atomar  # noqa: E402


class AtomarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "zustand.json")
        self.addCleanup(self.tmp.cleanup)

    def _dateien(self):
        return sorted(os.listdir(self.tmp.name))

    def test_schreiben_und_lesen(self):
        atomar.schreibe_json(self.pfad, {"positionen": [1], "modus": "papier"})
        self.assertEqual(atomar.lade_json(self.pfad, dict),
                         {"positionen": [1], "modus": "papier"})

    def test_format_wie_bisher(self):
        # indent 2, Umlaute im Klartext, Zeilenende am Schluss.
        atomar.schreibe_json(self.pfad, {"a": "ä"}, newline="\n")
        with open(self.pfad, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), '{\n  "a": "ä"\n}\n')

    def test_keine_nebendatei_bleibt(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        atomar.schreibe_json(self.pfad, {"n": 2})
        self.assertEqual(self._dateien(), ["zustand.json", "zustand.json.bak"])

    def test_bak_ist_der_vorstand(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        atomar.schreibe_json(self.pfad, {"n": 2})
        with open(self.pfad + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"n": 1})

    def test_fehlende_datei_gibt_vorgabe(self):
        self.assertEqual(atomar.lade_json(self.pfad, lambda: {"leer": True}),
                         {"leer": True})

    def test_vorgabe_ist_je_aufruf_frisch(self):
        a = atomar.lade_json(self.pfad, lambda: {"positionen": []})
        a["positionen"].append("x")
        self.assertEqual(atomar.lade_json(self.pfad, lambda: {"positionen": []}),
                         {"positionen": []})

    def test_defekte_datei_ohne_bak_ist_laut(self):
        with open(self.pfad, "w", encoding="utf-8") as f:
            f.write('{"positionen": [')          # abgeschnitten
        with self.assertRaises(atomar.ZustandDefekt):
            atomar.lade_json(self.pfad, dict)

    def test_leere_datei_ist_defekt_nicht_leer(self):
        open(self.pfad, "w").close()
        with self.assertRaises(atomar.ZustandDefekt):
            atomar.lade_json(self.pfad, dict)

    def test_defekte_datei_faellt_auf_bak_zurueck(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        atomar.schreibe_json(self.pfad, {"n": 2})
        with open(self.pfad, "w", encoding="utf-8") as f:
            f.write("{")
        with mock.patch("sys.stderr"):
            self.assertEqual(atomar.lade_json(self.pfad, dict), {"n": 1})

    def test_defekte_datei_verdraengt_gute_bak_nicht(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        atomar.schreibe_json(self.pfad, {"n": 2})       # bak = n1
        with open(self.pfad, "w", encoding="utf-8") as f:
            f.write("{")
        atomar.schreibe_json(self.pfad, {"n": 3})       # Vorstand defekt
        with open(self.pfad + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"n": 1})

    def test_gesperrte_datei_ist_kein_leerer_bestand(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        with mock.patch("builtins.open", side_effect=PermissionError), \
                mock.patch("atomar.time.sleep"):
            with self.assertRaises(PermissionError):
                atomar.lade_json(self.pfad, dict)

    def test_replace_wird_bei_sperre_wiederholt(self):
        echt = os.replace
        aufrufe = []

        def spinnt(a, b):
            aufrufe.append(1)
            if len(aufrufe) < 3:
                raise PermissionError("Leser haelt die Datei")
            return echt(a, b)

        with mock.patch("atomar.os.replace", side_effect=spinnt), \
                mock.patch("atomar.time.sleep"):
            atomar.schreibe_json(self.pfad, {"n": 1})
        self.assertGreaterEqual(len(aufrufe), 3)
        self.assertEqual(atomar.lade_json(self.pfad, dict), {"n": 1})

    def test_abbruch_beim_serialisieren_laesst_altstand_ganz(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        with self.assertRaises(TypeError):
            atomar.schreibe_json(self.pfad, {"n": object()})
        self.assertEqual(atomar.lade_json(self.pfad, dict), {"n": 1})
        self.assertFalse([d for d in self._dateien() if ".tmp-" in d])

    def test_abbruch_beim_ersetzen_raeumt_nebendatei_auf(self):
        atomar.schreibe_json(self.pfad, {"n": 1})
        with mock.patch("atomar.os.replace", side_effect=OSError("voll")), \
                mock.patch("atomar.time.sleep"):
            with self.assertRaises(OSError):
                atomar.schreibe_json(self.pfad, {"n": 2})
        self.assertEqual(atomar.lade_json(self.pfad, dict), {"n": 1})
        self.assertFalse([d for d in self._dateien() if ".tmp-" in d])


if __name__ == "__main__":
    unittest.main()
