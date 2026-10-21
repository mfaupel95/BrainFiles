#!/usr/bin/env python3
"""Tests fuer die MCP-Zombie-Wache.

Warum es diese Datei gibt: am 30.09.2026 hat die Wache einen Spawn-Sturm
gemeldet, aber ihre Meldung war das GEGENTEIL der Wahrheit - ein gelungener Kill
stand als "Auto-Kill fehlgeschlagen" im Text, und die Ursache (toter
Docker-Daemon) fehlte ganz. Geprueft werden deshalb REGELN:

  1. Wurde wirklich gekillt, darf die Meldung nicht 'fehlgeschlagen' sagen.
  2. Liess sich der Kill nicht nachpruefen, darf kein Erfolg erfunden werden.
  3. Bei Ueberlauf + totem Docker + MCP_DOCKER in der Config muss die URSACHE
     im Text stehen - sonst kann der Leser den Sturm nicht beenden.
  4. Ist alles im Rahmen, kommt NICHTS (das ist der Normalfall alle 15 Minuten).

Die Wache wird nicht nachgebaut, sondern geladen und mit einer erfundenen
Prozesstabelle gefuettert; nur _powershell ist gefaelscht. So laeuft der echte
_killen/_lebende-Code mit.

HINWEIS: Diese Datei lag am 30.09.2026 um 02:42 schon einmal fertig da und war
um 02:45 wieder weg - eine parallele Sitzung arbeitet im selben Ordner und hat
untracked Dateien weggeraeumt. Sofort nach dem Schreiben stagen.
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]          # BrainFiles - kein fester Benutzerpfad
SPEC = importlib.util.spec_from_file_location(
    "mcp_zombie_wache", HIER / "mcp-zombie-wache.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)
ECHT_DOCKER_LAEUFT = w._docker_laeuft   # unveraendert gesichert: BasisTest.lauf ersetzt global (Test-Isolation)


class Fake:
    """Erfundener Rechner: Prozesstabelle, Commit, Docker-Zustand."""

    def __init__(self, gruppen=None, commit_mb=8000, sterben=True):
        self.prozesse = []
        pid = 2000
        marker = dict(w.MARKER)
        marker.update(w.NODE_MARKER)
        for g, anzahl in (gruppen or {}).items():
            for _ in range(anzahl):
                pid += 1
                self.prozesse.append({
                    "ProcessId": pid,
                    "CommandLine": str(WURZEL / "Agenten" / "MCP-Server" / g /
                                       ".venv" / "Scripts" / "python.exe") + " " + marker[g],
                    "CreationDate": "/Date(1759100000000)/",
                })
        self.commit_mb = commit_mb
        self.sterben = sterben
        self.ps_aufrufe = []

    def powershell(self, skript: str) -> str | None:
        self.ps_aufrufe.append(skript)
        if "Get-CimInstance Win32_Process" in skript:
            return json.dumps(self.prozesse)
        if "FreeVirtualMemory" in skript:
            return str(self.commit_mb)
        if "Stop-Process" in skript:
            if self.sterben:
                um = {int(z) for z in re.findall(r"Stop-Process -Id (\d+)", skript)}
                self.prozesse = [p for p in self.prozesse if p["ProcessId"] not in um]
            return ""
        if "Get-Process -Id" in skript:
            gefragt = {int(z) for z in re.findall(r"\d+", skript)}
            lebend = {p["ProcessId"] for p in self.prozesse} & gefragt
            return "\n".join(str(i) for i in sorted(lebend))
        return ""


class BasisTest(unittest.TestCase):
    def lauf(self, fake, docker=None, mcp_docker=True) -> str:
        w._prozesse_json = lambda: fake.powershell("Get-CimInstance Win32_Process")
        w._powershell = fake.powershell
        w._docker_laeuft = lambda: docker
        w._mcp_docker_konfiguriert = lambda: mcp_docker
        ausgabe = io.StringIO()
        with redirect_stdout(ausgabe):
            w.main()
        return ausgabe.getvalue()


class KillMeldungTest(BasisTest):
    def test_erfolgreicher_kill_heisst_nicht_fehlgeschlagen(self):
        """Der Fehler vom 30.09.2026: 'Auto-Kill fehlgeschlagen' bei Erfolg."""
        fake = Fake({"mail": 20})
        text = self.lauf(fake)
        self.assertIn("MCP-Zombies gekillt", text)
        self.assertNotIn("fehlgeschlagen", text)
        self.assertNotIn("nicht gegriffen", text)
        self.assertIn("17 Prozesse", text)
        self.assertEqual(len(fake.prozesse), 3, "genau BEHALTEN_JE_GRUPPE bleiben uebrig")

    def test_kill_der_nicht_wirkt_wird_als_solcher_gemeldet(self):
        fake = Fake({"mail": 20}, sterben=False)
        text = self.lauf(fake)
        self.assertNotIn("MCP-Zombies gekillt", text)
        self.assertIn("Kill hat nicht gegriffen", text)

    def test_unklare_nachpruefung_erfindet_keinen_erfolg(self):
        """Antwortet PowerShell nicht, ist der Ausgang UNBEKANNT - nicht gut."""
        fake = Fake({"mail": 20})
        echt = fake.powershell

        def nur_prozesse(skript):
            if "Stop-Process" in skript or "Get-Process -Id" in skript:
                return None                     # gescheiterter Aufruf
            return echt(skript)

        w._prozesse_json = lambda: nur_prozesse("Get-CimInstance Win32_Process")
        w._powershell = nur_prozesse
        w._docker_laeuft = lambda: None
        w._mcp_docker_konfiguriert = lambda: False
        ausgabe = io.StringIO()
        with redirect_stdout(ausgabe):
            w.main()
        text = ausgabe.getvalue()
        self.assertNotIn("MCP-Zombies gekillt", text)
        self.assertIn("NICHT", text)
        self.assertIn("nachpruefen", text)


class UrsacheTest(BasisTest):
    def test_toter_docker_und_mcp_docker_ergeben_ursachenzeile(self):
        text = self.lauf(Fake({"mail": 20}), docker=False, mcp_docker=True)
        self.assertIn("URSACHE", text)
        self.assertIn("Docker-Daemon", text)
        self.assertIn("MCP_DOCKER", text)

    def test_ohne_mcp_docker_in_der_config_keine_ursachenzeile(self):
        text = self.lauf(Fake({"mail": 20}), docker=False, mcp_docker=False)
        self.assertNotIn("URSACHE", text)

    def test_laufender_docker_ergibt_keine_ursachenzeile(self):
        text = self.lauf(Fake({"mail": 20}), docker=True, mcp_docker=True)
        self.assertNotIn("URSACHE", text)

    def test_ohne_ueberlauf_keine_ursachenzeile(self):
        """Ein toter Docker allein ist kein MCP-Sturm - nicht melden."""
        text = self.lauf(Fake({"mail": 2}), docker=False, mcp_docker=True)
        self.assertEqual(text, "")


class NormalbetriebTest(BasisTest):
    def test_gesunde_lage_meldet_nichts(self):
        text = self.lauf(Fake({"mail": 3, "kraken": 2, "archiv": 1}, commit_mb=20000))
        self.assertEqual(text, "")

    def test_commit_allein_unter_grenze_wird_gemeldet(self):
        text = self.lauf(Fake({"mail": 3}, commit_mb=1200))
        self.assertIn("freies Commit nur 1200 MB", text)

    def test_gesamtzahl_ueber_grenze_greift_auch_ohne_gruppenueberlauf(self):
        """Sechs Gruppen a 5 = 30 > GESAMT (24), aber keine ueber MAX_JE_GRUPPE (6)."""
        gruppen = {g: 5 for g in w.MARKER}
        text = self.lauf(Fake(gruppen))
        self.assertNotEqual(text, "")
        self.assertIn("MCP-Zombies gekillt", text)


class NodeTest(BasisTest):
    """T-424: die Wache sieht seit 05.10.2026 auch die ant.dir-NODE-MCP-Server.

    Am 05.10.2026 wuchsen 84 node-Knoten (pdf-server/desktopcommander/
    canva.affinity/revolut-x-api, je 18-24 Generationen) ungesehen, weil
    _prozesse_json nur python/pythonw filterte. Jetzt wird node.exe mitgelesen
    und je Server-Gruppe auf BEHALTEN_JE_GRUPPE gekuerzt.
    """

    def test_node_ueberlauf_wird_erkannt_und_gekuerzt(self):
        fake = Fake({"pdf-server": 20})
        text = self.lauf(fake)
        self.assertIn("MCP-Zombies gekillt", text)
        self.assertIn("pdf-server", text)
        self.assertEqual(len(fake.prozesse), 3,
                         "node-Gruppe wird wie jede andere auf BEHALTEN_JE_GRUPPE gekuerzt")

    def test_node_im_rahmen_meldet_nichts(self):
        text = self.lauf(Fake({"pdf-server": 2, "revolut-x-api": 1}, commit_mb=20000))
        self.assertEqual(text, "")

    def test_node_und_python_gemischt_zaehlen_gesamt(self):
        # 4 python-Gruppen a 5 + 1 node-Gruppe a 5 = 25 > GESAMT (24), keine ueber MAX_JE_GRUPPE.
        gruppen = {g: 5 for g in w.MARKER}
        gruppen["pdf-server"] = 5
        text = self.lauf(Fake(gruppen))
        self.assertIn("MCP-Zombies gekillt", text)


class NachpruefungTest(unittest.TestCase):
    def test_lebende_fragt_powershell_nur_einmal(self):
        """Vorher: ein Aufruf je PID - bei 130 Prozessen dauerte das Minuten."""
        fake = Fake({"mail": 20})
        w._powershell = fake.powershell
        fake.ps_aufrufe.clear()
        w._lebende([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        self.assertEqual(len(fake.ps_aufrufe), 1)

    def test_gruppenerkennung(self):
        for gruppe, marker in w.MARKER.items():
            self.assertEqual(w._gruppe(r"C:\x\MCP-Server\a\.venv\python.exe " + marker),
                             gruppe)
        for gruppe, marker in w.NODE_MARKER.items():
            self.assertEqual(
                w._gruppe(r"C:\x\MCP-Server\ant.dir.gh.owner." + marker + r"\dist\index.js"),
                gruppe)
        self.assertIsNone(w._gruppe(r"C:\x\andere\python.exe run.py"))
        self.assertIsNone(w._gruppe(r"C:\x\andere\node.exe server.js"))

    def test_docker_pruefung_ohne_docker_ist_none(self):
        """Kein Docker installiert darf nicht als 'Docker laeuft' gelten."""
        import subprocess as sp
        echt = sp.run
        # BasisTest.lauf tauscht _docker_laeuft global gegen eine Lambda aus; damit dieser
        # Test die ECHTE Funktion prueft (nicht die uebriggebliebene Stellvertreterin aus
        # einem frueheren Testlauf), ist die Ursprungsfunktion gesichert und wird zurueckgesetzt.
        w._docker_laeuft = ECHT_DOCKER_LAEUFT

        def platzt(*a, **k):
            raise FileNotFoundError("docker")

        sp.run = platzt
        try:
            self.assertIsNone(w._docker_laeuft())
        finally:
            sp.run = echt


class KreisTest(BasisTest):
    """T-200 MCP_DOCKER-Abgleichkreis: unter Docker-tot + MCP_DOCKER + Ueberlauf wird auf
    ZERO gekuerzt (nicht auf BEHALTEN_JE_GRUPPE) und die Kreislauf-Meldung kommt -
    damit konvergiert der naechste Zyklus statt weiter zu killen (Ping-Pong)."""

    def test_kreis_kuerzt_alle_gruppen_auf_zero(self):
        fake = Fake({"mail": 20, "kraken": 10})
        text = self.lauf(fake, docker=False, mcp_docker=True)
        self.assertIn("ABGLEICHKREIS", text)
        self.assertIn("aufgebrochen", text)
        self.assertEqual(fake.prozesse, [],
                         "unter Kreis bleiben KEINE Prozesse - drei 'lebende' naehren den Abgleich")
        self.assertNotIn("MCP-Zombies gekillt", text)   # eigne Meldung, nicht Symptombehandlung

    def test_kreis_ohne_ueberlauf_meldet_nichts(self):
        # Ein toter Docker + MCP_DOCKER, aber alle Gruppen im Rahmen = kein Kreis.
        text = self.lauf(Fake({"mail": 3}), docker=False, mcp_docker=True)
        self.assertEqual(text, "")

    def test_zweiter_zyklus_ist_idempotent(self):
        # Nach dem Aufbrechen ist die Prozesstabelle leer; der naechste Lauf im selben
        # Zustand darf NICHT erneut 'aufgebrochen' rufen (sonst wirkt er wie Neu-Spawning)
        # und muss ohne weitere Meldung enden, falls der Abgleich nichts nachspawnt.
        fake = Fake({"mail": 20, "kraken": 10})
        text1 = self.lauf(fake, docker=False, mcp_docker=True)
        assert "ABGLEICHKREIS" in text1 and not fake.prozesse
        text2 = self.lauf(fake, docker=False, mcp_docker=True)
        self.assertEqual(text2, "",
                         "leere Prozesstabelle unter Kreis = bereits aufgebrochen, kein neuer Kill")

    def test_kreis_bricht_auch_ohne_gruppenueberlauf_nicht_frisch_an(self):
        # Idempotenz-Falle im ersten Lauf: Zwei Gruppen gerade ueber GESAMT, aber keine ueber
        # MAX_JE_GRUPPE - das ist nur Ueberlauf, kein Docker-Kreis.
        fake = Fake({"mail": 4, "kraken": 4})
        text = self.lauf(fake, docker=False, mcp_docker=True)
        self.assertNotIn("ABGLEICHKREIS", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
