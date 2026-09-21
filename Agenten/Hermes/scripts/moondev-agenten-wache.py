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

MAX_AGENTEN = 10             # 4 Agenten x (Launcher + Interpreter) = 8 im Normalbetrieb
MAX_JE_AGENT = 2             # EIN Agent = ZWEI Prozesse; mehr ist der Leak
SCHONFRIST_S = 300           # so lange raeumt der Treiber selbst auf (s. Schonfrist
#                             dort). Juengere Waisen sind NICHT gemeldet - sonst
#                             alarmiert die Wache bei jedem Agentenneustart, weil
#                             das alte Prozesspaar noch im Aufraeumfenster steht.
MIN_COMMIT_MB = 6000         # darunter klemmt der naechste Modellstart
KENNUNG = ("src.agents", "kraken_agent.py")

# FALSCHE ALARME DER ERSTEN FASSUNG (21.09.2026, 12:19-13:39 alle 15 Minuten):
# Sie meldete "8 Prozesse laenger als 1 h" als Leak-Signatur. Falsch - im
# Normalbetrieb laeuft ein Agent STUNDENLANG, und sein Prozesspaar altert mit.
# Die Leak-Signatur ist nicht das ALTER, sondern die ZAHL JE AGENT: erwartet
# sind genau zwei Prozesse (Startprogramm + Interpreter). Alles darueber ist ein
# zweiter Satz desselben Agenten - genau das war der Leak vom 21.09.2026 (84
# Prozesse = mehrfache Saetze). Das Alter steht nur noch in der Meldung.


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
        "Select-Object ProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Compress")
    if not roh:
        return []
    try:
        daten = json.loads(roh)
    except ValueError:
        return []
    return [daten] if isinstance(daten, dict) else daten


def alter_von(eintrag) -> float:
    """Alter eines Prozesses in Sekunden; sehr gross, wenn unlesbar."""
    import datetime as _dt
    roh = str(eintrag.get("CreationDate") or "")
    ziffern = "".join(c for c in roh if c.isdigit())
    if not ziffern:
        return 1e9
    try:
        stamp = _dt.datetime.fromtimestamp(int(ziffern) / 1000.0)
    except (ValueError, OSError, OverflowError):
        return 1e9
    return max(0.0, (_dt.datetime.now() - stamp).total_seconds())


def main() -> int:
    if sys.platform != "win32":
        return 0
    alle = prozesse()
    # NUR echte Interpreter, nicht jede Huelle mit dem Wort in der Kommandozeile:
    # eine PowerShell-/tasklist-Abfrage, die "kraken_agent.py" enthaelt, sah in
    # der ersten Fassung wie ein Agent aus und zaehlte mit (gemessen 21.09.2026:
    # kraken=5 statt 2). Der Leak-Entdecker darf nicht die eigene Suche finden.
    agenten = [e for e in alle
               if (e.get("Name") or "").lower() in ("python.exe", "pythonw.exe")
               and any(k in (e.get("CommandLine") or "") for k in KENNUNG)]
    # Alter aus "/Date(ms)/"
    import datetime as dt
    alt, jung = [], 0
    for e in agenten:
        stunden = alter_von(e) / 3600
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

    # Je Agent zaehlen, nicht ueber alles: 4 Agenten = 8 Prozesse im Normalfall.
    je_agent = {}
    for e in agenten:
        # Nur Prozesse AELTER als die Schonfrist zaehlen: was juenger ist, steht
        # noch im Aufraeumfenster des Treibers (gemessen 21.09.2026: vier alte
        # Paare + ein laufendes Paar = sechs Sniper-Prozesse im Normalbetrieb
        # eines abstuerzenden Agenten).
        if alter_von(e) < SCHONFRIST_S:
            continue
        cmd = e.get("CommandLine") or ""
        name = "kraken_agent.py" if "kraken_agent.py" in cmd else             (cmd.split("src.agents.")[-1].split()[0] if "src.agents." in cmd else "?")
        je_agent[name] = je_agent.get(name, 0) + 1
    zu_viel = {n: k for n, k in je_agent.items() if k > MAX_JE_AGENT}

    gereift = [e for e in agenten if alter_von(e) >= SCHONFRIST_S]
    grund = []
    if len(gereift) > MAX_AGENTEN:
        grund.append("MoonDev-Agentenprozesse ueber der Schonfrist: %d (Grenze %d) "
                     "- im Normalbetrieb sind es 8 (4 Agenten x 2)"
                     % (len(gereift), MAX_AGENTEN))
    if zu_viel:
        grund.append("mehr als %d Prozess(e) je Agent: %s - das ist die "
                     "Leak-Signatur (ein zweiter Satz desselben Agenten laeuft mit)"
                     % (MAX_JE_AGENT, ", ".join("%s=%d" % (n, k) for n, k in zu_viel.items())))
    if commit_frei and commit_frei < MIN_COMMIT_MB:
        grund.append("freies Commit nur %d MB von %d MB - der naechste Modellstart "
                     "(lokaler Modell-Rueckfall) scheitert" % (commit_frei, commit_gesamt))
    if not grund:
        return 0
    print("MoonDev-Wache " + dt.datetime.now().strftime("%d.%m. %H:%M"))
    for g in grund:
        print("  - " + g)
    if zu_viel:
        print("  Aufraeumen laeuft im MoonDev-Treiber (jeder Zyklus, Schonfrist 10 min);")
        print("  laeuft er nicht, zuerst: Get-ScheduledTask MaxHirn-MoonDev-Dauerlauf pruefen.")
    if alt:
        print("  (aeltester Agentenprozess %.1f h - im Normalbetrieb laeuft ein "
              "Agent stundenlang, das Alter allein ist kein Befund)"
              % max(h for _, h in alt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
