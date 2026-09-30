"""Tests fuer gateway-launcher-wache.py (T-217).

Geprueft wird die REGEL, nicht der Tageszustand: welche Startzeile gilt als
kaputt, welche Datei wird gewaehlt, was passiert bei fehlendem Python. Die
Pruefung gegen die echten Dateien laeuft als letzter Test nur darauf, dass sie
ohne Absturz durchkommt - ein rotes Ergebnis dort waere ein Befund, keine
kaputte Pruefung.
"""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PFAD = Path(__file__).resolve().parent / "gateway-launcher-wache.py"


def laden():
    spec = importlib.util.spec_from_file_location("gw_launcher_wache", PFAD)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


W = laden()

GESUND = """' Hermes Agent Gateway
Option Explicit
Dim sh, env
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\\irgendwo"
sh.Run "C:\\irgendwo\\tools\\python-3.14.7+20260901-win32-x64\\pythonw.exe -m hermes_cli.main gateway run", 0, False
"""

KAPUTT = """' Hermes Agent Gateway
Option Explicit
Dim sh, env
Set sh = CreateObject("WScript.Shell")
sh.Run "C:\\irgendwo\\tools\\python-3.14.7+20260901-win32-x64\\python.exe -m hermes_cli.main gateway run", 0, False
"""

# Die reparierte Datei traegt den Befund als KOMMENTAR - darin steht python.exe.
# Eine Pruefung, die Kommentarzeilen mitzaehlt, meldet den gesunden Launcher
# als kaputt. Genau dieser Fall steht im Haus.
GESUND_MIT_KOMMENTAR = GESUND + (
    "' Wer den Start von Hand nachsehen will:\n"
    "'   python.exe -m hermes_cli.main gateway run\n"
)


class StartzeileTest(unittest.TestCase):
    def test_run_zeile_ignoriert_kommentare(self):
        zeile = W.run_zeile(GESUND_MIT_KOMMENTAR)
        self.assertIn("pythonw.exe", zeile)

    def test_ohne_startzeile_kein_treffer(self):
        self.assertIsNone(W.run_zeile("' nur ein Kommentar\nDim x\n"))

    def test_gesunder_launcher_ohne_befund(self):
        self.assertIsNone(W.vbs_befund(GESUND))
        self.assertIsNone(W.vbs_befund(GESUND_MIT_KOMMENTAR))

    def test_konsolenprogramm_ist_ein_befund(self):
        grund = W.vbs_befund(KAPUTT)
        self.assertIsNotNone(grund)
        self.assertIn("python.exe", grund)
        self.assertIn("Fensterstil 0", grund)

    def test_fehlende_startzeile_ist_ein_befund(self):
        self.assertIsNotNone(W.vbs_befund("Option Explicit\nDim sh\n"))

    def test_fremdes_programm_ist_ein_befund(self):
        text = 'sh.Run "C:\\Windows\\System32\\cmd.exe /c start", 0, False\n'
        self.assertIsNotNone(W.vbs_befund(text))


class LauncherWahlTest(unittest.TestCase):
    def test_neueste_vbs_gewinnt(self):
        with tempfile.TemporaryDirectory() as d:
            alt = Path(d) / "Hermes_Gateway_alt.vbs"
            neu = Path(d) / "Hermes_Gateway_2ef9d0b7.vbs"
            alt.write_text(GESUND, encoding="utf-8")
            neu.write_text(GESUND, encoding="utf-8")
            import os
            os.utime(alt, (1_600_000_000, 1_600_000_000))
            self.assertEqual(W.launcher_vbs(d), neu)

    def test_leerer_ordner_gibt_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(W.launcher_vbs(d))

    def test_ordner_fehlt_gibt_none(self):
        self.assertIsNone(W.launcher_vbs(Path("C:/gibt-es-nicht-xyz")))


class ToolsPythonTest(unittest.TestCase):
    def test_neuestes_python_gewinnt(self):
        with tempfile.TemporaryDirectory() as d:
            alt = Path(d) / "python-3.13.0-win32-x64"
            neu = Path(d) / "python-3.14.7-win32-x64"
            for p in (alt, neu):
                p.mkdir()
                (p / "python.exe").write_text("x", encoding="utf-8")
            import os
            os.utime(alt / "python.exe", (1_600_000_000, 1_600_000_000))
            self.assertEqual(W.tools_python(d), neu / "python.exe")

    def test_ohne_python_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(W.tools_python(d))


class ImportProbeTest(unittest.TestCase):
    """Die Probe laeuft gegen den EIGENEN Interpreter mit gefaelschtem Inhalt."""

    def setUp(self):
        self.alt_probe = W.PROBE
        W.PROBE = "print('ok')"

    def tearDown(self):
        W.PROBE = self.alt_probe

    def test_erfolg(self):
        ok, meldung = W.probe_import(Path(sys.executable), timeout=60)
        self.assertTrue(ok, meldung)

    def test_fehlendes_modul_wird_gemeldet(self):
        W.PROBE = "import modul_gibt_es_nicht_xyz"
        ok, meldung = W.probe_import(Path(sys.executable), timeout=60)
        self.assertFalse(ok)
        self.assertIn("modul_gibt_es_nicht_xyz", meldung)

    def test_unbrauchbares_programm_wird_gemeldet(self):
        with tempfile.TemporaryDirectory() as d:
            py = Path(d) / "python.exe"
            py.write_text("kein Programm", encoding="utf-8")
            ok, meldung = W.probe_import(py, timeout=60)
            self.assertFalse(ok)
            self.assertTrue(meldung)


