#!/usr/bin/env python3
"""Tests fuer die Stillstands-Pruefung der MoonDev-Agentenwache (01.10.2026).

Anlass: Der kraken_agent lief als Prozess weiter und schrieb 31 Stunden keine
Zeile. Die Wache hat bisher nur Prozesszahl und Commit-Limit geprueft - ein
haengender Agent war von aussen unsichtbar.

Die Tests arbeiten auf Temp-Ordnern und biegen `LOG_ORDNER` und `MERK` um: eine
Wache, die im Test die echte Merkdatei schreibt, macht die naechste echte
Meldung stumm.

Aufruf aus diesem Ordner:
    python -m unittest test_moondev_agenten_wache
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))


def _lade():
    pfad = os.path.join(HIER, "moondev-agenten-wache.py")
    spec = importlib.util.spec_from_file_location("moondev_agenten_wache", pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["moondev_agenten_wache"] = modul
    spec.loader.exec_module(modul)
    return modul


WACHE = _lade()


def _prozess(cmd, name="python.exe"):
    """Prozessattrappe. Der Name gehoert dazu - die Wache prueft ihn."""
    return {"Name": name, "CommandLine": cmd}


class StillstandsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_log = WACHE.LOG_ORDNER
        self.alt_merk = WACHE.MERK
        WACHE.LOG_ORDNER = self.tmp.name
        WACHE.MERK = os.path.join(self.tmp.name, "merk.json")

    def tearDown(self):
        WACHE.LOG_ORDNER = self.alt_log
        WACHE.MERK = self.alt_merk
        self.tmp.cleanup()

    def _log(self, name, minuten_alt):
        pfad = os.path.join(self.tmp.name, "moondev_%s.log" % name)
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("eine Zeile\n")
        wenn = time.time() - minuten_alt * 60
        os.utime(pfad, (wenn, wenn))
        return pfad

    def test_frisches_log_ist_kein_befund(self):
        self._log("kraken", 5)
        self.assertEqual(WACHE.stillstand({"kraken": _prozess("x")}), [])

    def test_altes_log_ist_ein_befund(self):
        self._log("kraken", 1857)
        befunde = WACHE.stillstand({"kraken": _prozess("x")})
        self.assertEqual(len(befunde), 1)
        self.assertIn("kraken", befunde[0])
        self.assertIn("1857", befunde[0])

    def test_fehlendes_log_ist_kein_befund(self):
        # Nicht jeder Agent schreibt ein Log - ein fehlendes Log ist kein Hang.
        self.assertEqual(WACHE.stillstand({"ohne_log": _prozess("x")}), [])

    def test_dieselbe_feststellung_wird_nicht_wiederholt(self):
        self._log("kraken", 200)
        self.assertEqual(len(WACHE.stillstand({"kraken": _prozess("x")})), 1)
        self.assertEqual(WACHE.stillstand({"kraken": _prozess("x")}), [])

    def test_erholung_loescht_den_merker(self):
        self._log("kraken", 200)
        WACHE.stillstand({"kraken": _prozess("x")})
        # Der Agent schreibt wieder: Merker weg, und eine SPAETERE Stoerung
        # wird sofort gemeldet (nicht erst nach MERK_H).
        self._log("kraken", 1)
        WACHE.stillstand({"kraken": _prozess("x")})
        self._log("kraken", 200)
        self.assertEqual(len(WACHE.stillstand({"kraken": _prozess("x")})), 1)

    def test_grenze_genau_bei_still_min(self):
        self._log("kraken", WACHE.STILL_MIN - 1)
        self.assertEqual(WACHE.stillstand({"kraken": _prozess("x")}), [])
        self._log("kraken", WACHE.STILL_MIN + 1)
        self.assertEqual(len(WACHE.stillstand({"kraken": _prozess("x")})), 1)


class NamensTest(unittest.TestCase):
    def test_kraken_wird_zu_kraken(self):
        namen = WACHE.agenten_namen([
            _prozess(r"C:\x\.venv\Scripts\python.exe O:\repo\src\agents\kraken_agent.py")])
        self.assertEqual(list(namen), ["kraken"])

    def test_unterstrich_name_wird_gekuerzt(self):
        # Der Logname des Treibers ist moondev_new_or_top.log - ohne "_agent".
        namen = WACHE.agenten_namen([
            _prozess(r".venv\Scripts\python.exe O:\repo\src\agents\new_or_top_agent.py")])
        self.assertEqual(list(namen), ["new_or_top"])

    def test_die_eigene_suche_zaehlt_nicht(self):
        """Der Entdecker darf nicht die eigene Suche finden.

        Eine tasklist-Abfrage mit "kraken_agent.py" im Suchtext traegt denselben
        Text in der Kommandozeile - und sah in der ersten Fassung der Wache wie
        ein Agent aus (gemessen 21.09.2026: kraken=5 statt 2). Der Prozessname
        muss deshalb python.exe oder pythonw.exe sein.
        """
        namen = WACHE.agenten_namen([
            _prozess("python -m http.server"),
            _prozess(r"C:\Tools\tasklist.exe /FI kraken_agent.py", name="tasklist.exe"),
            _prozess(r"C:\Windows\System32\powershell.exe -Command Get-CimInstance kraken_agent.py",
                     name="powershell.exe"),
        ])
        self.assertEqual(namen, {})

    def test_mehrere_prozesse_eines_agenten_ergeben_einen_namen(self):
        namen = WACHE.agenten_namen([
            _prozess(r".venv\Scripts\python.exe O:\repo\src\agents\sniper_agent.py"),
            _prozess(r".venv\Scripts\python.exe O:\repo\src\agents\sniper_agent.py")])
        self.assertEqual(list(namen), ["sniper"])


if __name__ == "__main__":
    unittest.main()