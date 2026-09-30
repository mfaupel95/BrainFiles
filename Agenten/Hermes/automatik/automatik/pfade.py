"""Wo Engine und Reaktionsschicht liegen - eine Stelle, alles umstellbar.

Die beiden Vorgaenger-Tasks haben je einen eigenen Workspace und je eigene
Umgebungsvariablen. Diese Datei ist der einzige Ort, an dem beide Welten
zusammenkommen; jeder Pfad ist ueber eine Variable umstellbar, damit der Test
in einem eigenen Verzeichnis laeuft und den Betrieb nicht anfasst.

HERMES_AUTOMATIK_ENGINE    Workspace der Engine (t_9f7db046)
HERMES_AUTOMATIK_REAKTION  Workspace der Reaktionsschicht (t_f682e5c1)
HERMES_AUTOMATIK_BASIS     Arbeitsordner der Engine (Log, Zustand) - wie Engine
HERMES_AUTOMATIK_REGISTRY  Registry, die gefahren wird - wie Engine
HERMES_AUTOMATIK_KOPPLUNG  Arbeitsordner DIESER Schicht (Marken, Protokoll)
HERMES_AUTOMATIK_REAKTIONSKONFIG  reaktionen.yaml
HERMES_AUTOMATIK_ABLAGE   Zustandsdateien der Reaktionsschicht (Test: eigener Ordner)

Absichtlich werden HERMES_AUTOMATIK_BASIS und _REGISTRY NICHT umbenannt: die
Kopplung fuehrt keinen zweiten Zustand ein. Wer den Tick von Hand startet und
danach die Kopplung, arbeitet garantiert auf demselben Log.
"""
from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
GESCHWISTER = WORKSPACE.parent

# Im konsolidierten Home liegen Engine, Reaktionsschicht und Kopplung im
# SELBEN Ordner (Agenten/Hermes/automatik/). Der GESCHWISTER-Default der
# Vorgaenger-Workspaces (kanban/workspaces/t_*) existiert hier nicht mehr;
# beide Standards zeigen deshalb auf WORKSPACE selbst. Ueber
# HERMES_AUTOMATIK_ENGINE / _REAKTION bleibt jeder Pfad umstellbar.
STANDARD_ENGINE = WORKSPACE
STANDARD_REAKTION = WORKSPACE


def _pfad(name: str, standard: Path) -> Path:
    wert = os.environ.get(name)
    return Path(wert) if wert else standard


def engine() -> Path:
    return _pfad("HERMES_AUTOMATIK_ENGINE", STANDARD_ENGINE)


def reaktion() -> Path:
    return _pfad("HERMES_AUTOMATIK_REAKTION", STANDARD_REAKTION)


def basis() -> Path:
    """Arbeitsordner der Engine - dort liegt laeufe.jsonl und zustand.db."""
    p = _pfad("HERMES_AUTOMATIK_BASIS", engine() / "betrieb" / "arbeit")
    p.mkdir(parents=True, exist_ok=True)
    return p


def registry() -> Path:
    return _pfad("HERMES_AUTOMATIK_REGISTRY", engine() / "betrieb" / "registry.yaml")


def kopplung() -> Path:
    """Eigener Arbeitsordner: Marken und Protokoll dieser Schicht."""
    p = _pfad("HERMES_AUTOMATIK_KOPPLUNG", WORKSPACE / "arbeit")
    p.mkdir(parents=True, exist_ok=True)
    return p


def reaktionskonfig() -> Path:
    return _pfad(
        "HERMES_AUTOMATIK_REAKTIONSKONFIG", reaktion() / "reaktionen.yaml"
    )


def ablage() -> Path:
    """Ordner der vier Zustandsdateien der Reaktionsschicht.

    Die Reaktionsschicht legt Protokoll, Zustand, Nachlauf und Sperren neben
    ihren Code (reaktion.Ablage). Fuer einen Testlauf muss dieser Ordner
    getrennt umstellbar sein: sonst schreibt jeder Probelauf in den echten
    Zustand und der naechste Betriebslauf rechnet mit Testzahlen weiter.
    """
    return _pfad("HERMES_AUTOMATIK_ABLAGE", reaktion())


def log_datei() -> Path:
    """Das Uebergabe-Log der Engine (JSONL, nur angehaengt)."""
    return basis() / "laeufe.jsonl"


def marken_datei() -> Path:
    return kopplung() / "kopplung.json"


def protokoll_datei() -> Path:
    return kopplung() / "kopplung-log.jsonl"


def module_einhaengen() -> None:
    """Beide Workspaces auf sys.path - genau einmal, in fester Reihenfolge.

    Warum nicht importieren und gut: beide Seiten sind Ordner ohne Paketnamen
    (engine/ ist ein Paket IM Workspace, reaktion.py liegt flach). Ein fester
    Einhaengepunkt haelt die Importe der Vorgaenger unveraendert lauffaehig -
    eine Kopie ihrer Dateien waere sofort veraltet.
    """
    import sys

    for ordner in (engine(), reaktion()):
        s = str(ordner)
        if s not in sys.path:
            sys.path.insert(0, s)
