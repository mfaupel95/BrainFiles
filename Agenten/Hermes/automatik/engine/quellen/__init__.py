"""Trigger-Quellen: aus der Aussenwelt werden Ausloeser.

Jede Quelle beantwortet genau eine Frage: "ist seit meinem letzten Blick etwas
passiert, das zu einer Regel dieses Typs passt?" Sie startet nichts und urteilt
nicht ueber Erlaubnis - das macht engine/steuerung.py.

Merken statt Horchen: die Engine laeuft als kurzer Prozess (Cron ruft sie auf,
kein Dauerdienst, siehe zustand.py). Jede Quelle fuehrt darum eine Marke in der
Zustands-DB ("wo war ich"). Marken werden gesetzt, SOBALD ein Ereignis gesehen
wurde - nicht erst nach erfolgreichem Lauf. Das ist bewusst at-most-once: ein
Lauf, der abstuerzt, wird NICHT automatisch wiederholt. Ein Rechner, der
schlagartig ausgeht (Kernel-Power 41, Ursache offen), wuerde sonst beim
Hochfahren einen Stapel nachgeholter Automatik starten - genau der Fall, den die
Spezifikation mit nur_wenn_wach ausdruecklich verbietet.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _schluessel(*teile) -> str:
    """Markenschluessel einer Quelle. Getrennt gehalten, damit zwei Quellen
    sich nie gegenseitig die Marke ueberschreiben."""
    return "quelle:" + ":".join(str(t) for t in teile)


from . import board, datei, nachricht, verkettung, zeit  # noqa: E402


@dataclass
class Ausloeser:
    """Ein konkreter Treffer: diese Regel, wegen dieses Ereignisses."""

    regel_id: str
    typ: str
    ausgeloest_durch: str
    werte: dict = field(default_factory=dict)  # fliessen in die Parameter des Laufs
    prioritaet: int = 100


QUELLEN = {
    "board_event": board,
    "datei": datei,
    "zeit": zeit,
    "nachricht": nachricht,
    "skill_ergebnis": verkettung,
}


def sammeln(reg, con, jetzt=None) -> list[Ausloeser]:
    """Alle Quellen befragen, Treffer nach Prioritaet sortiert zurueckgeben.

    Sortierung: kleinere Prioritaet zuerst; bei Gleichstand bleibt die
    Reihenfolge der Registry-Datei erhalten (stabiler Sort ueber den Index).
    """
    treffer: list[Ausloeser] = []
    for typ, quelle in QUELLEN.items():
        regeln = reg.fuer_trigger(typ)
        if not regeln:
            continue
        treffer.extend(quelle.pruefen(regeln, con, jetzt=jetzt))

    reihenfolge = {r.id: i for i, r in enumerate(reg.regeln)}
    treffer.sort(key=lambda a: (a.prioritaet, reihenfolge.get(a.regel_id, 999)))
    return treffer
