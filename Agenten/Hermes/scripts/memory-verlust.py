#!/usr/bin/env python3
"""Findet Memory-Eintraege, die belegbar ersetzt oder entfernt wurden und heute fehlen.

Warum das geht: Jedes Ergebnis eines `replace`/`remove`-Aufrufs traegt im JSON die Felder
`replaced_entries` bzw. `removed_entries` mit dem VOLLEN Text des getroffenen Eintrags.
state.db (Tabelle messages, tool_name='memory') ist damit ein Archiv aller Eintraege,
die je ersetzt oder geloescht wurden - unabhaengig von Sicherungen.

Aufrufe:
  python memory-verlust.py                 # Liste: belegte Verluste (Volltext gekuerzt)
  python memory-verlust.py --alles         # Volltexte ausgeben
  python memory-verlust.py --retten DATEI  # Volltexte als Markdown zurueckschreiben
  python memory-verlust.py --json DATEI    # Maschinenlesbar

Als Verlust gilt: der Eintrag steht heute NICHT mehr in memories/MEMORY.md.
Ein absichtliches Entfernen (action 'remove') wird getrennt ausgewiesen.
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HERMES = os.path.dirname(HIER)                      # Agenten/Hermes
DB = os.path.join(HERMES, "state.db")
MEMORY = os.path.join(HERMES, "memories", "MEMORY.md")


def zeit(rohwert):
    """state.db speichert Zeitstempel als Unix-Zeit (REAL); lesbar machen."""
    try:
        return datetime.datetime.fromtimestamp(float(rohwert)).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return str(rohwert)


def eintraege_aus_db(db=DB):
    """Alle belegten replaced_entries/removed_entries aus state.db."""
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    treffer = []
    for r in con.execute(
        "select timestamp, session_id, content from messages "
        "where tool_name='memory' and content like '%_entries%' order by timestamp"
    ):
        txt = (r["content"] or "").strip()
        if not txt.startswith("{"):
            continue
        try:
            d = json.loads(txt)
        except ValueError:
            continue
        for feld in ("replaced_entries", "removed_entries"):
            for _, alt in (d.get(feld) or {}).items():
                alt = re.sub(r"\s+", " ", str(alt)).strip()
                if alt:
                    treffer.append({"ts": zeit(r["timestamp"]), "sid": r["session_id"],
                                    "art": feld, "text": alt})
    con.close()
    return treffer


def flachmachen(text):
    """Alles ausser Wortzeichen/./-/ zu einem Leerzeichen, klein - fuer Kopfvergleiche."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w./-]+", " ", text.lower())).strip()


def noch_da(text, memory_text):
    """Steht der Eintrag heute noch im Gedaechtnis - ganz, umgeschrieben oder wiederhergestellt?

    Drei Proben, weil ein Eintrag auf drei Weisen weiterleben kann:
      1. woertlich (normiert),
      2. umgeschrieben mit gleichem Anfang (erste 70 Zeichen),
      3. wiederhergestellt mit Vermerk - dann steht die KOPF-SIGNATUR (erste drei
         Wortzeichen, ohne Satzzeichen) wieder da, z. B. bei
         'HERMES-CONFIG 30.09.2026 (Stand; am ... WIEDERHERGESTELLT ...)'.
    """
    flach = re.sub(r"\s+", " ", memory_text)
    if text in flach:
        return True
    if text[:70] in flach:
        return True
    sig = " ".join(re.findall(r"[\w./-]+", text.lower())[:3])
    return len(sig) >= 15 and sig in flachmachen(memory_text)


def verluste(db=DB, memory=MEMORY):
    with open(memory, encoding="utf-8") as f:
        mem = f.read()
    raus = []
    for t in eintraege_aus_db(db):
        if noch_da(t["text"], mem):
            continue
        raus.append(t)
    return raus


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alles", action="store_true", help="Volltexte ausgeben")
    ap.add_argument("--retten", metavar="DATEI", help="Volltexte als Markdown sichern")
    ap.add_argument("--json", metavar="DATEI", help="maschinenlesbar sichern")
    ap.add_argument("--db", default=DB)
    ap.add_argument("--memory", default=MEMORY)
    a = ap.parse_args(argv)

    alle = eintraege_aus_db(a.db)
    raus = verluste(a.db, a.memory)
    absichtlich = [t for t in raus if t["art"] == "removed_entries"]

    print("Belegte Ersetzungen/Entfernungen: %d" % len(alle))
    print("davon heute NICHT mehr im Gedaechtnis: %d (davon absichtlich entfernt: %d)"
          % (len(raus), len(absichtlich)))
    for t in raus:
        print("\n=== %s | %s | %s | %d Zeichen" % (t["ts"], t["art"], t["sid"], len(t["text"])))
        print("   ", t["text"] if a.alles else t["text"][:200])

    if a.json:
        json.dump(raus, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\ngeschrieben: %s" % a.json)
    if a.retten:
        with open(a.retten, "w", encoding="utf-8", newline="") as f:
            f.write("# Belegte Memory-Verluste (aus state.db)\n\n")
            for t in raus:
                f.write("## %s | %s | Sitzung %s\n\n" % (t["ts"], t["art"], t["sid"]))
                f.write(t["text"] + "\n\n")
        print("geschrieben: %s" % a.retten)
    return 0


if __name__ == "__main__":
    sys.exit(main())