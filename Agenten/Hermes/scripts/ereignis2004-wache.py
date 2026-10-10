#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache auf Windows-Ereignis 2004 (Resource-Exhaustion-Detector).

WARUM: Ereignis 2004 feuert, wenn der Commit (virtueller Speicher) knapp wird.
341-mal in 90 Tagen (gemessen 07.10.2026). Die Auslagerungsdatei wurde
vergroessert (Commit-Grenze 103,7 GB), aber Commit frei war nur 13 GB.
Nach Entlastung (TradingView, llama-server, WSL) sind es 4 in 24 h -
weniger, aber nicht 0. Die Wache beobachtet, ob 2004 auf 0 geht.

Gemeldet wird NUR, was neu ist:
  1. jede NEUE 2004-Gruppe (mehrere Ereignisse in kurzer Zeit = eine Meldung)
  2. ein RUECKGANG: wenn 24 h ohne 2004 vergangen sind

LEERE AUSGABE = nichts senden (Watchdog-Muster).
Zustand in Agenten/Hermes/cache/ereignis2004-wache.json.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python ereignis2004-wache.py              # pruefen
    python ereignis2004-wache.py --jetzt      # zeigen, nichts schreiben
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "..", "cache", "ereignis2004-wache.json")
CACHE = os.path.normpath(CACHE)


def lade_zustand() -> dict:
    if os.path.exists(CACHE):
        try:
            with open(CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"letzte_meldung": None, "letzte_2004": None, "rueckgang_gemeldet": False}


def schreibe_zustand(z: dict) -> None:
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)


def hole_2004(seit_tage: int = 1) -> list:
    """Ereignis 2004 aus dem System-Log holen."""
    ps = (
        "Get-WinEvent -FilterHashtable @{LogName='System'; Id=2004; "
        "StartTime=(Get-Date).AddDays(-" + str(seit_tage) + ")} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object @{n='TimeCreated';e={$_.TimeCreated.ToString('o')}}, "
        "@{n='Msg';e={$_.Message.Substring(0,[Math]::Min(120,$_.Message.Length))}} | "
        "ConvertTo-Json -Depth 2"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return []
        data = json.loads(r.stdout)
        if isinstance(data, dict):
            data = [data]
        return data
    except Exception:
        return []


def berichte(ereignisse: list, zustand: dict, jetzt: datetime) -> tuple[list, dict]:
    """Reine Meldelogik: (meldungen, neuer_zustand).

    `ereignisse`: Liste mit 'TimeCreated' (ISO) - sortiert aufsteigend erwartet.
    `zustand`: Merk-Dict, wird fuer den naechsten Lauf zurueckgegeben.
    Gruppiert 2004-Ereignisse in 5-Minuten-Gruppen und meldet nur neue.
    """
    z = dict(zustand)
    anzahl = len(ereignisse)

    letztes_2004 = None
    zeiten = []
    for e in ereignisse:
        try:
            t = datetime.fromisoformat(e["TimeCreated"].replace("Z", "+00:00"))
            if t.tzinfo is not None:
                t = t.astimezone().replace(tzinfo=None)
            zeiten.append(t)
        except Exception:
            continue
    if zeiten:
        zeiten.sort()
        letztes_2004 = ereignisse[-1].get("TimeCreated")

    meldungen = []

    # 1. Neue 2004-Gruppe
    if anzahl > 0:
        gruppen = []
        aktuelle_gruppe = []
        for t in zeiten:
            if aktuelle_gruppe and (t - aktuelle_gruppe[-1]) > timedelta(minutes=5):
                gruppen.append(aktuelle_gruppe)
                aktuelle_gruppe = []
            aktuelle_gruppe.append(t)
        if aktuelle_gruppe:
            gruppen.append(aktuelle_gruppe)

        letzte_meldung = z.get("letzte_meldung")
        neue_gruppen = 0
        for g in gruppen:
            gruppe_zeit = max(g)
            if letzte_meldung is None or gruppe_zeit > datetime.fromisoformat(letzte_meldung):
                neue_gruppen += 1

        if neue_gruppen > 0:
            meldungen.append(
                f"Ereignis 2004: {anzahl} in 24 h, {neue_gruppen} neue Gruppe(n). "
                f"Letztes: {letztes_2004}"
            )
            z["letzte_meldung"] = jetzt.isoformat()
            z["letzte_2004"] = letztes_2004
            z["rueckgang_gemeldet"] = False

    # 2. Rueckgang: 24 h ohne 2004
    if anzahl == 0 and not z.get("rueckgang_gemeldet"):
        meldungen.append("Ereignis 2004: 0 in 24 h - Rueckgang.")
        z["rueckgang_gemeldet"] = True
        z["letzte_meldung"] = jetzt.isoformat()

    return meldungen, z


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jetzt", action="store_true", help="zeigen, nichts schreiben")
    args = ap.parse_args()

    z = lade_zustand()
    jetzt = datetime.now()

    # 2004-Ereignisse der letzten 24 h
    ereignisse = hole_2004(seit_tage=1)

    meldungen, z_neu = berichte(ereignisse, z, jetzt)

    if meldungen:
        for m in meldungen:
            print(m)

    if not args.jetzt:
        schreibe_zustand(z_neu)

    return 0


if __name__ == "__main__":
    sys.exit(main())
