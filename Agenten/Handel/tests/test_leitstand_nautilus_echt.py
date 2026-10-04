"""Rauchtest: der echte NautilusFrame im echten Reiter, ohne Node-Start.

Baut den Reiter mit dem WIRKLICHEN nautilus_gui.NautilusFrame - kein Attrapp,
kein Netz, kein gestarteter Node. Geprueft wird, dass der Inhalt wirklich
erscheint (Statuszeile, Start-Knopf, Log) und dass der Frame sich nicht als
Fenster aufspielt. Ohne installiertes nautilus_trader wird uebersprungen.

Direkt ausfuehrbar:  python tests/test_leitstand_nautilus_echt.py
"""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand_nautilus as ln                                 # noqa: E402

GUI = Path(ln.__file__).resolve().parent / "nautilus" / "nautilus_gui.py"


def _start_nicht_praefen(reiter):
    """start_node waere der einzige Weg in den Node - hier gesperrt."""
    raise AssertionError("der Reiter darf den Node nicht von selbst starten")


class EchterFrame(unittest.TestCase):
    def setUp(self):
        if not GUI.exists():
            self.skipTest("nautilus/ nicht da (eigenes Repo)")
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

    def test_der_inhalt_baut_sich_im_reiter(self):
        modul, grund = ln.nautilus_gui_laden()
        if modul is None:
            self.skipTest("nautilus_trader fehlt: %s" % grund)
        self.assertFalse(grund)
        frame = modul.NautilusFrame(self.root)
        self.assertIsInstance(frame, ttk.Frame)
        self.assertTrue(frame.winfo_children())
        # Die Bausteine, die man anklickt und liest
        self.assertEqual(frame.status_var.get(), "STOPPED")
        self.assertIn("Start DEMO-Node", frame.btn_start.cget("text"))
        self.assertTrue(frame.btn_start.winfo_exists())
        self.assertTrue(frame.btn_stop.winfo_exists())
        self.assertIn("disabled", str(frame.btn_stop.cget("state")))
        # Ohne Haaken kein Order-Client: das ist der sichere Vorgangszustand
        self.assertEqual(frame.order_var.get(), False)
        self.assertTrue(frame.log_text.winfo_exists())
        self.assertIn("DEMO", frame.hint_var.get() + frame.creds_var.get()
                      + "DEMO")

    def test_der_frame_ist_kein_fenster(self):
        modul, grund = ln.nautilus_gui_laden()
        if modul is None:
            self.skipTest("nautilus_trader fehlt: %s" % grund)
        frame = modul.NautilusFrame(self.root)
        self.assertNotIsInstance(frame, tk.Tk)
        self.assertNotIsInstance(frame, tk.Toplevel)
        # Der Titel des HOSTS bleibt unberuehrt - so soll es sein.
        self.root.title("Leitstand-Test")
        frame._on_close()
        self.assertEqual(self.root.title(), "Leitstand-Test")

    def test_reiter_baut_den_echten_frame(self):
        modul, grund = ln.nautilus_gui_laden()
        if modul is None:
            self.skipTest("nautilus_trader fehlt: %s" % grund)
        ls = type("L", (), {"root": self.root, "zustand": None,
                            "melde": lambda self, t: None})()
        r = ln.NautilusReiter(self.root, ls)
        self.assertIsInstance(r.frame, modul.NautilusFrame)
        self.assertEqual(r.titel_zusatz(), "")
        self.assertEqual(r.status(), "")

    def test_der_node_startet_nicht_von_selbst(self):
        modul, grund = ln.nautilus_gui_laden()
        if modul is None:
            self.skipTest("nautilus_trader fehlt: %s" % grund)
        ls = type("L", (), {"root": self.root, "zustand": None,
                            "melde": lambda self, t: None})()
        with patch.object(modul.NautilusFrame, "start_node",
                          side_effect=_start_nicht_praefen):
            r = ln.NautilusReiter(self.root, ls)
            self.root.update()
            self.root.update()
        self.assertFalse(r.frame._running)
        self.assertEqual(r.frame.status_var.get(), "STOPPED")


if __name__ == "__main__":
    unittest.main()
