#!/usr/bin/env python3
"""Skill-Bibliothek entdoppeln und ungenutzte Fremd-Baeume weglegen.

WARUM: Jeder geladene Skill kostet Name + Beschreibung in JEDER Anfrage.
Gemessen 21.09.2026: 331 SKILL.md, ~78.900 Zeichen (~19.700 Token) Dauerlast -
davon sind 44 Namen mehrfach vorhanden (116 Eintraege) und mehrere Baeume
komplett ungenutzt.

REGEL, nach der entschieden wird (nicht nach Bauchgefuehl):
  1. Ein Baum, aus dem NIE ein Skill benutzt wurde, wird als Ganzes weggelegt.
  2. Ein Baum mit wenigen genutzten Skills behaelt genau diese; der Rest geht weg.
  3. Byte-identische Doppel: nur EINE Fassung bleibt, und zwar die im
     benutzten Baum.
  4. Eigene Arbeit (brainfiles, software-development, autonomous-ai-agents,
     claude-code-imports, github, productivity, handel, ...) wird NIE angefasst.

Weggelegt heisst: nach `skills/.archive/<baum>/` verschoben - Hermes laedt von
dort nicht, `hermes curator restore` bzw. ein Rueckschieben holt alles zurueck.
Nichts wird geloescht.

    python skills-entdoppeln.py            # nur zeigen (Trockenlauf)
    python skills-entdoppeln.py --anwenden # wirklich verschieben
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
SKILLS = HERMES / "skills"
ARCHIV = SKILLS / ".archive"

# Baeume, die unangetastet bleiben - eigene Arbeit und alles, was benutzt wird.
UNANTASTBAR = {
    "brainfiles", "software-development", "autonomous-ai-agents",
    "claude-code-imports", "github", "productivity", "handel", "chat",
    "journal-spiegelung", "note-taking", "mlops", "devops", "creative",
    "email", "media", "system", "one-skill-to-rule-them-all",
}


def skills_im_baum(baum: Path):
    for p in baum.rglob("SKILL.md"):
        if ".archive" in p.parts or ".curator_backups" in p.parts:
            continue
        yield p


def name_von(p: Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")[:1500]
    m = re.search(r"^name:\s*(.+)$", t, re.M)
    return (m.group(1).strip() if m else p.parent.name).lower()


def beschreibung_von(p: Path) -> str:
    t = p.read_text(encoding="utf-8", errors="replace")[:2500]
    m = re.search(r"^description:\s*(.+)$", t, re.M)
    return m.group(1).strip() if m else ""


def genutzte_namen() -> set:
    """Namen mit use-Zaehler > 0, aus `hermes curator usage`."""
    import subprocess
    umg = dict(os.environ)
    for k in ("PYTHONHOME", "PYTHONPATH"):
        umg.pop(k, None)
    exe = HERMES / "bin" / "hermes.exe"
    p = subprocess.run([str(exe), "curator", "usage"], capture_output=True,
                       text=True, timeout=600, env=umg, cwd=str(HERMES))
    raus = set()
    for z in (p.stdout or "").splitlines():
        teile = z.split()
        if len(teile) >= 6 and teile[-1] != "never":
            # Name kann Leerzeichen haben: alles vor der origin-Spalte.
            for i, t in enumerate(teile):
                if t in ("agent", "bundled", "hub", "local"):
                    name = " ".join(teile[:i]).strip().lower()
                    try:
                        if int(teile[i + 1]) > 0:
                            raus.add(name)
                    except (ValueError, IndexError):
                        pass
                    break
    return raus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true",
                    help="wirklich verschieben (ohne: nur zeigen)")
    a = ap.parse_args()

    genutzt = genutzte_namen()
    print("genutzte Skill-Namen laut curator: %d" % len(genutzt))

    baeume = {}
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d.is_symlink() or os.path.islink(str(d))
                or getattr(os.path, "isjunction", lambda _p: False)(str(d))):
            # Junction/Symlink (die okx-* zeigen auf ~/.agents/skills). Ein
            # Verschieben wuerde nur den Verweis umhaengen und die Quelle
            # fuer andere Agenten mitreissen - Finger weg. Achtung: Python
            # meldet eine Windows-Junction NICHT als symlink, nur
            # os.path.isjunction erkennt sie (gemessen 21.09.2026).
            continue
        ps = list(skills_im_baum(d))
        if not ps:
            continue
        namen = {name_von(p): p for p in ps}
        baeume[d.name] = {"pfad": d, "skills": ps, "namen": namen,
                          "genutzt": sorted(n for n in namen if n in genutzt)}

    weg_ganz, weg_teil, last_vorher, last_nachher = [], [], 0, 0
    for baum, b in baeume.items():
        for p in b["skills"]:
            last_vorher += len(name_von(p)) + len(beschreibung_von(p)) + 6
        if baum in UNANTASTBAR:
            for p in b["skills"]:
                last_nachher += len(name_von(p)) + len(beschreibung_von(p)) + 6
            continue
        if not b["genutzt"]:
            weg_ganz.append(baum)
        else:
            behalten = set(b["genutzt"])
            fuer_weg = [p for p in b["skills"] if name_von(p) not in behalten]
            if fuer_weg:
                weg_teil.append((baum, fuer_weg, sorted(behalten)))
            for p in b["skills"]:
                if name_von(p) in behalten:
                    last_nachher += len(name_von(p)) + len(beschreibung_von(p)) + 6

    print("\n=== Baeume, aus denen NIE etwas benutzt wurde (ganz weg) ===")
    n_ganz = 0
    for baum in weg_ganz:
        k = len(baeume[baum]["skills"])
        n_ganz += k
        print("  %-38s %3d Skills" % (baum, k))
    print("\n=== Baeume, die nur ihre genutzten behalten ===")
    n_teil = 0
    for baum, fuer_weg, behalten in weg_teil:
        n_teil += len(fuer_weg)
        print("  %-38s %3d weg, behaelt: %s" % (baum, len(fuer_weg),
                                                ", ".join(behalten)))

    print("\nDauerlast je Anfrage: %d -> %d Zeichen (~%d -> ~%d Token)"
          % (last_vorher, last_nachher, last_vorher // 4, last_nachher // 4))
    print("weggelegt: %d Skills (%d ganze Baeume, %d einzeln)"
          % (n_ganz + n_teil, n_ganz, n_teil))

    if not a.anwenden:
        print("\nTrockenlauf - nichts verschoben. Mit --anwenden ausfuehren.")
        return 0

    ARCHIV.mkdir(parents=True, exist_ok=True)
    for baum in weg_ganz:
        ziel = ARCHIV / baum
        if ziel.exists():
            print("  schon im Archiv, uebersprungen: %s" % baum)
            continue
        shutil.move(str(baeume[baum]["pfad"]), str(ziel))
        print("  verschoben: %s -> .archive/" % baum)
    for baum, fuer_weg, _ in weg_teil:
        for p in fuer_weg:
            rel = p.parent.relative_to(SKILLS)
            ziel = ARCHIV / rel
            if ziel.exists():
                continue
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p.parent), str(ziel))
        print("  ausgeduennt: %s" % baum)
    print("\nFertig. Zurueckholen: Ordner aus skills/.archive/ zurueckschieben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
