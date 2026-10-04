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
    kopf, zellen = kandidaten(baum)
    zu_schmal = []
    for sp, text in kopf:
        if text and schrift.measure(str(text)) + RAND > baum.column(sp, "width"):
            zu_schmal.append((sp, "UEBERSCHRIFT", schrift.measure(str(text)), str(text)))
    for iid, sp, text in zellen:
        if text is None or text == "":
            continue
        noetig = schrift.measure(str(text)) + RAND
        if noetig > baum.column(sp, "width"):
            zu_schmal.append((iid, sp, noetig, str(text)))

    # "ZU BREIT" ist bei kleiner Schrift ein FEHLER und bei grosser keiner:
    # brauchen die Texte mehr, als der Baum hergibt, ist die waagerechte
    # Leiste die richtige Antwort - sie hat jede Tabelle. Gemessen: Schrift 11
    # -> 970 px in 954 px Platz mit UEBERHANG (die Spalten waren breiter als
    # ihr Text noetig), Schrift 16 -> 1276 px in 1186 px, weil die Texte
    # 1276 px brauchen. Beides sieht gleich aus, ist aber nicht dasselbe.
    zustand = "PASST"
    if summe > platz:
        zustand = ("ZU BREIT (+%d px) - kein UEBERHANG, der Text braucht es"
                   % (summe - platz) if not zu_schmal else
                   "BRAUCHT +%d px - waagerechte Leiste noetig"
                   % (summe - platz))
    print("-" * 78)
    print("%s  —  Baum %d px | Spalten %d px | Platz %d px  %s"
          % (titel, breite_baum, summe, platz, zustand))

    stretch = [sp for sp in baum["columns"] if baum.column(sp, "stretch")]
    if stretch:
        print("   stretch=True: %s  (verfaelscht jede gerechnete Breite)"
              % ", ".join(stretch))

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
    ap.add_argument("--reiter", action="store_true",
                    help="jeden Reiter einmal waehlen und messen "
                         "(sonst misst Tk die inaktiven mit 1 px)")
    ap.add_argument("--schrift", type=int, default=0,
                    help="Schriftgroesse in der Messung (Vorgabe: die "
                         "der Handelszentrale, 11). Der Nutzer kann im "
                         "Leitstand bis 16 waehlen - 13 ist sein "
                         "gespeicherter Wert, siehe "
                         "leitstand_zustand.json.")
    ap.add_argument("--dpi", action="store_true",
                    help="mit dpi_bewusst() - Standard ist der Weg der "
                         "Handelszentrale selbst: ohne, mit tk scaling 1.1")
    args = ap.parse_args()

    design = design_laden()
    if args.dpi:
        design.dpi_bewusst()          # erst VOR dem ersten Tk()
    if HIER not in sys.path:
        sys.path.insert(0, HIER)
    import handelszentrale as hz

    root = tk.Tk()
    # NICHT withdraw(): ein verborgenes Fenster hat keine Geometrie. Tk
    # vermisst ein verborgenes Widget mit 1 px, und die Rechnung bekaeme
    # keinen Platz - gemeldet wurde dann "ZU BREIT (+114 px)" fuer eine
    # Tabelle, die im echten Fenster mit 1058 px in 1226 px passt.
    # Stattdessen aus dem Bild auf einer Position links vom Bildschirm.
    root.geometry("%dx%d-3200-0" % (args.breite, args.hoehe))
    if not args.dpi:
        try:
            root.tk.call("tk", "scaling", 1.1)   # wie handelszentrale.main()
        except Exception:                                    # noqa: BLE001
            pass
    zentrale = hz.Handelszentrale(root)
    root.geometry("%dx%d" % (args.breite, args.hoehe))
    root.update()
    root.update_idletasks()

    # Die Schriftgroesse aus der Messung, nicht die aus dem Modul: der
    # Nutzer waehlt sie im Fenster (Leitstand: 8..16, sein gespeicherter
    # Wert ist 13), und `zeichen_breite` liest genau dieses Attribut.
    groesse = args.schrift or hz.SCHRIFT_GROESSE
    hz.SCHRIFT_GROESSE = groesse
    schrift = tkfont.Font(family=hz.SCHRIFT_ART, size=groesse)
    print("Fenster %dx%d | DPI-Faktor %.3f | Schrift %s %d"
          % (root.winfo_width(), root.winfo_height(),
             design.skalierung(root), hz.SCHRIFT_ART, hz.SCHRIFT_GROESSE))

    # Alle Treeviews des Fensters finden, ohne die Handelszentrale
    # anzufassen: jede Tabelle, die sie gebaut hat, liegt als Kind im Baume.
    baeume = []
    for kind in root.winfo_children():
        _sammle(kind, baeume)

    # Die Nachrechnung braucht mehrere Takte: sie rechnet weiter, solange
    # sich die Zeilenzahl aendert (hoechstens fuenf Durchgaenge). Nach EINEM
    # `update()` hat sie einmal gerechnet, aber der zweite Durchgang fehlt -
    # und genau der schaltet die Nachrechnung frei. Drei Takte sind einer mehr
    # als noetig; danach wird gemessen, nicht geraten.
    for _ in range(3):
        zentrale.refresh()
        root.update()
        root.update_idletasks()
    print("Nachrechnung: %d Durchgaenge, fertig=%s"
          % (zentrale._breiten_durchgang, zentrale._breiten_gesetzt))

    gesamt, gemessen = 0, 0
    if args.reiter:
        nb = notebook_von(root)
        if nb is not None:
            gesamt, gemessen = _reiter_messen(root, baeume, schrift, nb)
    else:
        for baum in baeume:
            # Nur een aktiver Reiter ist von Tk wirklich vermessen. Die
            # uebrigen bekommen 1 px und wuerden als "ZU BREIT (+1229 px)"
            # daselbe melden - das ist eine Messluecke, kein Layoutfehler.
            if baum.winfo_ismapped() and baum.winfo_width() > 2:
                gesamt += bericht("%s / %s" % (_titel(baum),
                                                _tabellenname(baum)),
                                  baum, schrift)
                gemessen += 1
        if gemessen < len(baeume):
            print("NICHT GEMESSEN: %d von %d Tabellen (Reiter nicht aktiv) - "
                  "mit --reiter messen" % (len(baeume) - gemessen, len(baeume)))
    print("=" * 78)
    print("Tabellen %d | ZU SCHMAL GESAMT: %d" % (gemessen, gesamt))
    root.destroy()
    return 1 if gesamt else 0


