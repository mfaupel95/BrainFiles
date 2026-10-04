"""sperrgruende: Spurenliste aus dauerlauf.py und Auswertung der Vorschau-Ausgabe."""

import os
import subprocess
import sys
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import sperrgruende as sg  # noqa: E402


def _ergebnis(stdout):
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


class SpurenlisteTest(unittest.TestCase):
    def test_liest_die_spuren_aus_dauerlauf(self):
        namen = sg.spurenliste()
        self.assertGreater(len(namen), 5)
        self.assertEqual(len(namen), len(set(namen)))
        self.assertIn("scanner", namen)
        self.assertIn("kraken", namen)

    def test_namen_sind_schluessel_ohne_sonderzeichen(self):
        for n in sg.spurenliste():
            self.assertRegex(n, r"^[A-Za-z0-9_]+$")


class SperrgrundTest(unittest.TestCase):
    def test_spur_ohne_handeln(self):
        self.assertEqual(sg.sperrgrund("gibt_es_nicht", 5),
                         ("gibt_es_nicht", None, "kein handeln.py"))

    def test_sperrzeile_wird_gefunden(self):
        aus = "start\n  gesperrt durch: Freigabefenster; Kill-Switch\nende\n"
        with mock.patch.object(sg.subprocess, "run",
                               return_value=_ergebnis(aus)):
            name, grund, fehler = sg.sperrgrund("scanner", 5)
        self.assertEqual((name, fehler), ("scanner", None))
        self.assertEqual(grund, "Freigabefenster; Kill-Switch")

    def test_keine_sperrzeile(self):
        with mock.patch.object(sg.subprocess, "run",
                               return_value=_ergebnis("alles frei\n")):
            self.assertEqual(sg.sperrgrund("scanner", 5),
                             ("scanner", None, "keine Sperrzeile"))

    def test_zeitueberschreitung(self):
        with mock.patch.object(sg.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("x", 5)):
            self.assertEqual(sg.sperrgrund("scanner", 5),
                             ("scanner", None, "Zeitueberschreitung (5 s)"))

    def test_umgebung_ohne_pythonhome_und_mit_routinemarke(self):
        with mock.patch.dict(os.environ, {"PYTHONHOME": "x", "PYTHONPATH": "y"}), \
                mock.patch.object(sg.subprocess, "run",
                                  return_value=_ergebnis("")) as run:
            sg.sperrgrund("scanner", 5)
        umg = run.call_args.kwargs["env"]
        self.assertNotIn("PYTHONHOME", umg)
        self.assertNotIn("PYTHONPATH", umg)
        self.assertEqual(umg["MAXHIRN_ROUTINE"], "1")
        self.assertIn("--vorschau", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
