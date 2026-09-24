"""Statischer SkillSpector-Scan ueber ganze Skill-Bibliotheken.

Sammelt jeden Ordner, der DIREKT eine SKILL.md traegt, ueberspringt
byte-identische Doppel (MD5 der SKILL.md) und Ordner unter einem
Junction-Elternteil, und ruft je Skill

    <skillspector>/.venv/Scripts/skillspector.exe scan <ordner> --no-llm -f json -o <out>

auf. Ein Bericht je Skill in --out, Fortschritt in <out>/lauf.log.

Aufruf (das EXE liegt unter O:, NICHT ueber die Werkstatt-Junction):

    O:/Werkstatt/skillspector/.venv/Scripts/python.exe skillbibliothek-scan.py \
        --basis C:/Users/<user>/Documents/GitHub \
        --basis O:/Werkstatt/Repos \
        --out C:/Users/<user>/Documents/BrainFiles/Agenten/Hermes/cache/skillspector-fundus \
        --arbeiter 8

Danach auswerten: alle JSONs einlesen, `analysis_completeness.execution_successful`
pruefen (false = unvollstaendig geprueft, NICHT sauber) und die Regel-IDs
zaehlen statt die Risikowerte zu mitteln. Regelbedeutungen:
<skillspector>/src/skillspector/nodes/analyzers/pattern_defaults.py
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SP = Path("O:/Werkstatt/skillspector")
EXE = SP / ".venv/Scripts/skillspector.exe"
FRIST_S = 300
AUSLASSEN = {".git", ".venv", "venv", "node_modules", "__pycache__", ".archive", "dist", "build"}


def md5(p: Path) -> str:
    try:
        return hashlib.md5(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def ziele(basis: Path) -> list[Path]:
    gefunden = []
    for p in basis.rglob("SKILL.md"):
        d = p.parent
        if any(t in d.parts for t in AUSLASSEN):
            continue
        if any(os.path.isjunction(x) for x in [d, *d.parents]):
            continue  # SkillSpector verweigert symlink-/Junction-Eltern
        gefunden.append(d)
    return sorted(gefunden)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", action="append", required=True,
                    help="Wurzel(n) der Skill-Bibliothek, native Pfade (C:/..., O:/...)")
    ap.add_argument("--out", required=True, help="Zielordner fuer die Berichte")
    ap.add_argument("--arbeiter", type=int, default=8)
    ap.add_argument("-n", "--nur", type=int, default=0, help="nur die ersten N Skills (Probelauf)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    gesucht: list[tuple[str, Path]] = []
    gesehen: set[str] = set()
    doppelt = 0
    for basis_roh in a.basis:
        basis = Path(basis_roh)
        for d in ziele(basis):
            h = md5(d / "SKILL.md") or str(d)
            if h in gesehen:
                doppelt += 1
                continue
            gesehen.add(h)
            gesucht.append((basis.name, d))
    if a.nur:
        gesucht = gesucht[: a.nur]
    print(f"Ziele: {len(gesucht)}  (Doppelte uebersprungen: {doppelt})", flush=True)

    def scan(paar: tuple[str, Path]) -> tuple[str, str, float]:
        wurzel, d = paar
        slug = f"{wurzel}__{str(d).replace(os.sep, '__')}"[:150]
        bericht = out / f"{slug}.json"
        if bericht.exists() and bericht.stat().st_size > 0:
            return slug, "vorhanden", 0.0
        t0 = time.time()
        try:
            r = subprocess.run(
                [str(EXE), "scan", str(d), "--no-llm", "-f", "json", "-o", str(bericht)],
                capture_output=True, timeout=FRIST_S,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            rc = r.returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
        return slug, str(rc), round(time.time() - t0, 1)

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.arbeiter) as pool, \
            open(out / "lauf.log", "a", encoding="utf-8") as log:
        for slug, rc, dauer in pool.map(scan, gesucht):
            zeile = f"{rc}\t{dauer}s\t{slug}"
            print(zeile, flush=True)
            log.write(zeile + "\n")
            log.flush()
    print(f"fertig in {round(time.time() - t0)}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
