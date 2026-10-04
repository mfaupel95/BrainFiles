"""Welcher Notaus-Ton traegt weissen Text mit mindestens 4,5:1?

Gemessen am 04.10.2026: der Notaus-Knopf des Leitstands setzt
`bg=#c0392b` (ein Nicht-Token neben dem Rot der Hauspalette) gegen
`fg="white"` - **3,23:1**. Das ist der eine Knopf, der sofort lesbar sein
muss; unter 4,5:1 ist er das nicht.

Gesucht ist ein Rot aus der Hauspalette mit ausreichendem Kontrast zu
Weiss. `FARBEN["rot"]` ist dafuer vermutlich zu dunkel, `zellrot` noch
mehr - aber beides ist gemessen, nicht vermutet.

Aufruf:  scanner/.venv/Scripts/python.exe notaus_contrast.py
"""

from __future__ import annotations

import importlib.util
import os
import sys

HANDEL = os.path.dirname(os.path.abspath(__file__))


def lade_quelle():
    pfad = os.path.join(os.path.dirname(HANDEL), "Werkzeuge",
                        "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leuchtdichte(hexfarbe):
    h = hexfarbe.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def verhaeltnis(a, b):
    la, lb = leuchtdichte(a), leuchtdichte(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    d = lade_quelle()
    weiss = "#ffffff"
    ist = "#c0392b"          # der Wert, der heute im Knopf steht

    print("Notaus-Knopf: weisser Text auf einem Rot")
    print()
    print("%-14s %-9s %8s  %s" % ("Farbe", "Herkunft", "Weiss", "Urteil"))
    print("-" * 58)
    print("%-14s %-9s %8.2f  %s"
          % (ist, "Fremdwert", verhaeltnis(ist, weiss),
             "ZU WENIG (heute)" if verhaeltnis(ist, weiss) < 4.5 else "ok"))
    for name in ("rot", "zellrot", "notaus_aktiv"):
        wert = {"rot": d.FARBEN["rot"], "zellrot": d.FARBEN["zellrot"],
                "notaus_aktiv": "#e74c3c"}[name]
        v = verhaeltnis(wert, weiss)
        print("%-14s %-9s %8.2f  %s"
              % (wert, name, v, "traegt Weiss" if v >= 4.5 else "zu dunkel"))

    # Nicht nur auf Weiss: der Knopf muss auch von der Fensterflaeche
    # zu trennen sein, sonst verschwindet seine Kontur.
    print()
    bester = None
    for name in ("rot", "zellrot"):
        wert = d.FARBEN[name]
        v = verhaeltnis(wert, weiss)
        if v >= 4.5 and (bester is None or v > bester[1]):
            bester = (wert, v, name)
    if bester is None:
        print("Kein Rot der Palette traegt weissen Text mit 4,5:1.")
        print("Der Knopf braucht dann einen ausdruecklich als Notaus")
        print("benannten Ton - als eigene Entscheidung, mit Begruendung,")
        print("nicht als Nebenprodukt des Imports.")
        return 1
    print("Empfehlung: FARBEN[%r] = %s (Weiss %.2f:1, gegen bg %.2f:1)"
          % (bester[2], bester[0], bester[1],
             verhaeltnis(bester[0], d.FARBEN["bg"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())