"""Tests der GUI-Bindung: liest die GUI die Felder, die es wirklich gibt?

Kein Fenster, kein Netz: geprueft wird fuss_texte() - die reine Funktion
hinter der Fusszeile - und die Formpruefung, dass die Feldnamen, die die GUI
liest, auch geschrieben werden.

Befund 13.09.2026: Die Fusszeile las einsatz_pro_position,
kumulierte_verluste und kill_switch. Keines dieser Felder existiert im
Zustand - handeln.py schreibt verluste_usd, die Grenzen stehen in
wachen.json. Folge: "Einsatz: ?" und "kum. Verluste: 0.00 USD" unabhaengig
vom echten Zustand, und der Kill-Switch stand selbst bei gerissenem Deckel
auf "frei". Diese Tests halten die Bindung fest.

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (HIER, os.path.join(HIER, "..")):
    if p not in sys.path:
        sys.path.insert(0, p)

import gui                                                 # noqa: E402
import handeln as h                                        # noqa: E402

WACHEN = {"max_einsatz_je_position_usd": 50, "max_gesamt_risiko_usd": 500}


class FusszeileTest(unittest.TestCase):

    def test_verluste_kommen_aus_verluste_usd(self):
        # Nicht aus kumulierte_verluste - das Feld gibt es nicht, und die
        # Fusszeile zeigte deshalb immer 0.00 USD.
        _, t_verluste, _, kill = gui.fuss_texte({"verluste_usd": 123.45}, WACHEN)
        self.assertIn("123.45", t_verluste)
        self.assertFalse(kill)

    def test_einsatz_kommt_aus_den_wachen(self):
        t_einsatz, _, _, _ = gui.fuss_texte({}, WACHEN)
        self.assertIn("50", t_einsatz)
        t_ohne, _, _, _ = gui.fuss_texte({}, {})
        self.assertIn("?", t_ohne)

    def test_kill_switch_ist_die_rechnung_nicht_ein_feld(self):
        # Zustand mit kill_switch=true, aber ohne Verluste: die GUI darf
        # nicht auf ein Feld hereinfallen, das niemand schreibt.
        _, _, t_kill, aktiv = gui.fuss_texte(
            {"kill_switch": True, "verluste_usd": 0.0}, WACHEN)
        self.assertFalse(aktiv)
        self.assertIn("frei", t_kill)

    def test_kill_switch_aktiv_bei_gerissenem_deckel(self):
        _, _, t_kill, aktiv = gui.fuss_texte({"verluste_usd": 500.0}, WACHEN)
        self.assertTrue(aktiv)
        self.assertIn("AKTIV", t_kill)

    def test_knapp_unter_dem_deckel_ist_frei(self):
        _, _, _, aktiv = gui.fuss_texte({"verluste_usd": 499.99}, WACHEN)
        self.assertFalse(aktiv)


class FormTest(unittest.TestCase):
    """Die GUI-Felder muessen die Form treffen, die handeln.py erzeugt."""

    def test_zustandsfelder_der_gui_schreibt_handeln_auch(self):
        z = h.lade_zustand()
        # Felder, die die GUI liest (fuss_texte, _zeige, _lies_zustand).
        for feld in ("verluste_usd", "positionen", "modus", "letzter_lauf"):
            self.assertIn(feld, z, "handeln.lade_zustand() kennt %s nicht" % feld)

    def test_wachenfelder_der_gui_stehen_in_der_echten_datei(self):
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        for feld in ("max_einsatz_je_position_usd", "max_gesamt_risiko_usd"):
            self.assertIn(feld, w, "wachen.json kennt %s nicht" % feld)

    def test_gui_liest_keine_erfundenen_felder(self):
        # Der Quelltext darf die drei Feldnamen nicht mehr enthalten, die
        # niemand schreibt - sonst kommt die Luecke beim naechsten Umbau
        # zurueck.
        with open(os.path.join(HIER, "gui.py"), encoding="utf-8") as f:
            text = f.read()
        for feld in ("einsatz_pro_position", "kumulierte_verluste",
                     "kill_switch"):
            self.assertNotIn('"%s"' % feld, text,
                             "gui.py liest wieder %s" % feld)


if __name__ == "__main__":
    unittest.main()
