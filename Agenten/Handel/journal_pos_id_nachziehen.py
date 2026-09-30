#!/usr/bin/env python3
"""Die Spalte `pos_id` in VORHANDENE Journale nachziehen (T-095).

WARUM ES DIESES WERKZEUG GIBT
-----------------------------
Die Spuren schreiben in eine bestehende Journaldatei nur die Spalten, die
deren KOPF nennt (`pos_kennung.spalten`). Ohne diesen Schritt bliebe die
Kennung in jedem Altjournal ungeschrieben - die Auswertung fiele still auf die
Instrumentenpaarung zurueck, und die Warnung im Log waere der einzige Hinweis.

WAS ES TUT
----------
Es haengt `pos_id` als LETZTE Spalte an die Kopfzeile. Die Zeilen selbst werden
NICHT angefasst: `csv.DictReader` gibt einem kurzen Altbestand fuer die neue
Spalte `None`, und das zaehlt als "keine Kennung" - genau der Zustand, der
ausgewiesen wird. Eine Sicherung liegt daneben (`*.bak-JJJJMMTT`).

SICHERHEIT
----------
Ein Journal, das juenger als `--schonfrist` Sekunden ist, wird uebersprungen:
der Dauerlauf schreibt waehrend eines Zyklus an dieselbe Datei, und ein
gleichzeitiger Anhang ginge beim Neuschreiben verloren. Ohne `--anwenden` ist
der Lauf eine Vorschau.

Aufruf (aus Agenten/Handel):
    .venv/Scripts/python.exe journal_pos_id_nachziehen.py
    .venv/Scripts/python.exe journal_pos_id_nachziehen.py --anwenden
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
SPALTE = "pos_id"
SCHONFRIST_S = 300.0


def journal_dateien() -> list:
    """Alle Handelsjournale der Spuren - ohne Sicherungen und Altbestaende."""
    treffer = []
    for name in sorted(os.listdir(HIER)):
        ordner = os.path.join(HIER, name)
        if not os.path.isdir(ordner) or name.startswith("."):
            continue
        for datei in sorted(os.listdir(ordner)):
            if not datei.startswith("handelsjournal") or not datei.endswith(".csv"):
                continue
            if ".bak" in datei or "falsch" in datei or "verworfen" in datei:
                continue
            treffer.append(os.path.join(ordner, datei))
    return treffer


def kopf_und_rest(pfad):
    """(Kopfzeile, Zeilenende, Rest) eines Journals - ohne es zu veraendern."""
    with open(pfad, "rb") as f:
        roh = f.read()
    if b"\n" not in roh:
        return None, b"", b""
    kopf, rest = roh.split(b"\n", 1)
    ende = b"\r\n" if kopf.endswith(b"\r") else b"\n"
    return kopf.rstrip(b"\r"), ende, rest


def nachziehen(pfad, anwenden=False, schonfrist=SCHONFRIST_S):
    """(erledigt, meldung) - haengt die Spalte an, wenn sie fehlt."""
    kopf, ende, rest = kopf_und_rest(pfad)
    if kopf is None:
        return False, "keine Kopfzeile"
    felder = [k.strip().decode("utf-8", "replace") for k in kopf.split(b",")]
    if SPALTE in felder:
        return False, "hat die Spalte schon"
    if not anwenden:
        return True, "wuerde %s anhaengen (%d Spalten -> %d)" % (
            SPALTE, len(felder), len(felder) + 1)
    alter = time.time() - os.path.getmtime(pfad)
    if alter < schonfrist:
        return False, "erst %.0f s alt - Schonfrist %.0f s" % (alter, schonfrist)
    sicherung = "%s.bak-%s" % (pfad, datetime.now().strftime("%Y%m%d"))
    shutil.copy2(pfad, sicherung)
    neu = kopf + b"," + SPALTE.encode("utf-8") + ende + rest
    with open(pfad, "wb") as f:
        f.write(neu)
    return True, "nachgezogen (%d Spalten), Sicherung %s" % (
        len(felder) + 1, os.path.basename(sicherung))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--anwenden", action="store_true",
                    help="wirklich schreiben (sonst nur Vorschau)")
    ap.add_argument("--schonfrist", type=float, default=SCHONFRIST_S,
                    help="Journale, die juenger sind, ueberspringen (Sekunden)")
    ap.add_argument("--nur", help="nur Dateien, deren Pfad diesen Text enthaelt")
    a = ap.parse_args(argv)

    dateien = journal_dateien()
    if a.nur:
        dateien = [d for d in dateien if a.nur in d]
    geaendert = 0
    for pfad in dateien:
        try:
            ok, meldung = nachziehen(pfad, a.anwenden, a.schonfrist)
        except OSError as e:
            ok, meldung = False, "nicht lesbar: %s" % e
        if ok:
            geaendert += 1
        print("%-58s %s" % (os.path.relpath(pfad, HIER), meldung))
    print("\n%d von %d Journalen %s" % (
        geaendert, len(dateien), "nachgezogen" if a.anwenden else "zu aendern"))
    return 0


if __name__ == "__main__":
    sys.exit(main())