"""Skill-Inventar sammeln und als JSON/Markdown ausgeben (Kanban t_3d28119b)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from risiko_marker import RANG  # noqa: E402
from skill_bewerten import belege, eingaben  # noqa: E402
from skill_lesen import SKILLS, ZIEL, frontmatter  # noqa: E402


def sammle():
    zeilen = []
    for pfad in sorted(SKILLS.rglob("SKILL.md")):
        rel = pfad.relative_to(SKILLS).as_posix()
        if rel.startswith(".archive/"):
            continue
        text = pfad.read_text(encoding="utf-8", errors="replace")
        kopf = frontmatter(text)
        klasse, funde = belege(text)
        zeilen.append(
            {
                "name": kopf.get("name") or pfad.parent.name,
                "pfad": rel,
                "zweck": re.sub(r"\s+", " ", kopf.get("description", ""))[:160],
                "version": kopf.get("version", ""),
                "zeichen": len(text),
                "eingaben": eingaben(kopf, text),
                "nebenwirkung": klasse,
                "belege": funde,
            }
        )
    archiv = SKILLS / ".archive"
    anzahl_archiv = sum(1 for _ in archiv.rglob("SKILL.md")) if archiv.is_dir() else 0
    return {
        "quelle": SKILLS.as_posix(),
        "aktive_skills": len(zeilen),
        "archiviert": anzahl_archiv,
        "verteilung": {k: sum(1 for z in zeilen if z["nebenwirkung"] == k) for k in RANG},
        "skills": zeilen,
    }


def schreibe(daten):
    (ZIEL / "inventar.json").write_text(
        json.dumps(daten, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    md = ["# Skill-Inventar (maschinell erzeugt: scripts/inventar.py)", ""]
    md.append("Quelle: %s" % daten["quelle"])
    md.append("")
    md.append("Aktive Skills: %d, archiviert: %d" % (daten["aktive_skills"], daten["archiviert"]))
    md.append("Nebenwirkungen: " + ", ".join("%s=%d" % kv for kv in daten["verteilung"].items()))
    md.append("")
    md.append("| Skill | Nebenwirkung | Eingaben | Zweck |")
    md.append("|---|---|---|---|")
    for z in daten["skills"]:
        md.append(
            "| %s | %s | %s | %s |"
            % (
                z["pfad"],
                z["nebenwirkung"],
                ", ".join(z["eingaben"]) or "-",
                z["zweck"].replace("|", "/")[:90],
            )
        )
    md.append("")
    (ZIEL / "inventar.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
