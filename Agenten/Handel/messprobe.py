"""Messprobe: passen Spalten und Ueberschriften in das Fenster?

Kein Test - eine Messung am echten Fenster. Sie beantwortet die Frage
'ist hier etwas abgeschnitten?' mit Zahlen statt mit einem Blick auf ein Bild.

Regeln, die sie misst (belegt am 30.09.2026, Skill desktop-fenster):
  * Jede Spalte muss stretch=False haben und ihre Breite aus der echten
    Widget-Breite mal design.skalierung() rechnen. Tk verteilt sonst die
    Restbreite selbst (gemessen: 191 statt 125 px).
  * Die Summe der Spaltenbreiten muss in die Breite des Baums minus der
    Rollbalken und des Innenrands (~40 px) passen, sonst laeuft die letzte
    Spalte aus dem Fenster.
  * Text, der in eine Spalte soll, wird auf die Spalte gekuerzt - nicht die
    Spalte auf den Text.

Sie braucht KEINE Aenderung an handelszentrale.py: Kandidaten sind die Zeilen
im Treeview selbst plus die Ueberschriften.

Aufruf aus dem Handel-Ordner:
    scanner/.venv/Scripts/python.exe messprobe.py            # alle Tabellen
    scanner/.venv/Scripts/python.exe messprobe.py --breite 1000
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys

import tkinter as tk
from tkinter import font as tkfont

HIER = os.path.dirname(os.path.abspath(__file__))
WERKZEUGE = os.path.join(os.path.dirname(HIER), "Werkzeuge")

ROLLENDE = 40      # zwei Rollbalken (2 x 16) + Innenrand
RAND = 8           # Luft in der Zelle, damit der Text nicht ansteht


def design_laden():
    """fenster_design ueber Pfad laden - nie ueber sys.path (dort liegen
    Module mit denselben Namen wie in Handel/)."""
    pfad = os.path.join(WERKZEUGE, "fenster_design.py")
    spec = importlib.util.spec_from_file_location("fenster_design", pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kandidaten(baum):
    """Alle Texte, die in eine Spalte müssen: Überschrift und Zellinhalt."""
    kopf = []
    zellen = []
    for sp in baum["columns"]:
        kopf.append((sp, baum.heading(sp, "text") or ""))
    for iid in baum.get_children():
        werte = baum.item(iid, "values")
        for sp, text in zip(baum["columns"], werte):
            zellen.append((iid, sp, text))
    return kopf, zellen


def bericht(titel, baum, schrift):
    """Breite je Spalte, Summe gegen den Platz, zu schmale Texte."""
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

    kopf, zellen = kandidaten(baum)
    zu_schmal = []
    for sp, text in kopf:
        if not text:
            continue
        noetig = schrift.measure(str(text)) + RAND
        if noetig > baum.column(sp, "width"):
            zu_schmal.append((sp, "UEBERSCHRIFT", noetig, str(text)))
    for iid, sp, text in zellen:
        if text is None or text == "":
            continue
        noetig = schrift.measure(str(text)) + RAND
        if noetig > baum.column(sp, "width"):
            zu_schmal.append((iid, sp, noetig, str(text)))

    for sp in baum["columns"]:
        print("   %-12s %5d px" % (sp, baum.column(sp, "width")))
    if zu_schmal:
        print("   ZU SCHMAL: %d von %d Texten" % (len(zu_schmal),
                                                   len(kopf) + len(zellen)))
        for wo, sp, noetig, text in zu_schmal[:12]:
            print("     %-14s %-12s braucht %4d  %s"
                  % (wo[:14], sp, noetig, text[:40]))
        if len(zu_schmal) > 12:
            print("     ... und %d weitere" % (len(zu_schmal) - 12))
    else:
        print("   alle %d Texte passen" % (len(kopf) + len(zellen)))
    return len(zu_schmal)


def main() -> int:
    ap = argparse.ArgumentParser(description="Layout-Messung")
    ap.add_argument("--breite", type=int, default=1280)
    ap.add_argument("--hoehe", type=int, default=860)
    args = ap.parse_args()

    design = design_laden()
    design.dpi_bewusst()
    if HIER not in sys.path:
        sys.path.insert(0, HIER)
    import handelszentrale as hz

    root = tk.Tk()
    root.withdraw()
    hz.Handelszentrale(root)
    root.geometry("%dx%d" % (args.breite, args.hoehe))
    root.update()
    root.update_idletasks()

    schrift = tkfont.Font(family=hz.SCHRIFT_ART, size=hz.SCHRIFT_GROESSE)
    print("Fenster %dx%d | DPI-Faktor %.3f | Schrift %s %d"
          % (root.winfo_width(), root.winfo_height(),
             design.skalierung(root), hz.SCHRIFT_ART, hz.SCHRIFT_GROESSE))

    # Alle Treeviews des Fensters finden, ohne die Handelszentrale
    # anzufassen: jede Tabelle, die sie gebaut hat, liegt als Kind im Baume.
    baeume = []
    for kind in root.winfo_children():
        _sammle(kind, baeume)

    gesamt = 0
    for baum in baeume:
        gesamt += bericht(baum.winfo_class() + " (%d Zeilen)"
                          % len(baum.get_children()), baum, schrift)
    print("=" * 78)
    print("Tabellen %d | ZU SCHMAL GESAMT: %d" % (len(baeume), gesamt))
    root.destroy()
    return 1 if gesamt else 0


def _sammle(widget, gefunden):
    """Alle Treeviews unterhalb von widget einsammeln."""
    if widget.winfo_class() == "Treeview":
        gefunden.append(widget)
    for kind in widget.winfo_children():
        _sammle(kind, gefunden)


if __name__ == "__main__":
    sys.exit(main())