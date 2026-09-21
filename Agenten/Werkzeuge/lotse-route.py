#!/usr/bin/env python3
"""Lotse-Router: Ziel finden und Auftrag abschicken - ohne Umwege.

WARUM ES DIESES SKRIPT GIBT: Ein Sprachmodell als Verteiler wandert gern in die
Arbeit selbst hinein (gemessen 21.09.2026: der Bot zaehlte Repos und las
Verzeichnisse, statt zu delegieren). Dieses Skript macht die zwei Schritte, die
der Verteiler braucht, mechanisch und nachvollziehbar:

    --liste              alle Ziele mit ihrer Beschreibung
    --suche <wort>       welche Ziele passen zu diesem Stichwort
    --an <ziel> <auftrag>  den Auftrag wirklich abschicken und die Antwort holen

Der Verteiler-Bot (`lotse`) benutzt genau diese drei Aufrufe; alles andere ist
nicht seine Aufgabe. Rein lesend, solange nicht `--an` gerufen wird.

Aufruf aus der Wurzel (BrainFiles):
    python Agenten/Werkzeuge/lotse-route.py --liste
    python Agenten/Werkzeuge/lotse-route.py --suche handel
    python Agenten/Werkzeuge/lotse-route.py --an basic-memory "Pruefe die Notizen"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
HERMES = WURZEL / "Agenten" / "Hermes"
PROFILE = HERMES / "profiles"
HANDEL = WURZEL / "Agenten" / "Handel"

# Werkzeuge statt Bots: was der Verteiler direkt nennen darf.
WERKZEUGE = (
    ("Handel/spuren_stand.py", "Tabelle aller Handelsspuren (erlaubt, Fenster, Buch)"),
    ("Handel/sperrgruende.py", "woran eine Spur haengt (nur das Fenster?)"),
    ("Handel/kosten_wendepunkt.py", "Gebuehr, ab der eine Spur kippt"),
    ("Handel/auswertung_alle.py", "Zahlen je Spur (Runden, Treffer, Ergebnis)"),
    ("Handel/spiegelstand.py", "Bedingung 4: Journal byte-genau gegen Q:"),
    ("Werkzeuge/repos-updaten.py", "Fremd-Klone auf den Stand ihrer Quelle"),
    ("Werkzeuge/fundus-suche.ps1", "Skills in fremden Baeumen suchen"),
    ("Hermes/scripts/moondev-agenten-wache.py", "Wache auf Agentenprozesse/Commit"),
)


def ziele():
    """Alle Bot-Profile mit Beschreibung - aus profile.yaml, nicht geraten."""
    raus = []
    if not PROFILE.is_dir():
        return raus
    for d in sorted(PROFILE.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        beschreibung = ""
        py = d / "profile.yaml"
        if py.is_file():
            for zeile in py.read_text(encoding="utf-8", errors="replace").splitlines():
                if zeile.strip().startswith("description:"):
                    beschreibung = zeile.split(":", 1)[1].strip().strip('"\'')
                    break
        raus.append((d.name, beschreibung or "(keine Beschreibung)"))
    return raus


def suche(wort):
    w = wort.lower()
    treffer = [(n, b) for n, b in ziele() if w in n.lower() or w in b.lower()]
    if not treffer:
        treffer = [(n, b) for n, b in ziele()
                   if any(t in n.lower() for t in w.split())]
    werk = [(p, b) for p, b in WERKZEUGE if w in p.lower() or w in b.lower()]
    return treffer, werk


def schicke(ziel: str, auftrag: str) -> int:
    """Auftrag an einen Bot. Gibt den Text der Antwort aus (Ende)."""
    exe = HERMES / "bin" / "hermes.exe"
    if not exe.is_file():
        print("hermes.exe fehlt: %s" % exe)
        return 2
    umg = dict(os.environ)
    # Bekannte Falle: ein geerbtes PYTHONHOME/PYTHONPATH killt den Start des
    # Kindes ("Fatal Python error: init_import_site").
    for k in ("PYTHONHOME", "PYTHONPATH"):
        umg.pop(k, None)
    p = subprocess.run([str(exe), "-p", ziel, "chat", "-q", auftrag],
                       capture_output=True, text=True, timeout=1800,
                       cwd=str(WURZEL), env=umg)
    aus = (p.stdout or "").strip()
    fehler = (p.stderr or "").strip()
    print("=== %s (Rueckgabecode %s) ===" % (ziel, p.returncode))
    print(aus[-4000:] if aus else "(keine Ausgabe)")
    if p.returncode != 0 and fehler:
        print("--- stderr ---")
        print(fehler[-1000:])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--liste", action="store_true", help="alle Ziele nennen")
    ap.add_argument("--suche", metavar="WORT", help="Ziele zu einem Stichwort")
    ap.add_argument("--an", nargs=2, metavar=("ZIEL", "AUFTRAG"),
                    help="Auftrag an ein Ziel abschicken")
    a = ap.parse_args()

    if a.an:
        return schicke(a.an[0], a.an[1])
    if a.suche:
        treffer, werk = suche(a.suche)
        print("Bots zu '%s':" % a.suche)
        for n, b in treffer[:12]:
            print("  %-26s %s" % (n, b[:100]))
        if not treffer:
            print("  (keiner - dann Werkzeug oder Skill)")
        print("Werkzeuge zu '%s':" % a.suche)
        for p, b in werk[:8]:
            print("  %-40s %s" % (p, b[:90]))
        return 0
    print("Bots (%d):" % len(ziele()))
    for n, b in ziele():
        print("  %-26s %s" % (n, b[:110]))
    print("Werkzeuge:")
    for p, b in WERKZEUGE:
        print("  %-40s %s" % (p, b[:90]))
    print("\nAuftrag abschicken:  --an <ziel> \"<auftrag>\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
