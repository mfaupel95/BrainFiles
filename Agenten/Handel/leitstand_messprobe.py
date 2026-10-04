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


def stil_segui(gross):
    """Die Ueberschriftenfamilie des Leitstands, sonst die Fenster-Schrift.

    `leitstand_stil.py` setzt Segoe UI fuer KOPF/TITEL und Consolas fuer
    TABELLE - zwei Familien in einem Fenster. Wer nur eine misst,
    verschafft sich falsche Zahlen fuer die Haelfte der Spalten.
    """
    try:
        import leitstand_stil
        fam = dict(leitstand_stil._SCHRIFTEN)[leitstand_stil.TITEL][1]
        return fam
    except Exception:                                        # noqa: BLE001
        return ""


def bericht(titel, baum, schrift, schrift_kopf=None):
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
        f_kopf = schrift_kopf or schrift
        if kopf and f_kopf.measure(kopf) + RAND > breite:
            zu_schmal.append((sp, "UEBERSCHRIFT", f_kopf.measure(kopf) + RAND,
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
    # Zwei Fehler, beide beim Bauen gemessen (Befund des UI-Audits vom
    # 04.10.2026): `withdraw()` nimmt dem Fenster jede Geometrie, und eine
    # `geometry()` VOR dem Konstruktor wird von `Leitstand.__init__` ueber
    # `start_lage` ueberschrieben - die Sonde misste deshalb 2611x1469
    # statt der angeforderten 1280x860, also eine Fenstergroesse, die
    # niemand benutzt. Also: sichtbar bauen, AUSSERHALB des Bildschirms
    # positionieren, und die Groesse NACH dem Konstruktor setzen.
    try:
        root.tk.call("tk", "scaling", 1.1)      # wie handelszentrale.main()
    except Exception:                                        # noqa: BLE001
        pass
    ls.Handelszentrale = hz.Handelszentrale    # der Reiter braucht sie
    lei = ls.Leitstand(root)
    root.update()
    root.update_idletasks()
    # Die Geometrie NACH dem Konstruktor und NACH einem Aufbau-Durchgang:
    # ein Reiter, der beim Aufbau seinen Inhalt holt, vergroessert das Fenster
    # ueber seine eigene Mindesthoehe hinaus (gemessen 1379x1469 statt
    # 1280x860). Also erst aufbauen lassen, dann setzen.
    root.geometry("%dx%d-3200-0" % (args.breite, args.hoehe))
    root.update()
    root.update_idletasks()
    print("angefordert %dx%d, tatsaechlich %dx%d"
          % (args.breite, args.hoehe, root.winfo_width(),
             root.winfo_height()))

    # Die Fenster-Schrift, gemessen am Font des Fensters - nicht die der
    # Handelszentrale. Der Leitstand nutzt Segoe UI fuer Ueberschriften und
    # Consolas fuer Zeilen; eine Sonde, die nur Consolas misst, ueberschaetzt
    # den Bedarf um rund ein Viertel (gemessen 141 px gegen 110 px fuer
    # "Anfrage verfaellt in").
    gross = lei.schrift if getattr(lei, "schrift", None) else hz.SCHRIFT_GROESSE
    schrift_zeile = tkfont.Font(family=hz.SCHRIFT_ART, size=gross)
    schrift_kopf = tkfont.Font(family=stil_segui(gross), size=gross)
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
        # ZWEIMAL auffrischen: manche Reiter lesen ihre Datei beim Bauen
        # und bekommen den Inhalt erst danach (der Markt-Reiter haelt seine
        # Berichte in prognose_berichte/, die der erste Durchlauf noch
        # nicht kennt). Einmal gemessen: die Erkläerungsspalte stand mit
        # 3584 px gegen 110 px im zweiten Durchlauf - das war der erste
        # Bauwert, nicht das Ergebnis.
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
                              baum, schrift_zeile, schrift_kopf)
            gemessen += 1
    print("=" * 78)
    print("Tabellen %d | ZU SCHMAL GESAMT: %d" % (gemessen, gesamt))
    root.destroy()
    return 1 if gesamt else 0


if __name__ == "__main__":
    sys.exit(main())