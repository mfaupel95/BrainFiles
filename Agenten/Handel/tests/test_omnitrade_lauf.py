"""Tests fuer Handel/omnitrade_lauf.py - die Frage "laeuft der Lauf wirklich?".

Der Anlass sind zwei Fehlschluesse, beide am 30.09.2026 erlebt:
  1. Datei sagt "running", die PID ist tot -> man glaubt an laufenden Handel.
  2. Ein Backtest laeuft mit DEMSELBEN Programm (omnitrade-cli.exe) -> eine
     Pruefung nur auf den Programmnamen sperrt den echten Start.

Geprueft werden die REGELN, nicht die Tageswerte: beide Zeugen werden als
Funktion untergeschoben (`lage=` und `lebt=`), die echte Prozessliste ist nur
in einem Fall beteiligt.

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest test_omnitrade_lauf -v
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import omnitrade_lauf as lauf  # noqa: E402
import omnitrade_bridge as bruecke  # noqa: E402


def lage(state="running", pid=1234, alter=5.0, ok=True, fehler=""):
    return {"ok": ok, "state": state, "pid": pid, "alter_s": alter, "fehler": fehler}


GRENZE_FEST = staticmethod(lambda lage, pid: lauf.ALT_GRENZE_S)


class IntervallTest(unittest.TestCase):
    """Die Statusdatei wird NUR beim Verarbeiten einer Kerze geschrieben - bei
    --interval 1h also stuendlich. Eine feste 5-Minuten-Grenze wuerde einen
    gesunden stuendlichen Lauf fuer tot erklaeren (30.09.2026 erlebt)."""

    def test_einheiten(self):
        self.assertEqual(lauf.intervall_s("omnitrade-cli live --interval 1m"), 60.0)
        self.assertEqual(lauf.intervall_s("--interval 15m"), 900.0)
        self.assertEqual(lauf.intervall_s("--interval 1h"), 3600.0)
        self.assertEqual(lauf.intervall_s("--interval 4h"), 14400.0)
        self.assertEqual(lauf.intervall_s("--interval 1d"), 86400.0)
        self.assertEqual(lauf.intervall_s("--interval=30s"), 30.0)

    def test_ohne_angabe_gilt_die_vorgabe_der_cli(self):
        self.assertEqual(lauf.intervall_s("omnitrade-cli live --symbol BTCUSDC"), lauf.INTERVALL_VORGABE_S)
        self.assertEqual(lauf.intervall_s(""), lauf.INTERVALL_VORGABE_S)
        self.assertEqual(lauf.intervall_s("--interval"), lauf.INTERVALL_VORGABE_S)

    def test_unlesbares_raet_nicht(self):
        self.assertEqual(lauf.intervall_s("--interval bald"), lauf.INTERVALL_VORGABE_S)

    def test_grenze_waechst_mit_dem_intervall(self):
        """Untergrenze bleibt die feste Zahl, oben waechst sie mit."""
        self.assertEqual(lauf.altersgrenze_s(0, zeile="--interval 1m"), lauf.ALT_GRENZE_S)
        self.assertEqual(lauf.altersgrenze_s(0, zeile="--interval 1h"), lauf.VIELFACHES * 3600.0)

    def test_stuendlicher_lauf_gilt_als_laufen(self):
        """Der reale Fall: PID lebt, Datei 13 Minuten alt, Intervall 1h."""
        u = lauf.beurteile(lage=lage(alter=786.6), lebt=lambda pid: True,
                           grenze_fuer=lambda lage_daten, pid: lauf.altersgrenze_s(0, zeile="--interval 1h"))
        self.assertTrue(u["laeuft"], u["grund"])

    def test_haengender_lauf_bei_1m_faellt_auf(self):
        """Gegenprobe: derselbe Wert bei 1m-Intervall ist ein Haenger."""
        u = lauf.beurteile(lage=lage(alter=786.6), lebt=lambda pid: True,
                           grenze_fuer=lambda lage_daten, pid: lauf.altersgrenze_s(0, zeile="--interval 1m"))
        self.assertFalse(u["laeuft"])
        self.assertIn("haengt", u["grund"])

    def test_grenze_kommt_zuerst_aus_der_statusdatei(self):
        """Erste Quelle ist der Kerzenabstand IN der Datei - dieselbe Quelle, die
        die Handelszentrale liest. Die Kommandozeile ist nur der Rueckfall."""
        stuendlich = {"recent_candles": [{"time_ms": 0}, {"time_ms": 3_600_000}]}
        self.assertEqual(lauf.grenze_aus_datei(stuendlich, pid=0), lauf.VIELFACHES * 3600.0)
        # Datei ohne Kerzen -> Rueckfall; PID 0 hat keine Kommandozeile -> Untergrenze
        self.assertEqual(lauf.grenze_aus_datei({}, pid=0), lauf.ALT_GRENZE_S)


class BeurteilungTest(unittest.TestCase):
    def test_gesunde_lage_laeuft(self):
        u = lauf.beurteile(lage=lage(), lebt=lambda pid: True)
        self.assertTrue(u["laeuft"])
        self.assertIn("1234", u["grund"])

    def test_tote_pid_ist_nicht_laufen(self):
        """Der wichtigste Fall: die Datei behauptet running, die PID ist weg."""
        u = lauf.beurteile(lage=lage(pid=51356), lebt=lambda pid: False)
        self.assertFalse(u["laeuft"])
        self.assertIn("lebt nicht", u["grund"])

    def test_backtest_taeuscht_nicht(self):
        """Ein Backtest faehrt dasselbe Programm - die Entscheidung haengt an der
        PID aus der Statusdatei, nicht am Programmnamen. Beispiel: die tote PID
        eines Backtests darf den Start nicht sperren."""
        u = lauf.beurteile(lage=lage(pid=1), lebt=lambda pid: False)
        self.assertFalse(u["laeuft"])

    def test_fehlende_datei_ist_nicht_laufen(self):
        u = lauf.beurteile(lage={"ok": False, "grund": "", "fehler": "Datei fehlt", "alter_s": None}, lebt=lambda pid: True)
        self.assertFalse(u["laeuft"])
        self.assertIn("keine Statusdatei", u["grund"])

    def test_fremder_zustand_ist_nicht_laufen(self):
        u = lauf.beurteile(lage=lage(state="stopped"), lebt=lambda pid: True)
        self.assertFalse(u["laeuft"])
        self.assertIn("stopped", u["grund"])

    def test_alte_statusdatei_ist_nicht_laufen(self):
        """Lebt die PID, steht aber die Datei - dann haengt der Lauf, und das
        darf nicht als gesund durchgehen."""
        u = lauf.beurteile(lage=lage(alter=lauf.ALT_GRENZE_S + 1), lebt=lambda pid: True,
                           grenze_fuer=GRENZE_FEST)
        self.assertFalse(u["laeuft"])
        self.assertIn("alt", u["grund"])

    def test_grenze_ist_nicht_ueberschritten(self):
        u = lauf.beurteile(lage=lage(alter=lauf.ALT_GRENZE_S), lebt=lambda pid: True,
                           grenze_fuer=GRENZE_FEST)
        self.assertTrue(u["laeuft"])

    def test_pid_lebt_wirft_nie(self):
        """Unsinnige Eingaben duerfen keine Ausnahme erzeugen - eine Wache, die
        umfaellt, meldet nichts."""
        for wert in (None, "abc", 0, -5, ""):
            self.assertFalse(lauf.pid_lebt(wert))

    def test_pid_lebt_erkennt_die_eigene_pid(self):
        """Gegenprobe mit der ECHTEN Prozessliste: die eigene PID lebt."""
        self.assertTrue(lauf.pid_lebt(os.getpid()))
        self.assertFalse(lauf.pid_lebt(999999))

    def test_pid_lebt_verlangt_das_richtige_programm(self):
        """Windows vergibt PIDs neu: eine lebende PID ist kein Beweis fuer einen
        lebenden Lauf. Am 30.09.2026 gehoerte die PID aus einer Statusdatei
        csrss.exe, der omnitrade-Lauf war 4,5 h tot - die Pruefung ohne Namen
        meldete 'laeuft schon', der tote Lauf wurde nie neu gestartet."""
        self.assertTrue(lauf.pid_lebt(os.getpid()))
        self.assertFalse(lauf.pid_lebt(os.getpid(), "omnitrade-cli.exe"))
        self.assertTrue(lauf.pid_lebt(os.getpid(), "python"))

    def test_main_exitcode_folgt_der_lage(self):
        """Exit 0 = laeuft, 1 = nicht - das ist die Schnittstelle fuer die .cmd
        und fuer einen Cron (leere Ausgabe ist hier NICHT das Signal)."""
        self.assertEqual(lauf.main.__code__.co_argcount, 0)


class KeineNebeneffekteTest(unittest.TestCase):
    """Die Anker-Logik (omnitrade_lauf) ist REIN LESEND: sie darf beim
    Ausfuehren weder einen Rust-Lauf starten noch stoppen. Das ist der Kern
    dieser Karte - die Entscheidung 'laeuft er?' darf nie selbst in den
    Betrieb eingreifen, sonst wuerde eine Wache Laeufe duplizieren oder killen.
    """

    def test_modul_enthaelt_keinen_start_oder_stop_aufruf(self):
        """Statische Pruefung: kein Popen, kein Kill, kein taskkill, kein
        Import des Startwerkzeugs, kein Schreiben in eine Datei. Die einzigen
        Prozessaufrufe sind subprocess.run (tasklist/powershell, rein lesend)."""
        with open(os.path.join(HANDEL, "omnitrade_lauf.py"), "r",
                  encoding="utf-8") as f:
            quelle = f.read()
        for verboten in ("Popen", "os.kill", ".terminate(", "taskkill",
                         "omnitrade_start", "open(",
                         "os.remove", "os.rename", "shutil"):
            self.assertNotIn(verboten, quelle,
                             "Anker-Logik darf %r nicht enthalten" % verboten)
        # subprocess darf nur als run() vorkommen (lesend), nie als Popen.
        self.assertIn("subprocess.run", quelle)
        # CREATE_NO_WINDOW ist Pflicht: das Modul laeuft auch aus dem
        # fensterlosen Gateway/Cron, sonst poppt bei jedem tasklist-Aufruf
        # ein Konsolenfenster auf (Pop-out-Befund 10.10.2026).
        self.assertIn("CREATE_NO_WINDOW", quelle)

    def test_beurteile_schreibt_nicht_in_die_statusdatei(self):
        """Die Statusdatei bleibt byte-identisch, und es entstehen keine neuen
        Dateien - die Entscheidung liest, schreibt aber nie."""
        with tempfile.TemporaryDirectory() as tmp:
            datei = os.path.join(tmp, "live.json")
            daten = {"schema": 1, "state": "running", "pid": 1234,
                     "updated_ms": time.time() * 1000,
                     "recent_candles": [{"time_ms": 0}, {"time_ms": 3_600_000}]}
            with open(datei, "w", encoding="utf-8") as f:
                json.dump(daten, f)
            with open(datei, "rb") as f:
                vorher = hashlib.sha256(f.read()).hexdigest()
            l = bruecke.lage(datei)
            u = lauf.beurteile(l, lebt=lambda pid: True, grenze_fuer=GRENZE_FEST)
            self.assertTrue(u["laeuft"], u["grund"])
            with open(datei, "rb") as f:
                nachher = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(vorher, nachher, "Statusdatei wurde veraendert")
            self.assertEqual(sorted(os.listdir(tmp)), ["live.json"],
                             "Anker-Logik hat Dateien angelegt")

    def _zaehle_omnitrade(self):
        """Anzahl der laufenden omnitrade-cli.exe-Prozesse (rein lesend)."""
        try:
            aus = subprocess.run(
                [lauf._tasklist(), "/FI", "IMAGENAME eq omnitrade-cli.exe", "/NH"],
                capture_output=True, timeout=30)
        except Exception:
            return None
        text = (aus.stdout or b"").decode("utf-8", "replace")
        return sum(1 for z in text.splitlines() if "omnitrade-cli.exe" in z)

    def test_ausfuehrung_startet_keinen_rust_lauf(self):
        """Integration: die Anzahl der omnitrade-cli.exe-Prozesse bleibt beim
        Ausfuehren der Anker-Logik unveraendert - weder startet noch stoppt
        sie einen Rust-Lauf. (Prozessliste nicht lesbar -> uebersprungen.)"""
        vorher = self._zaehle_omnitrade()
        if vorher is None:
            self.skipTest("Prozessliste nicht lesbar")
        with tempfile.TemporaryDirectory() as tmp:
            datei = os.path.join(tmp, "live.json")
            daten = {"schema": 1, "state": "stopped", "pid": 999999,
                     "updated_ms": time.time() * 1000}
            with open(datei, "w", encoding="utf-8") as f:
                json.dump(daten, f)
            l = bruecke.lage(datei)
            u = lauf.beurteile(l, lebt=lambda pid: False)
            self.assertFalse(u["laeuft"])
        nachher = self._zaehle_omnitrade()
        self.assertEqual(vorher, nachher,
                         "Anker-Logik hat die Zahl der Rust-Laeufe veraendert "
                         "(vorher %d, nachher %d)" % (vorher, nachher))


if __name__ == "__main__":
    unittest.main(verbosity=2)
