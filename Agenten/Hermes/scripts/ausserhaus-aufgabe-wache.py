#!/usr/bin/env python3
"""Wache: Die Windows-Aufgabe 'MaxHirn-Ausserhaus-Kopie' ist taeglich VERSCHWUNDEN.

BEFUND (05.10.2026): Der Cron 'ausserhaus-aufgabe-sichern' (08:30) legt sie seit
dem 30.09. JEDEN Tag neu an - sie ueberlebt also keinen Tag. Beim Nachmessen am
05.10. fehlte sie um 22:30 UND um 22:52, war um 22:55 nach dem Anlegen wieder da.
Das TaskScheduler-Ereignisprotokoll war AUS (erst 22:51 eingeschaltet), deshalb
gibt es fuer die bisherigen Faelle keine Spur.

DIESE WACHE MACHT ZWEI DINGE:
 1. Sie legt die Aufgabe wieder an, wenn sie fehlt (wie der Tages-Cron) - aber
    im 10-Minuten-Takt, damit die 21:30-Kopie nicht mehr ausfaellt.
 2. Sie SCHREIBT DEN ZUSTAND MIT ZEITSTEMPEL in eine Merkdatei, sodass die
    Lebensdauer messbar wird: aus 'angelegt 22:54' und 'weg 22:55' laesst sich
    die Ueberlebenszeit ablesen, statt sie zu raten.

Leere Ausgabe = nichts zu melden (Watchdog-Muster). Nur ein Wechsel
(da -> weg / weg -> angelegt) wird gemeldet.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

NAME = "MaxHirn-Ausserhaus-Kopie"
HIER = Path(__file__).resolve()
HERMES = HIER.parents[1]                     # .../Agenten/Hermes
WURZEL = HIER.parents[3]                     # .../BrainFiles
MERK = HERMES / "cache" / "ausserhaus-aufgabe-wache.json"
REGISTRAR = WURZEL / "Agenten" / "Routinen" / "ausserhaus-kopie-aufgabe.ps1"


def _ohne_python_leck(env: dict) -> dict:
    env = dict(env)
    for n in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(n, None)
    return env


def _ps(argumente: list[str], frist: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", *argumente],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        timeout=frist, env=_ohne_python_leck(os.environ),
    )


def da() -> bool:
    """schtasks /query ist hier die verlaessliche Sicht (Get-ScheduledTask findet
    vorhandene Aufgaben in dieser Umgebung nicht)."""
    p = _ps(["schtasks", "/query", "/tn", NAME, "/fo", "list"], frist=60)
    if p.returncode != 0:
        return False
    return "Aufgabenname" in ((p.stdout or "") + (p.stderr or ""))


def _merk_lesen() -> dict:
    try:
        return json.loads(MERK.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merk_schreiben(d: dict) -> None:
    MERK.parent.mkdir(parents=True, exist_ok=True)
    tmp = MERK.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, MERK)


def _dauer_text(von: str | None, bis: str) -> str:
    if not von:
        return "unbekannt"
    try:
        a = datetime.fromisoformat(von)
        b = datetime.fromisoformat(bis)
    except Exception:
        return "unbekannt"
    s = int((b - a).total_seconds())
    if s < 3600:
        return f"{s // 60} min"
    return f"{s / 3600:.1f} h"


def main() -> int:
    jetzt = datetime.now().isoformat(timespec="seconds")
    ist_da = da()
    merk = _merk_lesen()
    vorher = merk.get("zustand")
    zeilen: list[str] = []

    if not ist_da:
        if not REGISTRAR.is_file():
            print(f"Ausserhaus-Kopie fehlt und der Registrar fehlt: {REGISTRAR}")
            return 1
        p = _ps(["-File", str(REGISTRAR)])
        ok = da()
        if ok:
            dauer = _dauer_text(merk.get("angelegt_um"), jetzt)
            zeilen.append(
                f"Ausserhaus-Aufgabe war WEG und ist wieder angelegt "
                f"(Ueberlebenszeit der vorigen: {dauer})."
            )
            merk = {"zustand": "da", "angelegt_um": jetzt, "weg_um": jetzt}
        else:
            text = ((p.stdout or "") + (p.stderr or "")).strip()
            print("Ausserhaus-Aufgabe liess sich NICHT anlegen. Registrar sagte:")
            print(text[-800:])
            return 1
    else:
        if vorher == "weg":
            zeilen.append(
                f"Ausserhaus-Aufgabe ist wieder da (angelegt {jetzt})."
            )
        merk = {
            "zustand": "da",
            "angelegt_um": merk.get("angelegt_um") or jetzt,
            "zuletzt_gesehen": jetzt,
        }

    merk["zustand"] = "da" if ist_da else merk.get("zustand", "weg")
    merk["letzte_pruefung"] = jetzt
    _merk_schreiben(merk)

    if zeilen:
        print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
