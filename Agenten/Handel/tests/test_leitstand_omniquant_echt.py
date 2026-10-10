"""Rauchtest: der ECHTE OmniquantReiter im echten Rahmen, ohne Netzstart.

Baut den Reiter mit dem wirklich OmniquantGui - kein Attrapp. Der Kurs-Worker
wird gestoppt, bevor er startet (sonst ginge Netz raus). Geprueft wird, dass
das Fenster sich baut und der Reiter daraus etwas Echtes meldet.

Direkt ausfuehrbar:  python tests/test_leitstand_omniquant_echt.py
"""

import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand as lst                                        # noqa: E402
from omniquant.gui import OmniquantGui, OmniquantReiter        # noqa: E402


class EchterReiter(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        self.ls = type("L", (), {"root": self.root, "zustand": None,
                                 "melde": lambda s, t: None})()
        # Kein Netz: `_kurs_worker` ist eine METHODE von OmniquantGui
        # (nicht ein Modul-Attribut), und wird fuer jeden gebauten Reiter
        # einmal gestartet. Ohne diesen Ersatz ging bei jedem Test Netz raus.
        p = patch.object(OmniquantGui, "_kurs_worker",
                         lambda self, insts: None)
        p.start()
        self.addCleanup(p.stop)

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_der_reiter_baut_die_echte_gui(self):
        r = OmniquantReiter(self.root, self.ls)
        self.assertTrue(hasattr(r._gui, "zustand"))
        self.assertTrue(hasattr(r._gui, "bericht"))
        # OmniquantGui ist eine KOMPOSITION, kein Widget: sie baut in ein
        # uebergebenes `root` hinein. Deshalb war das Einbetten so leicht -
        # und deshalb ist der Reiter der BEHAELTER, nicht die GUI selbst.
        self.assertIs(r._gui.root, r)
        self.assertTrue(r.winfo_children())

    def test_status_ist_lesbar_nach_dem_bau(self):
        r = OmniquantReiter(self.root, self.ls)
        s = r.status()
        self.assertTrue(s.startswith("Omniquant"), s)
        self.assertIsInstance(s, str)

    def test_titel_zusatz_ist_ein_string(self):
        r = OmniquantReiter(self.root, self.ls)
        self.assertIn(r.titel_zusatz(), ("", " ●"))

    def test_refresh_liest_neu_ohne_absturz(self):
        r = OmniquantReiter(self.root, self.ls)
        vorher = dict(getattr(r._gui, "zustand", {}) or {})
        self.assertIsNone(r.refresh())
        self.assertEqual(r.status().split(" — ")[0], "Omniquant")
        self.assertIsInstance(vorher, dict)

    def test_rahmen_kann_den_reiter_bauen(self):
        # Der ganze Leitstand mit allen sieben Reitern - ohne Netz und ohne
        # laufenden Node. Genau das ist der Weg, den Max startet.
        import datetime as dt
        from unittest.mock import patch as pa
        with pa.object(lst.hz, "Handelszentrale"):
            ls = lst.Leitstand(self.root,
                               zustand=lst.Zustand(Path(tempfile.mkdtemp()) / "z.json"),
                               uhr=lambda: dt.datetime(2026, 10, 4, 22, 0),
                               herz=lambda: "Dauerlauf läuft nicht")
            self.root.update()
        # Der Rahmen baut ALLE Reiter aus lst.REITER; feste Zahl und Position
        # sind seit Prozesse/FreqTrade veraltet - geprueft wird die Zusage selbst.
        self.assertEqual(ls.titel, [t for t, _k in lst.REITER])
        self.assertIn("Omniquant", ls.titel)
        self.assertIn("Nautilus", ls.titel)


if __name__ == "__main__":
    unittest.main()
