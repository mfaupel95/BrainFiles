#!/usr/bin/env python3
"""Bestand der Haus-Codebasis: Umfang, Hotspots, Doppelungen, Tests.

Der Anlass: die Frage "wie gross ist unser Handelssystem" ergab 634.815 Zeilen -
davon 513.266 aus einem fremden Projekt (`Agenten/Handel/OpenAlice`). Diese Zahl
ist ohne die Grenze wertlos. `bestand.py` benutzt deshalb die eine Quelle
(`Agenten/Werkzeuge/fremd.py` -> `Agenten/FREMD-Liste.json`) und zaehlt
standardmaessig NUR eigenen Code.

Aufruf (aus der BrainFiles-Wurzel oder absolut):

    python Agenten/Werkzeuge/bestand.py                     # eigener Code
    python Agenten/Werkzeuge/bestand.py --mit-fremd         # alles, zum Vergleich
    python Agenten/Werkzeuge/bestand.py --bereich Agenten/Handel
    python Agenten/Werkzeuge/bestand.py --json

Rein lesend, nur Standardbibliothek. Gesperrte Ordner (venvs, Caches, Klone,
Laufzeitdaten) werden VOR dem Abstieg abgeschnitten - sonst laeuft der Lauf in
eine Python-Installation hinein und braucht Minuten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

import fremd  # noqa: E402

BEREICHE = (
    "Agenten/Handel", "Agenten/Bus", "Agenten/Werkzeuge", "Agenten/MCP-Server",
    "Agenten/Routinen", "Agenten/Hermes/scripts", "Agenten/Hermes/skills",
    "Werkstatt",
)
# Namen, die in KEINEM Bereich betreten werden. Bewusst als Namen, nicht als
# Muster - ein Muster traefe sonst ein echtes Projekt.
OHNE = {
    ".venv", "venv", "__pycache__", "node_modules", ".git", ".archive", "tools",
    ".previous-python", "cache", "site-packages", "dist", "build", "target",
    ".mypy_cache", ".pytest_cache", "user_data", "hub", "logs", "daten",
}
ENDUNGEN = {".py", ".ps1", ".sh", ".cmd", ".bat"}
MERKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")


def dateien_sammeln(wurzel: Path, bereiche, mit_fremd: bool) -> list[Path]:
    eintraege = fremd.laden(wurzel) if not mit_fremd else []
    gefunden: list[Path] = []
    for b in bereiche:
        basis = wurzel / b
        if not basis.is_dir():
            continue
        for ordner, unterordner, namen in os.walk(basis):
            unterordner[:] = [o for o in unterordner
                              if o not in OHNE and not o.startswith(".previous")]
            for n in namen:
                if Path(n).suffix.lower() not in ENDUNGEN:
                    continue
                p = Path(ordner) / n
                if not mit_fremd and fremd.ist_fremd(p.relative_to(wurzel).as_posix(),
                                                     eintraege) is not None:
                    continue
                gefunden.append(p)
    return gefunden


def zeilen(p: Path) -> int:
    try:
        return p.read_bytes().count(b"\n") + 1
    except OSError:
        return 0


def messen(wurzel: Path, bereiche, mit_fremd: bool) -> dict:
    dateien = dateien_sammeln(wurzel, bereiche, mit_fremd)
    groessen = {p: zeilen(p) for p in dateien}

    je_bereich: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for p in dateien:
        rel = p.relative_to(wurzel).as_posix()
        for b in bereiche:
            if rel.startswith(b):
                je_bereich[b][0] += 1
                je_bereich[b][1] += groessen[p]
                break

    nach_hash: dict[str, list[str]] = defaultdict(list)
    for p in dateien:
        try:
            roh = p.read_bytes()
        except OSError:
            continue
        if len(roh) >= 2000:
            nach_hash[hashlib.md5(roh).hexdigest()].append(p.relative_to(wurzel).as_posix())
    doppel = {h: v for h, v in nach_hash.items() if len(v) > 1}

    merker = []
    for p in dateien:
        try:
            n = len(MERKER.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
        if n:
            merker.append((n, p.relative_to(wurzel).as_posix()))

    tests = [p for p in dateien
             if p.name.startswith("test_") or "/tests/" in p.as_posix()]
    gesamt = sum(groessen.values())
    testzeilen = sum(groessen[p] for p in tests)

    return {
        "mit_fremd": mit_fremd,
        "dateien": len(dateien),
        "zeilen": gesamt,
        "je_bereich": {b: {"dateien": v[0], "zeilen": v[1]}
                       for b, v in sorted(je_bereich.items(), key=lambda kv: -kv[1][1])},
        "hotspots": [(groessen[p], p.relative_to(wurzel).as_posix())
                     for p in sorted(dateien, key=lambda x: groessen[x], reverse=True)[:12]],
        "doppelte_gruppen": len(doppel),
        "doppelte_beispiele": [v for _, v in sorted(doppel.items(), key=lambda kv: -len(kv[1]))[:5]],
        "merker_dateien": len(merker),
        "merker_top": sorted(merker, reverse=True)[:5],
        "tests": {"dateien": len(tests), "zeilen": testzeilen,
                  "anteil": round(testzeilen / gesamt, 4) if gesamt else 0.0},
    }


def bericht(m: dict) -> str:
    kopf = "MIT Fremd-Material" if m["mit_fremd"] else "NUR eigener Code (ohne Fremd-Material)"
    z = [
        f"Bestand - {kopf}",
        f"{m['dateien']} Dateien, {m['zeilen']} Zeilen",
        "",
        "Umfang je Bereich:",
    ]
    for b, v in m["je_bereich"].items():
        z.append(f"  {b:<32} {v['dateien']:>5} Dateien {v['zeilen']:>9} Zeilen")
    z += ["", "Groesste Einzeldateien:"]
    for n, p in m["hotspots"]:
        z.append(f"  {n:>7} Zeilen  {p}")
    z += ["", f"Doppelte Inhalte (byte-gleich, ab 2 kB): {m['doppelte_gruppen']} Gruppen"]
    for v in m["doppelte_beispiele"]:
        z.append(f"  {len(v)}x: " + " | ".join(v[:3]))
    z += ["", f"Merker (TODO/FIXME/HACK/XXX): {m['merker_dateien']} Dateien"]
    for n, f in m["merker_top"]:
        z.append(f"  {n:>3}  {f}")
    t = m["tests"]
    z += ["", f"Tests: {t['dateien']} Dateien, {t['zeilen']} Zeilen "
              f"({t['anteil']:.0%} des Codes)"]
    if not m["mit_fremd"]:
        z += ["", "Ohne Fremd-Material. Zum Vergleich: --mit-fremd "
                  "(Quelle: Agenten/FREMD-Liste.json)"]
    return "\n".join(z)


def main() -> int:
    p = argparse.ArgumentParser(description="Bestand der Haus-Codebasis")
    p.add_argument("--mit-fremd", action="store_true",
                   help="auch fremdes Material mitzaehlen (Klone, Fremdprojekte)")
    p.add_argument("--bereich", action="append", default=None,
                   help="nur dieser Bereich (mehrfach moeglich)")
    p.add_argument("--json", action="store_true", help="Maschinenlesbar")
    a = p.parse_args()

    wurzel = fremd.wurzel()
    bereiche = tuple(a.bereich) if a.bereich else BEREICHE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    m = messen(wurzel, bereiche, a.mit_fremd)
    print(json.dumps(m, indent=2, ensure_ascii=False) if a.json else bericht(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())