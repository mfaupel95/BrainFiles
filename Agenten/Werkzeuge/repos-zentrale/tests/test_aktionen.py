"""Tests fuer aktionen.py - kein Test startet etwas: die Aufrufe sind ersetzt."""

import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aktionen  # noqa: E402
import manifest  # noqa: E402
import scan  # noqa: E402


class FakePopen:
    """Merkt sich, wie es gerufen wurde, und startet nichts."""

    rufe: list[tuple] = []

    def __init__(self, argv, **kwargs):
        FakePopen.rufe.append((list(argv), dict(kwargs)))
        self.pid = 4242
        self.returncode = None

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def terminate(self):
        pass


def zeile(ordner="demo", start=None, *, pfad=None, bot=None) -> manifest.Zeile:
    repo = scan.Repo(
        ordner=ordner,
        pfad=pfad or Path("C:/x") / ordner,
        art="python",
        git=True,
        venv=".venv",
        venv_python=Path("C:/x") / ordner / ".venv" / "Scripts" / "python.exe",
        node_modules=False,
        readme="README.md",
    )
    return manifest.Zeile(ordner=ordner, gruppe="startbar", repo=repo, start=start, bot=bot)


class ArgvTest(unittest.TestCase):
    def test_ordner_geht_an_den_explorer(self):
        self.assertEqual(aktionen.argv_ordner(Path("C:/x/demo")), ["explorer", "C:\\x\\demo"])

    def test_terminal_ist_wt_im_richtigen_ordner(self):
        argv = aktionen.argv_terminal(Path("C:/x/demo"))
        self.assertEqual(argv[0], "wt.exe")
        self.assertIn("-d", argv)
        self.assertEqual(argv[argv.index("-d") + 1], "C:\\x\\demo")

    def test_bot_nennt_profil_und_ordner_getrennt(self):
        argv, cwd = aktionen.argv_bot("Moon-Dev-Agents", Path("C:/x/demo"))
        self.assertEqual(argv, ["hermes", "-p", "moon-dev-agents", "chat"])
        self.assertEqual(cwd, Path("C:/x/demo"))

    def test_logname_enthaelt_repo_und_zeitpunkt(self):
        p = aktionen.log_pfad(Path("C:/logs"), "moon-dev-ai-agents",
                              datetime(2026, 9, 18, 14, 5))
        self.assertEqual(p.name, "moon-dev-ai-agents-20260918-1405.log")


class LogPfadTest(unittest.TestCase):
    def test_ordnername_wird_entschaerft(self):
        p = aktionen.log_pfad(Path("C:/logs"), "böse/../ding", datetime(2026, 9, 18, 0, 0))
        self.assertNotIn("/", p.name)
        self.assertNotIn("..", p.name)


