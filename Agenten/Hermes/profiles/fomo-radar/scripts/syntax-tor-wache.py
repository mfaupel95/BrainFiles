#!/usr/bin/env python3
"""Wrapper: fahert das geteilte Syntax-Tor fuer dieses Hermes-Profil.

Das eigentliche Werkzeug liegt an EINER Stelle im geteilten Baum:
    Agenten/Hermes/scripts/syntax-tor-wache.py

Der Cron dieses Profils loest `script` aber relativ zu
`profiles/fomo-radar/scripts/` auf. Statt den Code zu kopieren (zwei Fassungen
driften auseinander - genau die Fehlerklasse, gegen die diese Wache gebaut ist)
startet dieser Wrapper das geteilte Skript als Kindprozess und reicht dessen
Ausgabe und Exit-Code durch. Leere Ausgabe = kein Befund = nichts senden.
"""
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[4]                       # scripts -> fomo-radar -> profiles -> Hermes -> Agenten
ZIEL = WURZEL / "Hermes" / "scripts" / "syntax-tor-wache.py"
PY = WURZEL / "Handel" / "scanner" / ".venv" / "Scripts" / "python.exe"

if not ZIEL.exists():
    print("syntax-tor-wache: geteiltes Skript fehlt (%s)" % ZIEL)
    raise SystemExit(1)

lauf = [str(PY) if PY.exists() else sys.executable, str(ZIEL)] + sys.argv[1:]
p = subprocess.run(lauf, capture_output=True, text=True, errors="replace")
# Die SyntaxWarnings des Baums nicht als Befund ausgeben.
for zeile in p.stdout.splitlines():
    if zeile.startswith("SYNTAX-TOR") or zeile.strip().startswith("Agenten"):
        print(zeile)
    elif "Befund" in zeile or "Hinweis" in zeile:
        print(zeile)
raise SystemExit(p.returncode)
