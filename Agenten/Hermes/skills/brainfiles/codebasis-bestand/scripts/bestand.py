"""Bestand der eigenen Codebasis messen: Umfang, Hotspots, Doppelungen, Merker.

Rein lesend. Geht mit os.walk und schneidet gesperrte Ordner VOR dem Abstieg ab -
rglob und `find -exec cat` laufen in die venvs hinein und brauchen Minuten.

    python scripts/bestand.py                          # Standard-Wurzeln
    python scripts/bestand.py --ohne Agenten/Handel/OpenAlice
    python scripts/bestand.py --wurzeln Agenten/Handel --top 10 --json

Fremde Baeume ausdruecklich ausschliessen und BEIDE Zahlen nennen: die Zahl ohne
Fremde ist die Antwort auf "wie gross ist unser Code".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

# Ordner, in denen nie eigener Code liegt (Interpreter, Caches, Fremdinstallationen).
OHNE = {
    ".venv", "venv", "__pycache__", "node_modules", ".git", ".archive", "tools",
    "cache", "site-packages", "dist", "build", "target", ".mypy_cache",
    ".pytest_cache", "logs", "daten", "hub", "user_data", ".idea", ".vscode",
}
ENDUNGEN = {".py", ".ps1", ".sh", ".cmd"}
MERKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
STANDARD_WURZELN = (
    "Agenten/Handel,Agenten/Bus,Agenten/Werkzeuge,Agenten/Routinen,"
    "Agenten/MCP-Server,Agenten/Hermes/scripts"
)


def wurzel_finden(start: Path) -> Path:
    """Die BrainFiles-Wurzel ueber ihre Merkmale finden, nicht ueber die Tiefe.

    Ein `parents[n]` bricht, sobald das Skript eine Ebene tiefer liegt - und
    laeuft dann still auf ein falsches Verzeichnis.
    """
    for kandidat in (start, *start.parents):
        if (kandidat / "Agenten").is_dir() and (kandidat / "MaxHirn").is_dir():
            return kandidat
    raise SystemExit("BrainFiles-Wurzel nicht gefunden - --wurzel angeben")


def zeilen(pfad: Path) -> int:
    try:
        return pfad.read_bytes().count(b"\n") + 1
    except OSError:
        return 0


def sammeln(wurzel: Path, bereiche: list[str], ohne: set[str]) -> list[Path]:
    dateien: list[Path] = []
    for bereich in bereiche:
        basis = wurzel / bereich
        if not basis.is_dir():
            continue
        for pfad, ordner, namen in os.walk(basis):
            ordner[:] = [
                o for o in ordner
                if o not in OHNE and not o.startswith(".previous")
            ]
            for name in namen:
                if Path(name).suffix.lower() in ENDUNGEN:
                    dateien.append(Path(pfad) / name)
    if ohne:
        dateien = [
            d for d in dateien
            if not any(
                f"/{o}/" in d.as_posix() or d.as_posix().endswith(o)
                for o in ohne
            )
        ]
    return dateien


def bericht(wurzel: Path, dateien: list[Path], top: int, ab_bytes: int) -> dict:
    je_bereich: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for d in dateien:
        teile = d.relative_to(wurzel).as_posix().split("/")
        schluessel = "/".join(teile[:2]) if len(teile) > 1 else teile[0]
        eintrag = je_bereich[schluessel]
        eintrag[0] += 1
        eintrag[1] += zeilen(d)

    groessen = sorted(
        ((zeilen(d), d.relative_to(wurzel).as_posix()) for d in dateien), reverse=True
    )

    nach_hash: dict[str, list[str]] = defaultdict(list)
    for d in dateien:
        try:
            roh = d.read_bytes()
        except OSError:
            continue
        if len(roh) < ab_bytes:
            continue
        nach_hash[hashlib.md5(roh).hexdigest()].append(d.relative_to(wurzel).as_posix())
    doppel = sorted(
        ((len(v), sorted(v)) for v in nach_hash.values() if len(v) > 1),
        key=lambda p: -p[0],
    )

    treffer = []
    for d in dateien:
        try:
            text = d.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        n = len(MERKER.findall(text))
        if n:
            treffer.append((n, d.relative_to(wurzel).as_posix()))
    treffer.sort(reverse=True)

    tests = [d for d in dateien if d.name.startswith("test_") or "/tests/" in d.as_posix()]
    gesamt = sum(zeilen(d) for d in dateien)
    testz = sum(zeilen(d) for d in tests)
    return {
        "dateien": len(dateien),
        "zeilen": gesamt,
        "bereiche": {k: {"dateien": v[0], "zeilen": v[1]} for k, v in je_bereich.items()},
        "hotspots": [{"zeilen": z, "pfad": p} for z, p in groessen[:top]],
        "doppel_gruppen": len(doppel),
        "doppel": [{"anzahl": n, "pfade": v[:4]} for n, v in doppel[:top]],
        "merker": [{"anzahl": n, "pfad": p} for n, p in treffer[:top]],
        "merker_dateien": len(treffer),
        "test_dateien": len(tests),
        "test_zeilen": testz,
        "test_anteil": round(testz / max(1, gesamt), 3),
        "namens_haeufung": [
            {"name": n, "anzahl": c}
            for n, c in Counter(d.name for d in dateien).most_common(12) if c > 1
        ],
    }


def drucken(b: dict) -> None:
    print(f"Dateien: {b['dateien']}   Zeilen: {b['zeilen']}")
    print("\n--- Umfang je Bereich ---")
    for k, v in sorted(b["bereiche"].items(), key=lambda kv: -kv[1]["zeilen"]):
        print(f"{k:<40} {v['dateien']:>5} Dateien {v['zeilen']:>9} Zeilen")
    print("\n--- Groesste Einzeldateien ---")
    for h in b["hotspots"]:
        print(f"{h['zeilen']:>7} Zeilen  {h['pfad']}")
    print(f"\n--- Doppelungen (byte-gleich): {b['doppel_gruppen']} Gruppen ---")
    for d in b["doppel"]:
        print(f"  {d['anzahl']}x: " + " | ".join(d["pfade"]))
    print("\n--- Haeufige Dateinamen ---")
    for n in b["namens_haeufung"]:
        print(f"  {n['anzahl']:>3}x {n['name']}")
    print(f"\n--- Merker (TODO/FIXME/HACK/XXX): {b['merker_dateien']} Dateien ---")
    for m in b["merker"]:
        print(f"  {m['anzahl']:>3}  {m['pfad']}")
    print(
        f"\n--- Tests: {b['test_dateien']} Dateien / {b['test_zeilen']} Zeilen "
        f"({b['test_anteil']:.0%} des gemessenen Codes) ---"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Bestand der eigenen Codebasis messen.")
    ap.add_argument("--wurzel", default="", help="BrainFiles-Wurzel (Vorgabe: ueber die Merkmale gefunden)")
    ap.add_argument("--wurzeln", default=STANDARD_WURZELN, help="Bereiche, mit Komma getrennt")
    ap.add_argument("--ohne", default="", help="Fremde Baeume ausschliessen, mit Komma getrennt")
    ap.add_argument("--top", type=int, default=12, help="Zeilen je Liste")
    ap.add_argument("--ab-bytes", type=int, default=2000, help="Mindestgroesse fuer den Doppelungsvergleich")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbar ausgeben")
    args = ap.parse_args()

    wurzel = Path(args.wurzel).resolve() if args.wurzel else wurzel_finden(Path(__file__).resolve().parent)
    bereiche = [b.strip() for b in args.wurzeln.split(",") if b.strip()]
    ohne = {o.strip() for o in args.ohne.split(",") if o.strip()}
    dateien = sammeln(wurzel, bereiche, ohne)
    b = bericht(wurzel, dateien, args.top, args.ab_bytes)
    if args.json:
        print(json.dumps(b, indent=2, ensure_ascii=False))
    else:
        print(f"Wurzel: {wurzel}")
        if ohne:
            print(f"ausgeschlossen: {', '.join(sorted(ohne))}")
        drucken(b)


if __name__ == "__main__":
    main()
