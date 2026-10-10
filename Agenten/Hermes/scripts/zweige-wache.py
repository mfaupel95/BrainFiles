#!/usr/bin/env python3
"""Wache auf Worktree-Fehler im BrainFiles-Baum (T-387, 10.10.2026).

WARUM: Am 10.10.2026 lagen zwei Worktrees im HAUPTBAUM statt unter
`.worktrees/` (`Agenten/.claude/worktrees/sweet-heisenberg-85efc5` und
`init-4ede6f`), einer davon detached HEAD (`push-noema`). Keine Wache meldete
das - die Fehler blieben unentdeckt, bis sie aufgeraeumt wurden. Ein Worktree
im Hauptbaum ist ein Fehler, auch wenn er sauber ist: er verunreinigt den
geteilten Arbeitsbaum und kann von `fremdarbeit-einziehen.ps1` als Fremdarbeit
committet werden.

Diese Wache ruft `Agenten/Werkzeuge/zweige.py --json` auf und meldet NUR die
Worktree-Fehlerklassen, die `zweige.py` seit 10.10.2026 ausweist:
  - Worktree liegt NICHT unter `.worktrees/` (im Hauptbaum)
  - detached HEAD (Worktree ohne Zweig)
  - verwaister Eintrag (Ordner fehlt, git registriert ihn noch)

Sie aendert NICHTS: kein `git worktree remove`, kein `branch -d`. Sie meldet
nur, mit dem Pfad. Aufraeumen entscheidet der Mensch (oder `zweige.py
--entfernen`).

MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts senden). Dieselbe
Feststellung hoechstens einmal je RUHE_STUNDEN.

Aufruf (Hermes-Cron, no_agent, alle 6 h):
    python Agenten/Hermes/scripts/zweige-wache.py
    python Agenten/Hermes/scripts/zweige-wache.py --alle   # Lage immer zeigen
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]                       # scripts -> Hermes -> Agenten -> BrainFiles
ZWEIGE = WURZEL / "Agenten" / "Werkzeuge" / "zweige.py"
MERK = HIER / "cache" / "zweige-wache.json"

RUHE_STUNDEN = 6.0        # dieselbe Feststellung hoechstens alle 6 h


def _merk_lesen():
    try:
        return json.loads(MERK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _merk_schreiben(stand):
    MERK.parent.mkdir(parents=True, exist_ok=True)
    MERK.write_text(json.dumps(stand, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def _fehler_zeilen(befunde):
    """Worktree-Fehlerklassen aus dem zweige.py-JSON extrahieren."""
    zeilen = []
    for w in befunde.get("worktrees", []):
        if w.get("haupt"):
            continue
        if not w.get("lage_ok", True):
            zweig = (w.get("zweig") or "-").replace("refs/heads/", "")
            zeilen.append("Worktree NICHT unter .worktrees/: %s (Zweig %s)"
                          % (w["pfad"], zweig))
        if w.get("detached"):
            zeilen.append("detached HEAD: %s (Worktree ohne Zweig)" % w["pfad"])
        if w.get("verwaist"):
            zeilen.append("verwaister Worktree-Eintrag: %s (Ordner fehlt, "
                          "git registriert ihn noch)" % w["pfad"])
    return zeilen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alle", action="store_true",
                    help="Lage immer zeigen, nicht nur bei Auffaelligkeit")
    args = ap.parse_args(argv)

    if not ZWEIGE.is_file():
        print("zweige-wache: %s fehlt" % ZWEIGE)
        return 1

    proc = subprocess.run(
        [sys.executable, str(ZWEIGE), "--json"],
        cwd=str(WURZEL), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    if proc.returncode != 0:
        print("zweige-wache: zweige.py fehlgeschlagen (%d): %s"
              % (proc.returncode, (proc.stderr or proc.stdout).strip()[:300]))
        return 1

    try:
        befunde = json.loads(proc.stdout)
    except ValueError as e:
        print("zweige-wache: zweige.py lieferte kein JSON: %s" % e)
        return 1

    fehler = _fehler_zeilen(befunde)
    if not fehler:
        if args.alle:
            print("zweige-wache: keine Worktree-Fehler (%d Worktrees)"
                  % len(befunde.get("worktrees", [])))
        return 0

    # Ruhe: dieselbe Feststellung nicht staendig wiederholen.
    merk = _merk_lesen()
    jetzt = time.time()
    schluessel = "|".join(sorted(fehler))
    letzte = merk.get("letzte")
    if letzte and schluessel == merk.get("schluessel") \
            and jetzt - letzte < RUHE_STUNDEN * 3600:
        return 0
    merk["letzte"] = jetzt
    merk["schluessel"] = schluessel
    _merk_schreiben(merk)

    print("Worktree-Fehler im BrainFiles-Baum (%d):" % len(fehler))
    for z in fehler:
        print("  - " + z)
    print("Aufraeumen: python Agenten/Werkzeuge/zweige.py --entfernen "
          "(oder von Hand). Diese Wache aendert nichts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
