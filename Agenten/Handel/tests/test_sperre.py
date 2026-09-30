"""Die Sperrdatei des Dauerlaufs: haelt sie einen Doppelstart auf?

WARUM DIESER TEST
-----------------
Am 15.09.2026 liefen zwei Dauerlaeufe gleichzeitig und schrieben in dieselben
Dateien (dauerlauf.py, Modulkopf). Die Abwehr dagegen war eine Datei mit einer
nackten PID - und eine nackte PID traegt drei Luecken:

1. Ein direkt gestarteter `python dauerlauf.py` prueft sie gar nicht.
2. Er schreibt sie auch nicht, ist also fuer den Waechter unsichtbar.
3. Windows vergibt PIDs wieder. Traegt irgendein fremder Python-Prozess die
   alte Nummer, meldet der Waechter dauerhaft "laeuft bereits" und startet
   nie wieder neu - die Luecke hebelt die Wiederbelebung aus.

Die Startzeit des Prozesses schliesst (3): eine wiederverwendete PID hat eine
andere Startzeit. Die Pruefung im Prozess selbst schliesst (1) und (2).

GRUNDSATZ: Bei Zweifel startet der Lauf, statt zu blockieren. Die
Doppelstart-Abwehr bleibt beim Waechter, der Prozess ergaenzt sie nur. Jede
Unsicherheit - unlesbare Datei, verweigerter Zugriff, psutil-Fehler - zaehlt
deshalb als "nicht belegt".

Kein Fall hier fasst eine echte Sperrdatei an; alle Pfade zeigen in einen
Temp-Ordner.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psutil

import risikostufe
import sperre


class TestLesen(unittest.TestCase):
    """lies(): was in der Datei steht, und was fehlende Angaben bedeuten."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="sperre-test-")
        self.datei = os.path.join(self.ordner, "dauerlauf.pid")

    def schreib(self, inhalt):
        with open(self.datei, "w", encoding="ascii") as f:
            f.write(inhalt)

    def test_altes_einfeldformat_gibt_pid_ohne_zeit(self):
        """Die Fassung vor dem 29.09.2026 trug nur die Nummer."""
        self.schreib("4711\n")
        self.assertEqual(sperre.lies(self.datei), (4711, None))

    def test_neues_zweifeldformat_gibt_pid_und_zeit(self):
        self.schreib("4711 1790668314.127303\n")
        pid, zeit = sperre.lies(self.datei)
        self.assertEqual(pid, 4711)
        self.assertAlmostEqual(zeit, 1790668314.127303, places=3)

    def test_fehlende_datei_ist_kein_fehler(self):
        self.assertIsNone(sperre.lies(self.datei))

    def test_unlesbarer_inhalt_zaehlt_als_keine_sperre(self):
        """Lieber starten als an einer kaputten Datei haengen bleiben."""
        for muell in ("", "\n", "keine-zahl", "4711 keine-zahl\n"):
            with self.subTest(muell=muell):
                self.schreib(muell)
                ergebnis = sperre.lies(self.datei)
                self.assertTrue(ergebnis is None or ergebnis == (4711, None))


