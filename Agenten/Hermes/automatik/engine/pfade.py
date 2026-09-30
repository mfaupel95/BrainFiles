"""Pfade und Einstellungen der Auto-Ausfuehrungs-Engine.

Alles ist ueber Umgebungsvariablen umstellbar, damit Tests in einem eigenen
Verzeichnis laufen und die Engine im Betrieb nichts anfassen muss, was ihr
nicht gehoert.

HERMES_AUTOMATIK_BASIS      Arbeitsverzeichnis (Log, Zustand, Nachrichten-Eingang)
HERMES_AUTOMATIK_WURZEL     Wurzel fuer relative Pfade der Registry (BrainFiles)
HERMES_AUTOMATIK_KANBAN_DB  Kanban-Datenbank fuer den board_event-Trigger
HERMES_AUTOMATIK_VALIDATOR  Pfad zu registry_pruefen.py (eine Implementierung der Regeln)
HERMES_AUTOMATIK_REGISTRY   Standard-Registry, wenn die CLI keine nennt
HERMES_AUTOMATIK_SKRIPTPFADE  Zusaetzliche Skript-Verzeichnisse (os.pathsep-getrennt)
HERMES_AUTOMATIK_HERMES_BIN Binary fuer skill_art=skill (Standard: Hermes/bin/hermes.exe)
HERMES_AUTOMATIK_SKILL_START 1 = Skill-Laeufe wirklich starten (Standard: nein, siehe lauf.py)
"""
from __future__ import annotations

import os
from pathlib import Path

HIER = Path(__file__).resolve().parent
WORKSPACE = HIER.parent
HERMES = Path("C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes")
BRAINFILES = Path("C:/Users/faupe/Documents/BrainFiles")


def _pfad(name: str, standard: Path) -> Path:
    wert = os.environ.get(name)
    return Path(wert) if wert else standard


def basis() -> Path:
    p = _pfad("HERMES_AUTOMATIK_BASIS", WORKSPACE / "arbeit")
    p.mkdir(parents=True, exist_ok=True)
    return p


def wurzel() -> Path:
    """Wurzel, auf die sich relative Registry-Pfade beziehen."""
    return _pfad("HERMES_AUTOMATIK_WURZEL", BRAINFILES)


def log_datei() -> Path:
    return basis() / "laeufe.jsonl"


def zustand_datei() -> Path:
    return basis() / "zustand.db"


def nachrichten_eingang() -> Path:
    p = basis() / "nachrichten"
    p.mkdir(parents=True, exist_ok=True)
    return p


def kanban_db() -> Path:
    return _pfad("HERMES_AUTOMATIK_KANBAN_DB", HERMES / "kanban.db")


def validator() -> Path:
    return _pfad(
        "HERMES_AUTOMATIK_VALIDATOR",
        WORKSPACE / "spez" / "scripts" / "registry_pruefen.py",
    )


def standard_registry() -> Path:
    return _pfad(
        "HERMES_AUTOMATIK_REGISTRY",
        WORKSPACE / "betrieb" / "registry.yaml",
    )


def skriptpfade() -> list[Path]:
    """Wo skill_art=skript gesucht wird - gleiche Liste wie im Validator."""
    pfade = [validator().parent, HERMES / "scripts"]
    extra = os.environ.get("HERMES_AUTOMATIK_SKRIPTPFADE", "")
    for teil in extra.split(os.pathsep):
        if teil.strip():
            pfade.append(Path(teil.strip()))
    return pfade


def hermes_bin() -> Path:
    return _pfad("HERMES_AUTOMATIK_HERMES_BIN", HERMES / "bin" / "hermes.exe")


def skill_start_frei() -> bool:
    return os.environ.get("HERMES_AUTOMATIK_SKILL_START", "") == "1"


def absolut(pfad: str) -> Path:
    """Registry-Pfad (relativ zur Wurzel oder absolut) zu einem echten Pfad."""
    p = Path(pfad)
    return p if p.is_absolute() else (wurzel() / p)