class MeldungTest(unittest.TestCase):
    def test_gleiche_feststellung_wird_nicht_wiederholt(self):
        with tempfile.TemporaryDirectory() as d:
            stand = Path(d) / "stand.json"
            jetzt = datetime(2026, 9, 30, 12, 0)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                W.melden(["Befund A", "Zeile 2"], {"_pfad": str(stand)}, jetzt)
                W.melden(["Befund A", "Zeile 2"], json.loads(stand.read_text(encoding="utf-8")) | {"_pfad": str(stand)},
                         jetzt + timedelta(hours=1))
            self.assertEqual(puffer.getvalue().count("Befund A"), 1)

    def test_nach_der_frist_wieder(self):
        with tempfile.TemporaryDirectory() as d:
            stand = Path(d) / "stand.json"
            jetzt = datetime(2026, 9, 30, 12, 0)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                W.melden(["Befund A"], {"_pfad": str(stand)}, jetzt)
                W.melden(["Befund A"], json.loads(stand.read_text(encoding="utf-8")) | {"_pfad": str(stand)},
                         jetzt + timedelta(hours=W.WIEDERHOLUNG_H + 1))
            self.assertEqual(puffer.getvalue().count("Befund A"), 2)

    def test_neue_feststellung_immer(self):
        with tempfile.TemporaryDirectory() as d:
            stand = Path(d) / "stand.json"
            jetzt = datetime(2026, 9, 30, 12, 0)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                W.melden(["Befund A"], {"_pfad": str(stand)}, jetzt)
                W.melden(["Befund B"], json.loads(stand.read_text(encoding="utf-8")) | {"_pfad": str(stand)},
                         jetzt + timedelta(minutes=5))
            self.assertIn("Befund A", puffer.getvalue())
            self.assertIn("Befund B", puffer.getvalue())


class DurchlaufTest(unittest.TestCase):
    """main() in einem Temp-Ordner: gesund = leise, kaputt = Meldung."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.dienst = d / "dienst"
        self.tools = d / "tools"
        self.dienst.mkdir()
        (self.tools / "python-3.14.7-win32-x64").mkdir(parents=True)
        self.py = self.tools / "python-3.14.7-win32-x64" / "python.exe"
        self.py.write_text("x", encoding="utf-8")
        (self.py.parent / "pythonw.exe").write_text("x", encoding="utf-8")
        self.stand = d / "stand.json"
        self.alt = (W.DIENST, W.TOOLS, W.HOME, W.CHECKOUT, W.PROBE, W.probe_import)
        W.DIENST, W.TOOLS, W.HOME, W.CHECKOUT = self.dienst, self.tools, d, d
        W.PROBE = "print('ok')"
        # Die Probe selbst wird hier gefaelscht: das gefaelschte python.exe ist
        # eine Textdatei und wuerde nur WinError 216 liefern. Das echte
        # Unterprozess-Verhalten prueft ImportProbeTest gegen den eigenen
        # Interpreter; hier geht es um die Verdrahtung in main().
        W.probe_import = lambda py, timeout=180: (True, "ok")
        self.argv = sys.argv

    def tearDown(self):
        (W.DIENST, W.TOOLS, W.HOME, W.CHECKOUT, W.PROBE,
         W.probe_import) = self.alt
        sys.argv = self.argv
        self.tmp.cleanup()

    def _lauf(self, py_fehler=False):
        if py_fehler:
            W.probe_import = lambda py, timeout=180: (False, "rc=1, No module named pydantic_core")
        sys.argv = ["wache", "--tools", str(self.tools), "--stand", str(self.stand),
                    "--vbs", str(self.dienst / "Hermes_Gateway_x.vbs")]
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = W.main()
        return rc, puffer.getvalue()

    def test_gesund_ist_leise(self):
        (self.dienst / "Hermes_Gateway_x.vbs").write_text(GESUND, encoding="utf-8")
        rc, ausgabe = self._lauf()
        self.assertEqual(rc, 0)
        self.assertEqual(ausgabe.strip(), "")

    def test_kaputte_startzeile_wird_gemeldet(self):
        (self.dienst / "Hermes_Gateway_x.vbs").write_text(KAPUTT, encoding="utf-8")
        rc, ausgabe = self._lauf()
        self.assertEqual(rc, 0)
        self.assertIn("pythonw.exe", ausgabe)

    def test_totes_tools_python_wird_gemeldet(self):
        (self.dienst / "Hermes_Gateway_x.vbs").write_text(GESUND, encoding="utf-8")
        rc, ausgabe = self._lauf(py_fehler=True)
        self.assertIn("pip install -e hermes-agent", ausgabe)

    def test_fehlendes_pythonw_wird_gemeldet(self):
        (self.dienst / "Hermes_Gateway_x.vbs").write_text(GESUND, encoding="utf-8")
        (self.py.parent / "pythonw.exe").unlink()
        rc, ausgabe = self._lauf()
        self.assertIn("pythonw.exe fehlt", ausgabe)

    def test_fehlender_launcher_wird_gemeldet(self):
        rc, ausgabe = self._lauf()
        self.assertIn("Launcher-VBS nicht gefunden", ausgabe)

    def test_echte_dateien_laufen_ohne_absturz(self):
        """Gegen die Dateien im Haus: kein Absturz, Ausgabe nur als Befund."""
        (W.DIENST, W.TOOLS, W.HOME, W.CHECKOUT, W.PROBE,
         W.probe_import) = self.alt
        sys.argv = ["wache", "--stand", str(self.stand), "--probe-aus"]
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = W.main()
        self.assertEqual(rc, 0)
        ausgabe = puffer.getvalue()
        if ausgabe.strip():
            self.assertTrue("python" in ausgabe.lower(), ausgabe)


if __name__ == "__main__":
    unittest.main(verbosity=2)