#!/usr/bin/env python
"""Welche Werte der laufenden config.yaml weichen vom Hermes-Standard ab? (rein lesend)

Warum: eine Frage wie "optimier meine Einstellungen" oder "setz X auf Standard" braucht
zuerst die LISTE der Abweichungen - aus dem Kopf geraten werden einzelne Werte vergessen,
und ein Wert, der zufaellig dem Standard entspricht, wird "korrigiert".

Aufruf (Python MIT yaml - sonst ModuleNotFoundError, das ist kein Befund):

    <HERMES_HOME>/hermes-agent/venv/Scripts/python.exe \
      Agenten/Hermes/skills/brainfiles/hermes-config-ops/scripts/config-abweichungen.py

Ausgabe je Zeile: <pfad>  IST: <wert>  SOLL: <wert>, darunter die Zahl.

Deutung:
- "<kein Standard-Schluessel>" = eigener Block (Provider, MCP-Server, a2a_agents) - kein
  Fehler, sondern der Grund, warum die Liste lang ist. Nicht alles davon ist Ballast.
- "<fehlt>" = der Standard kennt den Schluessel, die Datei setzt ihn nicht (es gilt der
  Standardwert) - meist harmlos.
- Ein Eintrag ist nur dann ein Kandidat zum Umstellen, wenn die ABWEICHUNG gewollt war.
  Vor jeder Aenderung den Leser im Code suchen (`grep -rln "<schluessel>"
  hermes-agent/hermes_cli/ hermes-agent/agent/`), nicht den Wert allein beurteilen.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.update(flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    else:
        out[prefix] = obj
    return out


def kurz(wert):
    text = json.dumps(wert, default=str)
    return text if len(text) <= 44 else text[:41] + "..."


def main(argv):
    import yaml  # bewusst spaet, damit die Fehlermeldung eindeutig ist

    home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
    pfad = Path(argv[1]) if len(argv) > 1 else home / "config.yaml"
    checkout = home / "hermes-agent"
    if str(checkout) not in sys.path:
        sys.path.insert(0, str(checkout))
    from hermes_cli.config_defaults import DEFAULT_CONFIG

    if not pfad.is_file():
        print(f"config nicht gefunden: {pfad}")
        return 2

    ist = flatten(yaml.safe_load(pfad.read_text(encoding="utf-8")) or {})
    soll = flatten(DEFAULT_CONFIG)

    zeilen = []
    for key in sorted(set(ist) | set(soll)):
        if key not in soll:
            zeilen.append((key, kurz(ist[key]), "<kein Standard-Schluessel>"))
        elif key not in ist:
            zeilen.append((key, "<fehlt>", kurz(soll[key])))
        elif ist[key] != soll[key]:
            zeilen.append((key, kurz(ist[key]), kurz(soll[key])))

    print(f"config: {pfad}")
    for key, i, s in zeilen:
        print(f"{key:<52} IST: {i:<46} SOLL: {s}")
    print(f"Abweichungen: {len(zeilen)} (Standard kennt {len(soll)} Schluessel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
