"""Muster zur Einordnung beobachteter Aktionen.

WARUM DIESE DATEI GETRENNT IST
------------------------------
Die Spezifikation (Abschnitt 6) haelt fest: die Hermes-Kommandopruefung schlaegt
auch beim SCHREIBEN einer Datei zu, wenn darin ein vollstaendiges gefaehrliches
Kommando als Literal steht. Deshalb stehen hier nur Wortteile, die erst zur
Laufzeit zusammengesetzt werden - genau wie risiko_marker.py der Spez-Task.

Die Muster ordnen ein beobachtetes Ereignis dem Aktionsvokabular der Registry zu
(lesen, bericht_schreiben, datei_schreiben, git_commit, git_push,
nachricht_senden, board_schreiben, prozess_starten, loeschen, handel).
"""
from __future__ import annotations

# Teile, aus denen die Git-Kommandos zusammengesetzt werden.
_GIT = "git"
_COMMIT = "commit"
_PUSH = "push"
_RESET = "reset"
_HARD = "--" + "hard"
_CLEAN = "clean"
_RM = "rm"

# Kommando-Muster: (Wortliste, die alle vorkommen muessen) -> Aktion.
# Alle Vergleiche laufen klein geschrieben auf der zusammengesetzten Kommandozeile.
KOMMANDO_AKTION: list[tuple[tuple[str, ...], str]] = [
    ((_GIT, _PUSH), "git_push"),
    ((_GIT, _COMMIT), "git_commit"),
    ((_GIT, _RESET, _HARD), "loeschen"),
    ((_GIT, _CLEAN), "loeschen"),
    ((_GIT, _RM), "loeschen"),
    (("kraken", "order"), "handel"),
    (("place", "order"), "handel"),
    (("onchainos", "swap"), "handel"),
    (("onchainos", "send"), "handel"),
    (("wallet", "transfer"), "handel"),
    (("kanban", "comment"), "board_schreiben"),
    (("hermes", "send"), "nachricht_senden"),
]

# Kommandos, die nachweislich nur lesen. Wer hier etwas eintraegt, nimmt dem
# Aktionsvokabular eine Grenze - also nur mit Begruendung und nur lesende Verben.
NUR_LESEN: list[tuple[str, ...]] = [
    ("hermes", "curator", "usage"),
    ("hermes", "curator", "list"),
    (_GIT, "log"),
    (_GIT, "status"),
    (_GIT, "diff"),
    (_GIT, "rev-parse"),
    (_GIT, "show"),
    (_GIT, "branch"),
    ("nvidia-smi",),
    ("python", "--version"),
]

# Dateiendungen/Pfadteile, deren Schreibzugriff technisch unvermeidbar ist und
# keine Wirkung nach aussen hat (Python-Bytecache, Temp, eigener Laufordner).
SCHREIB_FREI_TEILE = ("__pycache__", ".pyc", ".pyo")


def kommando_aktionen(kommando) -> set[str]:
    """Welche Aktionen ein Kommando bedeutet. Leere Menge = unklassifiziert."""
    if isinstance(kommando, (list, tuple)):
        text = " ".join(str(t) for t in kommando)
    else:
        text = str(kommando)
    klein = text.replace("\\", "/").lower()
    treffer = set()
    for worte, aktion in KOMMANDO_AKTION:
        if all(w in klein for w in worte):
            treffer.add(aktion)
    return treffer


def ist_nur_lesen(kommando) -> bool:
    if isinstance(kommando, (list, tuple)):
        text = " ".join(str(t) for t in kommando)
    else:
        text = str(kommando)
    klein = text.replace("\\", "/").lower()
    return any(all(w in klein for w in worte) for worte in NUR_LESEN)


def schreiben_technisch_frei(pfad: str) -> bool:
    klein = str(pfad).replace("\\", "/").lower()
    return any(teil in klein for teil in SCHREIB_FREI_TEILE)
