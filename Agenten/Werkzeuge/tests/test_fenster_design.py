"""Tests fuer das gemeinsame Fenster-Design (ohne tkinter, ohne Fenster)."""

import importlib.util
import re
import unittest
from pathlib import Path

PFAD = Path(__file__).resolve().parent.parent / "fenster_design.py"
_spec = importlib.util.spec_from_file_location("fenster_design", PFAD)
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)

HEX = re.compile(r"^#[0-9a-f]{6}$")


class FakeStyle:
    """Merkt sich configure/map, wie ttk.Style es tut."""

    def __init__(self):
        self.conf, self.karte, self.theme = {}, {}, None

    def theme_use(self, name):
        self.theme = name

    def configure(self, name, **kw):
        self.conf.setdefault(name, {}).update(kw)

    def map(self, name, **kw):
        self.karte.setdefault(name, {}).update(kw)


class TokensTest(unittest.TestCase):
    def test_alle_farben_sind_hex(self):
        for name, wert in d.FARBEN.items():
            self.assertRegex(wert, HEX, name)

    def test_bisherige_namen_bleiben(self):
        # handelszentrale.py und fenster.py greifen unter diesen Namen zu.
        for name in ("bg", "blatt", "gitter", "text", "matt", "akzent", "blau",
                     "gruen", "rot", "gelb", "zellgruen", "zellrot", "auswahl"):
            self.assertIn(name, d.FARBEN)

    def test_flaechen_werden_nach_oben_heller(self):
        def hell(n):
            return sum(int(d.FARBEN[n][i:i + 2], 16) for i in (1, 3, 5))
        self.assertLess(hell("blatt"), hell("bg"))
        self.assertLess(hell("bg"), hell("gitter"))
        self.assertLess(hell("gitter"), hell("auswahl"))

    def test_abstaende_im_vierer_raster(self):
        for name, wert in d.ABSTAND.items():
            if name != "xs":
                self.assertEqual(wert % 4, 0, name)


class SchriftTest(unittest.TestCase):
    def test_basis_und_relativ(self):
        self.assertEqual(d.schrift(11), ("Consolas", 11))
        self.assertEqual(d.schrift(11, d.TINY)[1], 11 + d.TINY)
        self.assertEqual(d.schrift(11, 0, True)[2], "bold")

    def test_auswahl_enthaelt_vorgabe(self):
        self.assertIn(str(d.SCHRIFT_GROESSE), d.SCHRIFT_AUSWAHL)

    def test_zeilenhoehe(self):
        self.assertEqual(d.zeilenhoehe(8), 18)       # Untergrenze
        self.assertEqual(d.zeilenhoehe(11), 22)
        self.assertEqual(d.zeilenhoehe(16), 32)


class VorzeichenFarbeTest(unittest.TestCase):
    def test_zuordnung(self):
        self.assertEqual(d.vorzeichen_farbe(1.5), "gruen")
        self.assertEqual(d.vorzeichen_farbe("-0.2"), "rot")
        self.assertEqual(d.vorzeichen_farbe(0), "matt")
        self.assertEqual(d.vorzeichen_farbe(None), "matt")
        self.assertEqual(d.vorzeichen_farbe("", "text"), "text")


class StilTest(unittest.TestCase):
    def test_setzt_alle_stile_aus_tokens(self):
        st = FakeStyle()
        d.stil_anwenden(st, 12)
        self.assertEqual(st.theme, "clam")
        self.assertEqual(st.conf["."]["font"], ("Consolas", 12))
        self.assertEqual(st.conf["Treeview"]["rowheight"], 24)
        self.assertEqual(st.conf["Treeview"]["background"], d.FARBEN["blatt"])
        self.assertEqual(st.conf["Treeview.Heading"]["foreground"],
                         d.FARBEN["akzent"])
        self.assertEqual(st.karte["Treeview"]["background"],
                         [("selected", d.FARBEN["auswahl"])])
        for name in ("TLabel", "TButton", "TEntry", "TCombobox", "TNotebook",
                     "TNotebook.Tab", "Vertical.TScrollbar"):
            self.assertIn(name, st.conf)

    def test_schriftwechsel_aendert_zeilenhoehe(self):
        st = FakeStyle()
        d.stil_anwenden(st, 9)
        d.stil_anwenden(st, 15)
        self.assertEqual(st.conf["Treeview"]["rowheight"], 30)

    def test_fehlendes_theme_ist_unschaedlich(self):
        class OhneTheme(FakeStyle):
            def theme_use(self, name):
                raise RuntimeError("kein clam")
        d.stil_anwenden(OhneTheme())

    def test_kein_tkinter_import(self):
        self.assertNotIn("import tkinter", PFAD.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
