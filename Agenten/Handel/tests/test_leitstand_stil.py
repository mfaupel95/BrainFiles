"""Tests fuer leitstand_stil: Theme, benannte Schriften, keine festen Schriften/Farben."""

import ast
import sys
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import font as tkfont, ttk

HIER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HIER))

import leitstand_stil as stil  # noqa: E402


def _hell(farbe):
    r, g, b = (int(farbe[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class Anwenden(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_farben_der_zentrale_und_hellerer_mattton(self):
        st = stil.anwenden(self.root, 11)
        self.assertEqual(st.lookup("Treeview", "background"), stil.FARBEN["blatt"])
        self.assertEqual(st.lookup(".", "background"), stil.FARBEN["bg"])
        self.assertEqual(st.lookup("Matt.TLabel", "foreground"), "#bac2de")
        self.assertEqual(str(self.root.cget("bg")), stil.FARBEN["bg"])

    def test_schriftgroesse_und_zeilenhoehe(self):
        st = stil.anwenden(self.root, 12)
        self.assertEqual(tkfont.nametofont(stil.TEXT, self.root).cget("size"), 12)
        self.assertEqual(tkfont.nametofont(stil.TITEL, self.root).cget("size"), 14)
        zeile = tkfont.nametofont(stil.TABELLE, self.root).metrics("linespace")
        self.assertGreaterEqual(int(st.lookup("Treeview", "rowheight")), zeile * 1.4)

    def test_zweimal_anwenden_aendert_die_schrift_bestehender_widgets(self):
        stil.anwenden(self.root, 10)
        lbl = ttk.Label(self.root, text="x", font=stil.FETT)
        txt = tk.Text(self.root)
        feld = ttk.Entry(self.root)
        stil.anwenden(self.root, 15)
        self.assertEqual(str(lbl.cget("font")), stil.FETT)
        self.assertEqual(tkfont.nametofont(stil.FETT, self.root).cget("size"), 15)
        self.assertEqual(str(txt.cget("font")), stil.MONO)
        self.assertEqual(str(feld.cget("font")), stil.TEXT)
        self.assertEqual(str(txt.cget("background")), stil.FARBEN["blatt"])

    def test_tags_dunkel_statt_pastell(self):
        for name, werte in stil.TAGS.items():
            if "background" in werte:
                self.assertLess(_hell(werte["background"]), 0.3, name)
        baum = ttk.Treeview(self.root)
        stil.tags(baum)
        self.assertEqual(str(baum.tag_configure("wartet", "background")),
                         stil.TAGS["wartet"]["background"])


class KeineFestenWerte(unittest.TestCase):
    """Schriften und Farben stehen nur im Stil, sonst skaliert der Wechsel nicht mit."""

    # Fensterdateien - keine Werkzeuge. `glob("leitstand*.py")` fängt
    # seit dem 04.10.2026 auch die Messsonden mit
    # (`leitstand_messprobe.py`, `leitstand_palette_check.py`), und die
    # enthalten zwangslaeufig Hexwerte und Fonttupel, weil sie
    # gerade das pruefen. Ein Werkzeug baut kein Fenster; die Regel
    # gilt fuer die Fenster.
    # Ohne fuehrenden Unterstrich: die Dateien heissen
    # `leitstand_messprobe.py` und `leitstand_palette_check.py`, ein
    # Muster "_messprobe" traf also nie und die Liste blieb leer -
    # der Test lief gegen NICHTS und war gruen.
    # Achtung: ein Name im Klassenkoerper ist im genexpr einer
    # KLASSENATTRIBUT-Liste nicht sichtbar (NameError, gemessen am
    # 04.10.2026). Deshalb wird die Werkzeugliste beim Aufruf
    # gebildet und nicht beim Anlegen der Liste.
    DATEIEN = sorted(p for p in HIER.glob("leitstand*.py")
                      if p.name != "leitstand_stil.py"
                      and "messprobe" not in p.name
                      and "palette_check" not in p.name
                      and "check" not in p.name)

    def _baeume(self):
        for p in self.DATEIEN:
            yield p.name, ast.parse(p.read_text(encoding="utf-8"))

    def test_die_liste_ist_nicht_leer(self):
        """Gegenprobe: ein Muster, das nichts trifft, macht beide
        Tests gruen, ohne zu pruefen. Genau das ist beim Bauen
        passiert (`endswith("_messprobe")` traf nie)."""
        self.assertGreaterEqual(len(self.DATEIEN), 5)
        self.assertIn("leitstand_markt.py",
                      [p.name for p in self.DATEIEN])

    def test_kein_font_tupel_mit_zahl(self):
        treffer = []
        for name, baum in self._baeume():
            for k in ast.walk(baum):
                if (isinstance(k, ast.keyword) and k.arg == "font"
                        and isinstance(k.value, ast.Tuple)
                        and any(isinstance(e, ast.Constant) and isinstance(e.value, int)
                                for e in k.value.elts)):
                    treffer.append("%s:%d" % (name, k.value.lineno))
        self.assertEqual(treffer, [])

    def test_keine_hexfarben_ausserhalb_des_stils(self):
        treffer = []
        for name, baum in self._baeume():
            for k in ast.walk(baum):
                if (isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and len(k.value) == 7 and k.value.startswith("#")):
                    treffer.append("%s:%d %s" % (name, k.lineno, k.value))
        self.assertEqual(treffer, [])


if __name__ == "__main__":
    unittest.main()
