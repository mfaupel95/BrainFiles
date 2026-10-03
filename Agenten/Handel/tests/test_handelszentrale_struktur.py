r"""Struktur der Handelszentrale: jede Tabelle hat eine Leiste, nichts steht doppelt.

Prueft den Quelltext per AST, reine Funktionen und das gebaute Fenster - drei
Regeln, die beim naechsten neuen Abschnitt sonst still verloren gehen:

  * Treeviews werden AUSSCHLIESSLICH ueber `tabelle_mit_leiste` gebaut. Eine
    Tabelle ohne Leiste ist bei mehr Zeilen als Platz ein Abschnitt, den man
    nicht lesen kann - der Befund vom 30.09.2026: die Spurtabelle forderte
    `height=len(SPUREN)` an (42 Zeilen), kein Fenster zeigte sie ganz, und
    ohne Leiste half auch Vergroessern nicht.
  * Kein Name wird in derselben Datei zweimal definiert. Die Zentrale hatte
    zwei wortgleiche `spur_zeile`-Funktionen; Python laesst die letzte
    gewinnen, die erste war tot - eine Aenderung nur an ihr wirkte wie keine.
  * Die Spuren-Seite ist eine Scrollflaeche: Scrollregion, Leiste, Mausrad.

Was hier NICHT geprueft wird: dass `yview` nach `yview_moveto` wandert. Ein
verstecktes Test-Fenster hat keine Geometrie - nachgemessen: yview bleibt
(0.0, 1.0), auch mit 40 Zeilen in einer Fuenf-Zeilen-Tabelle. Ein solcher Test
bewiese Tk, nicht die Zentrale; geprueft wird die Verdrahtung.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_handelszentrale_struktur
"""

import ast
import os
import sys
import unittest
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as hz  # noqa: E402


def _baum():
    with open(hz.__file__, encoding="utf-8") as f:
        return ast.parse(f.read())


def _namen_eines_scopes(knoten):
    """Alle Funktions-/Klassennamen, die in DIESEM Scope definiert werden."""
    aus = []
    for kind in knoten.body:
        if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            aus.append(kind.name)
    return aus


def _treeview_Aufrufe(knoten):
    """Zeilennummern aller `X.Treeview(...)`-Bauaufrufe unterhalb von `knoten`."""
    zeilen = []
    for kind in ast.walk(knoten):
        if (isinstance(kind, ast.Call) and isinstance(kind.func, ast.Attribute)
                and kind.func.attr == "Treeview"):
            zeilen.append(kind.lineno)
    return zeilen


class DoppeltDefinitionTest(unittest.TestCase):
    """Doppelte Definitionen sind Tottungen, keine Redundanz."""

    def test_kein_Name_zweimal_im_gleichen_Scope(self):
        doppelt = []
        for knoten in ast.walk(_baum()):
            if not isinstance(knoten, (ast.Module, ast.ClassDef)):
                continue
            namen = _namen_eines_scopes(knoten)
            for name in set(namen):
                if namen.count(name) > 1:
                    doppelt.append("%s::%s" % (getattr(knoten, "name", "Modul"), name))
        self.assertEqual(doppelt, [],
                         "doppelt definiert (die letzte gewinnt, die fruehere ist tot): %s"
                         % sorted(doppelt))

    def test_spur_zeile_hat_genau_eine_Fassung(self):
        # Der konkrete Fall vom 30.09.2026 - als Gegenprobe auf die Regel oben.
        wurzeln = [k for k in ast.walk(_baum())
                   if isinstance(k, ast.FunctionDef) and k.name == "spur_zeile"]
        self.assertEqual(len(wurzeln), 1)