class StartTest(unittest.TestCase):
    def setUp(self):
        FakePopen.rufe = []
        self.t = tempfile.TemporaryDirectory()
        self.logs = Path(self.t.name) / "logs"

    def tearDown(self):
        self.t.cleanup()

    def test_start_schreibt_argv_und_cwd_ohne_shell(self):
        ergebnis = aktionen.start_ausfuehren(
            zeile(start=[".venv\\Scripts\\pythonw.exe", "moongui.py"]),
            self.logs,
            popen=FakePopen,
            jetzt=datetime(2026, 9, 18, 14, 5),
        )
        self.assertIsNone(ergebnis.fehler)
        self.assertEqual(ergebnis.pid, 4242)
        self.assertEqual(len(FakePopen.rufe), 1)
        argv, kwargs = FakePopen.rufe[0]
        self.assertEqual(argv, [".venv\\Scripts\\pythonw.exe", "moongui.py"])
        self.assertEqual(kwargs.get("cwd"), "C:\\x\\demo")
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(ergebnis.log.name, "demo-20260918-1405.log")

    def test_start_ohne_befehl_startet_nichts(self):
        ergebnis = aktionen.start_ausfuehren(zeile(start=None), self.logs, popen=FakePopen)
        self.assertEqual(FakePopen.rufe, [])
        self.assertIsNotNone(ergebnis.fehler)
        self.assertIsNone(ergebnis.pid)

    def test_fehlendes_programm_ist_ein_fehlertext_kein_absturz(self):
        def boese_popen(*a, **kw):
            raise FileNotFoundError("nicht da")

        ergebnis = aktionen.start_ausfuehren(zeile(start=["gibtsnicht.exe"]), self.logs,
                                             popen=boese_popen)
        self.assertIsNone(ergebnis.pid)
        self.assertIn("FileNotFoundError", ergebnis.fehler)

    def test_relatives_programm_wird_gegen_das_repo_aufgeloest(self):
        # Windows loest argv[0] gegen das Arbeitsverzeichnis des Aufrufers auf,
        # nicht gegen cwd des Kindes - deshalb muss der Pfad absolut werden.
        with tempfile.TemporaryDirectory() as t:
            repo_pfad = Path(t) / "demo"
            (repo_pfad / ".venv" / "Scripts").mkdir(parents=True)
            (repo_pfad / ".venv" / "Scripts" / "pythonw.exe").write_bytes(b"")
            z = zeile(start=[".venv\\Scripts\\pythonw.exe", "gui.py"], pfad=repo_pfad)
            aktionen.start_ausfuehren(z, self.logs, popen=FakePopen)
            argv, kwargs = FakePopen.rufe[0]
            self.assertTrue(Path(argv[0]).is_absolute(), argv)
            self.assertEqual(Path(argv[0]).name, "pythonw.exe")
            self.assertEqual(argv[1], "gui.py")

    def test_programm_auf_dem_path_bleibt_unveraendert(self):
        aktionen.start_ausfuehren(zeile(start=["npm", "start"]), self.logs, popen=FakePopen)
        argv, _ = FakePopen.rufe[0]
        self.assertEqual(argv, ["npm", "start"])

    def test_prozesshandle_wird_zurueckgegeben(self):
        ergebnis = aktionen.start_ausfuehren(zeile(start=["x.exe"]), self.logs, popen=FakePopen)
        self.assertIsNotNone(ergebnis.prozess)
        self.assertEqual(ergebnis.prozess.pid, 4242)

    def test_das_log_traegt_die_startzeile(self):
        ergebnis = aktionen.start_ausfuehren(zeile(start=["x.exe"]), self.logs,
                                             popen=FakePopen,
                                             jetzt=datetime(2026, 9, 18, 14, 5))
        inhalt = ergebnis.log.read_text(encoding="utf-8")
        self.assertIn("demo", inhalt)
        self.assertIn("x.exe", inhalt)

    def test_ereignis_wird_angehaengt_nicht_ueberschrieben(self):
        aktionen.start_ausfuehren(zeile(start=["x.exe"]), self.logs, popen=FakePopen,
                                  jetzt=datetime(2026, 9, 18, 14, 5))
        aktionen.ereignis_anhaengen(self.logs / "demo-20260918-1405.log", "beendet (Code 0)")
        inhalt = (self.logs / "demo-20260918-1405.log").read_text(encoding="utf-8")
        self.assertIn("beendet (Code 0)", inhalt)
        self.assertIn("x.exe", inhalt)


class DokuTest(unittest.TestCase):
    def test_doku_oeffnen_ruft_den_starter(self):
        gerufen = []
        fehler = aktionen.doku_oeffnen(Path("C:/x/README.md"), starter=gerufen.append)
        self.assertIsNone(fehler)
        self.assertEqual(gerufen, ["C:\\x\\README.md"])

    def test_doku_oeffnen_meldet_fehler_statt_zu_werfen(self):
        def boese(_):
            raise OSError("kein Programm")

        fehler = aktionen.doku_oeffnen(Path("C:/x/README.md"), starter=boese)
        self.assertIn("OSError", fehler)


if __name__ == "__main__":
    unittest.main()
