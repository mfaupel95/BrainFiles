"""Doppelte Klone finden - mit Junction-Pruefung VOR dem Urteil.

Warum die Pruefung zuerst kommt: zwei Pfade mit demselben Inhalt sind kein
Duplikat, wenn einer ein Verweis ist (Junction/Symlink). Ein Fingerabdruck ueber
beide Pfade liefert dann denselben Hash, und wer daraufhin "aufraeumt", laesst
den Verweis ins Leere zeigen. Dieses Skript listet die Verweise deshalb zuerst
und gruppiert die Klone danach nach Herkunft (origin).

Aufruf (aus der BrainFiles-Wurzel):
    python Agenten/Hermes/skills/brainfiles/repos-zentrale/scripts/klon-doppel.py [WURZEL]

WURZEL ist optional und muss nicht angegeben werden (Vorgabe: die Wurzel, in der
das Skript liegt). Rein lesend: es wird nur `git config --get` und `rev-parse`
aufgerufen, nichts geschrieben, kein Netz.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SPERRE = {".venv", "venv", "node_modules", "__pycache__", ".git", "target",
          "dist", "build", ".worktrees", "copilot-worktrees", ".cache",
          "site-packages", "logs", "daten", "cache", ".next"}


def git(pfad: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(pfad), *args], capture_output=True,
                           text=True, timeout=20)
        return (r.stdout or "").strip()
    except Exception:                                     # noqa: BLE001
        return ""


def wurzel_finden() -> Path:
    hier = Path(__file__).resolve()
    for kandidat in hier.parents:
        if (kandidat / "Agenten").is_dir() and (kandidat / "MaxHirn").is_dir():
            return kandidat
    return Path.cwd()


def verweise(wurzel: Path, start: list[Path] | None = None,
             tiefe: int = 2) -> list[tuple[str, str, str]]:
    r"""Alle Reparse-Punkte (Junctions/Symlinks) unter der Wurzel.

    Wichtig: `os.walk` folgt Verweisen NICHT. Wer nur die Wurzel absucht, findet
    deshalb `Werkstatt\intelligent-trading-bot` nicht, wenn `Werkstatt`
    selbst ein Verweis ist - genau die Falle, die einen Doppel-Scan zum Luegen
    bringt. Deshalb wird jeder Startordner EINZELN abgesucht und ueber den Pfad
    entdoppelt.
    """
    treffer: list[tuple[str, str, str]] = []
    gesehen: set[str] = set()
    basis = str(wurzel)
    for w in (start or [wurzel]):
        if not w.is_dir():
            continue
        for pfad, ordner, _dateien in os.walk(w):
            p = Path(pfad)
            try:
                rel = p.relative_to(wurzel)
            except ValueError:
                continue
            if len(rel.parts) > tiefe:
                ordner[:] = []
                continue
            for name in list(ordner):
                kind = p / name
                try:
                    ist_verweis = kind.is_symlink() or os.path.isjunction(kind)
                except OSError:
                    continue
                if not ist_verweis:
                    continue
                schluessel = str(kind.relative_to(wurzel))
                ordner.remove(name)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                art = "Junction" if os.path.isjunction(kind) else "Symlink"
                treffer.append((schluessel, art, os.path.realpath(kind).replace(basis, ".")))
    return treffer


def klone(wurzel: Path, start: Path, tiefe_max: int = 5) -> list[tuple[str, str, str]]:
    """(pfad relativ zur Wurzel, origin, HEAD) aller Klone unter `start`."""
    treffer: list[tuple[str, str, str]] = []
    for pfad, ordner, _dateien in os.walk(start):
        p = Path(pfad)
        try:
            tiefe = len(p.relative_to(wurzel).parts)
        except ValueError:
            continue
        ordner[:] = [o for o in ordner if o not in SPERRE]
        if (p / ".git").is_dir():
            treffer.append((str(p.relative_to(wurzel)),
                            git(p, "config", "--get", "remote.origin.url"),
                            git(p, "rev-parse", "--short", "HEAD")))
            ordner[:] = []
            continue
        if tiefe >= tiefe_max:
            ordner[:] = []
    return treffer


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    wurzel = Path(argv[0]).resolve() if argv else wurzel_finden()

    print(f"Wurzel: {wurzel}")
    start = [w for w in (wurzel / "Werkstatt",
                         wurzel / "Werkstatt" / "Ausgemustert", wurzel / "Agenten",
                         wurzel / "MaxHirn" / "skills", wurzel / "MaxHirn")
             if w.is_dir()]

    print("\n== VERWEISE ZUERST (ein Verweis ist kein Duplikat) ==")
    for pfad, art, ziel in verweise(wurzel, [wurzel, *start], tiefe=2):
        print(f"   {pfad}  [{art}] -> {ziel}")
    gefunden: list[tuple[str, str, str]] = []
    gesehen: set[str] = set()
    for s in start:
        for eintrag in klone(wurzel, s):
            if eintrag[0] not in gesehen:
                gesehen.add(eintrag[0])
                gefunden.append(eintrag)

    nach_herkunft: dict[str, list[tuple[str, str, str]]] = {}
    for pfad, herkunft, head in gefunden:
        schluessel = herkunft.lower().removesuffix(".git") or f"OHNE-ORIGIN:{Path(pfad).name.lower()}"
        nach_herkunft.setdefault(schluessel, []).append((pfad, herkunft, head))

    print(f"\nKlone gefunden: {len(gefunden)}")
    print("\n== GLEICHE HERKUNFT AN MEHREREN ORTEN ==")
    doppelt = 0
    for schluessel, liste in sorted(nach_herkunft.items()):
        if len(liste) < 2:
            continue
        doppelt += 1
        print(f"\n{schluessel}")
        for pfad, _herkunft, head in liste:
            print(f"   {pfad}   ({head})")
    if not doppelt:
        print("   keine")
    print("\nUrteil erst nach der Verweisliste oben: liegt einer der Pfade darunter, "
          "ist es EINE Ablage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
