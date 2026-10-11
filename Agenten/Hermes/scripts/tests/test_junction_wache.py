"""Tests fuer junction-wache.py - die Verweis-Pruefung (T-390).

Aufbau wie test_konfig_doktor_wache.py: unittest, echte Junctions in %TEMP%,
die echte BrainFiles-Wurzel bleibt unberuehrt.

Warum diese Wache (11.10.2026): die konfig-doktor-wache prueft dieselben
Verweise, aber nur alle 4 h - ein Verlust zwischen zwei Laeufen faellt durch
ihr Fenster (gemessen 11.10.: Verlust 02:00, Reparatur 02:20, naechster
konfig-doktor-Lauf 05:18). Diese Wache laeuft alle 10 min und prueft
zusaechlich, dass das Ziel nicht ein (fast) leerer Schatten ist.
"""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
WACHE = os.path.join(os.path.dirname(HIER), "junction-wache.py")


def lade_wache():
    spec = importlib.util.spec_from_file_location("junction_wache", WACHE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def junction(link: Path, target: Path) -> bool:
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode == 0 and link.exists()


class VerweisTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = lade_wache()

    def setUp(self):
        self.basis = Path(tempfile.mkdtemp(prefix="junction-wache-test-"))
        self.echt = self.basis / "EchtesZiel"
        self.echt.mkdir()
        for i in range(5):
            (self.echt / ("eintrag%d" % i)).write_text("x", encoding="utf-8")
        self.falsch = self.basis / "FalschesZiel"
        self.falsch.mkdir()
        self.addCleanup(shutil.rmtree, self.basis, True)

    def test_gesunde_junction_schweigt(self):
        j = self.basis / "Gesund"
        self.assertTrue(junction(j, self.echt))
        self.assertEqual(self.m.verweis_lage(self.basis, "Gesund", str(self.echt)), "")

    def test_echter_ordner_statt_verweis_wird_gemeldet(self):
        d = self.basis / "Schatten"
        d.mkdir()
        (d / "a").write_text("x", encoding="utf-8")
        text = self.m.verweis_lage(self.basis, "Schatten", str(self.echt))
        self.assertTrue(text)
        self.assertIn("KEIN Verweis", text)
        self.assertIn("1 Eintraege", text)

    def test_junction_auf_falsches_ziel_wird_gemeldet(self):
        j = self.basis / "Falsch"
        self.assertTrue(junction(j, self.falsch))
        text = self.m.verweis_lage(self.basis, "Falsch", str(self.echt))
        self.assertTrue(text)
        self.assertIn("zeigt auf", text)

    def test_junction_auf_leeres_ziel_wird_gemeldet(self):
        leer = self.basis / "Leer"
        leer.mkdir()
        j = self.basis / "LeerZiel"
        self.assertTrue(junction(j, leer))
        text = self.m.verweis_lage(self.basis, "LeerZiel", str(leer))
        self.assertTrue(text, "leeres Ziel muss als Schatten gemeldet werden")
        self.assertIn("leeres Ziel", text)

    def test_junction_wird_erkannt_trotz_islink_false(self):
        j = self.basis / "Junc"
        self.assertTrue(junction(j, self.echt))
        self.assertFalse(os.path.islink(str(j)),
                         "Annahme falsch: islink liefert hier doch True")
        self.assertTrue(self.m._ist_verweis(j))

    def test_fehlt_ganz_wird_gemeldet(self):
        text = self.m.verweis_lage(self.basis, "GibtEsNicht", str(self.echt))
        self.assertTrue(text)
        self.assertIn("fehlt ganz", text)

    def test_normalisiert_schraegstriche_und_praefix(self):
        n = self.m._normalisiert
        self.assertEqual(n("\\\\?\\O:\\Werkstatt"), n("o:/werkstatt/"))
        self.assertEqual(n("C:\\x\\"), n("c:\\x"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
