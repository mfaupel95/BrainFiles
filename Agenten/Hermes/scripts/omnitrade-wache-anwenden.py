#!/usr/bin/env python3
"""Cron-Aufrufer fuer omnitrade-wache.py im Anwenden-Modus.

Der Hermes-Cron `omnitrade-waechter` (no_agent) kann dem Skript keine
Argumente geben - das Feld `script` nimmt nur den Dateinamen. Der Kern
`omnitrade-wache.py` zeigt ohne Argument NUR die VORSCHAU (berechnete
Anker-Aenderungen, kein Start/Stopp). Dieser Wrapper reicht `--anwenden`
durch, damit der Waechter tote Laeufe weiterhin neu startet.

Aufruf: python omnitrade-wache-anwenden.py   (nur durch den Cron)
"""
import importlib.util
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "omnitrade_wache", HIER / "omnitrade-wache.py")
_wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wache)

if __name__ == "__main__":
    sys.exit(_wache.main(["--anwenden"]))
