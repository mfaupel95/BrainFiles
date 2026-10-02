"""Eine PID gilt nur als lebender Prozess, wenn der NAME auch stimmt.

Anlass (03.10.2026, gemessen): `atlas-watcher.py` pruefte mit
`tasklist /FI "PID eq n" /NH` nur, ob die ZAHL irgendwo in der Antwort
stand. Windows vergibt PIDs neu - die PID-Datei des Atlas-Watchers nannte
69928, ein toter Watcher, und 69928 war inzwischen `svchost.exe`:

    projectatlas.exe             96060 Console  1  29.208 K   <- der echte
    svchost.exe                  69928 Services 0  15.988 K   <- die tote PID

Der Waechter erkannte 69928 als lebenden Watcher, rief deshalb nie das
Startskript auf ... und haette trotzdem gemeldet. In der Praxis umgekehrt:
weil die PID-Datei nach einem Neustart nicht mehr beschrieben wurde (der
Start braucht laenger als die 8 s Wartezeit in watch-start.ps1), startete
der Waechter bei JEDEM Lauf neu - 18 haengende Projektionsprozesse mit je
~1 MB, waehrend der echte Watcher (9705 s CPU) nebenbei Arbeit tat.

Die Regel ist dieselbe wie bei `omnitrade_lauf.pid_lebt(pid, name=...)`:
eine lebende PID ist kein Beleg fuer einen lebenden Prozess. Der Test
faehrt beide Richtungen - die richtige PID mit richtigem Namen UND die
richtige Zahl, die einem fremden Prozess gehoert.

Ohne Netz, ohne echten Start: nur `tasklist` wird als Seam gebogen.
"""

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "atlas-watcher.py"      # liegt im SELBEN Ordner


def _modul():
    s = importlib.util.spec_from_file_location("atlas_watcher_test", str(ZIEL))
    m = importlib.util.module_from_spec(s)
    sys.modules[s.name] = m
    s.loader.exec_module(m)
    return m


class PidUndNameTest(unittest.TestCase):
    """prozess_laeuft() verlangt PID UND Programmname."""

    def setUp(self):
        self.m = _modul()
        self.alt_run = self.m.subprocess.run
        self.rufe = []

    def tearDown(self):
        self.m.subprocess.run = self.alt_run

    def _tasklist(self, ausgabe):
        """tasklist beantworten, ohne den echten Prozess zu beruehren."""
        def fake(cmd, *a, **k):
            self.rufe.append(cmd)
            class R:
                stdout = ausgabe
                stderr = ""
                returncode = 0
            return R()
        self.m.subprocess.run = fake

    def test_echte_pid_mit_richtigem_namen(self):
        self._tasklist("projectatlas.exe             96060 Console"
                       "                    1      29.208 K\r\n")
        self.assertTrue(self.m.prozess_laeuft(96060))

    def test_pid_eines_fremden_prozesses_gilt_nicht(self):
        # GENAU der gemessene Fehlerfall: die Zahl steht in der Antwort,
        # der Prozess ist aber nicht der gesuchte.
        self._tasklist("svchost.exe                  69928 Services"
                       "                    0      15.988 K\r\n")
        self.assertFalse(self.m.prozess_laeuft(69928),
                         "eine PID-Wiederverwendung wurde als Watcher "
                         "gezaehlt")

    def test_falscher_name_bei_richtiger_pid(self):
        self._tasklist("python.exe                    96060 Console"
                       "                    1       1.000 K\r\n")
        self.assertFalse(self.m.prozess_laeuft(96060))

    def test_freie_pid(self):
        self._tasklist("INFORMATION: Es werden keine Aufgaben mit den"
                       " angegebenen Kriterien ausgefuehrt.\r\n")
        self.assertFalse(self.m.prozess_laeuft(99999))

    def test_keine_pid(self):
        self._tasklist("")
        self.assertFalse(self.m.prozess_laeuft(None))
        self.assertFalse(self.m.prozess_laeuft(0))

    def test_ohne_namenspruefung_waere_der_fremde_fall_gruen(self):
        """Gegenprobe: die alte Logik (`Zahl in der Antwort`) ist falsch."""
        self._tasklist("svchost.exe                  69928 Services"
                       "                    0      15.988 K\r\n")
        alt = "69928" in "svchost.exe 69928 Services 0 15.988 K"
        self.assertTrue(alt, "die alte Logik haette den Fehler nicht gefunden")
        self.assertFalse(self.m.prozess_laeuft(69928))

    def test_erwarteter_name_ist_der_watcher(self):
        self.assertEqual(self.m.ERWARTETER_NAME.lower(),
                         "projectatlas.exe")


class StartskriptTest(unittest.TestCase):
    """watch-start.ps1 prueft den Prozessnamen - als TEXT, nicht ausgefuehrt."""

    def setUp(self):
        # Der Pfad gehoert aus dem Modul selbst, nicht geraten: das Skript
        # liegt in Agenten\Werkzeuge\projectatlas, der Test in
        # Agenten\Hermes\scripts - HIER.parent waere Agenten\Hermes.
        self.ps1 = (_modul().START).read_text(encoding="utf-8")

    def test_namenspruefung_im_startskript(self):
        self.assertIn("ProcessName -eq 'projectatlas'", self.ps1)

    def test_es_steht_da_und_dort_die_bloede_pid_allein_geprueft_wird(self):
        # Die Zeile, die den Fehler verursachte, darf nicht mehr allein stehen.
        self.assertNotIn("if ($alt -and (Get-Process -Id $alt -ErrorAction "
                         "SilentlyContinue)) {", self.ps1)


if __name__ == "__main__":
    unittest.main()