"""Omniquant-Reiter im Leitstand: refresh/status/titel_zusatz aus echtem Stand.

Der Reiter war nach Schritt 1 ein Hohlkoerper: `refresh()` tat nichts,
`status()` gab die Konstante "Omniquant" zurueck. Geprueft wird jetzt die
EIGENTLICHT: die Statusleiste nennt, was die Spur wirklich gerade tut, und
F5 liest neu.

Gegen die Verwechslung mit geratenen Feldern: zustand.json der Spur fuehrt
`modus`, nicht `live`. Ein Test faengt genau das ab - die Zustaende kommen
aus Attrappen, es wird keine echte Spur gelesen.

Direkt ausfuehrbar:  python tests/test_leitstand_omniquant_reiter.py
"""

import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import leitstand as lst                                        # noqa: E402
from omniquant import gui                                      # noqa: E402
from omniquant.gui import OmniquantReiter                      # noqa: E402


class Basis(unittest.TestCase):
    def setUp(self):
        self._gelesen = []
        self.addCleanup(self._gelesen.clear)
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.ls = type("L", (), {"root": self.root, "zustand": None,
                                 "melde": lambda s, t: None})()
        # OmniquantReiter baut in echt OmniquantGui (Netz beim Start). Fuer
        # die Interface-Pruefung wird die KLASSE im Modul ersetzt - `_gui`
        # ist ein Instanzattribut und selbst nicht patchbar.
        attrappe = type("A", (), {"__init__": lambda s, eltern, eigener_timer=True: None})
        p = patch.object(gui, "OmniquantGui", attrappe)
        p.start()
        self.addCleanup(p.stop)
        self.r = OmniquantReiter(self.root, self.ls)
        self.r._gelesen = self._gelesen

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def setze(self, zustand=None, bericht=None, alter=None):
        """Nur die Anzeigedaten ersetzen - die Reiter-METHODEN bleiben echt.

        Wichtig: `_gui` wird am Reiter-Objekt gesetzt, nicht an der Klasse.
        Wer eine ganze Attrappen-Klasse baut, verliert die Methoden, die
        man eigentlich pruefen will.
        """
        reiter = self.r

        def neu(self):
            reiter._gelesen.append(1)

        reiter._gui = type("G", (), {
            "zustand": zustand if zustand is not None else {},
            "bericht": bericht if bericht is not None else {},
            "bericht_alter": alter,
            "_planer": neu,
        })()


class Interface(Basis):
    def test_papier_zeigt_keinen_punkt(self):
        self.setze({"modus": "papier"})
        self.assertEqual(self.r.titel_zusatz(), "")

    def test_live_zeigt_den_punkt(self):
        self.setze({"modus": "live"})
        self.assertEqual(self.r.titel_zusatz(), " ●")

    def test_es_gibt_das_feld_nicht_das_geraten_wird(self):
        # zustand.json fuehrt `modus`, NICHT `live`. Wer `live` liest, sieht
        # nie einen Punkt und faelt es nicht - bis eine Position live laeuft.
        self.setze({"live": True})
        self.assertEqual(self.r.titel_zusatz(), "")

    def test_status_nennt_treffer_und_alter(self):
        self.setze({"modus": "papier"},
                   {"treffer": [1, 2, 3]}, alter=2.5)
        s = self.r.status()
        self.assertIn("Omniquant", s)
        self.assertIn("3 Treffer", s)
        self.assertIn("2.5 h alt", s)

    def test_status_bleibt_lesbar_ohne_daten(self):
        self.setze()
        self.assertEqual(self.r.status(), "Omniquant")

    def test_status_nennt_live(self):
        self.setze({"modus": "live"})
        self.assertIn("live", self.r.status())

    def test_refresh_liest_neu(self):
        self.setze()
        self.r.refresh()
        self.assertEqual(len(self._gelesen), 1)

    def test_refresh_nimmt_den_rahmen_nicht_mit(self):
        self.setze()
        g = self.r._gui

        def kaputt(self):
            raise RuntimeError("Wachen nicht lesbar")

        g.refresh_daten = kaputt
        self.assertIsNone(self.r.refresh())      # kein Absturz

    def test_immer_schliessbar(self):
        self.setze({"modus": "live"})
        self.assertTrue(self.r.abbrechbar())


class Verdrahtung(unittest.TestCase):
    def test_omniquant_haengt_am_rahmen(self):
        self.assertIn(OmniquantReiter, [k for _, k in lst.REITER])
        # Ueber den Titel, nicht ueber die Position (Prozesse, FreqTrade kamen dazu).
        i = [t for t, _k in lst.REITER].index("Omniquant")
        self.assertEqual(lst.KUERZEL["<Control-Key-%d>" % (i + 1)], ("reiter", i))

    def test_wer_einen_hintergrundprozess_haelt_sagt_es(self):
        # `abbrechbar()` ist OPTIONAL: der Rahmen nutzt
        # getattr(r, "abbrechbar", lambda: True)() - fehlt sie, gilt
        # "schliessbar". Ein Reiter, der etwas haelt, MUSS sie haben,
        # sonst raedt der Rahmen und zerstoert es beim X.
        for titel, klasse in lst.REITER:
            if klasse.__name__ in ("NautilusReiter", "BacktestReiter",
                                   "UrteileReiter"):
                self.assertTrue(hasattr(klasse, "abbrechbar"), titel)


if __name__ == "__main__":
    unittest.main()
