#!/usr/bin/env python3
"""Wache: Docker-Engine leben und heilen (T-239, 01.10.2026).

BAUART (Hausregel Watchdog): leere Ausgabe = alles gut, es wird nichts
gesendet. Laeuft als Hermes-Cron `no_agent` alle 15 Minuten.

WARUM ES DIE GIBT
-----------------
Am 30.09.2026 fiel die Docker-Engine zweimal an einem Tag aus (Log
`returning engine error`, Container-Status veraltet). Kein Programm hatte die
Kontrolle: die Systempruefung sieht die Engine nur EINMAL am Tag, und die
Container nautilus-demo (Boersen-Quoten-Knoten) und die freqtrade-Trockenlauf-Bots
haengen an ihr. Um 15:13 half der Handgriff `wsl --shutdown` und Docker Desktop
neu starten; um 17:37 war die Engine wieder weg - ohne Wache merkt niemand
davon, dass die Quoten still ausbleiben.

WAS SIE TUN DARF (und nur das)
------------------------------
1. `docker info` mit Zeitgrenze - antwortet die Engine: nichts, stille.
2. Antwortet sie NICHT: derselbe Handgriff, der am 30.09. geholfen hat -
   `wsl --shutdown`, Docker Desktop starten, bis 3 Minuten auf die Engine
   warten. Heilung wird gemeldet; dauerhafter Ausfall wird MELDEN NICHT
   erduenst: derselbe Befund (Engine weg, Heilversuch geplaunt) kommt
   hoechstens alle 6 Stunden erneut, eine ERHOLUNG wird immer gemeldet.
3. Sie startet keine Container selbst neu - die haben --restart-Policies;
   ihr Job ist die ENGINE.

GRENZE: Ein Lauf, der mitten in einem `hermes update` steckt, kann die Engine
restarten, obwohl der Update sie haelt. Prueft deshalb die Update-Sperre
(Agenten/Hermes/logs/update-*.log juenger als 20 min) und heilt dann nicht -
meldet nur den Zustand.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HERMES = os.path.dirname(HIER)
MERKER = os.path.join(HERMES, "cache", "docker-wache.json")
DESKTOP = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
INFO_FRIST_S = 25
HEILUNG_FRIST_S = 180
WIEDERHOLUNG_S = 6 * 3600


def _run(cmd, frist):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=frist,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"{type(e).__name__}: {e}"


def engine_lebt(runner=_run):
    code, _ = runner(["docker", "info", "--format", "{{.ServerVersion}}"], INFO_FRIST_S)
    return code == 0


def update_laeuft(hier=HERMES, grenz_s=20 * 60):
    logs = os.path.join(hier, "logs")
    try:
        for n in os.listdir(logs):
            if n.startswith("update-") and n.endswith(".log"):
                if time.time() - os.path.getmtime(os.path.join(logs, n)) < grenz_s:
                    return True
    except OSError:
        pass
    return False


def _start_desktop():
    det = subprocess.DETACHED_PROCESS if os.name == "nt" else 0
    subprocess.Popen([DESKTOP], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=det)


def heilen(runner=_run, schlafen=time.sleep, starten=_start_desktop):
    """Der Handgriff vom 30.09.: wsl --shutdown, Desktop starten, warten.
    Rueckgabe (ok, text). `starten` ist die Naht fuer Tests - ein Test darf
    nie die echte Desktop-App hochfahren."""
    code, aus = runner(["wsl", "--shutdown"], 60)
    if code != 0:
        return False, "wsl --shutdown fehlgeschlagen: %s" % (aus.strip()[:180] or "code %s" % code)
    schlafen(8)
    try:
        starten()
    except OSError as e:
        return False, "Docker Desktop nicht startbar: %s" % e
    waited = 0
    while waited < HEILUNG_FRIST_S:
        schlafen(10)
        waited += 10
        if engine_lebt(runner):
            return True, "Engine nach %d s wieder da" % waited
    return False, "Engine nach %d s weiter weg" % HEILUNG_FRIST_S


def merker_lesen():
    try:
        with open(MERKER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def merker_schreiben(d):
    os.makedirs(os.path.dirname(MERKER), exist_ok=True)
    with open(MERKER, "w", encoding="utf-8", newline="") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def lauf(runner=_run, schlafen=time.sleep, jetzt=None, starten=_start_desktop):
    """Meldtext oder leer. Reine Funktion ueber die Nahte (runner, schlafen, starten)."""
    jetzt = time.time() if jetzt is None else jetzt
    m = merker_lesen()
    if engine_lebt(runner):
        if m.get("status") == "weg":
            merker_schreiben({"status": "ok", "erholung": jetzt})
            return ("Docker-Wache: Engine ist zurueck (Heilung %s). Container "
                    "pruefen: docker ps." % datetime.fromtimestamp(m.get("seit", jetzt),
                                                                   timezone.utc).strftime("%H:%M"))
        if m.get("status") != "ok":
            merker_schreiben({"status": "ok"})
        return ""
    # Engine weg.
    if m.get("status") == "weg" and jetzt - m.get("seit", 0) < WIEDERHOLUNG_S:
        return ""                                        # dasselbe Ergebnis, noch nicht wieder melden
    if update_laeuft():
        merker_schreiben({"status": "weg", "seit": jetzt, "geheilt": False})
        return ("Docker-Wache: Engine antwortet nicht, aber ein hermes-update laeuft "
                "(Log < 20 min) - nicht geheilt, der Update haelt die Engine. "
                "Nach dem Update: docker info.")
    ok, text = heilen(runner, schlafen, starten)
    merker_schreiben({"status": "ok" if ok else "weg", "seit": jetzt, "geheilt": ok,
                      "text": text})
    if ok:
        return ("Docker-Wache: Engine war weg - geheilt (wsl --shutdown + Docker "
                "Desktop). %s. Container pruefen: docker ps." % text)
    return ("Docker-Wache: Engine war weg und Heilung MISSLUNGEN (%s). Handgriff "
            "pruefen: 'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe' von "
            "Hand starten, docker info. Ursache laut T-239 wahrscheinlich der "
            "MCP-Spawn-Kreis (T-152)." % text)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = lauf()
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
