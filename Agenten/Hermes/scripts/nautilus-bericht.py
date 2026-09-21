#!/usr/bin/env python3
"""Cron-Huelle: Nautilus-Bericht.

Der Bericht selbst liegt in `Agenten/Handel/nautilus/bericht.py` und braucht das
NAUTILUS-VENV (er importiert `trailing_stop_strategie`, und das zieht
nautilus_trader). Der Hermes-Cron startet Skripte aber mit dem eigenen
Interpreter - deshalb ruft diese Huelle den richtigen Interpreter als
Unterprozess und gibt dessen Ausgabe unveraendert weiter.

Leere Ausgabe gibt es hier nicht: der Bericht hat immer etwas zu sagen. Wer ihn
nicht taeglich will, schaltet den Job ab - nicht den Bericht.

Aufruf (Hermes-Cron, no_agent, taeglich 09:00): python nautilus-bericht.py
"""

import subprocess
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
PY = HANDEL / "nautilus" / ".venv" / "Scripts" / "python.exe"
BERICHT = HANDEL / "nautilus" / "bericht.py"


def main() -> int:
    if not PY.is_file():
        print("Nautilus-Bericht: Interpreter fehlt (%s) - nautilus/.venv neu bauen."
              % PY)
        return 0
    p = subprocess.run([str(PY), str(BERICHT), "--kurz"],
                       capture_output=True, text=True, timeout=300)
    aus = (p.stdout or "").strip()
    if not aus:
        print("Nautilus-Bericht: keine Ausgabe (Rueckgabecode %s) - %s"
              % (p.returncode, (p.stderr or "").strip()[:200]))
        return 0
    print(aus)
    return 0


if __name__ == "__main__":
    sys.exit(main())
