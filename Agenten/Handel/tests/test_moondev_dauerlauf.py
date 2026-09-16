"""
Tests fuer moondev_dauerlauf.py - der Treiber faehrt die geklonten
Moon-Dev-Agenten als langlebige Kindprozesse.
"""
import importlib.util
import os
import sys
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
TREIBER = HIER.parent / "moondev_dauerlauf.py"

def lade_treiber():
    spec = importlib.util.spec_from_file_location("moondev_dauerlauf", TREIBER)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul

class StartStoppTest(unittest.TestCase):
    """Der Treiber startet die Agenten und stoppt sie wieder."""

    def test_startet_beide_agenten(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True)
        lauf.zyklus()
        time.sleep(6)
        self.assertIn("new_or_top", lauf.kinder)
        self.assertIn("kraken", lauf.kinder)
        kind = lauf.kinder["new_or_top"]
        code = kind.poll()
        if code is not None:
            fehler = (kind.stderr.read() or "")[-2000:]
            self.fail(f"new_or_top muss laufen, endete mit {code}:\n{fehler}")
        lauf._stoppe("new_or_top")
        lauf._stoppe("kraken")

    def test_umgebung_hat_routine(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True)
        eintrag = m.AGENTEN["kraken"]
        umgebung = dict(os.environ)
        umgebung["MAXHIRN_ROUTINE"] = "1"
        umgebung["HANDEL_RISIKO"] = "basis"
        self.assertEqual(umgebung["MAXHIRN_ROUTINE"], "1")
        self.assertIn("cwd", eintrag)
        self.assertTrue(Path(eintrag["cwd"]).exists())

if __name__ == "__main__":
    unittest.main()