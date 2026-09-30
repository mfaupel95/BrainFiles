"""Pfade und Frontmatter-Leser fuer das Skill-Inventar (Kanban t_3d28119b)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve().parent
ZIEL = HIER.parent
SKILLS = Path(
    "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/profiles"
    "/one-skill-to-rule-them-all/skills"
)


def frontmatter(text):
    """YAML-Kopf flach einlesen; mehrzeilige Werte werden zusammengefaltet."""
    if not text.startswith("---"):
        return {}
    ende = text.find("\n---", 3)
    if ende < 0:
        return {}
    kopf = {}
    feld = None
    for zeile in text[3:ende].splitlines():
        treffer = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", zeile)
        if treffer:
            feld = treffer.group(1)
            kopf[feld] = treffer.group(2).strip()
        elif feld and zeile.strip():
            kopf[feld] = (kopf[feld] + " " + zeile.strip()).strip()
    return kopf
