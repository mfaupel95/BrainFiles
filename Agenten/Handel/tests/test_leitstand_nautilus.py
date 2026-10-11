"""Nautilus-Reiter im Leitstand: Trennung Fenster/Inhalt, Reiter-Interface, Kraken-Tabs.

Geprueft wird die EIGENTLICHT zu sichernde Regel: `NautilusFrame` ist ein
Frame ohne Fensterpflege (kein title/geometry/minsize/protocol/destroy), und
`NautilusFenster` macht als tk.Tk beides. Wer das verwechselt, baut beim
Einbetten ein Fenster im Fenster - der Fehler faellt erst zur Laufzeit auf.

Auch geprueft: ein Reiter, dessen nautilus_trader fehlt, baut trotzdem - mit
Begruendung statt Absturz. Und: Leitstand.py importiert Nautilus nicht direkt,
sonst waere ein fehlendes Rad ein toter Leitstand.

Ausbau 11.10.2026: Drei Tabs (OKX DEMO, Kraken Spot, Kraken Futures).
Die Kraken-Nodes laufen als Kindprozesse, read-only, ohne API-Keys.

Ohne Nautilus im venv werden die Teiltests uebersprungen; der Fall "fehlt"
wird mit einer Attrappe geprueft, der braucht kein echtes Rad.

Direkt ausfuehrbar:  python tests/test_leitstand_nautilus.py
"""

import sys
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch, MagicMock

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
        self.assertFalse(hasattr(r, "_okx_frame"))
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
        r._okx_frame._running = laeuft
        return r

    def test_laufender_node_zeigt_punkt_und_sperrt_das_schliessen(self):
        r = self._reiter(True)
        self.assertEqual(r.titel_zusatz(), " \u25cf")
        self.assertIn("l\u00e4uft", r.status())
        self.assertFalse(r.abbrechbar())

    def test_stehender_node_zeigt_nichts(self):
        r = self._reiter(False)
        self.assertEqual(r.titel_zusatz(), "")
        self.assertEqual(r.status(), "")
        self.assertTrue(r.abbrechbar())

    def test_refresh_ist_ein_no_op(self):
        r = self._reiter(False)
        self.assertIsNone(r.refresh())


