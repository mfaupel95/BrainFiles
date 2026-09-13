"""Die Handelszentrale darf NICHTS schreiben - der Dauerlauf bleibt der
einzige Schreiber.

Prueft den Quelltext per AST, nicht per Stichwortsuche: ein Kommentar mit dem
Wort "schreiben" ist kein Schreibzugriff, ein `json.dump` dagegen schon.
Geprueft werden:

  * jedes `open(...)` - der Modus darf kein w/a/x/+ enthalten
  * `json.dump`, `csv.writer`, `os.remove`/`rename`/`replace`/`mkdir`
  * `subprocess` als Modul (kein CLI-Aufruf; die Feed-Kurse holt lesen.preise)

Dazu ein Laufzeittest: ein voller Refresh gegen die echten Dateien darf die
Spurdateien nicht anfassen - verglichen werden Groesse und mtime vor/nach.

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import ast
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as gui                                 # noqa: E402
import dauerlauf                                              # noqa: E402


def _baum():
    with open(gui.__file__, encoding="utf-8") as f:
        return ast.parse(f.read())


class SchreibzugriffTest(unittest.TestCase):

    def test_kein_open_im_schreibmodus(self):
        for knoten in ast.walk(_baum()):
            if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                    and knoten.func.id == "open"):
                modus = None
                if len(knoten.args) > 1 and isinstance(knoten.args[1], ast.Constant):
                    modus = knoten.args[1].value
                for kw in knoten.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        modus = kw.value.value
                if modus is None:
                    continue
                self.assertNotIn(str(modus), ("w", "a", "x", "w+", "a+", "r+",
                                              "wb", "ab", "xb"),
                                 "handelszentrale.py oeffnet mit Modus %r" % modus)

    def test_kein_schreibender_bibliotheksaufruf(self):
        verboten = {("json", "dump"), ("json", "dumps"), ("csv", "writer"),
                    ("os", "remove"), ("os", "rename"), ("os", "replace"),
                    ("os", "mkdir"), ("os", "makedirs"), ("os", "rmdir"),
                    ("shutil", "rmtree"), ("shutil", "copy")}
        for knoten in ast.walk(_baum()):
            if isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Attribute):
                teil = knoten.func.value
                if isinstance(teil, ast.Name):
                    self.assertNotIn((teil.id, knoten.func.attr), verboten,
                                     "handelszentrale.py ruft %s.%s" % (teil.id, knoten.func.attr))

    def test_kein_subprocess(self):
        # Die Papierspur spiegel wird genauso geprueft: kein CLI-Pfad aus
        # einem Leseprogramm heraus.
        for knoten in ast.walk(_baum()):
            if isinstance(knoten, (ast.Import, ast.ImportFrom)):
                namen = ([a.name for a in knoten.names]
                         if isinstance(knoten, ast.Import) else [knoten.module or ""])
                self.assertNotIn("subprocess", namen)


class LeselaufTest(unittest.TestCase):
    """Ein Refresh gegen die echten Dateien darf keine davon veraendern."""

    def _fingerabdruck(self):
        aus = {}
        for spur in gui.SPUREN:
            ordner = os.path.join(HANDEL, dauerlauf.SPUREN[spur]["ordner"])
            for name in ("zustand.json", "wachen.json", "handelsjournal.csv"):
                pfad = os.path.join(ordner, name)
                if os.path.exists(pfad):
                    st = os.stat(pfad)
                    aus[pfad] = (st.st_size, st.st_mtime_ns)
        return aus

    def test_prueflauf_laesst_alle_spurdateien_unberuehrt(self):
        vorher = self._fingerabdruck()
        gui.pruefe()                       # der ganze Lesepfad ohne Fenster
        self.assertEqual(vorher, self._fingerabdruck())

    def test_keine_neue_datei_im_handel_ordner(self):
        # Ein Schreibzugriff koennte auch eine NEUE Datei anlegen (Cache,
        # __pycache__ ausgenommen).
        vorher = {n for n in os.listdir(HANDEL)}
        gui.pruefe()
        neu = {n for n in os.listdir(HANDEL)} - vorher
        self.assertEqual(neu, set(), "neue Dateien: %s" % sorted(neu))


if __name__ == "__main__":
    unittest.main()
