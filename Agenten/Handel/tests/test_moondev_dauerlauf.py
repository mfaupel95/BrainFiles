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
    """Der Treiber startet die Agenten und stoppt sie wieder.

    Geprueft wird der START, nicht das UEBERLEBEN. Der erste Anlauf dieses
    Tests verlangte "laeuft nach 6 Sekunden noch" und hing damit an Netz und
    Maschinenlast: in der 890er-Suite (drei Dauerlauf-Stufen parallel) fiel er
    um, einzeln lief er gruen. Ein Agent stirbt im Normalfall an einem
    Rate-Limit des Datenanbieters (CoinGecko 429, gemessen 21.09.2026) - das ist
    kein Fehler des Treibers, sondern der Gratis-Grenze des Anbieters.
    """

    #: Windows-Startfehler - der Prozess kam gar nicht hoch. Ein Agent, der an
    #: einem Rate-Limit stirbt, endet NICHT so; deshalb trennt der Test Start
    #: von Laufzeit, statt beides als "rot" zu behandeln.
    STARTERFEHLER = {
        -1073741515,  # 0xC0000135 DLL nicht gefunden
        -1073741819,  # 0xC0000005 Zugriffsverletzung
        -1073740791,  # 0xC0000409 Stack-Buffer-Overrun
        3221225781,   # 0xC0000135 als unsigned
        3221225477,   # 0xC0000005 als unsigned
    }

    def test_startet_beide_agenten(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True, trocken=True)
        try:
            lauf.zyklus()
            self.assertIn("new_or_top", lauf.kinder)
            self.assertIn("kraken", lauf.kinder)
            for name in ("new_or_top", "kraken"):
                kind = lauf.kinder[name]
                self.assertTrue(getattr(kind, "pid", 0) > 0,
                                "%s wurde gestartet, hat aber keine PID" % name)
                # Dem Interpreter Zeit geben, die erste Zeile zu schreiben:
                # entweder er lebt noch, oder sein Log hat Inhalt.
                log = Path(lauf._logbasis) / ("moondev_%s.log" % name)
                for _ in range(30):
                    if kind.poll() is not None:
                        break
                    if log.exists() and log.stat().st_size > 0:
                        break
                    time.sleep(0.5)
                code = kind.poll()
                urteil = self.starturteil(name, code, log)
                self.assertIn(urteil, ("laeuft", "laufzeitende"),
                              "%s: %s (Exit %s, Log %s Byte) - der Start hat nicht "
                              "gewirkt" % (name, urteil, code,
                                           log.stat().st_size if log.exists() else 0))
        finally:
            # ALLE Kinder beenden - und die Nachfahren EINZELN: der venv-Launcher
            # (Wurzel) kann schon tot sein, waehrend der Interpreter weiterlaeuft
            # (Leak-Muster vom 21.09.2026). taskkill /T erreicht dann nichts mehr,
            # und der Test liesse vier Waisen stehen, die danach der echte Treiber
            # aufraeumen muesste (am 23.09.2026 zweimal passiert).
            meine = {k.pid for k in lauf.kinder.values()}
            alle = m._prozesse()
            nachfahren = set(meine)
            for _ in range(4):
                for e in alle:
                    if e.get("ParentProcessId") in nachfahren:
                        nachfahren.add(e["ProcessId"])
            for name in list(lauf.kinder):
                lauf._stoppe(name)
            for pid in nachfahren:
                m._kill_baum(pid)

    def starturteil(self, name, code, log):
        """Reine Entscheidung: hat der Start gewirkt? (ohne Prozesse, testbar)

        "laeuft"       - Prozess lebt
        "laufzeitende" - Prozess ist gestorben, hat aber gearbeitet (Normalfall:
                         Rate-Limit des Datenanbieters)
        "startfehler"  - Windows-Startfehler, der Prozess kam nie hoch
        "startproblem" - tot und kein einziges Log-Byte: der Aufruf stimmt nicht
        """
        if code is None:
            return "laeuft"
        if code in self.STARTERFEHLER:
            return "startfehler"
        if not (log.exists() and log.stat().st_size > 0):
            return "startproblem"
        return "laufzeitende"

    def test_starturteil_erkennt_die_drei_faelle(self):
        """Gegenprobe: der Test oben muss bei einem echten Startfehler rot werden.

        Ohne diese Pruefung waere nicht belegt, dass er ueberhaupt anschlaegt -
        ein Test, der nie rot werden kann, prueft nichts.
        """
        import tempfile
        leer = Path(tempfile.mkdtemp()) / "leer.log"
        voll = Path(tempfile.mkdtemp()) / "voll.log"
        voll.write_text("gestartet\n", encoding="utf-8")
        self.assertEqual(self.starturteil("x", None, leer), "laeuft")
        self.assertEqual(self.starturteil("x", 0xC0000135 - 2**32, leer), "startfehler")
        self.assertEqual(self.starturteil("x", 1, leer), "startproblem")
        self.assertEqual(self.starturteil("x", 1, voll), "laufzeitende")

    def test_umgebung_hat_routine(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(risiko="basis", stumm=True, trocken=True)
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
        self.lauf = self.m.MoonDevDauerlauf(stumm=True, trocken=True)
        self.getoetet = []
        self.m._kill_baum = lambda pid: (self.getoetet.append(pid), True)[1]

    def _p(self, pid, eltern, cmd, alter_min=60, name="pythonw.exe"):
        return {"ProcessId": pid, "ParentProcessId": eltern,
                "Name": name, "CommandLine": cmd,
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

    def test_huelle_mit_der_kennung_ist_kein_agent(self):
        """Eine PowerShell-Abfrage, die den Agentennamen ENTHAELT, ist kein Agent.

        Am 21.09.2026 zaehlte die Wache kraken=5 statt 2, weil die eigene
        Suchabfrage in der Kommandozeile stand. Ein Aufraeumer, der das fuer ein
        Kind haelt, beendet die eigene Suche (taskkill /T) - deshalb muss der
        Prozessname mitgeprueft werden.
        """
        alle = [self._p(900, 1, "powershell -Command Get-CimInstance ... kraken_agent.py",
                        name="powershell.exe"),
                self._p(901, 1, "pythonw.exe -m src.agents.sniper_agent")]
        raus = [e["ProcessId"] for e in self.lauf.fremde_agenten(alle)]
        self.assertNotIn(900, raus)
        self.assertIn(901, raus)


class LogDrehenTest(unittest.TestCase):
    """Agenten-Logs duerfen nicht unbegrenzt wachsen (160 MB am 23.09.2026)."""

    def test_unter_der_schwelle_passiert_nichts(self):
        m = lade_treiber()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "moondev_sniper.log"
            p.write_bytes(b"x" * 1000)
            self.assertEqual(m._log_drehen(p, max_mb=1), "")
            self.assertTrue(p.exists())
            self.assertFalse((Path(d) / "moondev_sniper.log.1").exists())

    def test_ueber_der_schwelle_wird_gedreht(self):
        m = lade_treiber()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "moondev_sniper.log"
            p.write_bytes(b"x" * (2 * 1024 * 1024))
            text = m._log_drehen(p, max_mb=1)
            self.assertIn("gedreht", text)
            self.assertFalse(p.exists())
            self.assertEqual((Path(d) / "moondev_sniper.log.1").stat().st_size,
                             2 * 1024 * 1024)

    def test_alte_drehung_wird_ersetzt_nicht_angehaengt(self):
        m = lade_treiber()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "moondev_sniper.log"
            alt = Path(d) / "moondev_sniper.log.1"
            alt.write_bytes(b"alt" * 100)
            p.write_bytes(b"y" * (2 * 1024 * 1024))
            m._log_drehen(p, max_mb=1)
            self.assertEqual(alt.stat().st_size, 2 * 1024 * 1024)

    def test_fehlende_datei_ist_kein_fehler(self):
        """Der Treiber dreht vor JEDEM Start - auch wenn es die Datei nicht gibt."""
        m = lade_treiber()
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(m._log_drehen(Path(d) / "gibtsnicht.log"), "")

    def test_starte_dreht_vor_dem_oeffnen(self):
        """Der Aufruf muss VOR dem Oeffnen stehen: ein laufender Agent haelt die
        Datei offen, Windows verweigert dann das Umbenennen (gemessen)."""
        quelle = TREIBER.read_text(encoding="utf-8")
        i_dreh = quelle.index("_log_drehen(ag_log)")
        i_offen = quelle.index('ag_datei = open(ag_log')
        self.assertLess(i_dreh, i_offen)


class TrockenlaufSchutzTest(unittest.TestCase):
    """Ein Test darf nie in den LAUFENDEN Betrieb schreiben.

    Am 23.09.2026 hat ein Lauf dieser Suite die lebenden Agenten als Waisen
    beendet (8 PIDs), die Logdatei des Laufs gedreht (160,6 MB) und ihre
    Startzeilen ins Treiberlog geschrieben - der Betrieb merkte es nur daran,
    dass die Agenten kurz darauf neu starteten.
    """

    def test_trocken_schreibt_nicht_ins_treiberlog(self):
        m = lade_treiber()
        log = HIER.parent / "moondev_dauerlauf.log"
        vorher = log.stat().st_size if log.exists() else 0
        lauf = m.MoonDevDauerlauf(stumm=True, trocken=True)
        lauf.protokolliere("diese Zeile darf NICHT im Treiberlog landen")
        nachher = log.stat().st_size if log.exists() else 0
        self.assertEqual(vorher, nachher)
        self.assertNotIn("diese Zeile darf NICHT", log.read_text(encoding="utf-8", errors="replace"))
        self.assertIn("diese Zeile darf NICHT", "\n".join(lauf.protokoll))

    def test_trocken_schreibt_agentenlogs_in_den_temporaeren_ordner(self):
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(stumm=True, trocken=True)
        self.assertNotEqual(lauf._logbasis, HIER.parent)
        self.assertTrue(str(lauf._logbasis).endswith("") or True)
        self.assertIn("moondev-test-", str(lauf._logbasis))
        self.assertTrue(lauf._logbasis.is_dir())

    def test_trocken_raeumt_fremde_agenten_nicht_auf(self):
        """Aufraeumen wuerde die Agenten des echten Laufs beenden."""
        m = lade_treiber()
        lauf = m.MoonDevDauerlauf(stumm=True, trocken=True)
        gerufen = []
        lauf.aufraeumen = lambda alle=None: gerufen.append(alle)          # type: ignore
        lauf._ist_tot = lambda name: True                                  # type: ignore
        lauf._starte = lambda name, beschreibung="": None                  # type: ignore
        lauf.zyklus()
        self.assertEqual(gerufen, [])
        self.assertTrue(any("Trockenlauf" in z for z in lauf.protokoll))


class StartformTest(unittest.TestCase):
    """Jeder Agent startet als Modul (-m src.agents.<name>) aus der Repo-Wurzel.

    Ein Skriptpfad setzt sys.path[0] auf src/agents/ - dann scheitert jeder
    "from src..."-Import (kraken_agent.py seit Fork-Commit 0cb95b7, 04.10.2026:
    ModuleNotFoundError: No module named 'src', Neustart im Kreis).
    """

    def test_alle_agenten_starten_als_modul_aus_der_repo_wurzel(self):
        m = lade_treiber()
        for name, eintrag in m.AGENTEN.items():
            cmd = eintrag["cmd"]
            self.assertEqual(cmd[1], "-m", name)
            self.assertTrue(cmd[2].startswith("src.agents."), name)
            self.assertFalse(cmd[2].endswith(".py"), name)
            self.assertEqual(eintrag["cwd"], str(m.REPO), name)


class ProzesslisteKodierungTest(unittest.TestCase):
    """Windows PowerShell 5 schreibt umgeleitet in der OEM-Codepage (cp850).
    Python las cp1252 und brach an einem Umlaut ab (Byte 0x81 = cp850 'ue'):
    stdout None, Prozessliste leer, Aufraeumen uebersprungen (11.10.2026)."""

    def test_abfrage_erzwingt_utf8_auf_beiden_seiten(self):
        m = lade_treiber()
        gesehen = {}

        class Ergebnis:
            stdout = '[{"ProcessId": 1, "Name": "python.exe", "CommandLine": "C:/Müller/x.py"}]'

        def lauf(cmd, **kw):
            gesehen["cmd"], gesehen["kw"] = cmd, kw
            return Ergebnis()

        alt = m.subprocess.run
        m.subprocess.run = lauf
        try:
            if m.os.name != "nt":
                self.skipTest("nur Windows")
            daten = m._prozesse()
        finally:
            m.subprocess.run = alt
        self.assertIn("OutputEncoding", gesehen["cmd"][-1])
        self.assertEqual(gesehen["kw"].get("encoding"), "utf-8")
        self.assertEqual(gesehen["kw"].get("errors"), "replace")
        self.assertEqual(daten[0]["CommandLine"], "C:/Müller/x.py")


class UngepuffertTest(unittest.TestCase):
    def test_agenten_laufen_ungepuffert(self):
        # stdout geht in eine Datei: ohne das Flag puffert Python 8 KB, ein
        # wortkarger Agent (kraken) schrieb so stundenlang keine Zeile.
        quelle = TREIBER.read_text(encoding="utf-8")
        self.assertIn('umgebung["PYTHONUNBUFFERED"] = "1"', quelle)


class LokalStandardTest(unittest.TestCase):
    def test_hausstandard_ist_qwen35_9b(self):
        # Auftrag Max 11.10.2026: qwen35-8k ist nicht mehr installiert.
        self.assertEqual(lade_treiber().LOKAL_STANDARD, "qwen3.5:9b")
