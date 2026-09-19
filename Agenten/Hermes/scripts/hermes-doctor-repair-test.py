#!/usr/bin/env python
"""Wrapper fuer den EINMALIGEN Repair-Endtest nach dem Claude-Code-Rate-Limit-Reset.

Der Cron-Scheduler ruft Skripte OHNE Argumente auf (script-Feld ist nur ein
Pfad). Dieser Wrapper reicht --repair --aufgabe "<harmlose Aufgabe>" --max-turns 3
an hermes-doctor.py weiter.

Die Aufgabe ist BEWUSST harmlos: nur TODO-Kommentare zaehlen und befund.json
schreiben - KEIN Code aendern, KEINE Tests, KEIN Commit. Das prueft die volle
Repair-Pipeline (Worktree anlegen -> CLAUDE.md kopieren -> claude im WORKTREE
laufen lassen -> befund.json lesen -> Worktree entfernen), ohne den
Live-Checkout zu beruehren.
"""
import runpy
import sys

AUFGABE = (
    "Zaehle die TODO-Kommentare in den .py-Dateien des Checkouts "
    "(git grep -n 'TODO' -- '*.py' | wc -l) und schreibe das Ergebnis als "
    "befund.json in das Worktree-Wurzelverzeichnis. Aendere KEINEN Code, "
    "fuehre KEINE Tests aus, committe NICHTS. Das ist ein reiner "
    "Funktionstest der Doctor-Reparatur-Pipeline."
)

sys.argv = ["hermes-doctor.py", "--repair", "--aufgabe", AUFGABE, "--max-turns", "3"]
runpy.run_path("hermes-doctor.py", run_name="__main__")
