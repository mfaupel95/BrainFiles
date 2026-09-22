"""Verknuepft doppelte Skill-Ordner in den Bot-Profilen mit der Hauptbibliothek (Junction).

Die 19 Bot-Profile tragen weithin dieselbe Skill-Bibliothek als eigene Kopie.
Inhaltsgleiche Ordner werden durch eine Junction auf `Agenten/Hermes/skills/<...>`
ersetzt: gleicher Inhalt, EINE Quelle, weniger Platz. Verglichen wird der GANZE
Ordner (jede Datei), nicht nur die SKILL.md - sonst ginge eine abweichende
Referenzdatei verloren.

  python skill-kopien-verknuepfen.py                 # Trockenlauf (Standard)
  python skill-kopien-verknuepfen.py --anwenden
  python skill-kopien-verknuepfen.py --zuruecknehmen # aus der Sicherung zurueck

Sicherung: <profil>/skills/.sicherung-junctions/<relpfad>/ (vor dem Eingriff).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

H = Path(r"C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes")
LIB = H / "skills"
PROF = H / "profiles"
MANIFEST = H / "cache/skill-junctions.json"
SICHER = ".sicherung-junctions"


def datei_hash(p: Path) -> str:
    h = hashlib.md5()
    try:
        with open(p, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
    except OSError:
        return "?"
    return h.hexdigest()


def ordner_hash(d: Path) -> str:
    h = hashlib.md5()
    for f in sorted(x for x in d.rglob("*") if x.is_file()):
        h.update(str(f.relative_to(d)).replace(os.sep, "/").encode())
        h.update(datei_hash(f).encode())
    return h.hexdigest()


def skills(basis: Path) -> dict[str, Path]:
    """Name (relativer Pfad) -> Ordner, fuer jeden Ordner mit SKILL.md."""
    gefunden = {}
    for s in basis.rglob("SKILL.md"):
        d = s.parent
        if ".archive" in d.parts or ".git" in d.parts or d.name.startswith("."):
            continue
        if ".sicherung-junctions" in d.parts:
            continue
        gefunden[str(d.relative_to(basis)).replace(os.sep, "/")] = d
    return gefunden


def junction_anlegen(ziel: Path, quelle: Path) -> bool:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"New-Item -ItemType Junction -Path '{ziel}' -Target '{quelle}' | Out-Null"],
        capture_output=True, text=True,
    )
    return r.returncode == 0 and ziel.exists()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anwenden", action="store_true")
    ap.add_argument("--zuruecknehmen", action="store_true")
    ap.add_argument("--nur", default="", help="nur dieses Profil")
    a = ap.parse_args()

    if a.zuruecknehmen:
        if not MANIFEST.exists():
            print("nichts zurueckzunehmen:", MANIFEST)
            return 0
        eintraege = json.loads(MANIFEST.read_text(encoding="utf-8"))
        zurueck = 0
        for e in eintraege:
            p = Path(e["pfad"])
            q = Path(e["sicherung"])
            if not q.exists():
                print("Sicherung fehlt:", q)
                continue
            if os.path.isjunction(p):
                # Directory.Delete(..., $false) entfernt NUR die Verknuepfung, nie das Ziel
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[System.IO.Directory]::Delete('{p}', $false)"],
                    capture_output=True)
            shutil.rmtree(p, ignore_errors=True)
            shutil.copytree(q, p)
            shutil.rmtree(q, ignore_errors=True)
            zurueck += 1
        print(f"zurueckgenommen: {zurueck}")
        return 0

    lib = skills(LIB)
    lib_hash: dict[str, list[str]] = {}
    for name, d in lib.items():
        lib_hash.setdefault(ordner_hash(d), []).append(name)
    print(f"Hauptbibliothek: {len(lib)} Skills, {len(lib_hash)} verschiedene Inhalte")

    kandidaten = []
    eigen = 0
    for prof in sorted(p for p in PROF.iterdir() if p.is_dir() and (p / "skills").is_dir()):
        if a.nur and prof.name != a.nur:
            continue
        for name, d in skills(prof / "skills").items():
            if os.path.isjunction(d):
                continue
            treffer = lib_hash.get(ordner_hash(d))
            if treffer:
                kandidaten.append({
                    "profil": prof.name, "pfad": str(d), "quelle": str(LIB / treffer[0]),
                    "relpfad": name,
                    "sicherung": str(d.parent / SICHER / d.name),
                })
            else:
                eigen += 1
    platz = sum(sum(f.stat().st_size for f in Path(k["pfad"]).rglob("*") if f.is_file())
                for k in kandidaten)
    print(f"Kandidaten (inhaltsgleich, ganzordner): {len(kandidaten)}   profil-eigene Skills: {eigen}")
    print(f"Platz der Kopien: {platz / 1e6:.1f} MB")
    print("\nje Profil:")
    zaehler: dict[str, int] = {}
    for k in kandidaten:
        zaehler[k["profil"]] = zaehler.get(k["profil"], 0) + 1
    for name, n in sorted(zaehler.items(), key=lambda kv: -kv[1]):
        print(f"   {n:>4}  {name}")

    if not a.anwenden:
        print("\nTrockenlauf - nichts geaendert. Mit --anwenden ausfuehren.")
        return 0

    angelegt = []
    fehler = []
    for k in kandidaten:
        d, q = Path(k["pfad"]), Path(k["quelle"])
        sicher = Path(k["sicherung"])
        sicher.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(d, sicher)
            shutil.rmtree(d)
            if junction_anlegen(d, q):
                angelegt.append(k)
            else:
                shutil.copytree(sicher, d)
                fehler.append(k["pfad"])
        except OSError as e:
            fehler.append(f"{k['pfad']}: {e}")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(angelegt, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nverknuepft: {len(angelegt)}   Fehler: {len(fehler)}")
    for f in fehler[:10]:
        print("  ", f)
    print("Manifest:", MANIFEST)
    return 0


if __name__ == "__main__":
    sys.exit(main())