class TabellenBauregelTest(unittest.TestCase):
    """Keine Treeview ohne Leiste: `tabelle_mit_leiste` ist der einzige Bauplatz."""

    def _helfer(self):
        baum = _baum()
        helfer = [k for k in ast.walk(baum)
                  if isinstance(k, ast.FunctionDef) and k.name == "tabelle_mit_leiste"]
        self.assertEqual(len(helfer), 1, "der Helfer fehlt oder steht zweimal")
        return baum, helfer[0]

    def test_jeder_Treeview_Aufruf_liegt_im_Helfer(self):
        baum, helfer = self._helfer()
        erlaubt = range(helfer.lineno, helfer.end_lineno + 1)
        aussen = [z for z in _treeview_Aufrufe(baum) if z not in erlaubt]
        self.assertEqual(aussen, [],
                         "Treeviews ausserhalb von tabelle_mit_leiste (Zeilen %s) - "
                         "die bekamen keine Scrollbar" % aussen)

    def test_der_Helfer_baut_selbst_eine_Treeview(self):
        # Gegenprobe: die Regel oben darf nicht leer gewinnen, nur weil der
        # Helfer umgebaut und sein eigener Bauaufruf mitgenommen wurde.
        _baum2, helfer = self._helfer()
        self.assertTrue(_treeview_Aufrufe(helfer),
                        "tabelle_mit_leiste baut keine Treeview mehr")

    def test_keine_Hoehe_aus_der_Zeilenzahl_der_Spuren(self):
        """Keine Tabelle fordert so viele Zeilen an, wie es Spuren gibt.

        Per AST, nicht per Stichwortsuche: derselbe Text steht als erklaerende
        Erwahnung in Kommentaren und Docstrings der Zentrale - die zahlen nicht.
        Erlaubt ist die GEDEKELTE Form (`min(len(SPUREN), 12)`) - gebrochen ist
        nur die ungedeckelte, die mitwachst.
        """
        for knoten in ast.walk(_baum()):
            if not isinstance(knoten, ast.Call):
                continue
            gebaut = ((isinstance(knoten.func, ast.Name)
                       and knoten.func.id == "tabelle_mit_leiste")
                      or (isinstance(knoten.func, ast.Attribute)
                          and knoten.func.attr == "Treeview"))
            if not gebaut:
                continue
            for kw in knoten.keywords:
                if kw.arg not in ("hoehe", "height"):
                    continue
                text = ast.unparse(kw.value)
                if "SPUREN" not in text:
                    continue
                self.assertNotEqual(text, "len(SPUREN)",
                                    "ungedeckelte Zeilenzahl (Zeile %d): hoeher als "
                                    "jedes Fenster und ohne Leiste unerreichbar"
                                    % knoten.lineno)
                self.assertTrue(text.startswith("min("),
                                "Zeilenanzahl aus der Spurliste ohne Deckel "
                                "(Zeile %d): %s" % (knoten.lineno, text))


class RadRichtungTest(unittest.TestCase):
    """`_rad_schritte` ist die ganze Mausrad-Rechnung - ohne Fenster pruefbar."""

    class _E:
        def __init__(self, delta=None, num=None):
            if delta is not None:
                self.delta = delta
            if num is not None:
                self.num = num

    def test_windows_hoch_und_runter(self):
        self.assertEqual(hz._rad_schritte(self._E(delta=120)), -1)
        self.assertEqual(hz._rad_schritte(self._E(delta=-120)), 1)

    def test_x11_Knopf_4_und_5(self):
        self.assertEqual(hz._rad_schritte(self._E(num=4)), -1)
        self.assertEqual(hz._rad_schritte(self._E(num=5)), 1)

    def test_ohne_Bewegung_kein_Schritt(self):
        self.assertEqual(hz._rad_schritte(self._E()), 0)
        self.assertEqual(hz._rad_schritte(self._E(delta=0)), 0)

    def test_mehrere_Rasten_und_mehrere_Zeilen_pro_Schritt(self):
        self.assertEqual(hz._rad_schritte(self._E(delta=-240)), 2)
        self.assertEqual(hz._rad_schritte(self._E(num=5), zeilen=3), 3)

    def test_die_Seite_nimmt_drei_Zeilen_pro_Raste(self):
        # Eine Zeile pro Raste fuehlt sich auf einer langen Seite an, als
        # drehe man ins Leere.
        self.assertEqual(hz._rad_schritte(self._E(delta=-120), 3), 3)

    def test_feine_Raste_zahlt_als_ein_Schritt(self):
        # Manche Treiber melden delta=±40: eine Rechnung nur mit // 120
        # ergaebe 0 und das Rad stuese ins Leere.
        self.assertEqual(hz._rad_schritte(self._E(delta=-40)), 1)


class ScrollregionTest(unittest.TestCase):
    """`seite_region_neu` setzt die Region - und laesst leere Inhalte ohne.

    Am 01.10.2026 nachgemessen: ein Canvas ohne gemessenen Inhalt liefert
    bbox = (0, 0, 1, 1). Das als Scrollregion zu setzen sieht nach Erfolg aus,
    waehrend die Seite ein Pixel weit scrollt.
    """

    def setUp(self):
        try:
            self.root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_artefakt_Rahmen_bleibt_ohne_Region(self):
        wrapper, innen, c = hz.scrollbare_seite(self.root)
        self.root.update_idletasks()
        messung = hz.seite_region_neu(c, innen)
        # Nachgemessen: ein leerer Seiten-Canvas liefert bbox = (0, 0, 1, 1),
        # nicht None. Beides darf nicht als Scrollregion landen.
        self.assertTrue(messung is None or messung[3] <= 1, messung)
        self.assertEqual(str(c.cget("scrollregion")).strip(), "",
                         "ein 1-Pixel-Artefakt wurde als Scrollregion gesetzt")

    def test_inhalt_setzt_die_Region(self):
        wrapper, innen, c = hz.scrollbare_seite(self.root)
        hz.tk.Frame(innen, width=400, height=1200).pack(fill="x")
        self.root.update_idletasks()
        messung = hz.seite_region_neu(c, innen)
        self.assertTrue(messung, "bbox blieb leer, obwohl 1200 px Inhalt packed sind")
        region = str(c.cget("scrollregion")).split()
        self.assertEqual(len(region), 4)
        self.assertGreater(float(region[3]), 600.0,
                           "die Scrollregion bleibt kleiner als ihr Inhalt")


