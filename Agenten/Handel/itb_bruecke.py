#!/usr/bin/env python3
"""Bruecke: ITB-Export -> Bus-Journal -> fremd_signale (Tor und Papierbuch).

Aufruf: python itb_bruecke.py <itb_signale.csv> [--schreiben]

Ohne --schreiben wird nur angezeigt, was ans Journal gehaengt wuerde.
Die Bruecke entscheidet nichts: sie legt Signal-Zeilen ins Journal, und
handeln.py prueft sie mit fremd_tor und fremd_papier.

Dedupe: Die ID ist ein Hash des Signalinhalts. ITB schreibt den Export jede
Stunde neu, dieselbe Kerze kommt also mehrfach. Gleiche ID heisst: nicht
erneut anhaengen, und verarbeite() ueberspringt sie ohnehin.
"""
import hashlib
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "Bus"))

import itb_uebersetzer  # noqa: E402
import journal          # noqa: E402

WER = "itb-uebersetzer"


def ereignis_fuer(signal):
    """Journal-Zeile fuer ein Signal, mit inhaltsabhaengiger ID."""
    text = json.dumps(signal, sort_keys=True)
    e = journal.neu(WER, "signal", text=text)
    e["id"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    return e


def neue_ereignisse(csv_pfad, wurzel=None):
    """Alle uebersetzten Signale, die im Journal noch nicht stehen."""
    bekannt = {z.get("id") for z in journal.lesen(wurzel=wurzel)}
    signale = itb_uebersetzer.uebersetze(itb_uebersetzer.lese_export(csv_pfad))
    out = []
    for s in signale:
        e = ereignis_fuer(s)
        if e["id"] not in bekannt:
            bekannt.add(e["id"])
            out.append(e)
    return out


def bruecke(csv_pfad, wurzel=None, schreiben=False):
    """Gibt die neuen Ereignisse zurueck; mit schreiben=True haengt sie an."""
    neu = neue_ereignisse(csv_pfad, wurzel=wurzel)
    if schreiben:
        for e in neu:
            journal.anhaengen(e, wurzel=wurzel)
    return neu


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    neu = bruecke(argv[0], schreiben="--schreiben" in argv)
    for e in neu:
        print("%s  %s" % (e["id"][:8], e["text"]))
    print("%d neu%s" % (len(neu), "" if "--schreiben" in argv else " (Vorschau - nichts geschrieben)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
