"""Wie viele Fenster des Hauses hängen an EINER Quelle?

Die Hausregel: Farben, Schrift, Abstaende und ttk-Stile kommen aus
`Werkzeuge/fenster_design.py`. Wer daneben eigene Farben setzt, erzeugt
einen Wartungsfehler.

Dieses Skript zaehlt je Fenster nach, ohne zu raten:
  * laedt die Quelle? (per Dateipfad, transitiv, oder gar nicht)
  * eigene Farbwerte? (Hex-Literale, die NICHT in der Quelle stehen)
  * eigene Schriftfamilien? (Familien, die nicht design.SCHRIFT_ART sind)
  * eigene Schriftstufen? (absolute Zahlen statt relativer Konstanten)

Aufruf:  scanner/.venv/Scripts/python.exe design_quellen_check.py
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys

HANDEL = os.path.dirname(os.path.abspath(__file__))
WERKZEUGE = os.path.join(os.path.dirname(HANDEL), "Werkzeuge")

# (Anzeigename, Pfad, erwartet Quelle?)
FENSTER = [
    ("handelszentrale", os.path.join(HANDEL, "handelszentrale.py"), True),
    ("leitstand_stil", os.path.join(HANDEL, "leitstand_stil.py"), True),
    ("omniquant/gui", os.path.join(HANDEL, "omniquant", "gui.py"), True),
    ("moongui (Fremd-Klon)",
     os.path.join(os.path.dirname(HANDEL), "..", "Werkstatt",
                  "moon-dev-ai-agents", "moongui.py"), False),
]


def lade_quelle():
    pfad = os.path.join(WERKZEUGE, "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    d = lade_quelle()
    quelle_farben = set(d.FARBEN.values())
    quelle_familie = d.SCHRIFT_ART

    print("Eine Quelle: %s" % os.path.relpath(
        os.path.join(WERKZEUGE, "fenster_design.py"), os.path.dirname(HANDEL)))
    print("FARBEN %d | Familie %s | Basis %d"
          % (len(d.FARBEN), quelle_familie, d.SCHRIFT_GROESSE))
    print()
    print("%-20s %-9s %8s %8s %10s"
          % ("Fenster", "Quelle", "Farben", "Schrift", "Stufen"))
    print("-" * 60)

    sauber_alle = True
    for name, pfad, soll in FENSTER:
        if not os.path.exists(pfad):
            print("%-20s  FEHLT" % name)
            continue
        with open(pfad, encoding="utf-8", errors="replace") as f:
            src = f.read()

        laedt = ("fenster_design" in src and "exec_module" in src)
        transitiv = "import handelszentrale" in src or \
            "import handelszentrale as hz" in src

        hexes = set(re.findall(r'"(#[0-9a-fA-F]{6})"', src))
        fremde_farben = hexes - quelle_farben

        # font=("Familie", N) - und tkfont.Font(family=..., size=N)
        familien = set(re.findall(r'font=\("([^"]+)"', src))
        familien |= set(re.findall(r'family="([^"]+)"', src))
        fremde_familien = {x for x in familien
                           if x and x != quelle_familie
                           and not x.startswith("Tk")}

        stufen = {int(x) for x in re.findall(
            r'font=\("[^"]+",\s*(\d+)', src)}
        fremde_stufen = {x for x in stufen if x != d.SCHRIFT_GROESSE}

        quelle_text = "ja" if laedt else ("transitiv" if transitiv
                                           else "NEIN")
        if soll and not (laedt or transitiv):
            sauber_alle = False
        if fremde_farben or fremde_familien or fremde_stufen:
            sauber_alle = False

        print("%-20s %-9s %8d %8d %10s"
              % (name, quelle_text, len(fremde_farben),
                 len(fremde_familien),
                 ",".join(str(x) for x in sorted(fremde_stufen)) or "-"))
        if fremde_farben:
            print("    fremde Farben : %s"
                  % ", ".join(sorted(fremde_farben)[:8]))
        if fremde_familien:
            print("    fremde Familien: %s" % ", ".join(sorted(fremde_familien)))

    print()
    print("Urteil: %s"
          % ("jedes Fenster haengt an der einen Quelle" if sauber_alle else
             "mindestens ein Fenster umgeht sie"))
    return 0 if sauber_alle else 1


if __name__ == "__main__":
    sys.exit(main())