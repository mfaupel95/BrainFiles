"""Messen statt schaetzen: wie breit ist ein Zeichen MIT dpi_bewusst()?

`zeichenbreite_messen.py` misst ohne dpi_bewusst() und kam auf 8 px je
Zeichen (Consolas 11). Mit dpi_bewusst() setzt Tk die Schrift in
Geraetepixeln, dann sind es 11 px - genau der Unterschied, an dem die alte
Spurentabelle gescheitert ist: 110 px fuer die Spalte 'spur' sind bei 11 px
nur 10 Zeichen, `nautilus_kraken_futures` (23 Zeichen) passt nicht hinein.

WICHTIG - die Falle, die diesen Aufbau erzwungen hat (04.10.2026):
`dpi_bewusst()` muss VOR dem ERSTEN `Tk()` des Prozesses laufen. Ein Weg,
beide Faelle im selben Prozess zu messen, liefert deshalb immer 8 px und
nennt den zweiten Fall falsch: das erste `Tk()` hat den DPI-Kontext des
Prozesses festgelegt, jede spaetere `SetProcessDpiAwareness`-Wirkung ist
tot. Jeder Fall braucht einen eigenen Prozess - darum `--fall` plus ein
Kindprozess je Fall. Genau diese Fehlmessung ist beim Bauen passiert.

Aufruf:  scanner/.venv/Scripts/python.exe zeichenbreite_dpi.py
"""

import importlib.util
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont

HIER = os.path.dirname(os.path.abspath(__file__))
PROBE = "nautilus_kraken_futures"       # der laengste echte Spurname
BASIS = 11
SICH = os.path.join(HIER, "cache", "zeichenbreite_dpi.json")


def _design():
    pfad = os.path.join(HIER, "..", "Werkzeuge", "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ein_fall(mit_dpi):
    """Ein Messfall, EIN Prozess - dpi_bewusst() VOR dem ersten Tk()."""
    if mit_dpi:
        _design().dpi_bewusst()
    root = tk.Tk()
    root.withdraw()
    d = _design()
    f = tkfont.Font(family=d.SCHRIFT_ART, size=BASIS)
    breite = f.measure(PROBE)
    aus = {
        "dpi": mit_dpi,
        "faktor": d.skalierung(root),
        "dpi_px": root.winfo_fpixels("1i"),
        "breite": breite,
        "zeichen": len(PROBE),
        "je_zeichen": breite / len(PROBE),
        "gerundet": int(breite / len(PROBE) + 0.999),
    }
    root.destroy()
    return aus


def _kind(fall):
    print(json.dumps(_ein_fall(fall == "dpi")))


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--fall":
        _kind(sys.argv[2])
        return 0

    exe = os.path.join(HIER, "scanner", ".venv", "Scripts", "python.exe")
    if not os.path.exists(exe):
        exe = sys.executable
    faelle = {}
    for name in ("ohne", "dpi"):
        roh = subprocess.run([exe, os.path.abspath(__file__), "--fall", name],
                             capture_output=True, text=True)
        if roh.returncode != 0:
            print("Fall %s scheiterte: %s" % (name, roh.stderr[-400:]))
            return 1
        faelle[name] = json.loads(roh.stdout.strip().splitlines()[-1])

    print("Probe %r, Consolas %d" % (PROBE, BASIS))
    print("%-14s %8s %8s %8s %10s %10s"
          % ("Fall", "Faktor", "1i px", "Breite", "je Zeichen", "gerundet"))
    for name in ("ohne", "dpi"):
        f = faelle[name]
        print("%-14s %8.3f %8d %8d %10.2f %10d"
              % ("dpi_bewusst()" if name == "dpi" else "ohne",
                 f["faktor"], f["dpi_px"], f["breite"], f["je_zeichen"],
                 f["gerundet"]))
    if faelle["dpi"]["gerundet"] <= faelle["ohne"]["gerundet"]:
        print("\nFEHLER: der DPI-Fall ist nicht groesser - dpi_bewusst() wurde "
              "nach dem ersten Tk() gerufen oder ist wirkungslos.")
        return 1
    print("\nZEICHEN_BREITE (dpi_bewusst, im Fenster benutzt) = %d px"
          % faelle["dpi"]["gerundet"])
    print("Faktor = %.3f" % faelle["dpi"]["faktor"])
    os.makedirs(os.path.dirname(SICH), exist_ok=True)
    with open(SICH, "w", encoding="utf-8") as f:
        json.dump(faelle, f, indent=1)
    print("Beleg: %s" % SICH)
    return 0


if __name__ == "__main__":
    sys.exit(main())