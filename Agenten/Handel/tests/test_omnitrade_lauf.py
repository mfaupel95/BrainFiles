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

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import omnitrade_lauf as lauf  # noqa: E402


def lage(state="running", pid=1234, alter=5.0, ok=True, fehler=""):
    return {"ok": ok, "state": state, "pid": pid, "alter_s": alter, "fehler": fehler}


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
        u = lauf.beurteile(lage=lage(alter=lauf.ALT_GRENZE_S + 1), lebt=lambda pid: True)
        self.assertFalse(u["laeuft"])
        self.assertIn("alt", u["grund"])

    def test_grenze_ist_nicht_ueberschritten(self):
        u = lauf.beurteile(lage=lage(alter=lauf.ALT_GRENZE_S), lebt=lambda pid: True)
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

    def test_main_exitcode_folgt_der_lage(self):
        """Exit 0 = laeuft, 1 = nicht - das ist die Schnittstelle fuer die .cmd
        und fuer einen Cron (leere Ausgabe ist hier NICHT das Signal)."""
        self.assertEqual(lauf.main.__code__.co_argcount, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)