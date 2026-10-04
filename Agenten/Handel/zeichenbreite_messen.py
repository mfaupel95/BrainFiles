"""Messen statt schaetzen: wie breit ist ein Zeichen in der Fensterschrift?

Der Layout-Entwurf der Handelszentrale rechnet Spaltenbreiten ohne Fenster,
weil die Schrift Consolas FESTBREITE hat - jedes Zeichen gleich breit. Diese
Sonde belegt das am echten Font und liefert die Zahl fuer
`handelszentrale.ZEICHEN_BREITE`. Stimmen die Werte nicht, ist die Rechnung
falsch und die ganze Tabelle zu schmal.

Aufruf:  scanner/.venv/Scripts/python.exe zeichenbreite_messen.py
"""

import sys
import tkinter as tk
from tkinter import font as tkfont

BASIS = 11


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    f = tkfont.Font(family="Consolas", size=BASIS)
    proben = ("0123456789", "M" * 20, "i" * 20, "nautilus_kraken_futures",
              "BTC-USDT-SWAP", "scharf, noch 10:24 h", "3.14e-06", "15.182,44")
    print("Font Consolas %d px:" % BASIS)
    breiten = []
    for s in proben:
        b = f.measure(s)
        je = b / len(s)
        breiten.append(je)
        print("   %2d Zeichen -> %3d px  (je %5.2f)  %s"
              % (len(s), b, je, s[:30]))
    # Feste Breite heisst: alle Zeichensorten gleich. Die Spanne muss 0 sein.
    spanne = max(breiten) - min(breiten)
    print("\nSpanne je Zeichen: %.2f px  %s"
          % (spanne, "FESTBREITE" if spanne < 0.5 else "NICHT festbreit"))
    empfohlen = int(max(breiten) + 0.999)
    print("ZEICHEN_BREITE = %d  (aufrunden, damit nichts ansteht)" % empfohlen)
    root.destroy()
    return 0 if spanne < 0.5 else 1


if __name__ == "__main__":
    sys.exit(main())