def _titel(baum):
    """Der Reitername, in dem die Tabelle liegt - sonst sagt die Meldung
    nur 'Treeview' und man weiss nicht, welche Tabelle gemeint war."""
    try:
        nb = baum.master
        while nb is not None and nb.winfo_class() != "TNotebook":
            nb = nb.master
        if nb is not None:
            return nb.tab(nb.select(), "text")
    except Exception:                                        # noqa: BLE001
        pass
    return baum.winfo_name()


def notebook_von(root):
    """Das erste Notebook des Fensters (es hat nur eins)."""
    gefunden = []

    def lauf(w):
        if w.winfo_class() == "TNotebook":
            gefunden.append(w)
            return
        for kind in w.winfo_children():
            lauf(kind)

    lauf(root)
    return gefunden[0] if gefunden else None


def _reiter_messen(root, baeume, schrift, nb):
    """Jeden Reiter einmal waehlen, updaten, messen - sonst misst Tk 1 px.

    Zwei Fallen, beide beim Bauen gemessen:

    1. Zuordnung Tabelle -> Reiter aus dem WIDGET-Pfad, nicht aus
       `nb.select()`: das steht beim Messen schon auf dem naechsten Reiter,
       waehrend noch der alte Aufbau sichtbar ist.
    2. `winfo_ismapped()` bleibt bei einer einmal gezeigten Notebook-Seite
       TRUE, auch wenn sie nicht mehr vorne liegt. Ohne eigene Pruefung
       wurde dieselbe Tabelle unter jedem Reiternamen gezaehlt und die
       Summe war das Zwei- bis Vierfache der echten Zahl. Der Weg zur
       Auswahl ist `nb.select()`; der eines Baums ist
       `str(nb.select())` gefolgt vom Pfad des Baums.
    """
    gesamt, gemessen = 0, 0
    namen = {}
    for pfad in nb.tabs():
        try:
            namen[pfad] = nb.tab(pfad, "text")
        except Exception:                                    # noqa: BLE001
            pass

    def pfad_von(w):
        teile = []
        while w is not None and w is not root:
            teile.append(str(w))
            w = w.master
        return ".".join(reversed(teile))

    for pfad, titel in namen.items():
        nb.select(pfad)
        root.update()
        root.update_idletasks()
        vorne = pfad_von(root.nametowidget(nb.select()))
        for baum in baeume:
            if baum.winfo_width() <= 2:
                continue
            if not pfad_von(baum).startswith(vorne):
                continue          # gehoert zu einem anderen Reiter
            gesamt += bericht("%s / %s" % (titel, _tabellenname(baum)),
                              baum, schrift)
            gemessen += 1
    return gesamt, gemessen


def _tabellenname(baum):
    """Ein kurzer Eigenname der Tabelle aus ihren Spalten - 'Treeview' sagt
    nichts, wenn ein Fenster fuenf davon hat."""
    spalten = list(baum["columns"])
    if not spalten:
        return "Treeview"
    if {"spur", "modus", "fenster"} <= set(spalten):
        return "Spurtabelle"
    if {"instrument", "kurs", "stop", "ziel"} <= set(spalten):
        return "Positionstabelle"
    if {"name", "port", "strategie"} <= set(spalten):
        return "FreqTrade-Bots"
    if {"paar", "gv"} <= set(spalten):
        return "FreqTrade-Positionen"
    return "+".join(spalten[:3])


def _sammle(widget, gefunden):
    """Alle Treeviews unterhalb von widget einsammeln."""
    if widget.winfo_class() == "Treeview":
        gefunden.append(widget)
    for kind in widget.winfo_children():
        _sammle(kind, gefunden)


if __name__ == "__main__":
    sys.exit(main())