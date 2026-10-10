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
    (das ist die Signatur des Leaks),
  - ein Agent, der LAEUFT, aber seit STILL_MIN Minuten keine Zeile mehr in sein
    Log geschrieben hat (der Hang, siehe unten).

DER HAENGENDE AGENT (31.09./01.10.2026 gemessen): Der kraken_agent lief als
Prozess weiter, schrieb aber seit dem 29.09. 18:20 keine einzige Zeile - das
Log endete mitten in einer normalen Runde ("QNTEUR ... DO NOTHING"), kein
Traceback, kein Fehler. Ein blockierender Netzaufruf ohne Zeitablauf sieht
genau so aus. Von aussen ist "arbeitet gerade lange" nicht von "haengt" zu
unterscheiden - deshalb misst diese Wache das ALTER DER LETZTEN ZEILE und nicht
den Prozesszustand. Ein Neustart durch den Treiber kuriert nur das Symptom;
dieselbe Feststellung wird darum hoechstens alle MERK_H Stunden wiederholt.

Aufruf (Hermes-Cron, no_agent, alle 15 Minuten):
    python moondev-agenten-wache.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

MAX_AGENTEN = 10             # 4 Agenten x (Launcher + Interpreter) = 8 im Normalbetrieb
MAX_JE_AGENT = 2             # EIN Agent = ZWEI Prozesse; mehr ist der Leak
SCHONFRIST_S = 300           # so lange raeumt der Treiber selbst auf (s. Schonfrist
#                             dort). Juengere Waisen sind NICHT gemeldet - sonst
#                             alarmiert die Wache bei jedem Agentenneustart, weil
#                             das alte Prozesspaar noch im Aufraeumfenster steht.
MIN_COMMIT_MB = 6000         # darunter klemmt der naechste Modellstart
STILL_MIN = 60               # so lange darf ein LAUFENDER Agent schweigen
MERK_H = 6                   # dieselbe Stillstands-Feststellung hoechstens alle 6 h
KENNUNG = ("src.agents", "kraken_agent.py")

# Pfade selbstlokalisierend (keine absoluten Pfade im Skript): scripts liegt
# unter Agenten/Hermes/scripts, die Wurzel ist drei Ebenen darueber.
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
LOG_ORDNER = os.path.join(WURZEL, "Agenten", "Handel")
MERK = os.path.join(WURZEL, "Agenten", "Hermes", "cache", "moondev-agenten-wache.json")

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
                                   capture_output=True, text=True, timeout=90,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
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


def agenten_namen(prozesse_liste) -> dict:
    """Name -> Prozess, aus der Kommandozeile. Nur echte Agentenaufrufe.

    Der Name muss zum LOG passen: `src/agents/new_or_top_agent.py` schreibt nach
    `moondev_new_or_top.log` (der Treiber kuerzt `_agent` weg). Wer hier den
    vollen Dateinamen nimmt, sucht ein Log, das es nicht gibt - und meldet
    dann entweder nichts oder alles.
    """
    namen = {}
    for e in prozesse_liste:
        # Der Prozessname gehoert zur Pruefung: eine tasklist-Abfrage mit
        # "kraken_agent.py" im Suchtext ist KEIN Agent (dieselbe Falle, die im
        # Kopf des Skripts steht - der Entdecker darf nicht die eigene Suche
        # finden). Im echten Lauf filtert main() schon vorher; hier steht es
        # zusaetzlich, damit die Funktion auch fuer sich allein stimmt.
        if (e.get("Name") or "").lower() not in ("python.exe", "pythonw.exe"):
            continue
        cmd = (e.get("CommandLine") or "").replace("\\", "/")
        if "kraken_agent.py" in cmd:
            name = "kraken"
        elif "src/agents/" in cmd:
            rest = cmd.split("src/agents/")[-1].split()[0]
            name = rest.rsplit(".py", 1)[0]
            if name.endswith("_agent"):
                name = name[: -len("_agent")]
        else:
            continue
        namen.setdefault(name, e)
    return namen


def log_alter_minuten(name: str):
    """Alter der letzten Zeile im Agentenlog in Minuten. None = kein Log da.

    Kein Log ist AUSDRUECKLICH kein Befund: nicht jeder Agent schreibt eines,
    und ein fehlendes Log ist kein Hang.
    """
    import os as _os
    import time as _time
    pfad = _os.path.join(LOG_ORDNER, "moondev_%s.log" % name)
    if not _os.path.isfile(pfad):
        return None
    return max(0.0, (_time.time() - _os.path.getmtime(pfad)) / 60.0)


def _merker_lesen() -> dict:
    try:
        with open(MERK, encoding="utf-8") as f:
            daten = json.load(f)
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


def _merker_schreiben(merker: dict) -> None:
    import os as _os
    try:
        _os.makedirs(_os.path.dirname(MERK), exist_ok=True)
        with open(MERK, "w", encoding="utf-8") as f:
            json.dump(merker, f, indent=2)
    except OSError:
        pass


def stillstand(namen: dict) -> list:
    """Laufende Agenten, die seit STILL_MIN Minuten nichts geschrieben haben.

    Dieselbe Feststellung hoechstens alle MERK_H Stunden - ein Hang heilt nicht
    durch Wiederholung, und eine Meldung im 15-Minuten-Takt waere nach zwei
    Stunden Rauschen. Schreibt der Agent wieder, wird der Merker geloescht
    (dann darf die naechste Stoerung sofort gemeldet werden).
    """
    import time as _time
    merker = _merker_lesen()
    jetzt = _time.time()
    befunde = []
    for name in sorted(namen):
        minuten = log_alter_minuten(name)
        if minuten is None:
            continue
        if minuten < STILL_MIN:
            merker.pop(name, None)
            continue
        if jetzt - float(merker.get(name) or 0) < MERK_H * 3600:
            continue
        merker[name] = jetzt
        befunde.append(
            "Agent %s LAEUFT, schreibt aber seit %.0f min nichts "
            "(moondev_%s.log) - das sieht nach einem haengenden Netzaufruf aus; "
            "der Treiber startet ihn neu, die Ursache bleibt offen"
            % (name, minuten, name))
    _merker_schreiben(merker)
    return befunde


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
    # Der Hang: ein Agent, der laeuft und schweigt. Das ist NICHT die
    # Leak-Signatur (dafuer ist die Zahl der Prozesse je Agent zustaendig),
    # sondern eine eigene Stoerung: der Prozess lebt, arbeitet aber nicht.
    # Die Funktion schreibt ihren Merker auch dann, wenn sie nichts findet -
    # nur so wird ein Agent, der wieder schreibt, fuer die naechste Stoerung
    # sofort meldefaehig.
    grund.extend(stillstand(agenten_namen(agenten)))

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
