"""Nautilus-Reiter im Leitstand: Trennung Fenster/Inhalt, Reiter-Interface.

Geprueft wird die EIGENTLICHT zu sichernde Regel: `NautilusFrame` ist ein
Frame ohne Fensterpflege (kein title/geometry/minsize/protocol/destroy), und
`NautilusFenster` macht als tk.Tk beides. Wer das verwechselt, baut beim
Einbetten ein Fenster im Fenster - der Fehler faellt erst zur Laufzeit auf.

Auch geprueft: ein Reiter, dessen nautilus_trader fehlt, baut trotzdem - mit
Begruendung statt Absturz. Und: Leitstand.py importiert Nautilus nicht direkt,
sonst waere ein fehlendes Rad ein toter Leitstand.

Ohne Nautilus im venv werden die Teiltests uebersprungen; der Fall "fehlt"
wird mit einer Attrappe geprueft, der braucht kein echtes Rad.

Direkt ausfuehrbar:  python tests/test_leitstand_nautilus.py
"""

import sys
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand as lst                                        # noqa: E402
import leitstand_nautilus as ln                                 # noqa: E402
import lesepruefung                                             # noqa: E402

GUI = Path(ln.__file__).resolve().parent / "nautilus" / "nautilus_gui.py"


class Trennung(unittest.TestCase):
    """Der Quelltext, nicht die Laufzeit: der Test laeuft ohne venv-Rad."""

    def test_der_frame_hat_keine_fensterpflege(self):
        if not GUI.exists():
            self.skipTest("nautilus/ nicht da (eigenes Repo): %s" % GUI)
        quelle = GUI.read_text(encoding="utf-8")
        try:
            import ast
            baum = ast.parse(quelle)
        except SyntaxError as e:                     # pragma: no cover
            self.fail("nautilus_gui.py ist kapott: %s" % e)
        frame = [n for n in baum.body if isinstance(n, ast.ClassDef)
                 and n.name == "NautilusFrame"][0]
        verboten = ("self.title", "self.geometry", "self.minsize",
                    "self.protocol")
        for methode in frame.body:
            if not isinstance(methode, ast.FunctionDef):
                continue
            quelle_m = ast.unparse(methode)
            for verboten_wort in verboten:
                self.assertNotIn(verboten_wort, quelle_m,
                                 "NautilusFrame.%s ruft %s - Fensterpflege "
                                 "gehoert dem Eltern-Widget"
                                 % (methode.name, verboten_wort))

    def test_es_gibt_ein_fenster_mit_diesen_aufgaben(self):
        if not GUI.exists():
            self.skipTest("nautilus/ nicht da (eigenes Repo)")
        quelle = GUI.read_text(encoding="utf-8")
        for pflicht in ("class NautilusFenster(tk.Tk)", "self.geometry(",
                        "self.minsize(", "WM_DELETE_WINDOW"):
            self.assertIn(pflicht, quelle, pflicht)

    def test_der_rahmen_importiert_nautilus_nicht(self):
        # Wer nautilus_trader direkt in leitstand.py laedt, macht den ganzen
        # Leitstand zur Beute eines fehlenden Rades.
        self.assertNotIn("nautilus_gui", lst.__file__ and
                         Path(lst.__file__).read_text(encoding="utf-8"))


class ReiterOhneRad(unittest.TestCase):
    """Der Reiter muss den Leitstand nie mitnehmen."""

    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        self.tmp = None

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_fehlendes_rad_zeigt_text_statt_absturz(self):
        with patch.object(ln, "nautilus_gui_laden",
                          return_value=(None, "nautilus_trader fehlt: X")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        self.assertEqual(r.titel_zusatz(), " (fehlt)")
        self.assertIn("fehlt", r.status())
        self.assertTrue(r.abbrechbar())
        self.assertIsNone(r.frame)
        texte = [w.cget("text") for w in r.winfo_children()
                 if isinstance(w, ttk.Label)]
        self.assertTrue(any("nautilus_trader fehlt" in t for t in texte), texte)


class ReiterMitAttrappe(unittest.TestCase):
    """Mit einem Attrappen-Frame: das Interface, das der Leitstand ruft."""

    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    class Attrappe(ttk.Frame):
        def __init__(self, eltern):
            super().__init__(eltern)
            self._running = False

    def _reiter(self, laeuft):
        m = type("M", (), {"NautilusFrame": self.Attrappe})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        r.frame._running = laeuft
        return r

    def test_laufender_node_zeigt_punkt_und_sperrt_das_schliessen(self):
        r = self._reiter(True)
        self.assertEqual(r.titel_zusatz(), " ●")
        self.assertIn("läuft", r.status())
        self.assertFalse(r.abbrechbar())

    def test_stehender_node_zeigt_nichts(self):
        r = self._reiter(False)
        self.assertEqual(r.titel_zusatz(), "")
        self.assertEqual(r.status(), "")
        self.assertTrue(r.abbrechbar())

    def test_refresh_ist_ein_no_op(self):
        r = self._reiter(False)
        self.assertIsNone(r.refresh())


class Verdrahtung(unittest.TestCase):
    def test_der_reiter_haengt_am_rahmen(self):
        self.assertIs(lst.REITER[-1][1], ln.NautilusReiter)
        self.assertEqual(lst.REITER[-1][0], "Nautilus")
        self.assertEqual(lst.KUERZEL["<Control-Key-6>"], ("reiter", len(lst.REITER) - 1))

    def test_alle_reiter_haben_die_schnittstelle(self):
        for titel, klasse in lst.REITER:
            for name in ("refresh", "titel_zusatz", "status"):
                self.assertTrue(hasattr(klasse, name), "%s.%s fehlt" % (titel, name))

    def test_der_reiter_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(ln.__file__), [])


if __name__ == "__main__":
    unittest.main()
