"""Tests fuer hermes-doctor.py (Hermes-Doctor).

Laeuft aus dem scripts-Ordner:
    python -m unittest test_hermes_doctor
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

spec = importlib.util.spec_from_file_location("hermes_doctor", HIER / "hermes-doctor.py")
hd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hd)


class ClaudeGesperrtTest(unittest.TestCase):
    def test_erkennt_weekly_limit(self):
        self.assertTrue(hd.claude_gesperrt("You've hit your weekly limit"))

    def test_erkennt_out_of_credits(self):
        self.assertTrue(hd.claude_gesperrt('"overageStatus":"rejected","overageDisabledReason":"out_of_credits"'))

    def test_erkennt_rate_limit(self):
        self.assertTrue(hd.claude_gesperrt('"type":"rate_limit_event"'))

    def test_normale_antwort_nicht_gesperrt(self):
        self.assertFalse(hd.claude_gesperrt("Hier ist die Analyse der Befunde."))


class ClaudePfadTest(unittest.TestCase):
    def test_loest_pfad_auf(self):
        p = hd.claude_pfad()
        self.assertIsInstance(p, str)
        self.assertTrue(len(p) > 0)


class ParseClaudeJsonTest(unittest.TestCase):
    def test_extrahiert_result(self):
        text = json.dumps({"type": "result", "result": "ANALYSE", "num_turns": 2})
        self.assertEqual(hd.parse_claude_json(text), "ANALYSE")

    def test_kein_json_gibt_text_zurueck(self):
        self.assertEqual(hd.parse_claude_json("kein json"), "kein json")


class DiagnoseIntegrationTest(unittest.TestCase):
    def test_diagnose_schreibt_befund(self):
        """--diagnose muss eine befund-Datei unter logs/ erzeugen."""
        with tempfile.TemporaryDirectory() as tmp:
            # logs-Pfad umbiegen, damit der Test nicht ins echte logs/ schreibt
            orig_logs = hd.LOGS
            hd.LOGS = Path(tmp)
            try:
                # main() liest argparse aus sys.argv - direkt aufrufen mit Test-argv
                old_argv = sys.argv
                sys.argv = ["hermes-doctor.py", "--diagnose"]
                try:
                    hd.main()
                finally:
                    sys.argv = old_argv
                dateien = list(Path(tmp).glob("hermes-doctor-diagnose-*.json"))
                self.assertEqual(len(dateien), 1)
                befund = json.loads(dateien[0].read_text(encoding="utf-8"))
                self.assertEqual(befund["modus"], "diagnose")
                self.assertIn("roh", befund)
                self.assertIn("hermes_doctor", befund["roh"])
            finally:
                hd.LOGS = orig_logs


class BerichtTest(unittest.TestCase):
    def test_bericht_kompakt(self):
        roh = {
            "zeitpunkt": "2026-09-19 03:00:00",
            "hermes_doctor": "All checks passed\n⚠ eine Warnung",
            "git_status": "Zweig: main\nCommits hinter origin/main: 0",
            "log_fehler": "letzte 60 Zeilen gateway.log: keine CRITICAL/ERROR/Traceback",
        }
        b = hd.bericht(roh, "C:/pfad/befund.json")
        self.assertIn("Hermes-Doctor", b)
        self.assertIn("hermes doctor: OK", b)
        self.assertIn("Warnungen: 1", b)
        self.assertIn("gateway.log: keine Fehler", b)
        self.assertIn("C:/pfad/befund.json", b)

    def test_bericht_ok_ohne_warnung(self):
        roh = {
            "zeitpunkt": "t",
            "hermes_doctor": "All checks passed",
            "git_status": "Zweig: main",
            "log_fehler": "keine CRITICAL",
        }
        b = hd.bericht(roh, "x")
        self.assertNotIn("Warnungen", b)


class AufgabePromptTest(unittest.TestCase):
    def test_aufgabe_ueberschreibt_repair(self):
        roh = {"zeitpunkt": "t"}
        p = hd.claude_prompt(roh, "repair", aufgabe="Zaehle die TODO-Kommentare.")
        self.assertIn("AUFGABE:", p)
        self.assertIn("Zaehle die TODO-Kommentare.", p)
        # die Standard-Reparatur-Anweisung (BEFUNDE) darf NICHT erscheinen
        self.assertNotIn("BEFUNDE:", p)

    def test_ohne_aufgabe_bleibt_standard(self):
        roh = {"zeitpunkt": "t"}
        p = hd.claude_prompt(roh, "repair")
        self.assertIn("BEFUNDE:", p)
        self.assertNotIn("AUFGABE:", p)


if __name__ == "__main__":
    unittest.main()
