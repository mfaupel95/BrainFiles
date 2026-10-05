#!/usr/bin/env python3
"""Konfig-Doktor-Wache (no_agent) - meldet nur KRITISCH, leere Ausgabe = nichts.

WARUM DIESE WACHE EXISTIERT (05.10.2026)
----------------------------------------
Am 05.10.2026 um 22:12:52 war die Junction `BrainFiles/Werkstatt -> O:/Werkstatt`
durch einen echten, fast leeren Ordner ersetzt. Folge: alle 49 Repos, omnitrade,
OmniRoute und die Projekte waren ueber den BrainFiles-Pfad unsichtbar;
`omnitrade.cmd` meldete "keine Statusdatei", Repos-Zentrale und Repo-Bots lasen
ins Leere. Auf O: lag alles unversehrt - nur der Verweis war weg. Aufgefallen ist
es zufaellig in einer Sitzung, die den omnitrade-Stand pruefen wollte. Es gab
KEINE Wache dafuer, obwohl der konfig-doktor `LAUFZEIT-JUNCTION-*` als KRITISCH
kennt - nur rief ihn niemand auf.

ZWEI ZEUGEN, ABSICHTLICH
------------------------
1. DIREKTER VERWEIS-TEST (schnell, ohne Fremdprozess): fuer jeden erwarteten
   Verweis wird geprueft, dass er existiert, ein Reparse-Punkt ist und das Ziel
   ERREICHBAR ist. Das faengt den Vorfall oben in Millisekunden und funktioniert
   auch, wenn der Doktor selbst defekt ist.
2. KONFIG-DOKTOR (`Agenten/Routinen/konfig-doktor.ps1 -Kurz -OhneExtern`):
   breiter Blick (Regelpaare, Junction-Modul, Plattenplatz, Ballast). Gemeldet
   wird NUR KRITISCH - WARNUNGEN und HINWEISE sind fuer eine Wache Rauschen.

Ein Fehler der Pruefung ist NIE ein leeres Ergebnis: faellt der Doktor aus
(Exitcode 2, Zeitueberschreitung, unlesbare Ausgabe), wird das gemeldet, nicht
verschwiegen. Eine leere Ausgabe bedeutet genau eines: alles geprueft, nichts
KRITISCH.

Aufruf:
  python konfig-doktor-wache.py            # Cron-Betrieb: nur Befunde
  python konfig-doktor-wache.py --immer    # auch bei Gesundheit eine Zeile
  python konfig-doktor-wache.py --json     # Zustand fuer Werkzeuge

Merksatz: die Merkdatei traegt den Befund OHNE Zahlen, damit ein wachsender
Wert dieselbe Feststellung bleibt und nicht jede Stunde neu meldet. Ziffern
werden dabei als GANZE FOLGE ersetzt (nicht je Ziffer) - sonst macht '3' -> '#'
und '99' -> '##' aus derselben Feststellung zwei verschiedene Kennungen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent.parent          # Agenten/Hermes/scripts -> BrainFiles
DOKTOR = WURZEL / "Agenten" / "Routinen" / "konfig-doktor.ps1"
ZUSTAND = HIER.parent / "cache" / "konfig-doktor-wache.json"

# Erwartete Verweise: Name -> Ziel. Ein fehlender oder toter Verweis ist ein
# KRITISCHER Befund, weil daran ganze Baeume haengen (Repos, Modelle).
VERWEISE = {
    "Werkstatt": "O:\\Werkstatt",
    "Modelle": "O:\\Modelle",
}

DOKTOR_FRIST_S = 180.0      # der Kurz-Lauf braucht ~8 s; 180 s ist Luft
WIEDERHOLUNG_H = 12         # derselbe Befund hoechstens alle 12 h melden


def _powershell() -> str:
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0",
                        "powershell.exe")


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _merkdatei() -> dict:
    try:
        with open(Path(ZUSTAND), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merken(d: dict) -> None:
    try:
        ziel = Path(ZUSTAND)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with open(ziel, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError:
        pass


def _kennung(text: str) -> str:
    """Schluessel eines Befunds OHNE Zahlen - ein wachsender Wert bleibt
