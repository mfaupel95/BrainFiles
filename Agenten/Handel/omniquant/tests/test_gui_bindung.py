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

# Falle: gui.py legt beim Import den scanner-Ordner auf den Suchpfad (dort
# liegen okx und wachen_pruefung). Wird diese Datei einzeln aufgerufen
# (python tests/test_gui_bindung.py), liegt tests/ auf Position 0 und
# `import handeln` zieht scanner/handeln.py statt omniquant/handeln.py -
# der Test prueft dann die falsche Spur, und zwar still. Unter
# `-m unittest discover` faellt es nicht auf, weil das Modul schon geladen ist.
# Deshalb hier die Herkunft pruefen und notfalls die richtige Datei laden.
if os.path.dirname(os.path.abspath(getattr(h, "__file__", ""))) != HIER:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "handeln", os.path.join(HIER, "handeln.py"))
    h = importlib.util.module_from_spec(_spec)
    sys.modules["handeln"] = h
    _spec.loader.exec_module(h)

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


class TimerTest(unittest.TestCase):
    """T-345: der 15-s-Timer darf im Leitstand nicht doppelt laufen.

    OmniquantGui startet seinen Timer nur mit eigener_timer=True (Standalone).
    Der OmniquantReiter uebergibt False - der Leitstand-Takt (5 s) ruft
    _planer() ueber refresh() auf. Zwei Timer auf dieselbe Datei waeren eine
    stille Last.
    """

    class _FakeRoot:
        """Root ohne Tk: zeichnet after()-Aufrufe auf, tut sonst nichts."""

        def __init__(self):
            self.after_calls = []
            self.title_calls = []
            self.configure_calls = []
            self.geometry_calls = []
            self.minsize_calls = []

        def after(self, ms, fn):
            self.after_calls.append((ms, fn))
            return "id-%d" % len(self.after_calls)

        def title(self, s):
            self.title_calls.append(s)

        def configure(self, **kw):
            self.configure_calls.append(kw)

        def geometry(self, s):
            self.geometry_calls.append(s)

        def minsize(self, w, h):
            self.minsize_calls.append((w, h))

    def _gui_ohne_tk(self, root, eigener_timer):
        """OmniquantGui ohne echte Tk-Widgets: _baue/refresh_daten gemockt."""
        orig_baue = gui.OmniquantGui._baue
        orig_refresh = gui.OmniquantGui.refresh_daten
        gui.OmniquantGui._baue = lambda self: None
        gui.OmniquantGui.refresh_daten = lambda self: None
        try:
            return gui.OmniquantGui(root, eigener_timer=eigener_timer)
        finally:
            gui.OmniquantGui._baue = orig_baue
            gui.OmniquantGui.refresh_daten = orig_refresh

    def test_standalone_startet_den_timer(self):
        root = self._FakeRoot()
        self._gui_ohne_tk(root, eigener_timer=True)
        self.assertTrue(any(ms == gui.REFRESH_MS for ms, _ in root.after_calls),
                        "Standalone muss den 15-s-Timer starten")

    def test_leitstand_startet_keinen_timer(self):
        root = self._FakeRoot()
        self._gui_ohne_tk(root, eigener_timer=False)
        self.assertFalse(root.after_calls,
                         "Im Leitstand darf kein eigener Timer laufen (T-345)")

    def test_planer_plant_nur_bei_eigenem_timer(self):
        # _planer() ruft refresh_daten() -> _zeige() (echte Widgets) - mocken.
        orig_refresh = gui.OmniquantGui.refresh_daten
        gui.OmniquantGui.refresh_daten = lambda self: None
        try:
            root = self._FakeRoot()
            g = self._gui_ohne_tk(root, eigener_timer=False)
            root.after_calls.clear()
            g._planer()  # darf keinen after() nachlegen
            self.assertFalse(root.after_calls)

            root2 = self._FakeRoot()
            g2 = self._gui_ohne_tk(root2, eigener_timer=True)
            root2.after_calls.clear()
            g2._planer()
            self.assertTrue(any(ms == gui.REFRESH_MS for ms, _ in root2.after_calls))
        finally:
            gui.OmniquantGui.refresh_daten = orig_refresh


if __name__ == "__main__":
    unittest.main()
