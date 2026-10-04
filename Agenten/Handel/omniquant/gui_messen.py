"""Misst das GEBaute Fenster, nicht den Quelltext.

20 ersetzte Font-Literale sind kein blinder Tausch: `schrift(rel)` braucht
die Basis aus `fenster_design`, und eine falsche Zuordnung zeigt sich
erst am gerenderten Font. Dieses Skript baut das Fenster und liest die
tatsaechlich gesetzten Werte aus.

Aufruf (aus dem omniquant-Ordner):
    ../scanner/.venv/Scripts/python.exe gui_messen.py
"""

import os
import sys
import tkinter as tk
from tkinter import font as tkfont

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import gui  # noqa: E402


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except Exception:
        pass
    f = gui.OmniquantGui(root)
    root.geometry("1200x900-3200-0")
    root.update()
    root.update_idletasks()

    basis = gui.SCHRIFT_GROESSE
    print("Quelle: fenster_design.py, Basis %d, Familie %s"
          % (basis, gui.SCHRIFT_ART))
    print("Schriftgroesse des Fensters (Leitstand-Standard): %d" % basis)
    print()

    fett = tkfont.Font(family=gui.SCHRIFT_ART, size=basis)
    fein = tkfont.Font(family=gui.SCHRIFT_ART, size=basis + gui.KLEIN)
    winzig = tkfont.Font(family=gui.SCHRIFT_ART, size=basis + gui.TINY)
    print("  schrift(0)          -> %d pt   %r"
          % (fett.cget("size"), gui.schrift()))
    print("  schrift(KLEIN=%d)   -> %d pt   %r"
          % (gui.KLEIN, fein.cget("size"), gui.schrift(gui.KLEIN)))
    print("  schrift(TINY=%d)    -> %d pt   %r"
          % (gui.TINY, winzig.cget("size"), gui.schrift(gui.TINY)))
    print()

    # Gegenprobe Scaling: im Alleinstart setzt `main()` es, als Reiter
    # `_baue()`. Beide muessen dasselbe ergeben.
    print("tk scaling           : %s" % root.tk.call("tk", "scaling"))
    print()
    st = tk.ttk.Style()
    print("Treeview-Zeilenhoehe : %s (Quelle %d)"
          % (st.lookup("Treeview", "rowheight"),
             __import__("gui").design.zeilenhoehe(basis)))
    print("Treeview-Hintergrund: %s" % st.lookup("Treeview", "background"))
    print("Kopf-Hintergrund     : %s" % st.lookup("Treeview.Heading",
                                                  "background"))
    print("Auswahl              : %s" % st.lookup("Treeview", "selectbackground"))
    print()

    # Gegenprobe: die Palette muss der Quelle entsprechen, Schluessel fuer
    # Schluessel - nicht "sieht aehnlich aus".
    fehlt = sorted(set(gui.design.FARBEN) - set(gui.FARBEN))
    print("Farbschluessel der Quelle: %d | in diesem Fenster: %d | fehlt: %s"
          % (len(gui.design.FARBEN), len(gui.FARBEN), ", ".join(fehlt) or "-"))
    print("Identisch mit der Quelle: %s" % (gui.FARBEN is gui.design.FARBEN))

    root.destroy()
    return 0 if not fehlt else 1


if __name__ == "__main__":
    sys.exit(main())