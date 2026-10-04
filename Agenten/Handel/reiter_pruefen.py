"""Sind alle drei Reiter der Handelszentrale erreichbar?

Befund des UI-Audits vom 04.10.2026: `scrollbare_seite()` war nur am
Spuren-Reiter gebaut. Gemessen bei 1280x860 zeigte der FreqTrade-Reiter
121 px von 336 px Inhalt, omnitrade 141 von 468 - ohne Hinweis.

Dieses Skript misst, ob der INHALT der Seite hoeher ist als der sichtbare
Bereich. Ein Reiter, dessen Inhalt hineinpasst, braucht keine Scrollflaeche;
einer, der hoeher ist, braucht sie - und dann muss sie auch am Rad hängen.

Gemessen wird die tatsaechliche Fenstergeometrie, nicht eine gewuenschte:
`Leitstand` und `Handelszentrale` setzen ihre eigene Lage.

Aufruf:  scanner/.venv/Scripts/python.exe reiter_pruefen.py
"""

import importlib.util
import os
import sys
import tkinter as tk

HANDEL = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
d = os.path.join(HIER := os.path.dirname(os.path.abspath(__file__)),
                "..", "Werkzeuge", "fenster_design.py")
spec = importlib.util.spec_from_file_location("fd", d)
design = importlib.util.module_from_spec(spec)
spec.loader.exec_module(design)

import handelszentrale as hz

BREIT, HOCH = 1280, 860


def main() -> int:
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except Exception:
        pass
    z = hz.Handelszentrale(root)
    root.geometry("%dx%d" % (BREIT, HOCH))
    root.update()
    root.update_idletasks()

    nb = None
    for kind in root.winfo_children():
        if kind.winfo_class() == "TNotebook":
            nb = kind
            break
    if nb is None:
        print("kein Notebook gefunden")
        return 1

    print("Fenster %dx%d, Reiter %d"
          % (root.winfo_width(), root.winfo_height(), len(nb.tabs())))
    print()
    schlecht = []
    for i in range(len(nb.tabs())):
        titel = nb.tab(i, "text")
        nb.select(i)
        root.update()
        root.update_idletasks()
        # Der Notebook-Laetter holt die Seite. Bei einer scrollbaren Seite
        # ist das ein WRAPPER mit Canvas, und der INHALT sitzt eine Ebene
        # tiefer im Canvas-Fenster. Die erste Fassung mass nur die direkten
        # Kinder des Canvas (die Innenflaeche selbst, 262 px) und meldete
        # daraufhin "passt" fuer alle drei Reiter - das war eine
        # Messluecke, kein Befund.
        seite = root.nametowidget(nb.select())
        sichtbar = seite.winfo_height()
        hat_canvas = any(k.winfo_class() == "Canvas"
                         for k in seite.winfo_children())
        if hat_canvas:
            canvas = [k for k in seite.winfo_children()
                      if k.winfo_class() == "Canvas"][0]
            innen = canvas.winfo_children()
            inhalt = sum(k.winfo_reqheight() for k in innen)
            for k in innen:
                for u in k.winfo_children():
                    inhalt += u.winfo_reqheight()
        else:
            inhalt = sum(k.winfo_reqheight() for k in seite.winfo_children())
        passt = inhalt <= sichtbar
        print("%-12s Inhalt %4d px | sichtbar %4d px | Scrollflaeche %s  %s"
              % (titel, inhalt, sichtbar, "ja" if hat_canvas else "NEIN",
                 "passt" if passt else "SCHNEIDET %d px ab"
                 % (inhalt - sichtbar)))
        if not passt and not hat_canvas:
            schlecht.append(titel)
    print()
    if schlecht:
        print("REITER OHNE SCROLLFLAECHE, obwohl der Inhalt hineinpasst: %s"
              % ", ".join(schlecht))
        return 1
    print("Alle Reiter mit abschneidbarem Inhalt haben eine Scrollflaeche.")
    root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())