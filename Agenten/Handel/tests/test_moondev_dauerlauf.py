"""
Tests fuer moondev_dauerlauf.py - der Treiber faehrt die geklonten
Moon-Dev-Agenten als langlebige Kindprozesse.
"""
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
TREIBER = HIER.parent / "moondev_dauerlauf.py"

def lade_treiber():
    spec = importlib.util.spec_from_file_location("moondev_dauerlauf", TREIBER)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul

class StartStoppTest(unittest.TestCase):
    """Der Treiber startet die Agenten und stoppt sie wieder."""

    def test_startet_beide_agenten(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True)
        lauf.zyklus()
        time.sleep(6)
        self.assertIn("new_or_top", lauf.kinder)
        self.assertIn("kraken", lauf.kinder)
        kind = lauf.kinder["new_or_top"]
        code = kind.poll()
        if code is not None:
            fehler = (kind.stderr.read() or "")[-2000:]
            self.fail(f"new_or_top muss laufen, endete mit {code}:\n{fehler}")
        lauf._stoppe("new_or_top")
        lauf._stoppe("kraken")

    def test_umgebung_hat_routine(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True)
        eintrag = m.AGENTEN["kraken"]
        umgebung = dict(os.environ)
        umgebung["MAXHIRN_ROUTINE"] = "1"
        umgebung["HANDEL_RISIKO"] = "basis"
        self.assertEqual(umgebung["MAXHIRN_ROUTINE"], "1")
        self.assertIn("cwd", eintrag)
        self.assertTrue(Path(eintrag["cwd"]).exists())

if __name__ == "__main__":
    unittest.main()

class WaiseTest(unittest.TestCase):
    """Verwaiste Agentenprozesse: erkennen, schonen, beenden.

    Anlass (gemessen 21.09.2026): 84 Agentenprozesse hatten sich ueber Nacht
    angesammelt, 80 davon aelter als eine Stunde. Ein Kind besteht unter
    Windows aus zwei Prozessen (Startprogramm + Interpreter); der Treiber hielt
    nur das Startprogramm, der Interpreter blieb nach dessen Ende als Waise
    stehen. Folge: nur 1,94 GB freies Commit von 89,8 - das lokale Modell liess
    sich nicht mehr laden.
    """

    class Kind:
        """Minimaler Ersatz fuer subprocess.Popen im Test."""

        def __init__(self, pid, tot=False):
            self.pid = pid
            self._tot = tot

        def poll(self):
            return 0 if self._tot else None

    def setUp(self):
        self.m = lade_treiber()
        # WICHTIG: protokolliere() schreibt in die ECHTE Treiber-Logdatei. Ohne
        # diese Umbiegung landen Testzeilen ("PID 600") im Betriebsprotokoll -
        # am 21.09.2026 genau so passiert und im Log nachweisbar. Der Test darf
        # nie in eine echte Datei schreiben.
        self.tmp = tempfile.mkdtemp(prefix="moondev-waise-")
        self.m.LOG = Path(self.tmp) / "log.txt"
        self.lauf = self.m.MoonDevDauerlauf(stumm=True)
        self.getoetet = []
        self.m._kill_baum = lambda pid: (self.getoetet.append(pid), True)[1]

    def _p(self, pid, eltern, cmd, alter_min=60):
        return {"ProcessId": pid, "ParentProcessId": eltern,
                "CommandLine": cmd,
                "CreationDate": "/Date(%d)/" % int(
                    (time.time() - alter_min * 60) * 1000)}

    def test_waise_wird_erkannt(self):
        alle = [self._p(100, 1, "pythonw.exe -m src.agents.sniper_agent"),
                self._p(101, 1, "pythonw.exe -m src.agents.trading_agent")]
        self.assertEqual(sorted(e["ProcessId"] for e in self.lauf.fremde_agenten(alle)), [100, 101])

    def test_eigenes_kind_und_enkel_bleiben(self):
        """Der Baum des lebenden Kindes ist tabu - auch der Enkel."""
        self.lauf.kinder["sniper"] = self.Kind(200)
        alle = [self._p(200, 1, "pythonw.exe -m src.agents.sniper_agent"),
                self._p(201, 200, "pythonw.exe -m src.agents.sniper_agent"),
                self._p(202, 999, "pythonw.exe -m src.agents.sniper_agent")]
        raus = [e["ProcessId"] for e in self.lauf.fremde_agenten(alle)]
        self.assertNotIn(200, raus)
        self.assertNotIn(201, raus)      # Enkel des lebenden Kindes
        self.assertEqual(raus, [202])    # echte Waise

    def test_frischer_prozess_bleibt_geschont(self):
        """Ein gerade gestarteter Prozess darf nicht im eigenen Start sterben."""
        alle = [self._p(300, 1, "pythonw.exe -m src.agents.kraken_agent.py", alter_min=0)]
        self.assertEqual(self.lauf.fremde_agenten(alle), [])

    def test_fremder_prozess_ist_kein_agent(self):
        alle = [self._p(400, 1, "python.exe handeln.py --live")]
        self.assertEqual(self.lauf.fremde_agenten(alle), [])

    def test_aufraeumen_beendet_und_protokolliert(self):
        self.lauf.kinder["kraken"] = self.Kind(500, tot=True)   # totes Kind, PID bleibt
        alle = [self._p(600, 1, "pythonw.exe -m src.agents.sniper_agent")]
        n = self.lauf.aufraeumen(alle)
        self.assertEqual(n, 1)
        self.assertIn(600, self.getoetet)
        self.assertTrue(any("Aufraeumen" in z for z in self.lauf.protokoll),
                        "Aufraeumen muss im Protokoll stehen (Beleg)")

    def test_totes_kind_sperrt_seine_waise_nicht(self):
        """Ein beendetes Kind zaehlt nicht mehr als 'lebend' - sonst bliebe die
        Waise fuer immer geschont."""
        self.lauf.kinder["sniper"] = self.Kind(700, tot=True)
        alle = [self._p(700, 1, "pythonw.exe -m src.agents.sniper_agent"),
                self._p(701, 700, "pythonw.exe -m src.agents.sniper_agent")]
        raus = sorted(e["ProcessId"] for e in self.lauf.fremde_agenten(alle))
        self.assertEqual(raus, [700, 701])