class GebautesFensterTest(unittest.TestCase):
    """Im gebauten Fenster: Leiste, Rad und Scrollflaeche sind wirklich dran."""

    TABELLEN = ("t_spuren", "t_pos", "t_ft_bots", "t_ft_offen", "t_ft_zu",
                "t_laeufe", "t_omni", "t_omni_pos", "t_omni_journal")

    def setUp(self):
        try:
            self.root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        # Kein Netz im Test: Kurs- und FreqTrade-Abrufe werden abgefangen,
        # gebaut wird das echte Fenster. Die Patches muessen den ganzen Test
        # ueberleben - das ausdrueckliche `refresh()` weiter unten wuerfe sonst
        # echte Bot-Aufrufe und startete echte Kurs-Threads.
        for methode in ("_starte_kurs_worker", "_starte_freqtrade_worker"):
            patcher = mock.patch.object(hz.Handelszentrale, methode)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.app = hz.Handelszentrale(self.root)
        self.root.update_idletasks()
        self.app.refresh()
        self.root.update_idletasks()
        self.addCleanup(self.root.destroy)

    def test_jede_Tabelle_hat_eine_hoehere_und_breitere_Leiste(self):
        for attr in self.TABELLEN:
            baum = getattr(self.app, attr)
            self.assertTrue(str(baum.cget("yscrollcommand")),
                            "%s hat keine vertikale Scrollbar" % attr)
            self.assertTrue(str(baum.cget("xscrollcommand")),
                            "%s hat keine horizontale Scrollbar" % attr)

    def test_jede_Tabelle_ist_in_der_Hoehe_begrenzt(self):
        for attr in self.TABELLEN:
            hoehe = int(getattr(self.app, attr).cget("height"))
            self.assertLessEqual(hoehe, 20, "%s fordert %d Zeilen an" % (attr, hoehe))

    def test_jede_Tabelle_reagiert_auf_das_Mausrad(self):
        for attr in self.TABELLEN:
            baum = getattr(self.app, attr)
            self.assertTrue(str(baum.bind("<MouseWheel>")),
                            "%s hat keine Mausrad-Bindung" % attr)

    def test_die_Spuren_Seite_ist_eine_Scrollflaeche(self):
        c = self.app.seite_canvas
        self.assertTrue(str(c.cget("yscrollcommand")),
                        "die Spuren-Seite hat keine Scrollbar")
        self.assertTrue(str(c.bind("<MouseWheel>")),
                        "auf der Spuren-Seite tut das Mausrad nichts")
        messung = hz.seite_region_neu(c, self.app.seite)
        self.assertTrue(messung,
                        "die Seite hat Inhalt, aber keine messbare Scrollregion")
        self.assertGreater(messung[3], 200,
                           "die Scrollregion ist hoeher als zwei Zeilen - sonst gibt "
                           "es nichts zu scrollen")

    def test_Rahmen_unter_der_Seite_hoeren_auch_auf_das_Rad(self):
        """Das Rad landet auf dem Widget unter dem Zeiger, nicht auf dem Canvas."""
        gebunden = sum(1 for w in hz._nachkommen(self.app.seite)
                       if str(w.bind("<MouseWheel>")))
        self.assertGreater(gebunden, 5,
                           "nur %d Widgets der Spuren-Seite hoeren auf das Rad" % gebunden)

    def test_spurtabelle_zeigt_alle_Spuren_trotz_begrenzter_Hoehe(self):
        self.assertEqual(len(self.app.t_spuren.get_children()), len(hz.SPUREN))
        self.assertLess(int(self.app.t_spuren.cget("height")), len(hz.SPUREN),
                        "bei so viel Zeilen Platz wie Spuren waere die Leiste nutzlos")

    def test_Bedienelemente_bleiben_erhalten(self):
        # Die Umbauten duerfen das Bestehende nicht verlieren: Stufe, Schrift,
        # Konto, Summe, Dauerlauf-Kopf, FreqTrade-Umschalter, Chart, Konsole.
        for attr in ("w_stufe", "w_schrift", "l_konto", "l_summe", "l_dauerlauf",
                     "w_ft_bot", "l_ft", "l_omni", "l_omni_spur", "konsole",
                     "canvas", "c_ft", "t_spuren"):
            self.assertTrue(hasattr(self.app, attr), attr)
        self.assertIn("offene Positionen", self.app.l_summe.cget("text"))


if __name__ == "__main__":
    unittest.main()
