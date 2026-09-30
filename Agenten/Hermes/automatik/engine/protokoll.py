"""Strukturiertes Log: eine Zeile je Lauf (JSONL).

Felder nach Spezifikation Abschnitt 5 Punkt 4:
zeit, regel_id, trigger_typ, ausgeloest_durch, skill, modus, dauer_ms, exit,
aktionen_genutzt, abbruchgrund.

Dazu ergaenzt, weil die Reaktionsschicht (t_f682e5c1) sie braucht:
ergebnis (erfolg|fehler|uebersprungen|dry_run|bestaetigung_offen), ausgabe
(gekuerzt), registry_version, lauf_id, versuch.

Das Log ist die Uebergabe an die Reaktionsschicht. Es wird nur angehaengt und
nie umgeschrieben; eine kaputte Zeile darf den Leser nicht aufhalten (der Leser
ueberspringt sie, siehe zeilen_lesen).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import pfade

AUSGABE_MAX = 4000  # Zeichen; laengere Ausgaben werden gekuerzt markiert


def _jetzt_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def eintrag_bauen(
    regel_id: str,
    trigger_typ: str,
    ausgeloest_durch: str,
    skill: str,
    modus: str,
    ergebnis: str,
    dauer_ms: int = 0,
    exit_code=None,
    aktionen_genutzt=None,
    abbruchgrund: str | None = None,
    ausgabe: str = "",
    registry_version: str = "",
    versuch: int = 1,
    extra: dict | None = None,
) -> dict:
    gekuerzt = len(ausgabe) > AUSGABE_MAX
    e = {
        "zeit": _jetzt_iso(),
        "zeit_unix": int(time.time()),
        "lauf_id": "%s-%d-%d" % (regel_id, int(time.time() * 1000), os.getpid()),
        "regel_id": regel_id,
        "trigger_typ": trigger_typ,
        "ausgeloest_durch": ausgeloest_durch,
        "skill": skill,
        "modus": modus,
        "ergebnis": ergebnis,
        "dauer_ms": int(dauer_ms),
        "exit": exit_code,
        "aktionen_genutzt": sorted(aktionen_genutzt or []),
        "abbruchgrund": abbruchgrund,
        "ausgabe": ausgabe[:AUSGABE_MAX],
        "ausgabe_gekuerzt": gekuerzt,
        "registry_version": registry_version,
        "versuch": versuch,
    }
    if extra:
        e.update(extra)
    return e


def schreiben(eintrag: dict, datei: Path | None = None) -> dict:
    ziel = Path(datei) if datei else pfade.log_datei()
    ziel.parent.mkdir(parents=True, exist_ok=True)
    zeile = json.dumps(eintrag, ensure_ascii=False)
    with open(ziel, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(zeile + "\n")
    return eintrag


def zeilen_lesen(datei: Path | None = None, letzte: int | None = None) -> list[dict]:
    ziel = Path(datei) if datei else pfade.log_datei()
    if not ziel.exists():
        return []
    roh = ziel.read_text(encoding="utf-8", errors="replace").splitlines()
    if letzte:
        roh = roh[-letzte:]
    aus = []
    for zeile in roh:
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            aus.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue  # kaputte Zeile darf den Leser nicht aufhalten
    return aus
