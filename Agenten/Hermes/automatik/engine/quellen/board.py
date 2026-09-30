"""Trigger-Quelle board_event: Statuswechsel auf dem Kanban-Board.

Gelesen wird die Tabelle task_events der Kanban-DB, die die kanban_*-Tools
ohnehin schreiben (kein Hook noetig, keine Aenderung am Board). Verbindung
read-only ueber file:...?mode=ro - die Engine darf das Board nie beschaedigen,
auch nicht versehentlich.

Die Event-Arten des Boards sind feiner als das Trigger-Vokabular der
Spezifikation (created/claimed/blocked/review/done/failed). ARTEN bildet ab;
alles Uebrige (heartbeat, spawned, commented ...) ist kein Trigger.
"""
from __future__ import annotations

import json
import sqlite3

from .. import pfade
from . import _schluessel

# Event-Kind der Kanban-DB -> Trigger-Ereignis der Registry.
ARTEN = {
    "created": "created",
    "claimed": "claimed",
    "blocked": "blocked",
    "review_requested": "review",
    "completed": "done",
    "crashed": "failed",
    "gave_up": "failed",
}


def _verbinden(db=None):
    ziel = db or pfade.kanban_db()
    uri = "file:%s?mode=ro" % str(ziel).replace("\\", "/")
    con = sqlite3.connect(uri, uri=True, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def _ereignisse(kdb, ab_id: int, grenze: int = 500) -> list[dict]:
    """Neue Board-Ereignisse seit ab_id, alt nach jung."""
    con = _verbinden(kdb)
    try:
        zeilen = con.execute(
            "SELECT e.id, e.task_id, e.kind, e.payload, e.created_at,"
            " t.title, t.assignee, t.status"
            " FROM task_events e LEFT JOIN tasks t ON t.id = e.task_id"
            " WHERE e.id > ? ORDER BY e.id LIMIT ?",
            (int(ab_id), int(grenze)),
        ).fetchall()
    finally:
        con.close()
    return [dict(z) for z in zeilen]


def _passt(regel, ev: dict) -> bool:
    b = regel.bedingungen
    if ARTEN.get(ev["kind"]) != b.get("ereignis"):
        return False
    if b.get("assignee") and (ev.get("assignee") or "") != b["assignee"]:
        return False
    titel = b.get("titel_enthaelt")
    if titel and titel.lower() not in (ev.get("title") or "").lower():
        return False
    return True


def _grund(ev: dict) -> str:
    """Blockgrund/Meldung aus dem Payload ziehen, wenn vorhanden."""
    roh = ev.get("payload")
    if not roh:
        return ""
    try:
        daten = json.loads(roh)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(daten, dict):
        return ""
    for feld in ("reason", "summary", "error", "result"):
        if daten.get(feld):
            return str(daten[feld])[:500]
    return ""


def pruefen(regeln, con, jetzt=None, kdb=None):
    from . import Ausloeser

    if not regeln:
        return []

    marke = _schluessel("board", "letzte_event_id")
    from .. import zustand

    letzte = int(zustand.marke_lesen(con, marke, 0) or 0)

    try:
        neu = _ereignisse(kdb, letzte)
    except sqlite3.Error:
        # Board nicht lesbar (gesperrt, fehlt): kein Trigger, kein Absturz.
        return []

    if not neu:
        return []

    if letzte == 0:
        # Erster Lauf: nur die Marke setzen. Sonst wuerde die Engine die
        # gesamte Board-Historie als "gerade passiert" behandeln.
        zustand.marke_setzen(con, marke, neu[-1]["id"])
        return []

    treffer = []
    for ev in neu:
        for regel in regeln:
            if not _passt(regel, ev):
                continue
            treffer.append(Ausloeser(
                regel_id=regel.id,
                typ="board_event",
                ausgeloest_durch="task_event#%d %s %s" % (
                    ev["id"], ev["kind"], ev["task_id"]),
                werte={
                    "id": ev["task_id"],
                    "kind": ev["kind"],
                    "titel": ev.get("title") or "",
                    "assignee": ev.get("assignee") or "",
                    "reason": _grund(ev),
                },
                prioritaet=regel.prioritaet,
            ))

    zustand.marke_setzen(con, marke, neu[-1]["id"])
    return treffer
