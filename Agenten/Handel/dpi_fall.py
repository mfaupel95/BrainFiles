"""Was macht `tk scaling 1.1` gegenueber `dpi_bewusst()` - und was ist besser?

Der UI-Audit vom 04.10.2026 fand: KEIN Fenster ruft `dpi_bewusst()`, alle
drei setzen stattdessen `tk scaling 1.1`. Die Quelle bietet `dpi_bewusst()`
an und der Skill nennt es als Schritt 1 vor dem ersten `Tk()`.

Das sind zwei verschiedene Dinge, und der Unterschied ist nicht
Geschmackssache:

  * `dpi_bewusst()` (SetProcessDpiAwareness) sagt WINDOWS, dass die
    Anwendung dpi-aware ist. Windows stretcht dann nicht mehr das fertige
    Bitmap, sondern die Anwendung zeichnet in Geraetepixeln. Jede Schrift
    bleibt scharf.
  * `tk scaling 1.1` aendert nur Tk interne Punkte in Pixel. Das Fenster
    wird von Windows GESTRECKT, wenn es nicht dpi-aware ist - die Schrift
    wird weich, unabhaengig davon, welchen Wert man setzt.

Dieses Skript misst beide Faelle am selben Rechner: Fenster bauen,
Schriftbreite und Fenstermasse ablesen. Und es fragt Windows, ob der
Prozess dpi-aware ist.

Aufruf:  scanner/.venv/Scripts/python.exe dpi_fall.py
        scanner/.venv/Scripts/python.exe dpi_fall.py --dpi
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import tkinter as tk
from tkinter import font as tkfont

HANDEL = os.path.dirname(os.path.abspath(__file__))
WERKZEUGE = os.path.join(os.path.dirname(HANDEL), "Werkzeuge")


def dpi_awareness() -> int:
    """Was Windows ueber diesen Prozess weiss (-1 = unbekannt).

    0 = unaware (Windows stretcht das fertige Bitmap - jede Schrift
    wird weich), 1 = system-dpi-aware, 2 = per-monitor (ab Win 10
    1703). Nur 0 ist der Zustand, der die Schrift unscharf macht.
    """
    try:
        awareness = ctypes.c_int(-1)
        hr = ctypes.windll.shcore.GetProcessDpiAwareness(
            None, ctypes.byref(awareness))
        return awareness.value if hr == 0 else -1
    except Exception:                                        # noqa: BLE001
        return -1


def main() -> int:
    ap = argparse.ArgumentParser(description="DPI-Fall messen")
    ap.add_argument("--dpi", action="store_true",
                    help="mit dpi_bewusst() statt nur tk scaling")
    args = ap.parse_args()

    if args.dpi:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:                                    # noqa: BLE001
            pass

    root = tk.Tk()
    if not args.dpi:
        try:
            root.tk.call("tk", "scaling", 1.1)
        except Exception:                                    # noqa: BLE001
            pass

    from tkinter import ttk
    try:
        import handelszentrale as hz
    except Exception as e:                                   # noqa: BLE001
        print("Handelszentrale nicht ladbar: %s" % e)
        root.destroy()
        return 1

    z = hz.Handelszentrale(root)
    root.geometry("1280x860")
    root.update()
    root.update_idletasks()

    f = tkfont.Font(family=hz.SCHRIFT_ART, size=hz.SCHRIFT_GROESSE)
    probe = "nautilus_kraken_futures"
    breite = f.measure(probe)

    print("Fall            : %s" % ("dpi_bewusst()" if args.dpi
                                    else "nur tk scaling 1.1"))
    print("Prozess dpi-aware: %s" % dpi_awareness())
    print("tk scaling      : %.3f" % root.tk.call("tk", "scaling"))
    print("winfo_fpixels 1i: %d" % root.winfo_fpixels("1i"))
    print("System-Masse    : %dx%d" % (root.winfo_screenwidth(),
                                      root.winfo_screenheight()))
    print("Fenster         : %dx%d" % (root.winfo_width(), root.winfo_height()))
    print("Schrift         : %s %d" % (hz.SCHRIFT_ART, hz.SCHRIFT_GROESSE))
    print("Breite %-22s: %d px  (%.2f px je Zeichen)"
          % ("'" + probe + "'", breite, breite / len(probe)))
    print("design.skalierung: %.3f" % _skalierung(root))
    del z, ttk
    root.destroy()
    return 0


def _skalierung(root):
    import importlib.util
    pfad = os.path.join(WERKZEUGE, "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fd", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.skalierung(root)


if __name__ == "__main__":
    sys.exit(main())