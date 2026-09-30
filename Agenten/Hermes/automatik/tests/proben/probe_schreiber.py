"""Probeskript fuer die Engine-Tests: schreibt genau eine Datei.

Das Skript ist absichtlich dumm und laut: es legt die Zieldatei an und schreibt
hinein, was es ueber seinen Lauf weiss. Damit ist in den Tests nachweisbar, dass
wirklich DIESER Prozess gelaufen ist - nicht nur, dass die Engine 'erfolg'
gemeldet hat.

Aufruf durch die Engine (ueber vorlauf.py, Parameter aus der Registry):
    probe_schreiber.py --ziel <pfad> [--text <wort>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ziel", required=True)
    p.add_argument("--text", default="gelaufen")
    p.add_argument("--exit", type=int, default=0)
    args, _rest = p.parse_known_args()

    inhalt = {
        "text": args.text,
        "pid": os.getpid(),
        "regel": os.environ.get("HERMES_AUTOMATIK_REGEL", ""),
        "trigger": os.environ.get("HERMES_AUTOMATIK_TRIGGER", ""),
    }
    with open(args.ziel, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(inhalt, ensure_ascii=False))
    sys.stdout.write("probe_schreiber: %s\n" % args.ziel)
    return args.exit


if __name__ == "__main__":
    raise SystemExit(main())
