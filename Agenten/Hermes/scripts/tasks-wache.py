#!/usr/bin/env python
"""Aufgaben-Wache: offene Punkte aus TASKS.md nach Telegram (03.10.2026).

ZWEI Modi, zwei Cronjobs, ein Skript:

  --voll   die vollstaendige Liste, aber NUR wenn sie sich gegen den letzten
           Lauf geaendert hat. 49 Punkte jeden Morgen zu bekommen ist keine
           Benachrichtigung, sondern Last - und die Last ist der Grund, warum
           sie abgeschaltet wird und damit blind ist.
  --top    die ersten drei Eintraege, hoechstens einmal am Tag. Die Datei
           sortiert "## Offen" nach Aktualitaet (neueste zuerst) und fuehrt
           kein Prioritaetsfeld; die Dateireihenfolge ist deshalb die
           ehrlichste Regel fuer "was zuerst" - eine eigene Gewichtung wuerde
           eine erfinden.

Merksatz fuer die Aenderung: die volle Liste wird ueber die ANZAHL und die
NUMMERN verglichen, nicht ueber den Text. Sonst meldet jede Umformulierung
einen "Befund", und eine Wache, die bei jeder Kleinigkeit schreit, wird
abgeschaltet.

Beide Modi sind still bei Fehlern (TASKS.md fehlt, Abschnitt fehlt,
Regex passt nicht): dann ist die Frage nicht "was ist neu", sondern "was ist
kaputt" - und das gehoert gemeldet, aber nicht in jeden Lauf.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))
TASKS = os.path.join(WURZEL, "MaxHirn", "Archiv", "TASKS.md")
CACHE = os.path.join(os.path.dirname(HIER), "cache")   # Agenten/Hermes/cache
MERK_VOLL = os.path.join(CACHE, "tasks-wache-voll.json")
MERK_TOP = os.path.join(CACHE, "tasks-wache-top.json")

# "- [ ] **T-314 - Titel**"  mit optionalen Folgezeilen (eingerueckt)
BLOCK = re.compile(r"^- \[ \] \*\*(T-\d+) - (.+?)\*\*", re.M)


def lesen():
    """(nummern, [(id, titel)]) aus dem Abschnitt Offen. Nie werfen."""
    if not os.path.isfile(TASKS):
        return None, "TASKS.md fehlt (%s)" % TASKS
    with open(TASKS, encoding="utf-8") as fh:
        text = fh.read()
    if "## Offen" not in text:
        return None, "Abschnitt '## Offen' fehlt"
    teil = text.split("## Offen", 1)[1].split("\n## ", 1)[0]
    eintraege = [(m.group(1), " ".join(m.group(2).split()))
                 for m in BLOCK.finditer(teil)]
    if not eintraege:
        return None, "keine offenen Eintraege gefunden"
    return [e[0] for e in eintraege], eintraege


def merken(pfad, inhalt):
    os.makedirs(CACHE, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(inhalt, fh, ensure_ascii=False, indent=2)


def geholt(pfad):
    try:
        with open(pfad, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def kuerzen(text, grenze=95):
    return text if len(text) <= grenze else text[:grenze - 1] + "…"


def main():
    ap = argparse.ArgumentParser()
    gruppe = ap.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--voll", action="store_true")
    gruppe.add_argument("--top", action="store_true")
    args = ap.parse_args()

    nummern, eintraege = lesen()
    if nummern is None:
        alt = geholt(MERK_VOLL if args.voll else MERK_TOP)
        if alt.get("fehler") != eintraege:
            merken(MERK_VOLL if args.voll else MERK_TOP,
                   {"fehler": eintraege, "zeit": datetime.now().isoformat()})
            print("Aufgaben-Wache: %s" % eintraege)
        return 0

    heute = date.today().isoformat()
    if args.voll:
        alt = geholt(MERK_VOLL)
        if alt.get("nummern") == nummern:
            return 0                      # nichts geaendert -> schweigen
        neu = []
        bekannt = set(alt.get("nummern") or [])
        for nummer, titel in eintraege:
            if nummer not in bekannt:
                neu.append("%s %s" % (nummer, kuerzen(titel)))
        weg = [n for n in bekannt if n not in nummern]
        zeilen = ["*Aufgaben: %d offen* (vorher %d)" % (len(nummern), len(bekannt))]
        if neu:
            zeilen.append("*neu seit dem letzten Lauf:*")
            zeilen += ["- " + z for z in neu[:20]]
        if weg:
            zeilen.append("*erledigt oder umbenannt:* " + ", ".join(sorted(weg)))
        zeilen.append("")
        zeilen += ["%s %s" % (n, kuerzen(t, 110)) for n, t in eintraege[:49]]
        merken(MERK_VOLL, {"nummern": nummern, "zeit": datetime.now().isoformat()})
        print("\n".join(zeilen))
        return 0

    # --top
    alt = geholt(MERK_TOP)
    if alt.get("tag") == heute:
        return 0
    top = eintraege[:3]
    zeilen = ["*Aufgaben: die drei obersten (%d offen)*" % len(nummern),
              "Reihenfolge = Aktualitaet in TASKS.md, neueste zuerst.", ""]
    zeilen += ["%d. **%s** - %s" % (i, n, t) for i, (n, t) in enumerate(top, 1)]
    merken(MERK_TOP, {"tag": heute, "nummern": [n for n, _ in top],
                      "zeit": datetime.now().isoformat()})
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())