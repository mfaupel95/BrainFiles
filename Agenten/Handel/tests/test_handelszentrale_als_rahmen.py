"""Die Handelszentrale baut sich in einem Frame auf (Leitstand-Reiter) und
setzt allein gestartet weiter Titel und Mindestgroesse.

refresh() und _buero_im_bild() werden ersetzt: refresh startet Kurs-Threads
(Netz), _buero_im_bild verschiebt das Fenster. Ohne Bildschirm wird der Test
uebersprungen.

Direkt ausfuehrbar:  python tests/test_handelszentrale_als_rahmen.py
"""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import handelszentrale as hz                                   # noqa: E402


class Rahmen(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.ersetzt = {}
        for name in ("refresh", "_buero_im_bild"):
            p = patch.object(hz.Handelszentrale, name, autospec=True)
            self.ersetzt[name] = p.start()
            self.addCleanup(p.stop)

    def test_im_rahmen_bleibt_das_fenster_unberuehrt(self):
        self.root.title("Leitstand")
        rahmen = ttk.Frame(self.root)
        hz.Handelszentrale(rahmen)
        self.assertEqual(self.root.title(), "Leitstand")
        self.assertTrue(rahmen.winfo_children())
        self.ersetzt["_buero_im_bild"].assert_not_called()
        self.ersetzt["refresh"].assert_called_once()

    def test_allein_setzt_sie_titel_und_mindestgroesse(self):
        hz.Handelszentrale(self.root)
        self.assertTrue(self.root.title().startswith("Handelszentrale"))
        self.assertEqual(self.root.minsize(), (1000, 640))
        self.ersetzt["_buero_im_bild"].assert_called_once()


if __name__ == "__main__":
    unittest.main()
