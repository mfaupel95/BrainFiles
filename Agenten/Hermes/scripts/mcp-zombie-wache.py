#!/usr/bin/env python3
"""Wache auf die MCP-Server-Prozesse (Zombie-Vielfachheit / Commit-Druck).

WARUM: Am 29.09.2026 hat ein Rechner mit scheinbar gesunder CPU (12 %) und viel
freiem RAM trotzdem gequetscht - der virtuelle Speicher (Commit) war auf 1,3 GB
von 87,7 GB geschrumpft. Verursacher: ~200 verwaiste MCP-Server-Prozesse
(44 x mail, 42 x windows-mcp, 42 x kraken, 38 x archiv, 38 x tooluniverse,
14 x blender - je Server sollte ~2 laufen). Die MCP-Server spawnen sich
gegenseitig (Config liest jeden Server als Client der uebrigen), und seit dem
Boot (99 h) ist jede Vielfachheit unbegrenzt nachgewachsen. Folge: Commit-Druck
-> WinError 1455, SIGTERM-Wellen, lokaler Modell-Rueckfall wertlos.

Diese Wache ist die zweite Netzhaut. Anders als die moondev-Wache RAeUMT sie
selbst auf (nachweislich harmlos, 29.09.2026: 200 Prozesse gekillt, 1,3 ->
15,9 GB Commit frei, alle realen Clients haben danach neu gespawnt). Sie
behaelt je Server-Gruppe die BEHALTEN_JE_GRUPPE juengsten Prozesse (die aktuell
angebundenen) und killt den Rest.

MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts senden):
  - eine MCP-Server-Gruppe ueber MAX_JE_GRUPPE -> auf BEHALTEN_JE_GRUPPE kuerzen,
  - MCP-Server gesamt ueber MAX_GESAMT -> auf BEHALTEN_JE_GRUPPE je Gruppe kuerzen,
  - freies Commit unter MIN_COMMIT_MB (reiner Bericht, kein Auto-Kill),
  - Ueberlauf UND Docker tot UND MCP_DOCKER in der Config -> die URSACHE benennen.

NACHTRAG 30.09.2026: dieselbe Erschoepfung noch einmal, mit anderer Ursache. Der
Docker-Daemon war tot, der Gateway-Abgleich wollte trotzdem MCP_DOCKER starten,
und bei JEDEM Versuch startete er daraufhin ALLE sechs Gruppen neu - 146
Python-Prozesse, 1,0 GB Commit frei, WSL-VM tot, Docker tot: ein geschlossener
Kreis, den das Killen allein nicht oeffnen konnte. Zwei Fehler dieser Wache
wurden dabei gefunden:

  1. _killen() gab die noch LEBENDEN zurueck, der Aufrufer nannte sie 'tote'.
     Ein gelungener Kill wurde also als 'Auto-Kill fehlgeschlagen' gemeldet.
  2. Die Nachpruefung fragte PowerShell EINMAL JE PID - bei 130 Prozessen
     dauerte das Minuten.

Beides ist behoben; zusaetzlich nennt die Meldung jetzt die Ursache.

NIEMALS anfassen: Handels-Dauerlauf, MoonDev-Agenten, Gateway, SkillsBot,
Ollama, Bonsai - die Wache filtert hart auf 'MCP-Server' in der Kommandozeile.

Aufruf (Hermes-Cron, no_agent, alle 15 Minuten):
    python mcp-zombie-wache.py
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
import os

MAX_JE_GRUPPE = 6          # je Server-Gruppe; Normalbetrieb 1-3 je Client
GESAMT = 24                # MCP-Server gesamt
BEHALTEN_JE_GRUPPE = 3     # die 3 juengsten bleiben (aktiv angebundene)
MIN_COMMIT_MB = 5000       # darunter klemmt der naechste Modellstart

# Gruppe <-> Marker: Gruppe ueber eines dieser Marker-Substrings erkannt.
MARKER = {
    "mail":        "mail_mcp.py",
    "kraken":      "kraken_mcp.py",
    "archiv":      "archiv_mcp.py",
    "tooluniverse": "run_stdio.py",
    "windows-mcp": "windows_mcp",
    "blender":     "blmcp",
}

# Die Hermes-Config liegt eine Ebene ueber scripts/. Sie wird NUR gelesen
# (steht MCP_DOCKER drin?), nie geschrieben.
CONFIG = Path(__file__).resolve().parents[1] / "config.yaml"


def _powershell(skript: str) -> str | None:
    """PowerShell-Aufruf. None = der Aufruf ist GESCHEITERT (kein Ergebnis).

    Der Unterschied ist wichtig: unter Commit-Druck startet PowerShell selbst
    nicht mehr. Wer 'kein Ergebnis' als 'nichts gefunden' liest, meldet einen
    erfundenen Erfolg - genau das war am 30.09.2026 der Fall.
    """
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
            capture_output=True, text=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:                              # noqa: BLE001
        return None
    return (p.stdout or "").strip()


def _prozesse_json() -> str:
    return _powershell(
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR "
        "Name='pythonw.exe'\" | Select-Object ProcessId,CommandLine,CreationDate "
        "| ConvertTo-Json -Compress") or ""


def _alter_bool(roh: str) -> float:
    ziffern = "".join(c for c in (roh or "") if c.isdigit())
    if not ziffern:
        return 1e9
    try:
        stamp = dt.datetime.fromtimestamp(int(ziffern) / 1000.0)
    except (ValueError, OSError, OverflowError):
        return 1e9
    return max(0.0, (dt.datetime.now() - stamp).total_seconds())


def _gruppe(cmd: str) -> str | None:
    for g, m in MARKER.items():
        if m in cmd:
            return g
    return None


def _commit_frei_mb() -> int:
    roh = _powershell("$o=Get-CimInstance Win32_OperatingSystem; "
                      "[int]($o.FreeVirtualMemory/1KB)")
    try:
        return int(roh) if roh else 0
    except (ValueError, TypeError):
        return 0


def _lebende(ids: list) -> set | None:
    """Welche dieser PIDs leben noch? EIN Aufruf fuer alle.

    Vorher wurde je PID einzeln gefragt: bei 130 Prozessen dauerte allein die
    Nachpruefung Minuten, und die Wache lief in den naechsten Takt hinein.
    None = nicht feststellbar (NICHT 'alle tot').
    """
    if not ids:
        return set()
    liste = ",".join(str(i) for i in ids)
    roh = _powershell("Get-Process -Id %s -ErrorAction SilentlyContinue | "
                      "ForEach-Object { $_.Id }" % liste)
    if roh is None:
        return None
    return {int(z) for z in roh.split() if z.strip().isdigit()}


def _killen(ids: list) -> list | None:
    """Beendet PIDs per Stop-Process -Force (nativ; taskkill aus subprocess tut
    auf diesem Windows still nichts).

    Liefert die TATSAECHLICH beendeten - oder None, wenn das nicht feststellbar
    war. FEHLER bis 30.09.2026: die Funktion gab die noch LEBENDEN zurueck, der
    Aufrufer nannte sie 'tote'. Folge: ein gelungener Kill wurde als
    'Auto-Kill fehlgeschlagen' gemeldet, und die Zahl der Gekillten war 1 statt
    130. Eine Wache, deren Meldung das Gegenteil sagt, ist schlimmer als keine.
    """
    if not ids:
        return []
    body = ";".join("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % i
                    for i in ids)
    _powershell(body + "; Start-Sleep -Seconds 2")
    noch_da = _lebende(ids)
    if noch_da is None:
        return None
    return [i for i in ids if i not in noch_da]


def _mcp_docker_konfiguriert() -> bool:
    try:
        return "MCP_DOCKER" in CONFIG.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def _docker_laeuft() -> bool | None:
    """True/False; None = nicht feststellbar (kein Docker auf diesem Rechner)."""
    try:
        p = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"],
                           capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:                              # noqa: BLE001
        return None
    return bool((p.stdout or "").strip()) and p.returncode == 0


def _kreis_erkannt(gruppen: dict) -> bool:
    """T-200 ABBRUCH-IDEMPOTENZ: ``True`` wenn der MCP_DOCKER-Abgleichkreis geschlossen ist.

    Kreis = Docker-Daemon tot UND ``MCP_DOCKER`` in der Config UND eine MCP-Gruppe ueber
    MAX_JE_GRUPPE. In diesem Zustand startet der Gateway-Abgleich bei JEDEM Versuch alle
    Gruppen neu - die Wache darf NICHT nur die Ueberzahl killen und drei 'lebende' behalten,
    denn diese drei gelten dem Abgleich als bedient und naehren das Wiederhochspawnen: jede
    Runde killt die Wache neu, der Abgleich spawnt neu, eine Ping-Pong-Schleife ohne Ende.
    Die Abbruch-Idempotenz ist das Kuerzen auf ZERO (statt BEHALTEN_JE_GRUPPE): bleibt in dem
    Zustand kein MCP-Server uebrig, den der Abgleich als laufend ansehen kann, konvergiert der
    naechste Zyklus - derselbe Zustand fuehrt zur selben (leeren) Ende-Sicht, nicht zu neuem
    Killen. Das Killen aller Gruppen unter Kreis ist nachweislich harmlos (30.09.2026: der
    Abgleich spawnt reale Kunden von selbst wieder), Docker selbst wird nicht angetastet.
    """
    if _docker_laeuft() is not False:
        return False
    if not _mcp_docker_konfiguriert():
        return False
    return any(len(pros) > MAX_JE_GRUPPE for pros in gruppen.values())


def main() -> int:
    if sys.platform != "win32":
        return 0
    roh = _prozesse_json()
    if not roh:
        return 0
    try:
        daten = json.loads(roh)
    except ValueError:
        return 0
    eintraege = [daten] if isinstance(daten, dict) else daten

    gruppen: dict[str, list] = {}
    gesamt = 0
    for e in eintraege:
        cmd = e.get("CommandLine") or ""
        if "MCP-Server" not in cmd:
            continue
        g = _gruppe(cmd)
        if not g:
            continue
        gruppen.setdefault(g, []).append({
            "pid": e.get("ProcessId"),
            "alter": _alter_bool(e.get("CreationDate")),
        })
        gesamt += 1

    commit = _commit_frei_mb()
    kreis = _kreis_erkannt(gruppen)   # T-200: Docker tot + MCP_DOCKER + Ueberlauf
    ueber_je = {g: pros for g, pros in gruppen.items() if len(pros) > MAX_JE_GRUPPE}
    ueber_ges = gesamt > GESAMT

    gekillt: list[tuple[str, int]] = []
    unklar = False
    # Aufraeumen: jede Gruppe mit Ueberlauf auf BEHALTEN_JE_GRUPPE juengste kuerzen.
    # Unter dem T-200-Abgleichkreis aber auf ZERO: drei 'lebende' wuerden der Endlos-
    # Reconciliation als bedient gelten und das Wiederhochspawnen naehren (Ping-Pong).
    if kreis:
        for g, pros in gruppen.items():
            kill_ids = [p["pid"] for p in pros if p["pid"]]
            beendet = _killen(kill_ids)
            if beendet is None:
                unklar = True
                continue
            for p in pros:
                if p["pid"] in beendet:
                    gekillt.append((g, p["pid"]))
    else:
        ziel_gruppen = set(ueber_je.keys()) if ueber_je else set()
        if ueber_ges:
            ziel_gruppen |= set(gruppen.keys())
        if ziel_gruppen:
            for g in ziel_gruppen:
                pros = gruppen[g]
                nach_alter = sorted(pros, key=lambda x: x["alter"])  # juengste zuerst
                ueberschuss = nach_alter[BEHALTEN_JE_GRUPPE:]
                kill_ids = [p["pid"] for p in ueberschuss if p["pid"]]
                beendet = _killen(kill_ids)
                if beendet is None:
                    unklar = True
                    continue
                for p in nach_alter:
                    if p["pid"] in beendet:
                        gekillt.append((g, p["pid"]))

    grund = []
    if kreis:
        gruppiert: dict[str, int] = {}
        for g, _ in gekillt:
            gruppiert[g] = gruppiert.get(g, 0) + 1
        grund.append("MCP_DOCKER-ABGLEICHKREIS aufgebrochen: alle %d MCP-Server beendet "
                     "(Docker tot + MCP_DOCKER in der Config), Gruppen: %s"
                     % (len(gekillt), ", ".join("%s=%d" % (g, k) for g, k in
                                                sorted(gruppiert.items(), key=lambda x: -x[1]))))
        if unklar:
            grund.append("der Kill liess sich NICHT nachpruefen (PowerShell antwortet nicht) - "
                         "der Kreis ist dann nicht sicher aufgebrochen")
    elif gekillt:
        gruppiert: dict[str, int] = {}
        for g, _ in gekillt:
            gruppiert[g] = gruppiert.get(g, 0) + 1
        grund.append("MCP-Zombies gekillt (%d Prozesse auf je %d gekuerzt): %s"
                     % (len(gekillt), BEHALTEN_JE_GRUPPE,
                        ", ".join("%s=%d" % (g, k) for g, k in
                                  sorted(gruppiert.items(), key=lambda x: -x[1]))))
        if ueber_je:
            rest = ", ".join("%s=%d" % (g, len(p)) for g, p in ueber_je.items())
            grund.append("Gruppen ueber MAX_JE_GRUPPE waren: %s" % rest)
    elif unklar:
        grund.append("MCP-Server-Gruppen ueber Grenze, der Kill liess sich NICHT "
                     "nachpruefen (PowerShell antwortet nicht): %s"
                     % ", ".join("%s=%d" % (g, len(p)) for g, p in ueber_je.items()))
    elif ueber_je:
        grund.append("MCP-Server-Gruppen ueber Grenze, Kill hat nicht gegriffen: %s"
                     % ", ".join("%s=%d" % (g, len(p)) for g, p in ueber_je.items()))
    elif ueber_ges:
        grund.append("MCP-Server gesamt %d ueber Grenze %d, Kill hat nicht gegriffen"
                     % (gesamt, GESAMT))

    if commit and commit < MIN_COMMIT_MB and not gekillt:
        grund.append("freies Commit nur %d MB - der naechste lokale Modellstart "
                     "scheitert" % commit)

    # Die URSACHE nennen, nicht nur die Zahl. Am 30.09.2026 stand der Rechner bei
    # 1,0 GB Commit, weil ein einziger MCP-Server nicht starten konnte; die Wache
    # meldete damals nur 'Auto-Kill fehlgeschlagen' und schwieg zur Ursache. Wer
    # das liest, kann den Sturm nicht beenden - er killt und killt.
    if (ueber_je or ueber_ges) and _mcp_docker_konfiguriert() and _docker_laeuft() is False:
        grund.append("URSACHE: der Docker-Daemon antwortet nicht, aber MCP_DOCKER steht in "
                     "der Config. Der Abgleich des Gateways startet daraufhin bei JEDEM "
                     "Versuch alle Gruppen neu - Killen allein kann den Sturm nicht "
                     "beenden. Docker starten (oder MCP_DOCKER austragen), dann hoert es auf.")

    if not grund:
        return 0

    print("MCP-Zombie-Wache " + dt.datetime.now().strftime("%d.%m. %H:%M"))
    for g in grund:
        print("  - " + g)
    if commit:
        print("  freies Commit: %d MB" % commit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
