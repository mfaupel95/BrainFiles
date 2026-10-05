"""Misst, was die fremde Palette und die fehlende Schrift kosten.

Aus dem UI-Audit vom 04.10.2026, Befund 2 und 3 fuer `moongui.py`:

  * 17 eigene Farbwerte, KEINE davon aus `fenster_design.FARBEN`. Die
    Schnittmenge der Paletten ist leer - es ist eine zweite Palette ohne
    Namen, nicht ein Ton der Hauspaltte.
  * In KEINEM der acht `st.configure(...)`/`st.map(...)`-Aufrufe steht ein
    `font=`. ttk erbt damit aus `TkDefaultFont`, und das ist Segoe UI
    (proportional). Die Boersentabelle hat fuenf Zahlenspalten - die
    fluchten nicht, 24h-% und Vol sind nicht scanbar.

Dieses Skript vergleicht die beiden Paletten und misst, was Segoe UI
kostet: Consolas hat 8.00 px je Zeichen (fest), Segoe UI 9.71 und
proportional (ein 'i' ist schmaler als ein 'W').

Aufruf (aus Agenten/Handel):
    scanner/.venv/Scripts/python.exe moongui_palette_check.py
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import tkinter as tk
from tkinter import font as tkfont

HANDEL = os.path.dirname(os.path.abspath(__file__))
WERKZEUGE = os.path.join(os.path.dirname(HANDEL), "Werkzeuge")
REPO = os.path.abspath(os.path.join(
    os.path.dirname(HANDEL), "..", "Werkstatt", "Repos",
    "moon-dev-ai-agents"))
ZIEL = os.path.join(REPO, "moongui.py")


def haus_palette():
    pfad = os.path.join(WERKZEUGE, "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fd", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    d = haus_palette()
    with open(ZIEL, encoding="utf-8", errors="replace") as f:
        src = f.read()

    haus = set(d.FARBEN.values())
    eigen = set(re.findall(r'"(#[0-9a-fA-F]{6})"', src))
    fremd = sorted(eigen - haus)
    gemeinsam = sorted(eigen & haus)

    print("Hauspalette fenster_design.py : %d Werte" % len(haus))
    print("moongui.py                   : %d Werte, davon %d verschieden"
          % (len(re.findall(r'"(#[0-9a-fA-F]{6})"', src)), len(eigen)))
    print()
    print("in BEIDEN Paletten : %d  %s"
          % (len(gemeinsam), ", ".join(gemeinsam) if gemeinsam else "-"))
    print("nur in moongui     : %d" % len(fremd))
    print("   %s" % ", ".join(fremd))
    print()
    if not haus & eigen:
        print("=> Die Schnittmenge ist LEER. Das ist eine eigene Palette,")
        print("   nicht ein abweichender Ton der Hauspaltte.")
    print()

    # Der ttk-Aufbau ohne `font=`.
    stile = re.findall(r"st\.(?:configure|map)\(", src)
    mit_font = [z for z in stile
                if re.search(r"st\.(?:configure|map)\([^)]*font=", src)]
    print("st.configure/st.map Aufrufe : %d" % len(stile))
    print("davon mit font=            : %d" % len(mit_font))
    print()

    # Was kostet die geerbte Schrift?
    root = tk.Tk()
    root.withdraw()
    f_console = tkfont.Font(family=d.SCHRIFT_ART, size=d.SCHRIFT_GROESSE)
    # `Font(name="TkDefaultFont")` erzeugt einen NEUEN Font mit diesem
    # Namen und bricht mit "named font already exists" ab. Der
    # vorhandene geerbte Font kommt aus `nametofont`.
    f_segoe = tkfont.nametofont("TkDefaultFont", root)
    print("geerbter Font (TkDefaultFont): %s %d"
          % (f_segoe.cget("family"), f_segoe.cget("size")))
    print("Haus-Schrift               : %s %d"
          % (f_console.cget("family"), f_console.cget("size")))
    print()
    probe = "83806.8"
    b1 = f_console.measure(probe)
    b2 = f_segoe.measure(probe)
    print("Zahl %-8s Consolas %3d px | Segoe UI %3d px  (%+.0f %%)"
          % (probe, b1, b2, 100 * (b2 - b1) / b1))
    print()
    # Festbreite pruefen: alle Zeichen gleich breit?
    for name, f in (("Consolas", f_console), ("TkDefaultFont", f_segoe)):
        breiten = [f.measure(z) for z in "0iWM."]
        spanne = max(breiten) - min(breiten)
        print("%-14s Breiten '0iWM.' = %s  Spanne %d px  %s"
              % (name, breiten, spanne,
                 "festbreit (Zahlen fluchten)" if spanne == 0
                 else "PROPORTIONAL (fluchten nicht)"))
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())