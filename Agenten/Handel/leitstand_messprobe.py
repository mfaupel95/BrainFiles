"""Messprobe fuer den Leitstand - dasselbe Prinzip wie `messprobe.py`.

Der Leitstand rechnet seine Spaltenbreiten mit `tkfont.measure` am echten
Font, also ist er nicht auf die Zeichenzahl angewiesen. Trotzdem ist die
Messung noetig: seine letzte Spalte steht auf `stretch=True`, und genau die
verfaelscht jede gerechnete Breite. Diese Sonde misst das am Fenster.

Ein Unterschied zu `messprobe.py`: der Leitstand hat Reiter, deren Inhalt
beim Wechsel erst aufgebaut wird. Sie wird deshalb Reiter fuer Reiter
durchgeschaltet und nur der aktuelle gemessen.

Aufruf aus dem Handel-Ordner:
    scanner/.venv/Scripts/python.exe leitstand_messprobe.py
"""

from __future__ import annotations

import argparse
import os
import sys

import tkinter as tk
from tkinter import font as tkfont

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

ROLLENDE = 40
RAND = 8


def _tabellenname(baum):
    """Ein kurzer Eigenname aus den Spalten - die Zahl der Tabellen
    stimmt sonst nicht zur Aussage, um welche es geht."""
    spalten = set(baum["columns"])
    if not spalten:
        return "Treeview"
    if {"spur", "modus", "fenster"} <= spalten:
        return "Spurtabelle"
    if {"instrument", "kurs", "stop", "ziel"} <= spalten:
        return "Positionstabelle"
    if {"name", "port", "strategie"} <= spalten:
        return "FreqTrade-Bots"
    if {"paar", "gv"} <= spalten:
        return "FreqTrade-Positionen"
    if {"strategie", "symbol", "laufzeit"} <= spalten:
        return "Laeufe"
    if {"zeit", "modus", "aktion"} <= spalten:
        return "Journal"
    if {"instrument", "preis", "grund"} <= spalten:
        return "Haus-Buch Positionen"
    return "+".join(list(baum["columns"])[:2])


def sammle(widget, gefunden):
    if widget.winfo_class() == "Treeview":
        gefunden.append(widget)
    for kind in widget.winfo_children():
        sammle(kind, gefunden)


def bericht(titel, baum, schrift):
    breite_baum = baum.winfo_width()
    summe = sum(baum.column(sp, "width") for sp in baum["columns"])
    platz = breite_baum - ROLLENDE
    print("-" * 78)
    print("%s  —  Baum %d px | Spalten %d px | Platz %d px  %s"
          % (titel, breite_baum, summe, platz,
             "PASST" if summe <= platz else "ZU BREIT (+%d px)" % (summe - platz)))
    stretch = [sp for sp in baum["columns"] if baum.column(sp, "stretch")]
    if stretch:
        print("   stretch=True: %s  (verfaelscht jede gerechnete Breite)"
              % ", ".join(stretch))
    zu_schmal = []
    for sp in baum["columns"]:
        breite = baum.column(sp, "width")
        kopf = baum.heading(sp, "text") or ""
        if kopf and schrift.measure(kopf) + RAND > breite:
            zu_schmal.append((sp, "UEBERSCHRIFT", schrift.measure(kopf) + RAND,
                              kopf))
    # NUR die Zeilen, die wirklich gezeichnet sind. Eine Tabelle haelt mehrere
    # hundert Zeilen und zeigt eine mit height=8; die uebrigen sind ueber die
    # Leiste erreichbar und werden nicht abgeschnitten. Alle zu zaehlen war ein
    # Messfehler - gemessen 2276 "zu schmal" statt der sichtbaren Zahl.
    for iid in baum.get_children():
        try:
            box = baum.bbox(iid)
        except Exception:                                    # noqa: BLE001
            box = None
        if box is None:
            continue                      # nicht gezeichnet: nicht sichtbar
        for s2, t in zip(baum["columns"], baum.item(iid, "values")):
            if t is None or t == "":
                continue
            noetig = schrift.measure(str(t)) + RAND
            if noetig > baum.column(s2, "width"):
                zu_schmal.append((s2, "Zeile", noetig, str(t)))
    for sp in baum["columns"]:
        print("   %-16s %5d px" % (sp, baum.column(sp, "width")))
    if zu_schmal:
        print("   ZU SCHMAL: %d" % len(zu_schmal))
        for sp, art, noetig, text in zu_schmal[:10]:
            print("     %-16s %-12s braucht %4d  %s"
                  % (sp, art, noetig, text[:36]))
        if len(zu_schmal) > 10:
            print("     ... und %d weitere" % (len(zu_schmal) - 10))
    else:
        print("   alle Texte passen")
    return len(zu_schmal)


def main() -> int:
    ap = argparse.ArgumentParser(description="Leitstand-Layout messen")
    ap.add_argument("--breite", type=int, default=1280)
    ap.add_argument("--hoehe", type=int, default=860)
    args = ap.parse_args()

    import leitstand as ls
    import handelszentrale as hz

    root = tk.Tk()
    root.withdraw()
    try:
        root.tk.call("tk", "scaling", 1.1)      # wie handelszentrale.main()
    except Exception:                                        # noqa: BLE001
        pass
    ls.Handelszentrale = hz.Handelszentrale    # der Reiter braucht sie
    lei = ls.Leitstand(root)
    root.geometry("%dx%d" % (args.breite, args.hoehe))
    root.update()
    root.update_idletasks()

    schrift = tkfont.Font(family=hz.SCHRIFT_ART, size=hz.SCHRIFT_GROESSE)
    print("Fenster %dx%d | Schrift %s %d"
          % (root.winfo_width(), root.winfo_height(), hz.SCHRIFT_ART,
             hz.SCHRIFT_GROESSE))

    baeume = []
    for kind in root.winfo_children():
        sammle(kind, baeume)

    nb = lei.buch
    gesamt, gemessen = 0, 0
    for pfad in nb.tabs():
        titel = nb.tab(pfad, "text")
        nb.select(pfad)
        # `nb.select()` allein fuellt den Reiter nicht zuverlaessig - das
        # TabChanged-Event kommt nicht immer an, und die Messung lief dann in
        # zwei leere Tabellen (gemessen: "Tabellen 2" bei vier Reitern).
        # Der Reiter weiss selbst, wie er sich auffrischt: `_auffrischen`.
        i = list(nb.tabs()).index(pfad)
        try:
            lei._auffrischen(i)
        except Exception:                                    # noqa: BLE001
            pass
        root.update()
        root.update_idletasks()

        def pfad_von(w):
            teile = []
            while w is not None and w is not root:
                teile.append(str(w))
                w = w.master
            return ".".join(reversed(teile))

        ziel = pfad_von(root.nametowidget(nb.select()))
        for baum in baeume:
            if baum.winfo_width() <= 2:
                continue
            if not pfad_von(baum).startswith(ziel):
                continue
            gesamt += bericht("%s / %s" % (titel, _tabellenname(baum)),
                              baum, schrift)
            gemessen += 1
    print("=" * 78)
    print("Tabellen %d | ZU SCHMAL GESAMT: %d" % (gemessen, gesamt))
    root.destroy()
    return 1 if gesamt else 0


if __name__ == "__main__":
    sys.exit(main())