"""Baut die MoonDev-GUI und misst die Orderzeile am echten Fenster.

Das Skript liegt in BrainFiles, nicht im Repo: `Werkstatt/` ist eine
Junction auf O: und damit ausserhalb der Schreibgrenze des Werkzeugs. Der
Weg zum Modul geht deshalb ueber den Repo-Klon - genau so, wie die GUI
selbst startet (pythonw.exe moongui.py aus dem Repo-Ordner).

Nur lesen, das Fenster wird am Ende zerstoert.

Aufruf aus Agenten/Handel:
    scanner/.venv/Scripts/python.exe moongui_messen.py
"""

from __future__ import annotations

import os
import sys

HANDEL = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(os.path.dirname(HANDEL), "..", "Werkstatt",
                    "moon-dev-ai-agents")
REPO = os.path.abspath(REPO)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import tkinter as tk  # noqa: E402

import moongui  # noqa: E402


def main() -> int:
    root = tk.Tk()
    app = moongui.App(root)
    root.geometry("1160x800-3200-0")
    root.update()
    root.update_idletasks()

    breite = root.winfo_width()
    print("Fenster %dx%d  (Repo: %s)" % (breite, root.winfo_height(),
                                         os.path.basename(REPO)))
    print()
    schlecht = []
    for name, w in (("Instrument", app.order_inst_e),
                    ("Key", app.order_key),
                    ("Secret", app.order_secret),
                    ("Passphrase", app.order_pass)):
        links = w.winfo_rootx() - root.winfo_rootx()
        rechts = links + w.winfo_width()
        im_fenster = 0 <= links and rechts <= breite
        print("  %-12s x %4d..%4d  Breite %3d  %s"
              % (name, links, rechts, w.winfo_width(),
                 "sichtbar" if im_fenster else "AUSSERHALB"))
        if not im_fenster:
            schlecht.append(name)

    print()
    for beschriftung, w in (("Orderzeile", app.order_inst_e),
                            ("Zugangszeile", app.order_key)):
        m = w.master
        print("  %-13s %4d px verlangt an x=%d  %s"
              % (beschriftung, m.winfo_reqwidth(), m.winfo_x(),
                 "passt" if m.winfo_reqwidth() <= breite
                 else "ZU BREIT (%d px)" % (m.winfo_reqwidth() - breite)))

    root.destroy()
    print()
    if schlecht:
        print("AUSSERHALB DES FENSTERS: %s" % ", ".join(schlecht))
        return 1
    print("Alle Orderfelder liegen im sichtbaren Fenster.")
    return 0


if __name__ == "__main__":
    sys.exit(main())