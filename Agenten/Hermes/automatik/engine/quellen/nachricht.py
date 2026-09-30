"""Trigger-Quelle nachricht: eingehende Nachricht auf einem Kanal.

Die Engine horcht nicht selbst am Gateway. Sie liest einen Eingangsordner
(arbeit/nachrichten/*.json), in den ein Hook unter Agenten/Hermes/hooks/ die
Nachrichten legt. Das hat einen Grund: Hook-Fehler blockieren die Hermes-
Pipeline nicht und bleiben damit unsichtbar - eine Engine, die sich auf den Hook
als Startweg verliesse, wuerde lautlos nichts tun. Eine Datei dagegen liegt da
und wird beim naechsten Cron-Lauf gesehen, auch wenn der Hook zwischendurch
kaputt war.

Format einer Eingangsdatei (alles Weitere wird ignoriert):
    {"kanal": "telegram", "text": "spuren pruefen", "von": "7648512088",
     "zeit_unix": 1789880000}

Jede Datei wird genau einmal betrachtet und danach nach nachrichten/erledigt/
verschoben - auch wenn keine Regel passte. Ein Eingang, der nicht geleert wird,
waere ein Dauertrigger.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .. import pfade

MAX_PRO_LAUF = 50


def _dateien() -> list[Path]:
    ordner = pfade.nachrichten_eingang()
    try:
        return sorted(
            [p for p in ordner.glob("*.json") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
        )[:MAX_PRO_LAUF]
    except OSError:
        return []


def _lesen(p: Path):
    try:
        daten = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return daten if isinstance(daten, dict) else None


def _wegraeumen(p: Path) -> None:
    ziel = p.parent / "erledigt"
    try:
        ziel.mkdir(parents=True, exist_ok=True)
        p.replace(ziel / ("%d_%s" % (int(time.time()), p.name)))
    except OSError:
        pass


def _passt(regel, n: dict) -> bool:
    b = regel.bedingungen
    if (n.get("kanal") or "") != b.get("kanal"):
        return False
    absender = str(n.get("von") or "")
    erlaubt = b.get("nur_von")
    if erlaubt and absender not in [str(a) for a in erlaubt]:
        return False
    text = str(n.get("text") or "")
    for m in b.get("muster") or []:
        try:
            if re.search(m, text, re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def pruefen(regeln, con, jetzt=None):
    from . import Ausloeser

    treffer = []
    for datei in _dateien():
        n = _lesen(datei)
        _wegraeumen(datei)
        if not n:
            continue
        for regel in regeln:
            if not _passt(regel, n):
                continue
            treffer.append(Ausloeser(
                regel_id=regel.id, typ="nachricht",
                ausgeloest_durch="%s von %s: %s" % (
                    n.get("kanal"), n.get("von") or "?",
                    str(n.get("text") or "")[:120]),
                werte={
                    "text": str(n.get("text") or "")[:500],
                    "von": str(n.get("von") or ""),
                    "kanal": str(n.get("kanal") or ""),
                },
                prioritaet=regel.prioritaet,
            ))
    return treffer
