"""Zweites Probeskript: versucht, ausserhalb der Schreibpfade zu schreiben.

Damit wird geprueft, dass die Wache eine unerlaubte Aktion wirklich abbricht -
und zwar von aussen sichtbar (Exit 97, Verstossdatei, Zieldatei existiert nicht),
nicht nur als gute Absicht in einer SKILL.md.
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ziel", required=True)
    args, _rest = p.parse_known_args()

    with open(args.ziel, "w", encoding="utf-8") as fh:
        fh.write("das haette die Wache verhindern muessen\n")

    sys.stdout.write("probe_frech: geschrieben\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
