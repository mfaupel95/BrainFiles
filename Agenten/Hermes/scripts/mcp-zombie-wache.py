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
  - freies Commit unter MIN_COMMIT_MB (reiner Bericht, kein Auto-Kill).

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


def _powershell(skript: str) -> str:
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
            capture_output=True, text=True, timeout=90)
    except Exception:                              # noqa: BLE001
        return ""
    return (p.stdout or "").strip()


def _prozesse_json() -> str:
    return _powershell(
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR "
        "Name='pythonw.exe'\" | Select-Object ProcessId,CommandLine,CreationDate "
        "| ConvertTo-Json -Compress")


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


def _killen(ids: list) -> list:
    """Beendet PIDs per Stop-Process -Force (nativ; taskkill aus subprocess
    tut auf diesem Windows still nichts). Liefert die tatsaechlich beendeten."""
    if not ids:
        return []
    body = ";".join("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % i
                    for i in ids)
    _powershell(body + "; Start-Sleep -Seconds 2")
    # nachpruefen (ruhender Zustand): noch da?
    return [i for i in ids if _pid_lebt(i)]


def _pid_lebt(pid: int) -> bool:
    roh = _powershell(
        "if(Get-Process -Id %d -ErrorAction SilentlyContinue){'ja'}" % pid)
    return roh == "ja"


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
    ueber_je = {g: pros for g, pros in gruppen.items() if len(pros) > MAX_JE_GRUPPE}
    ueber_ges = gesamt > GESAMT

    gekillt: list[tuple[str, int]] = []
    # Aufraeumen: jede Gruppe mit Ueberlauf auf BEHALTEN_JE_GRUPPE juengste kuerzen
    ziel_gruppen = set(ueber_je.keys()) if ueber_je else set()
    if ueber_ges:
        ziel_gruppen |= set(gruppen.keys())
    if ziel_gruppen:
        for g in ziel_gruppen:
            pros = gruppen[g]
            nach_alter = sorted(pros, key=lambda x: x["alter"])  # juengste zuerst
            ueberschuss = nach_alter[BEHALTEN_JE_GRUPPE:]
            kill_ids = [p["pid"] for p in ueberschuss if p["pid"]]
            tote = _killen(kill_ids)
            for p in nach_alter:
                if p["pid"] in tote:
                    gekillt.append((g, p["pid"]))

    grund = []
    if gekillt:
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
    elif ueber_je:
        grund.append("MCP-Server-Gruppen ueber Grenze (Auto-Kill fehlgeschlagen): %s"
                     % ", ".join("%s=%d" % (g, len(p)) for g, p in ueber_je.items()))
    elif ueber_ges:
        grund.append("MCP-Server gesamt %d ueber Grenze %d (Auto-Kill fehlgeschlagen)"
                     % (gesamt, GESAMT))

    if commit and commit < MIN_COMMIT_MB and not gekillt:
        grund.append("freies Commit nur %d MB - der naechste lokale Modellstart "
                     "scheitert" % commit)

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
