"""Tabellen-Messprobe fuer JEDES tkinter-Fenster des Hauses.

Kein Test - eine Messung am echten Fenster. Sie beantwortet 'ist hier etwas
abgeschnitten?' mit Zahlen statt mit einem Blick auf ein Bild.

Der Aufrufer wird ueber die Kommandozeile benannt, damit diese Datei kein
einziges Fenster kennt:

    python tabellen-messprobe.py --fenster handelszentrale:Handelszentrale
    python tabellen-messprobe.py --fenster leitstand:Leitstand --breite 1600
    python tabellen-messprobe.py --fenster handelszentrale:Handelszentrale \\
        --breite 1000 --hoehe 640

Der Namensraum `modul:klasse` muss zu einem Fensterfuehrer passen, der
`root` als erstes Argument nimmt und sich selbst in den Baum packt
(`handelszentrale.Handelszentrale(root)`, `leitstand.Leitstand(root)`).

Gemessen wird:
  * Spaltenbreite je Spalte, Summe gegen den Platz im Baum (Rollbalken und
    Innenrand abgezogen) -> 'ZU BREIT' heisst, die letzte Spalte laeuft aus dem
    Fenster;
  * jeder Spaltenkopf und jeder Zellinhalt gegen `tkfont.measure()` -> jeder
    Ueberhang wird als eigener Text gezaehlt, nicht als Spalte;
  * jede Spalte mit `stretch=True` - die verfaelscht jede gerechnete Breite,
    weil Tk die Restbreite selbst verteilt.

Exitcode 1, sobald ein Text zu schmal ist oder eine Tabelle zu breit wird.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sys
import tkinter as tk
from tkinter import font as tkfont

ROLLENDE = 40      # zwei Rollbalken (2 x 16) + Innenrand
RAND = 8           # Luft in der Zelle, damit der Text nicht ansteht


def _design():
    """fenster_design ueber Pfad laden, nie ueber sys.path (dort liegen Module
    mit denselben Namen wie in Handel/)."""
    hier = os.path.dirname(os.path.abspath(__file__))
    for kandidat in (os.path.join(hier, "fenster_design.py"),
                     os.path.join(os.path.dirname(os.path.dirname(hier)),
                                  "Werkzeuge", "fenster_design.py")):
        if os.path.exists(kandidat):
            spec = importlib.util.spec_from_file_location("fenster_design",
                                                          kandidat)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit("fenster_design.py nicht gefunden - Pfad mit --design")


def _sammle(widget, gefunden):
    """Alle Treeviews unterhalb von widget einsammeln."""
    if widget.winfo_class() == "Treeview":
        gefunden.append(widget)
    for kind in widget.winfo_children():
        _sammle(kind, gefunden)


def _texte(baum):
    kopf = [(sp, baum.heading(sp, "text") or "") for sp in baum["columns"]]
    zellen = []
    for iid in baum.get_children():
        werte = baum.item(iid, "values")
        for sp, text in zip(baum["columns"], werte):
            zellen.append((iid, sp, text))
    return kopf, zellen


def _baum_beschriftung(baum):
    """Ein Treeview ohne Namen: der erste Spaltentext der Ueberschrift."""
    for sp in baum["columns"]:
        text = baum.heading(sp, "text")
        if text:
            return str(text)
    return "?"


def bericht(baum, schrift):
    """Messung EINES Baums. Liefert (zu schmale Texte, Tabelle zu breit)."""
    breite_baum = baum.winfo_width()
    summe = sum(baum.column(sp, "width") for sp in baum["columns"])
    platz = breite_baum - ROLLENDE
    titel = "%s (%d Zeilen)" % (_baum_beschriftung(baum),
                               len(baum.get_children()))
    print("-" * 78)
    # Eine Tabelle, die im aktuellen Reiter nicht sichtbar ist, hat Breite 1 px.
    # Ihre Spaltenbreiten sind die Vorgaben, nicht das Ergebnis - die Summe
    # waere eine Zahl ohne Fenster und wuerde als 'ZU BREIT' gemeldet.
    if breite_baum < 100:
        print("%s  —  NICHT SICHTBAR (Baum %d px): Breiten sind Vorgaben, "
              "Summe %d px wird NICHT gewertet" % (titel, breite_baum, summe))
        for sp in baum["columns"]:
            print("   %-14s %5d px%s" % (sp, baum.column(sp, "width"),
                                          "  stretch=True" if baum.column(sp, "stretch") else ""))
        return 0, False

    print("%s  —  Baum %d px | Spalten %d px | Platz %d px  %s"
          % (titel, breite_baum, summe, platz,
             "PASST" if summe <= platz else "ZU BREIT (+%d px)" % (summe - platz)))
    stretch = [sp for sp in baum["columns"] if baum.column(sp, "stretch")]
    if stretch:
        print("   stretch=True: %s  (verfaelscht jede gerechnete Breite)"
              % ", ".join(stretch))
    for sp in baum["columns"]:
        print("   %-14s %5d px" % (sp, baum.column(sp, "width")))

    kopf, zellen = _texte(baum)
    zu_schmal = []
    for sp, text in kopf:
        if text and schrift.measure(str(text)) + RAND > baum.column(sp, "width"):
            zu_schmal.append(("UEBERSCHRIFT", sp, schrift.measure(str(text)) + RAND,
                              str(text)))
    for iid, sp, text in zellen:
        if text is None or text == "":
            continue
        noetig = schrift.measure(str(text)) + RAND
        if noetig > baum.column(sp, "width"):
            zu_schmal.append((iid, sp, noetig, str(text)))

    if zu_schmal:
        print("   ZU SCHMAL: %d von %d Texten"
              % (len(zu_schmal), len(kopf) + len(zellen)))
        for wo, sp, noetig, text in zu_schmal[:12]:
            print("     %-14s %-14s braucht %4d  %s"
                  % (str(wo)[:14], sp, noetig, text[:40]))
        if len(zu_schmal) > 12:
            print("     ... und %d weitere" % (len(zu_schmal) - 12))
    else:
        print("   alle %d Texte passen" % (len(kopf) + len(zellen)))
    return len(zu_schmal), summe > platz


def main() -> int:
    ap = argparse.ArgumentParser(description="Layout-Messung (siehe Kopf)")
    ap.add_argument("--fenster", required=True,
                    help="modul:Klasse des Fensterfuehrers")
    ap.add_argument("--breite", type=int, default=1280)
    ap.add_argument("--hoehe", type=int, default=860)
    ap.add_argument("--ordner", default="",
                    help="Verzeichnis, in dem das Modul liegt (Vorgabe: .)")
    args = ap.parse_args()

    if args.ordner:
        sys.path.insert(0, os.path.abspath(args.ordner))
    design = _design()
    design.dpi_bewusst()

    modulname, _, klassenname = args.fenster.partition(":")
    if not klassenname:
        raise SystemExit("--fenster braucht die Form modul:Klasse")
    modul = importlib.import_module(modulname)
    klasse = getattr(modul, klassenname)

    root = tk.Tk()
    root.withdraw()
    klasse(root)
    # withdraw() erzeugt KEINE Geometrie (siehe SKILL.md) - die Breite kommt
    # von hier, sonst misst die Probe 1 px.
    root.geometry("%dx%d" % (args.breite, args.hoehe))
    root.update()
    root.update_idletasks()

    art = getattr(modul, "SCHRIFT_ART", design.SCHRIFT_ART)
    groesse = getattr(modul, "SCHRIFT_GROESSE", design.SCHRIFT_GROESSE)
    schrift = tkfont.Font(family=art, size=groesse)
    print("Fenster %dx%d | DPI-Faktor %.3f | Schrift %s %d"
          % (root.winfo_width(), root.winfo_height(), design.skalierung(root),
             art, groesse))

    baeume = []
    for kind in root.winfo_children():
        _sammle(kind, baeume)
    print("Tabellen gefunden: %d" % len(baeume))

    gesamt, zu_breit = 0, 0
    for baum in baeume:
        n, breit = bericht(baum, schrift)
        gesamt += n
        zu_breit += 1 if breit else 0
    print("=" * 78)
    print("ZU SCHMAL GESAMT: %d | ZU BREIT: %d" % (gesamt, zu_breit))
    root.destroy()
    return 1 if (gesamt or zu_breit) else 0


if __name__ == "__main__":
    sys.exit(main())