class KrakenTabs(unittest.TestCase):
    """Ausbau 11.10.2026: Kraken Spot und Futures als Tabs."""

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

    def test_zwei_kraken_tabs(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        self.assertEqual(len(r._kraken_frames), 2)
        self.assertIn("spot", r._kraken_frames)
        self.assertIn("futures", r._kraken_frames)

    def test_kraken_spot_frame(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        f = r._kraken_frames["spot"]
        self.assertEqual(f.produkt, "spot")
        self.assertEqual(f.symbol, "BTC/EUR")

    def test_kraken_futures_frame(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        f = r._kraken_frames["futures"]
        self.assertEqual(f.produkt, "futures")
        self.assertEqual(f.symbol, "PF_SOLUSD")

    def test_kraken_pid_dateien_unterschiedlich(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        spot_pid = r._kraken_frames["spot"]._pid_pfad
        futures_pid = r._kraken_frames["futures"]._pid_pfad
        self.assertNotEqual(spot_pid, futures_pid)

    def test_kraken_titel_zusatz_wenn_spot_laeuft(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        r._kraken_frames["spot"]._prozess = MagicMock()
        r._kraken_frames["spot"]._prozess.poll.return_value = None
        self.assertEqual(r.titel_zusatz(), " \u25cf")

    def test_kraken_abbrechbar_when_spot_laeuft(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        r._kraken_frames["spot"]._prozess = MagicMock()
        r._kraken_frames["spot"]._prozess.poll.return_value = None
        self.assertFalse(r.abbrechbar())

    def test_kraken_status_wenn_spot_laeuft(self):
        m = type("M", (), {"NautilusFrame": lambda eltern: ttk.Frame(eltern)})
        with patch.object(ln, "nautilus_gui_laden", return_value=(m, "")):
            r = ln.NautilusReiter(self.root, type("L", (), {})())
        r._kraken_frames["spot"]._prozess = MagicMock()
        r._kraken_frames["spot"]._prozess.poll.return_value = None
        self.assertIn("Kraken spot l\u00e4uft", r.status())


class KrakenNodeStartStop(unittest.TestCase):
    """Kraken-Node: Start/Stop als Kindprozess."""

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

    def test_start_schreibt_pid_datei(self):
        f = ln._KrakenNodeFrame(self.root, "spot", "BTC/EUR")
        f._pid_pfad.unlink(missing_ok=True)
        with patch.object(ln.subprocess, "Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_popen.return_value = mock_proc
            f._starten()
            self.assertTrue(f._pid_pfad.exists())
            self.assertEqual(f._pid(), 12345)
        f._pid_pfad.unlink(missing_ok=True)

    def test_stop_loescht_pid_datei(self):
        f = ln._KrakenNodeFrame(self.root, "spot", "BTC/EUR")
        f._pid_pfad.write_text("12345\n", encoding="ascii")
        with patch.object(ln, "psutil") as mock_psutil:
            mock_proc = MagicMock()
            mock_psutil.Process.return_value = mock_proc
            f._stoppen()
            self.assertFalse(f._pid_pfad.exists())

    def test_keys_werden_aus_env_entfernt(self):
        f = ln._KrakenNodeFrame(self.root, "spot", "BTC/EUR")
        f._pid_pfad.unlink(missing_ok=True)
        with patch.object(ln.subprocess, "Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 11111
            captured_env = {}
            def capture(*args, **kwargs):
                captured_env.update(kwargs.get("env", {}))
                return mock_proc
            mock_popen.side_effect = capture
            f._starten()
            self.assertNotIn("KRAKEN_SPOT_API_KEY", captured_env)
            self.assertNotIn("KRAKEN_SPOT_API_SECRET", captured_env)
            self.assertEqual(captured_env.get("KRAKEN_PRODUKT"), "spot")
        f._pid_pfad.unlink(missing_ok=True)


class Verdrahtung(unittest.TestCase):
    def test_der_reiter_haengt_am_rahmen(self):
        i = [t for t, _k in lst.REITER].index("Nautilus")
        self.assertIs(lst.REITER[i][1], ln.NautilusReiter)
        self.assertEqual(lst.KUERZEL["<Control-Key-%d>" % (i + 1)], ("reiter", i))

    def test_alle_reiter_haben_die_schnittstelle(self):
        for titel, klasse in lst.REITER:
            for name in ("refresh", "titel_zusatz", "status"):
                self.assertTrue(hasattr(klasse, name), "%s.%s fehlt" % (titel, name))

    def test_der_reiter_schreibt_nichts(self):
        self.assertEqual(lesepruefung.schreibstellen(ln.__file__), [])


class OrderClientBeschriftet(unittest.TestCase):
    """T-343: der Haken ist KEIN Weg der Spuren - und das steht sichtbar da."""

    def setUp(self):
        import tkinter as tk
        try:
            self.root = tk.Tk()
        except tk.TclError as e:
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        self.addCleanup(self._zu)
        modul, grund = ln.nautilus_gui_laden()
        if modul is None:
            self.skipTest("nautilus_trader fehlt: %s" % grund)
        self.modul = modul

    def _zu(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def frame(self):
        return self.modul.NautilusFrame(self.root)

    def _texte(self, widget, tief=0):
        r = []
        try:
            t = widget.cget("text")
            if t:
                r.append(str(t))
        except Exception:
            pass
        for k in widget.winfo_children():
            r += self._texte(k, tief + 1)
        return r

    def test_der_hinweis_erscheint_beim_anhaeken(self):
        f = self.frame()
        self.assertFalse(f.order_var.get())
        f._order_hinweis_sichtbar()
        self.assertFalse(f.order_hinweis.winfo_manager())
        f.order_var.set(True)
        f._order_hinweis_sichtbar()
        self.assertEqual(f.order_hinweis.winfo_manager(), "pack")
        self.assertIn("nicht der Weg der Spuren", f.order_hinweis.cget("text"))

    def test_die_warnung_sagt_es_dauerhaft(self):
        f = self.frame()
        texte = " ".join(self._texte(f))
        self.assertIn("NICHT der Orderweg der Spuren", texte)
        self.assertIn("Sperrenkette", texte)

    def test_jeder_start_mit_haken_schreibt_es_ins_log(self):
        f = self.frame()
        f.order_var.set(True)
        with patch.object(f, "_log") as geloggt, \
             patch.object(self.modul.node_mod, "load_client_configs",
                          side_effect=SystemExit("Keys fehlen")):
            f.start_node()
        texte = " ".join(str(c.args[0]) for c in geloggt.call_args_list)
        self.assertIn("KEIN Weg der Spuren", texte)

    def test_ohne_haken_steht_keine_hinweiszeile_im_log(self):
        f = self.frame()
        f.order_var.set(False)
        with patch.object(f, "_log") as geloggt, \
             patch.object(self.modul.node_mod, "load_client_configs",
                          side_effect=SystemExit("Keys fehlen")):
            f.start_node()
        texte = " ".join(str(c.args[0]) for c in geloggt.call_args_list)
        self.assertNotIn("KEIN Weg der Spuren", texte)


if __name__ == "__main__":
    unittest.main()
