#!/usr/bin/env python3
"""Welche Art von Null ist es? - jede Spur nach der Tabelle in
references/null-runden.md einordnen, BEVOR man ueber sie urteilt.

Die Auswertung zaehlt GESCHLOSSENE Runden. Eine Spur mit zwei heute
eroeffneten Positionen hat 0 geschlossene Runden und ist deshalb weder tot
noch still - sie arbeitet. Wer allein auf die Rundenzahl schliesst, legt
genau die Spuren still, die gerade Positionen halten.

Aufruf (aus dem Handel-Ordner, damit die Pfade passen):

    scanner/.venv/Scripts/python.exe null_runden_befund.py
    scanner/.venv/Scripts/python.exe null_runden_befund.py --alle
    scanner/.venv/Scripts/python.exe null_runden_befund.py --nur 0

Reihenfolge der Spalten ist die Reihenfolge der Entscheidung:
    zuerst  BUCH VOLL      (Position ohne Kurs - der eine echte Fehlerfall)
    dann   ARBEITET        (Positionen, Stop/Ziel noch nicht erreicht)
    dann   NUR AUSBUECHER   (Journal nur buchbereinigung/herzschlag)
    dann   WARTET          (leer, zustand frisch, kein Befund)
    zuletzt FEHLT          (keine Ergebnisdatei - Bedingung 4 unerfuellbar)

Liest nur. Schreibt nichts, legt nichts an, ruft keine Spur auf.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

BUCHHALTUNG = ("buchbereinigung", "herzschlag", "papier_altlast",
               "buch_nachgezogen_boerse", "anpassen")


def spurordner() -> list:
    return sorted(d for d in os.listdir(".")
                  if os.path.isfile(os.path.join(d, "handeln.py")))


def journal(spur: str):
    """(pfad, zeilen) der ERGEBNISdatei - ohne Sicherung und Verworfenes."""
    treffer = []
    for p in glob.glob(os.path.join(spur, "handelsjournal*.csv")):
        name = os.path.basename(p)
        if (".bak-" in name or "verworfen" in name
                or "falsch-skaliert" in name):
            continue
        treffer.append(p)
    if not treffer:
        return None, 0
    pfad = treffer[0]
    with open(pfad, encoding="utf-8", newline="") as fh:
        return pfad, max(0, sum(1 for _ in csv.DictReader(fh)))


def zustand(spur: str):
    p = os.path.join(spur, "zustand.json")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def einordnen(spur: str) -> dict:
    jpfad, zeilen = journal(spur)
    z = zustand(spur)
    positionen = (z or {}).get("positionen") or []
    lauf = str((z or {}).get("letzter_lauf") or "")

    ausbuecher = 0
    if jpfad:
        with open(jpfad, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("grund") or "").strip() in BUCHHALTUNG:
                    ausbuecher += 1

    if jpfad is None:
        lage = "FEHLT"
        grund = "keine Ergebnisdatei - Bedingung 4 unerfuellbar"
    elif positionen:
        lage = "BUCH VOLL"
        grund = ("%d Position(en) ohne Ausstieg - je Position pruefen, ob "
                 "sie einen Kurs bekommt" % len(positionen))
    elif zeilen == 0:
        lage = "WARTET"
        grund = "Journal leer, keine Position, Zustand %s" % (lauf[:16] or "?")
    elif ausbuecher >= zeilen:
        lage = "NUR AUSBUECHER"
        grund = "%d von %d Zeilen sind Buchhaltung - keine Handelsrunde" % (
            ausbuecher, zeilen)
    else:
        lage = "ARBEITET"
        grund = "%d Zeilen, davon %d Buchhaltung" % (zeilen, ausbuecher)

    return {"spur": spur, "lage": lage, "zeilen": zeilen,
            "positionen": len(positionen), "ausbucher": ausbuecher,
            "geprueft": lauf[:16], "grund": grund}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nur", default="0",
                    help="nur Spuren mit so vielen geschlossenen Runden "
                         "(Vorgabe 0 = die Null-Lagen)")
    ap.add_argument("--alle", action="store_true",
                    help="alle Spuren, nicht nur die mit 0")
    ap.add_argument("--spur", action="append", default=[],
                    help="nur diese Spur (wiederholbar)")
    a = ap.parse_args()

    spuren = a.spur or spurordner()
    if not a.spur and not a.alle and not os.path.isfile("auswertung_alle.py"):
        print("Auswertung nicht gefunden - bitte aus dem Handel-Ordner "
              "aufrufen.", file=sys.stderr)
        return 2

    treffer = [e for e in (einordnen(s) for s in spuren)]
    if not a.alle:
        grenze = int(a.nur)
        treffer = [e for e in treffer
                   if e["lage"] in ("BUCH VOLL", "WARTET", "NUR AUSBUECHER",
                                    "FEHLT") and e["zeilen"] <= grenze + 7]

    print("%-24s %-16s %6s %5s %5s  %s"
          % ("Spur", "Lage", "Zeilen", "Pos", "Ausb", "Begruendung"))
    print("-" * 108)
    for e in sorted(treffer, key=lambda x: (x["lage"], x["spur"])):
        print("%-24s %-16s %6d %5d %5d  %s"
              % (e["spur"], e["lage"], e["zeilen"], e["positionen"],
                 e["ausbucher"], e["grund"]))

    voll = [e for e in treffer if e["lage"] == "BUCH VOLL"]
    fehlt = [e for e in treffer if e["lage"] == "FEHLT"]
    print()
    print("%d Spur(en) mit offenen Positionen, %d ohne Ergebnisdatei."
          % (len(voll), len(fehlt)))
    if voll:
        print("Buch voll heisst NICHT 'tote Spur'. Erst je Position pruefen, "
              "ob sie einen Kurs bekommt - eine Position ohne Kurs ist immer "
              "ein Befund.")
    print("Merksatz: die Auswertung zaehlt GESCHLOSSENE Runden. Eine Spur mit "
          "heute eroeffneten Positionen steht bei 0 und arbeitet trotzdem. "
          "Nie allein auf die Rundenzahl schliessen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())