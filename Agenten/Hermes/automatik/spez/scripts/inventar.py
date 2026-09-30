"""Skill-Inventar erzeugen (Kanban t_3d28119b).

Baut inventar.json und inventar.md aus allen aktiven SKILL.md des Profils
one-skill-to-rule-them-all. Die Nebenwirkungsklasse jedes Skills wird belegt
(Marker + Zeilennummer), nicht geschaetzt.

Module: skill_lesen.py (Pfade/Frontmatter), risiko_marker.py (Markerlisten),
skill_bewerten.py (Belege/Eingaben), skill_sammeln.py (Sammeln/Schreiben).

Aufruf:
  python scripts/inventar.py
  python scripts/inventar.py --print
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_lesen import SKILLS  # noqa: E402
from skill_sammeln import sammle, schreibe  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="zeige", action="store_true")
    args = ap.parse_args()

    if not SKILLS.is_dir():
        print("Skill-Verzeichnis fehlt: %s" % SKILLS)
        return 2

    daten = sammle()
    schreibe(daten)
    print("inventar.json + inventar.md geschrieben: %d Skills" % daten["aktive_skills"])
    print("Verteilung: " + ", ".join("%s=%d" % kv for kv in daten["verteilung"].items()))
    if args.zeige:
        for z in daten["skills"]:
            print(" %-12s %s" % (z["nebenwirkung"], z["pfad"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
