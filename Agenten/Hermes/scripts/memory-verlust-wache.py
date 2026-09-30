#!/usr/bin/env python3
"""Wache: meldet NEUE Memory-Verluste, sonst nichts.

Ein `replace` mit falsch gewaehltem `old_text` loescht einen fremden Eintrag
vollstaendig (30.09.2026: 'HERMES-CONFIG 30.09.2026', 1117 Zeichen). Das Werkzeug
memory-verlust.py kann das messen - diese Wache ruft es auf und meldet nur, was
SEIT DEM LETZTEN LAUF neu dazugekommen ist.

Bauart (Hausregel): leere Ausgabe = nichts senden. Der erste Lauf legt die
Merkdatei an und schweigt (die Altfaelle sind bekannt, siehe T-246).

Aufruf:
  python memory-verlust-wache.py            # meldet nur Neues
  python memory-verlust-wache.py --alles    # zeigt auch die Altfaelle (Handbetrieb)
  python memory-verlust-wache.py --neu-baseline   # Merkdatei neu setzen
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HERMES = os.path.dirname(HIER)
MERKER = os.path.join(HERMES, "cache", "memory-verlust-wache.json")
WERKZEUG = os.path.join(HIER, "memory-verlust.py")
MAX_ZEILEN = 5
PRO_ZEILE = 160


def werkzeug_laden(pfad=WERKZEUG):
    spec = importlib.util.spec_from_file_location("memory_verlust", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["memory_verlust"] = m
    spec.loader.exec_module(m)
    return m


def kennung(eintrag):
    """Stabile Kennung eines Verlusts: der Anfang seines Textes."""
    roh = " ".join(eintrag["text"].split())[:200].lower()
    return hashlib.sha1(roh.encode("utf-8")).hexdigest()


def merker_lesen(pfad=MERKER):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("bekannt"), list):
        return None
    return d


def merker_schreiben(d, pfad=MERKER):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def meldung(neu):
    zeilen = ["Memory-Verlust: %d neue(r) Eintrag/Eintraege fehlen im Gedaechtnis." % len(neu)]
    for v in neu[:MAX_ZEILEN]:
        text = " ".join(v["text"].split())
        zeilen.append("- %s | %s | %s | %d Zeichen\n  %s"
                      % (v["ts"], v["art"], v["sid"], len(v["text"]),
                         text[:PRO_ZEILE] + ("..." if len(text) > PRO_ZEILE else "")))
    if len(neu) > MAX_ZEILEN:
        zeilen.append("... und %d weitere" % (len(neu) - MAX_ZEILEN))
    zeilen.append("Volltexte: python Agenten/Hermes/scripts/memory-verlust.py --alles")
    zeilen.append("Ursache pruefen: im Ergebnis des replace/remove steht unter "
                  "replaced_entries, WELCHER Eintrag getroffen wurde.")
    return "\n".join(zeilen)


def lauf(db=None, memory=None, merkerpfad=MERKER, alles=False, neu_baseline=False):
    """Gibt den Meldetext zurueck - leer heisst: nichts senden."""
    mv = werkzeug_laden()
    kwargs = {}
    if db:
        kwargs["db"] = db
    if memory:
        kwargs["memory"] = memory
    try:
        verluste = mv.verluste(**kwargs)
    except Exception as e:                                  # noqa: BLE001 - Wache muss melden
        return "Memory-Wache FEHLER: Verluste nicht messbar (%s: %s)" % (type(e).__name__, e)

    merker = merker_lesen(merkerpfad)
    if merker is None or neu_baseline:
        merker_schreiben({"bekannt": [kennung(v) for v in verluste],
                          "stand": "Baseline gesetzt"}, merkerpfad)
        if neu_baseline:
            return "Memory-Wache: Merkdatei neu gesetzt, %d Altfaelle als bekannt vermerkt." % len(verluste)
        return ""                                           # erster Lauf schweigt

    bekannt = set(merker.get("bekannt") or [])
    neu = [v for v in verluste if kennung(v) not in bekannt]
    if not neu:
        return ""
    merker["bekannt"] = sorted(bekannt | {kennung(v) for v in neu})
    merker_schreiben(merker, merkerpfad)
    if alles:
        return meldung(verluste)
    return meldung(neu)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alles", action="store_true", help="auch die bekannten Altfaelle zeigen")
    ap.add_argument("--neu-baseline", action="store_true", help="Merkdatei neu setzen")
    ap.add_argument("--merker", default=MERKER)
    a = ap.parse_args(argv)
    text = lauf(merkerpfad=a.merker, alles=a.alles, neu_baseline=a.neu_baseline)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())