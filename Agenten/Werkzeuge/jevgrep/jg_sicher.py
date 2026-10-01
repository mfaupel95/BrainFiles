"""Der sichere Aufruf: erst pruefen, dann suchen.

Der Wurzel-Aufrufer `jevgrep.cmd` ruft dieses Programm statt jevgrep direkt auf.
Subkommandos (`files`, `auth`, `doctor`, `skill`, `--help`, `--version`) laufen
ungeprueft durch; eine SUCHE bekommt vorher die Vorpruefung (Anbieter, Wurzelgroesse,
Kostenschaetzung). `--trotzdem` erzwingt eine grosse Wurzel, `--leise` schweigt bei
Erfolg - beide werden hier entfernt, weil jevgrep sie nicht kennt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import vorpruefung  # noqa: E402

JG = HIER / "node_modules" / "@dzhng" / "jevgrep" / "dist" / "bin" / "index.js"


def main() -> int:
    argv = sys.argv[1:]
    nur_eigene = {"--trotzdem", "--leise"}

    if argv and argv[0] in vorpruefung.SUBCOMMANDS:
        rc = 0
    else:
        rc = vorpruefung.pruefen(argv)
    if rc != 0:
        return rc

    sauber = [a for a in argv if a not in nur_eigene]
    return subprocess.run(["node", str(JG), *sauber], cwd=None).returncode


if __name__ == "__main__":
    sys.exit(main())