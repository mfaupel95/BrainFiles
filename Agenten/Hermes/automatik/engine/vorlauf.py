"""Vorlauf: installiert die Wache und startet dann das eigentliche Skript.

Aufruf (macht die Engine, nicht der Mensch):
    python engine/vorlauf.py <skript.py> [argumente...]

Der Audit-Hook MUSS vor dem ersten Byte des Skripts stehen, sonst kann das
Skript vor der Grenze schreiben. Darum dieser Zwischenstart: Hook setzen, dann
runpy mit run_name="__main__", damit sich das Skript wie ein normaler Start
verhaelt (argv, __main__-Block, relative Pfade ueber __file__).

Exit-Codes:
    97  Wache hat abgebrochen (Aktion ausserhalb erlaubte_aktionen)
    98  Vorlauf selbst kaputt (Skript fehlt, Hook nicht setzbar)
    sonst: Exit des Skripts
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER.parent) not in sys.path:
    sys.path.insert(0, str(HIER.parent))

from engine import wache  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("vorlauf: kein Skript genannt\n")
        return 98
    skript = Path(sys.argv[1])
    if not skript.exists():
        sys.stderr.write("vorlauf: Skript fehlt: %s\n" % skript)
        return 98

    # Ohne Konfiguration laeuft die Wache nicht - dann darf auch das Skript
    # nicht laufen, sonst waere die Grenze lautlos weg.
    if not wache.installieren():
        if os.environ.get("HERMES_AUTOMATIK_WACHE"):
            sys.stderr.write("vorlauf: Wache nicht installierbar\n")
            return 98
        sys.stderr.write("vorlauf: keine Wache-Konfiguration (HERMES_AUTOMATIK_WACHE)\n")
        return 98

    sys.argv = [str(skript)] + sys.argv[2:]
    try:
        runpy.run_path(str(skript), run_name="__main__")
    except SystemExit as e:
        code = e.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        sys.stderr.write(str(code) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
