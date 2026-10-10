#!/usr/bin/env python3
"""Wache auf den WebSocket-Trigger der scanner-Spur - sie MELDET, sie heilt nicht.

WARUM (02.10.2026)
------------------
Der Trigger (scanner/ws_trigger.py) entfernt die Wartezeit bis zum naechsten
15-Minuten-Zyklus: Signal beim Kerzenschluss, Ausfuehrung in Sekunden. Am
02.10.2026 16:49 wurde er gestoppt (Rechner-/Gateway-Neustart) und NIEMAND
hat es gemerkt - der Fuellpreis-Vergleich (herkunft=trigger vs. zyklus) stand
zwei Tage still, ohne eine einzige Zeile. Es gab keine Wache.

WAS DIESE WACHE TUT
-------------------
ZWEI Zeugen (Hausregel): die PID-Datei (scanner/ws_trigger.pid) und die
Frische des Logs (scanner/ws_trigger.log). Die PID zaehlt NUR mit dem
Programmnamen (pid-lebt-Lektion: Windows vergibt PIDs neu - eine lebende PID
ist kein Beweis fuer einen lebenden Prozess). Befunde:
  * tot: keine PID-Datei ODER Prozess weg
  * haengt: Prozess lebt, aber Log aelter als 20 min (kein Ping, kein
    Kerzenschluss - der 30-s-Ping schreibt jede halbe Minute)
Sie startet NICHTS. Leere Ausgabe = alles in Ordnung; nur ein WECHSEL des
Befunds wird gemeldet, hoechstens alle 6 Stunden je Befund.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python Agenten/Hermes/scripts/trigger-wache.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
SCANNER = os.path.join(REPO, "Agenten", "Handel", "scanner")
PID_DATEI = os.path.join(SCANNER, "ws_trigger.pid")
LOG_DATEI = os.path.join(SCANNER, "ws_trigger.log")
MERKDATEI = os.path.join(REPO, "Agenten", "Hermes", "cache", "trigger-wache.json")

# Der Trigger sendet alle 30 s einen Ping und schreibt ihn ins Log. 20 min
# ohne Logzeile heisst: Prozess haengt oder Feed tot - ein einzelner
# langsamer Zyklus loest keinen Fehlalarm aus.
LOG_ALTER_MAX_S = 20 * 60
MELDE_ABSTAND_S = 6 * 3600  # derselbe Befund hoechstens alle 6 h


def _jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _pid_und_prozess():
    """(pid, lebt) aus der PID-Datei; lebt nur, wenn der Prozess python ist."""
    try:
        with open(PID_DATEI, encoding="utf-8") as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None, False
    try:
        r = subprocess.run(
                    ["tasklist.exe", "/FI", "PID eq %d" % pid, "/NH"],
                    capture_output=True, text=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        # tasklist liefert eine Zeile je vergebener PID - der NAME muss python
        # sein, sonst ist die PID wiederverwendet (pid-lebt-Lektion).
        lebt = "python" in r.stdout.lower()
    except Exception:
        lebt = False
    return pid, lebt


def _log_alter_s():
    try:
        return time.time() - os.path.getmtime(LOG_DATEI)
    except OSError:
        return None


def _merk_laden():
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _merk_schreiben(stand):
    with open(MERKDATEI, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)


def main() -> int:
    pid, lebt = _pid_und_prozess()
    alter = _log_alter_s()

    if pid is None:
        befund = "tot (keine PID-Datei)"
    elif not lebt:
        befund = "tot (Prozess weg, PID %s)" % pid
    elif alter is not None and alter > LOG_ALTER_MAX_S:
        befund = "haengt (Prozess %s lebt, Log %d min alt)" % (pid, alter // 60)
    else:
        befund = None  # gesund

    if befund is None:
        return 0  # leere Ausgabe = nichts senden

    merk = _merk_laden()
    jetzt = time.time()
    letzte = merk.get(befund)
    if letzte and jetzt - letzte < MELDE_ABSTAND_S:
        return 0  # derselbe Befund schon gemeldet

    merk[befund] = jetzt
    _merk_schreiben(merk)
    print("TRIGGER-WACHE: %s (Log-Alter %s)" % (befund,
          "%d min" % (alter // 60) if alter is not None else "unbekannt"))
    print("Start: python Agenten/Handel/scanner/ws_trigger.py (Papier)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
