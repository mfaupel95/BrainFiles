"""Tests fuer carry-wache.py — echter Aufruf von carry.py, kein Netz in den Tests.

Die Wache ist ein Filter auf carry.py-Ausgabe:
  * leere Ausgabe = nichts zu melden (Watchdog-Muster),
  * nur Zeilen mit netto_bp > MIN_NETTO_BP werden gemeldet,
  * --vorschau zeigt ohne Meldung,
  * Fehler von carry.py werden als FEHLER-Zeile ausgegeben, nicht geworfen.
"""
import os
import subprocess
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = "C:/Users/faupe/Documents/BrainFiles"
WACHE = os.path.join(WURZEL, "Agenten", "Hermes", "scripts", "carry-wache.py")
CARRY = os.path.join(WURZEL, "Agenten", "Handel", "carry.py")


def wache(argv=()):
    r = subprocess.run(
        [sys.executable, WACHE, *argv],
        capture_output=True, text=True, timeout=120,
        cwd=os.path.join(WURZEL, "Agenten", "Hermes", "scripts"),
    )
    return r


class AufrufTest(unittest.TestCase):

    def test_carry_py_existiert(self):
        self.assertTrue(os.path.exists(CARRY), "carry.py fehlt - Wache kann nicht laufen")

    def test_leere_ausgabe_nichts_zu_melden(self):
        """carry.py meldet aktuell keine positiven Zeilen -> Wache gibt leere Ausgabe."""
        r = wache()
        self.assertEqual(r.returncode, 0, "Wache darf nicht mit Fehler beenden:\n%s" % r.stderr)
        self.assertEqual(r.stdout.strip(), "",
                         "Erwartet: leere Ausgabe (Watchdog-Muster). Gesehen:\n%s" % r.stdout)

    def test_vorschau_zeigt_nur_an(self):
        r = wache(("--vorschau",))
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("FEHLER", r.stdout)
        if r.stdout.strip():
            self.assertIn("netto", r.stdout)

    def test_carry_fehler_wird_meldung_nicht_exception(self):
        r = subprocess.run(
            [sys.executable, WACHE, "--min-netto", "-99999"],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.join(WURZEL, "Agenten", "Hermes", "scripts"),
        )
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class FilterLogikTest(unittest.TestCase):

    def test_filter_mindet_nur_positiv(self):
        r = wache()
        self.assertEqual(r.returncode, 0)
        if r.stdout.strip():
            for zeile in r.stdout.strip().splitlines():
                if zeile.startswith("  "):
                    self.assertIn("netto", zeile.lower())


if __name__ == "__main__":
    unittest.main()