dieselbe Feststellung. Ziffernfolgen werden als GANZE FOLGE ersetzt."""
    ohne_zahlen = re.sub(r"[0-9]+", "#", text)
    return hashlib.sha1(ohne_zahlen.encode("utf-8")).hexdigest()[:12]


# --- Zeuge 1: die Verweise selbst ------------------------------------------

def verweis_lage(wurzel, name: str, ziel: str) -> str:
    """'' wenn gesund, sonst ein Klartext-Befund. Nie werfen."""
    p = Path(wurzel) / name
    if not p.exists():
        return "%s fehlt ganz (erwartet: Verweis auf %s)" % (name, ziel)
    try:
        st = os.lstat(str(p))
    except OSError as e:
        return "%s nicht lesbar (%s)" % (name, e)
    attrs = getattr(st, "st_file_attributes", 0)
    ist_verweis = bool(attrs & 0x400) or os.path.islink(str(p))
    if not ist_verweis:
        try:
            anzahl = sum(1 for _ in os.scandir(str(p)))
        except OSError:
            anzahl = -1
        return ("%s ist KEIN Verweis mehr, sondern ein echter Ordner "
                "(%d Eintraege) - erwartet: Verweis auf %s"
                % (name, anzahl, ziel))
    try:
        os.listdir(str(p))
    except OSError as e:
        return ("%s zeigt ins Leere - Ziel %s nicht erreichbar (%s)"
                % (name, ziel, e))
    return ""


# --- Zeuge 2: der Doktor ----------------------------------------------------

def doktor_kurz(doktor, wurzel) -> tuple:
    """(kritisch, meldung, fehler). `kritisch=None` heisst 'nicht ermittelbar'."""
    if not Path(doktor).exists():
        return None, "", "konfig-doktor.ps1 fehlt (%s)" % doktor
    try:
        aus = subprocess.run(
            [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(doktor), "-Kurz", "-OhneExtern"],
            capture_output=True, timeout=DOKTOR_FRIST_S, cwd=str(wurzel),
        )
    except subprocess.TimeoutExpired:
        return None, "", "konfig-doktor brauchte laenger als %d s" % int(DOKTOR_FRIST_S)
    except OSError as e:
        return None, "", "konfig-doktor nicht startbar (%s)" % e
    roh = (aus.stdout or b"").decode("utf-8", "replace").strip()
    fehler = (aus.stderr or b"").decode("utf-8", "replace").strip()
    code = aus.returncode
    if code == 2:
        return None, roh, "konfig-doktor selbst defekt: %s" % (roh or fehler)[:300]
    if "KRITISCH" not in roh:
        return None, roh, ("konfig-doktor lieferte keine lesbare Zeile "
                           "(Exit %s): %s" % (code, (roh or fehler)[:200]))
    teil = roh.split("KRITISCH", 1)[1]
    ziffern = ""
    for c in teil:
        if c.isdigit():
            ziffern += c
        elif ziffern:
            break
    if not ziffern:
        return None, roh, "konfig-doktor: Zahl hinter KRITISCH nicht lesbar"
    return int(ziffern), roh, ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--immer", action="store_true",
                    help="auch bei Gesundheit eine Zeile ausgeben")
    ap.add_argument("--json", action="store_true", help="Zustand als JSON")
    a = ap.parse_args(argv)

    befunde = []
    for name, ziel in VERWEISE.items():
        text = verweis_lage(WURZEL, name, ziel)
        if text:
            befunde.append(text)

    kritisch, kurz, doktor_fehler = doktor_kurz(DOKTOR, WURZEL)
    if doktor_fehler:
        befunde.append(doktor_fehler)
    elif kritisch:
        befunde.append("konfig-doktor meldet %d KRITISCH (%s)" % (kritisch, kurz))

    jetzt = time.time()
    merk = _merkdatei()
    gesendet = merk.get("gesendet") or {}
    neu, wiederholt = [], 0
    for b in befunde:
        k = _kennung(b)
        letzte = gesendet.get(k)
        if letzte and (jetzt - float(letzte)) < WIEDERHOLUNG_H * 3600:
            wiederholt += 1
            continue
        neu.append(b)
        gesendet[k] = jetzt
    _merken({"gesendet": gesendet, "stand": _jetzt(),
             "befunde": befunde, "kritisch_doktor": kritisch})

    if a.json:
        print(json.dumps({"befunde": befunde, "neu": neu,
                          "wiederholt": wiederholt,
                          "kritisch_doktor": kritisch,
                          "doktor_fehler": doktor_fehler,
                          "stand": _jetzt()}, ensure_ascii=False, indent=2))
        return 0

    if not befunde:
        if a.immer:
            print("konfig-doktor-wache: gesund (%d Verweis(e) ok, Doktor KRITISCH 0)"
                  % len(VERWEISE))
        return 0

    if not neu:
        if a.immer:
            print("konfig-doktor-wache: %d Befund(e), alle innerhalb der "
                  "Merkfrist schon gemeldet" % len(befunde))
        return 0

    zeilen = ["konfig-doktor-wache: %d Befund(e)" % len(neu)]
    for b in neu:
        zeilen.append("  - " + b)
    if wiederholt:
        zeilen.append("  (%d weitere innerhalb der Merkfrist schon gemeldet)"
                      % wiederholt)
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
