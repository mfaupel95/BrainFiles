#!/usr/bin/env python3
"""Cron-Huelle fuer den Zeitversatz-Sammler (Hermes-Cron, no_agent).

Der Sammler selbst wohnt bei der Handelsspur
(`Agenten/Handel/zeitversatz_messen.py`) - dort gehoeren die Messwerkzeuge hin,
das Journal der Kopier-Spuren liegt daneben. Der Cron darf nur Skripte aus
`Agenten/Hermes/scripts/` starten, deshalb diese duenne Huelle: sie ruft das
Werkzeug mit dem scanner-venv auf und reicht ihm die Argumente durch.

Aufruf (Cron, alle 10 Minuten):
    python zeitversatz-sammeln.py            # sammelt, schweigt

Von Hand:
    python zeitversatz-sammeln.py --bericht  # Auswertung zeigen

LEERE AUSGABE = nichts senden (Wächter-Muster). Ein Fehler des Sammelwerks
wird gemeldet, damit ein stiller Ausfall nicht wie "keine Signale" aussieht.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
WERKZEUG = HANDEL / "zeitversatz_messen.py"
PYTHON = HANDEL / "scanner" / ".venv" / "Scripts" / "python.exe"


def main() -> int:
    if not WERKZEUG.is_file():
        print("Zeitversatz-Sammler fehlt: %s" % WERKZEUG)
        return 1
    python = str(PYTHON) if PYTHON.is_file() else sys.executable
    umgebung = dict(os.environ)
    umgebung.pop("PYTHONHOME", None)
    umgebung.pop("PYTHONPATH", None)
    lauf = subprocess.run([python, str(WERKZEUG), *sys.argv[1:]],
                          cwd=str(HANDEL), capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                          encoding="utf-8", errors="replace", env=umgebung,
                          timeout=600)
    aus = (lauf.stdout or "").strip()
    if lauf.returncode != 0:
        print("Zeitversatz-Sammler endete mit %d" % lauf.returncode)
        if (lauf.stderr or "").strip():
            print((lauf.stderr or "").strip()[-400:])
        return 1
    if aus:
        print(aus)
    return 0


if __name__ == "__main__":
    sys.exit(main())