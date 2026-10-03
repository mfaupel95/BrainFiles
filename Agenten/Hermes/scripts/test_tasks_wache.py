"""Die Aufgaben-Wache an ihren EIGENEN Regeln, nicht an Tageswerten.

Geprueft wird, was gelten soll:
  1. --voll schweigt, solange sich die Liste nicht geaendert hat.
  2. --voll meldet danach BEIDES: was neu kam und was weg ist.
  3. --top meldet hoechstens einmal am Tag, auch wenn man ihn zweimal ruft.
  4. Fehlt die Datei oder der Abschnitt, meldet die Wache den Grund
     einmal - und dann schweigt sie, statt jeden Lauf zu schreien.
  5. Gegenprobe: mit entfernter Merkmischwelle schweigt sie NICHT.
"""
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "..", "Agenten", "Hermes", "scripts")

KLUMPEN = """# Aufgaben

## Offen

- [ ] **T-200 - Der neueste Punkt** mit Text
  Kontext
- [ ] **T-100 - Der aeltere Punkt**
- [ ] **T-050 - Der drittelte Punkt**

## Erledigt

- [x] **T-001 - alt**
"""


def kern():
    pfad = os.path.join(SCRIPTS, "tasks-wache.py")
    spec = importlib.util.spec_from_file_location("tasks_wache", pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class AufgabenWacheTest(unittest.TestCase):
    def setUp(self):
        self.ord = tempfile.mkdtemp()
        self.tasks = os.path.join(self.ord, "TASKS.md")
        self.cache = os.path.join(self.ord, "cache")
        os.makedirs(self.cache)
        self.m = kern()
        self.m.TASKS = self.tasks
        self.m.CACHE = self.cache
        self.m.MERK_VOLL = os.path.join(self.cache, "voll.json")
        self.m.MERK_TOP = os.path.join(self.cache, "top.json")
        self.schreibe(KLUMPEN)

    def tearDown(self):
        shutil.rmtree(self.ord, ignore_errors=True)

    def schreibe(self, text):
        with open(self.tasks, "w", encoding="utf-8") as fh:
            fh.write(text)

    def lauf(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            sys.argv = ["t"] + list(args)
            self.m.main()
        return buf.getvalue()

    # 1 -------------------------------------------------------------
    def test_voll_schweigt_bei_unveraenderter_liste(self):
        self.assertIn("T-200", self.lauf("--voll"))
        self.assertEqual(self.lauf("--voll"), "",
                         "zweiter Lauf ohne Aenderung muss schweigen")

    # 2 -------------------------------------------------------------
    def test_voll_meldet_neu_und_weg(self):
        self.lauf("--voll")
        self.schreibe(KLUMPEN.replace("**T-200 - Der neueste Punkt**",
                                      "**T-201 - Ersetzt**"))
        aus = self.lauf("--voll")
        self.assertIn("T-201", aus, "der neue Punkt muss genannt werden")
        self.assertIn("T-200", aus, "der weggefallene auch - sonst weiss "
                                    "niemand, dass er erledigt ist")

    # 3 -------------------------------------------------------------
    def test_top_einmal_am_tag(self):
        erste = self.lauf("--top")
        self.assertIn("T-200", erste)
        self.assertEqual(self.lauf("--top"), "")

    # 4 -------------------------------------------------------------
    def test_fehlende_datei_meldet_einmal(self):
        os.remove(self.tasks)
        erste = self.lauf("--voll")
        self.assertIn("fehlt", erste)
        self.assertEqual(self.lauf("--voll"), "")

    # 5 - die Gegenprobe zu 1
    def test_gegenprobe_ohne_merkdatei_meldet_wieder(self):
        self.lauf("--voll")
        os.remove(self.m.MERK_VOLL)
        self.assertNotEqual(self.lauf("--voll"), "",
                            "ohne Merkdatei ist alles neu - das muss melden")

    # Reihenfolge ist die Auswahlregel, nicht die Nummer
    def test_top_ist_die_dateireihenfolge(self):
        aus = self.lauf("--top")
        self.assertLess(aus.index("T-200"), aus.index("T-100"))
        self.assertLess(aus.index("T-100"), aus.index("T-050"))


if __name__ == "__main__":
    unittest.main()