#!/usr/bin/env python3
"""Wache auf die MoonDev-Agentenprozesse und das Commit-Limit.

WARUM: Der MoonDev-Dauerlauf hat ueber Nacht (20.09. 22:17 bis 21.09. 10:00)
84 Agentenprozesse liegen lassen, 80 davon aelter als eine Stunde. Sie haben
das Windows-Commit-Limit gefuellt (1,94 GB frei von 89,8 GB) - Folge: das lokale
Modell liess sich nicht mehr laden, `git` starb im Sandbox-Terminal mit
WinError 1455, und der lokale Modell-Rueckfall der Profile war wertlos.

Seit 21.09.2026 raeumt der Treiber selbst auf (moondev_dauerlauf.aufraeumen,
taskkill /T auf den ganzen Baum). Diese Wache ist die zweite Netzhaut: sie merkt
es, wenn sich trotzdem etwas ansammelt ODER wenn das Commit-Limit eng wird -
auch dann, wenn der Treiber gerade nicht laeuft (dann raeumt niemand).

MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts senden):
  - mehr als MAX_AGENTEN Agentenprozesse,
  - weniger als MIN_COMMIT_MB freies Commit,
  - mehr als MAX_ALTE Agentenprozesse, die aelter als eine Stunde sind
    (das ist die Signatur des Leaks).

Aufruf (Hermes-Cron, no_agent, alle 15 Minuten):
    python moondev-agenten-wache.py
"""

from __future__ import annotations

import json
import subprocess
import sys

MAX_AGENTEN = 12             # 4 Agenten x Launcher+Interpreter = 8 im Normalbetrieb
MAX_ALTE = 2                 # aelter als 1 h: im Normalbetrieb laufen nur die Dauerlaeufer
MIN_COMMIT_MB = 6000         # darunter klemmt der naechste Modellstart
KENNUNG = ("src.agents", "kraken_agent.py")


def _powershell(skript: str) -> str:
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
                           capture_output=True, text=True, timeout=90)
    except Exception:                                          # noqa: BLE001
        return ""
    return (p.stdout or "").strip()


def prozesse() -> list:
    roh = _powershell(
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine } | "
        "Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress")
    if not roh:
        return []
    try:
        daten = json.loads(roh)
    except ValueError:
        return []
    return [daten] if isinstance(daten, dict) else daten


def main() -> int:
    if sys.platform != "win32":
        return 0
    alle = prozesse()
    agenten = [e for e in alle if any(k in (e.get("CommandLine") or "") for k in KENNUNG)]
    # Alter aus "/Date(ms)/"
    import datetime as dt
    alt, jung = [], 0
    for e in agenten:
        roh = str(e.get("CreationDate") or "")
        ziffern = "".join(c for c in roh if c.isdigit())
        if not ziffern:
            continue
        try:
            stamp = dt.datetime.fromtimestamp(int(ziffern) / 1000.0)
        except (ValueError, OSError, OverflowError):
            continue
        stunden = (dt.datetime.now() - stamp).total_seconds() / 3600
        if stunden >= 1:
            alt.append((e.get("ProcessId"), round(stunden, 1)))
        else:
            jung += 1

    os_roh = _powershell("$o=Get-CimInstance Win32_OperatingSystem; "
                         "'{0} {1}' -f ($o.FreeVirtualMemory/1KB), ($o.TotalVirtualMemorySize/1KB)")
    commit_frei = commit_gesamt = 0
    teile = os_roh.split()
    if len(teile) >= 2:
        try:
            commit_frei, commit_gesamt = int(float(teile[0])), int(float(teile[1]))
        except ValueError:
            pass

    grund = []
    if len(agenten) > MAX_AGENTEN:
        grund.append("MoonDev-Agentenprozesse: %d (Grenze %d)" % (len(agenten), MAX_AGENTEN))
    if len(alt) > MAX_ALTE:
        grund.append("%d Agentenprozess(e) laufen laenger als 1 h (Grenze %d) - "
                     "das ist die Signatur des Leaks; aeltester %s h"
                     % (len(alt), MAX_ALTE, max((h for _, h in alt), default=0)))
    if commit_frei and commit_frei < MIN_COMMIT_MB:
        grund.append("freies Commit nur %d MB von %d MB - der naechste Modellstart "
                     "(lokaler Modell-Rueckfall) scheitert" % (commit_frei, commit_gesamt))
    if not grund:
        return 0
    print("MoonDev-Wache " + dt.datetime.now().strftime("%d.%m. %H:%M"))
    for g in grund:
        print("  - " + g)
    if len(alt) > MAX_ALTE:
        print("  Aufraeumen laeuft im MoonDev-Treiber (jeder Zyklus, Schonfrist 10 min);")
        print("  laeuft er nicht, zuerst: Get-ScheduledTask MaxHirn-MoonDev-Dauerlauf pruefen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