class TestSchreiben(unittest.TestCase):
    """schreibe(): Format und Rundlauf."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="sperre-test-")
        self.datei = os.path.join(self.ordner, "dauerlauf.pid")

    def test_rundlauf(self):
        sperre.schreibe(self.datei)
        pid, zeit = sperre.lies(self.datei)
        self.assertEqual(pid, os.getpid())
        self.assertAlmostEqual(zeit, psutil.Process().create_time(), places=3)

    def test_eine_zeile_erstes_feld_ist_die_nackte_pid(self):
        """Der PowerShell-Waechter liest ($inhalt -split '\s+')[0].

        Mehrzeilig duerfte es nicht sein: Get-Content gaebe dann ein Array,
        und Get-Process -Id scheiterte daran.
        """
        sperre.schreibe(self.datei)
        with open(self.datei, encoding="ascii") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0].split()[0], str(os.getpid()))


class TestBelegt(unittest.TestCase):
    """belegt(): laeuft ein FREMDER Dauerlauf noch?"""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="sperre-test-")
        self.datei = os.path.join(self.ordner, "dauerlauf.pid")

    def schreib(self, inhalt):
        with open(self.datei, "w", encoding="ascii") as f:
            f.write(inhalt)

    def test_ohne_datei_frei(self):
        self.assertFalse(sperre.belegt(self.datei))

    def test_eigene_pid_ist_nicht_fremd(self):
        """Sonst sperrte ein Lauf sich beim Neuschreiben selbst aus."""
        sperre.schreibe(self.datei)
        self.assertFalse(sperre.belegt(self.datei))

    def test_tote_pid_frei(self):
        self.schreib("999999 1790668314.127303\n")
        self.assertFalse(sperre.belegt(self.datei))

    def test_lebende_pid_mit_passender_startzeit_belegt(self):
        fremd = _fremder_python()
        self.addCleanup(_beende, fremd)
        self.schreib("%d %r\n" % (fremd.pid, fremd.create_time()))
        self.assertTrue(sperre.belegt(self.datei))

    def test_lebende_pid_mit_abweichender_startzeit_frei(self):
        """Die wiederverwendete PID - genau die Luecke, die (3) hiess."""
        fremd = _fremder_python()
        self.addCleanup(_beende, fremd)
        self.schreib("%d %r\n" % (fremd.pid, fremd.create_time() - 3600.0))
        self.assertFalse(sperre.belegt(self.datei))

    def test_altes_format_lebender_python_gilt_als_belegt(self):
        """Ohne Startzeit bleibt nur, was der Waechter bisher konnte."""
        fremd = _fremder_python()
        self.addCleanup(_beende, fremd)
        self.schreib("%d\n" % fremd.pid)
        self.assertTrue(sperre.belegt(self.datei))


class TestPfad(unittest.TestCase):
    """pfad(): eine Sperrdatei je Risikostufe, sonst sperrten sie einander."""

    def setUp(self):
        self.vorher = os.environ.get("HANDEL_RISIKO")

    def tearDown(self):
        os.environ.pop("HANDEL_RISIKO", None)
        if self.vorher is not None:
            os.environ["HANDEL_RISIKO"] = self.vorher

    def test_je_stufe_eine_eigene_datei(self):
        namen = set()
        for stufe in ("niedrig", "mittel", "hoch"):
            os.environ["HANDEL_RISIKO"] = stufe
            namen.add(os.path.basename(sperre.pfad()))
        self.assertEqual(len(namen), 3)
        os.environ["HANDEL_RISIKO"] = "niedrig"
        self.assertEqual(os.path.basename(sperre.pfad()), "dauerlauf.pid")



class TestDauerlaufAnbindung(unittest.TestCase):
    """main() darf nicht loslaufen, wenn ein anderer Lauf die Sperre haelt.

    Das ist Luecke (1) aus dem Modulkopf von sperre.py: bis zum 29.09.2026
    pruefte nur der PowerShell-Waechter, und ein Handstart ging daran vorbei.
    """

    def setUp(self):
        self.vorher = os.environ.get("HANDEL_RISIKO")

    def tearDown(self):
        os.environ.pop("HANDEL_RISIKO", None)
        if self.vorher is not None:
            os.environ["HANDEL_RISIKO"] = self.vorher

    def test_belegte_sperre_beendet_den_start(self):
        import dauerlauf

        ordner = tempfile.mkdtemp(prefix="sperre-test-")
        datei = os.path.join(ordner, "dauerlauf.pid")
        gestartet = []

        with mock.patch.object(dauerlauf.sperre, "pfad", return_value=datei),              mock.patch.object(dauerlauf.sperre, "belegt", return_value=True),              mock.patch.object(dauerlauf, "Lauf",
                               side_effect=lambda *a, **k: gestartet.append(1)),              mock.patch.object(sys, "argv", ["dauerlauf.py"]):
            code = dauerlauf.main()

        self.assertEqual(code, 0)
        self.assertEqual(gestartet, [], "es wurde trotz Sperre ein Lauf gebaut")
        self.assertFalse(os.path.exists(datei),
                         "die fremde Sperre wurde ueberschrieben")


class TestEigenerStarter(unittest.TestCase):
    """Die Sperre des EIGENEN Starters blockiert den Lauf nicht.

    Anlass (30.09.2026): handel-dauerlauf.ps1 schreibt die PID des Prozesses,
    den Start-Process zurueckgibt. Bei einem venv-Startprogramm ist das der
    ELTERNPROZESS des Interpreters. Der Lauf sah damit eine lebende fremde
    Python-PID, hielt sie fuer einen zweiten Lauf und beendete sich sofort -
    alle drei Stufen standen still, ohne einen Zyklus und ohne Traceback.
    """

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="sperre-test-")
        self.datei = os.path.join(self.ordner, "dauerlauf.pid")

    def schreib(self, inhalt):
        with open(self.datei, "w", encoding="ascii") as f:
            f.write(inhalt)

    def test_sperre_des_eigenen_starters_blockiert_nicht(self):
        eltern = os.getppid()
        self.schreib("%d %r\n" % (eltern, psutil.Process(eltern).create_time()))
        self.assertFalse(sperre.belegt(self.datei),
                         "der Lauf sperrt sich mit der PID seines Starters selbst aus")

    def test_ein_fremder_lauf_bleibt_belegt(self):
        """Gegenprobe: die neue Regel darf die Doppelstart-Abwehr nicht aufheben."""
        fremd = _fremder_python()
        self.addCleanup(_beende, fremd)
        self.schreib("%d %r\n" % (fremd.pid, fremd.create_time()))
        self.assertTrue(sperre.belegt(self.datei))

    def test_ein_fremder_lauf_ohne_startzeit_bleibt_belegt(self):
        """Auch im alten Einfeldformat - die Regel greift nur beim Starter."""
        fremd = _fremder_python()
        self.addCleanup(_beende, fremd)
        self.schreib("%d\n" % fremd.pid)
        self.assertTrue(sperre.belegt(self.datei))


def _fremder_python():
    """Ein echter, lebender Python-Prozess, der nichts tut und nichts anfasst."""
    p = psutil.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                     stdout=-3, stderr=-3)
    return p


def _beende(p):
    try:
        p.kill()
        p.wait(timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    unittest.main()
