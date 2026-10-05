#!/usr/bin/env python
"""Status aller Telegram-Anbindungen eines Hermes-Home, ohne Secrets.

Drei Anbindungen, drei Wahrheiten:
  1. Gateway-Plattform telegram       -> gateway_state.json + logs/gateway.log
  2. Multiplex-Profil bots:telegram   -> derselbe Statusblock, eigener Eintrag
  3. SkillsBot-Bruecke (Agenten/Bus)  -> skillsbot.offset (Lebenszeichen) + .log

Aufruf ueber das terminal-Werkzeug:
    python scripts/telegram_status.py
    python scripts/telegram_status.py --home "C:/Pfad/zu/Hermes" --bus "C:/Pfad/zu/Bus"

Exit 0 = mindestens eine Anbindung lebt; Exit 1 = keine; Exit 2 = Status nicht lesbar.
Stdlib only. Es wird nie ein Tokenwert ausgegeben, nur Existenz und Laenge.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

LOG_MARKERS = {
    "connected": "✓ telegram connected",
    "missing": "No adapter available for telegram",
    "retry": "Reconnect telegram: no adapter yet",
    "polling": "Telegram polling confirmed healthy",
}
LOG_WINDOW = 4 * 1024 * 1024  # nur das Logende lesen


def _pfad(*teile: str) -> str:
    return os.path.join(*teile)


def gateway_status(home: str):
    """Liest gateway_state.json; liefert (daten, fehlertext)."""
    pfad = _pfad(home, "gateway_state.json")
    if not os.path.isfile(pfad):
        return None, f"gateway_state.json fehlt ({pfad})"
    try:
        with open(pfad, "r", encoding="utf-8") as fh:
            return json.load(fh), ""
    except (OSError, ValueError) as exc:
        return None, f"gateway_state.json unlesbar: {exc}"


def log_befund(home: str):
    """Letzte Treffer der entscheidenden Logzeilen (nur das Logende lesen)."""
    pfad = _pfad(home, "logs", "gateway.log")
    if not os.path.isfile(pfad):
        return ["logs/gateway.log fehlt - kein Beleg fuer den Startpfad"]
    try:
        with open(pfad, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - LOG_WINDOW))
            text = fh.read().decode("utf-8", "replace").replace("\x00", "")
    except OSError as exc:
        return [f"gateway.log unlesbar: {exc}"]
    zeilen = text.splitlines()
    treffer = []
    for name, marker in LOG_MARKERS.items():
        gefunden = [z for z in zeilen if marker in z]
        if gefunden:
            stamp = " ".join(gefunden[-1].split(" ")[:2])  # '2026-10-05 06:55:26,134'
            treffer.append(f"{name:<9} {stamp:<24} {marker!r}")
        else:
            treffer.append(f"{name:<9} {'--':<24} {marker!r} nicht im Logende")
    return treffer


def telegram_zeilen(daten: dict):
    """Jede Statuszeile mit 'telegram' im Namen."""
    zeilen = []
    for name, wert in sorted((daten.get("platforms") or {}).items()):
        if "telegram" not in name:
            continue
        wert = wert or {}
        zustand = wert.get("state", "?")
        detail = ""
        if zustand != "connected":
            detail = f"  code={wert.get('error_code')}  {wert.get('error_message') or ''}"
        beachtet = "  needs_attention" if wert.get("needs_attention") else ""
        zeilen.append(f"    {name:<26} {zustand}{beachtet}{detail}")
    return zeilen


def skillsbot_status(bus: str):
    """Lebenszeichen = die mtime von skillsbot.offset; dazu die letzte Logzeile."""
    zeilen = []
    offset = _pfad(bus, "skillsbot.offset")
    log = _pfad(bus, "skillsbot.log")
    if not os.path.isfile(offset):
        return ["    skillsbot.offset FEHLT - die Bruecke laeuft nicht oder legt nichts an"]
    end = datetime.fromtimestamp(os.path.getmtime(offset)).astimezone()
    zeilen.append(f"    skillsbot.offset      zuletzt {end:%m-%d %H:%M:%S}  (Lebenszeichen)")
    try:
        with open(offset, "r", encoding="utf-8") as fh:
            zeilen.append(
                f"    offset-Wert           {fh.read().strip()}  (Telegram update_id, KEINE Uhrzeit)")
    except OSError as exc:
        zeilen.append(f"    offset unlesbar: {exc}")
    if os.path.isfile(log):
        try:
            with open(log, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                fh.seek(max(0, fh.tell() - 8192))
                text = fh.read().decode("utf-8", "replace").replace("\x00", "")
            for z in [x for x in text.splitlines() if x.strip()][-1:]:
                zeilen.append(f"    letzte Logzeile       {z[:220]}")
        except OSError as exc:
            zeilen.append(f"    skillsbot.log unlesbar: {exc}")
    return zeilen


def main() -> int:
    ap = argparse.ArgumentParser(description="Status aller Telegram-Anbindungen")
    hier = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--home", default=os.environ.get("HERMES_HOME", hier))
    ap.add_argument("--bus", default="")
    args = ap.parse_args()

    bus = args.bus or _pfad(os.path.dirname(args.home), "Bus")
    befunde = []  # (Name, lebt, Befundzeile)

    print(f"Hermes-Home: {args.home}")
    print(f"Bus:         {bus}\n")

    daten, fehler = gateway_status(args.home)
    if daten is None:
        print(f"[Gateway] {fehler}")
        befunde.append(("Gateway-Plattform", False, fehler))
    else:
        print(f"[Gateway] pid={daten.get('pid')}  state={daten.get('gateway_state')}  "
              f"code_version={daten.get('code_version')}")
        zeilen = telegram_zeilen(daten)
        if zeilen:
            print("  Telegram-Plattformen:")
            for z in zeilen:
                print(z)
        else:
            print("  KEINE Telegram-Plattform im Status - der Gateway fuehrt sie nicht")
        # Getrennt je Eintrag: ein verbundener bots-Eintrag darf einen toten
        # Hauptbot NICHT verdecken - das war der Fehler der ersten Fassung.
        for name, wert in sorted((daten.get("platforms") or {}).items()):
            if "telegram" not in name:
                continue
            zustand = (wert or {}).get("state")
            lebt = zustand == "connected"
            zusatz = "" if lebt else f" [{zustand}, {(wert or {}).get('error_code') or 'ohne Code'}]"
            befunde.append((f"Gateway {name}", lebt, zustand + zusatz))
        if not any(b[0].startswith("Gateway telegram") for b in befunde):
            befunde.append(("Gateway telegram", False, "kein Eintrag im Status"))
        print("\n  Logbefund (nur Logende):")
        for z in log_befund(args.home):
            print("   ", z)

    print("\n[SkillsBot-Bruecke]")
    bus_zeilen = skillsbot_status(bus)
    for z in bus_zeilen:
        print(z)
    bus_lebt = any("FEHLT" not in z and "unlesbar" not in z for z in bus_zeilen)
    befunde.append(("SkillsBot-Bruecke", bus_lebt,
                    "Lebenszeichen vorhanden" if bus_lebt else "kein Lebenszeichen"))

    print("\nUrteil je Anbindung:")
    for name, lebt, zusatz in befunde:
        print(f"    {'OK    ' if lebt else 'KAPUT '} {name:<26} {zusatz}")
    tot = [n for n, lebt, _ in befunde if not lebt]
    if tot:
        print(f"\n-> {len(tot)} Anbindung(en) nicht gesund: {', '.join(tot)}")
    else:
        print("\n-> alle Anbindungen melden connected")
    print("Merksatz: 'connected' ist ein Zustandszeugen, kein Weg-Beweis - die "
          "End-to-End-Zustellung gehoert trotzdem gefahren.")
    return 1 if tot else 0


if __name__ == "__main__":
    sys.exit(main())