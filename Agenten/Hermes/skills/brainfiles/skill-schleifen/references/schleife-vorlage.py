"""Vorlage fuer eine Schleife: Prueffunktion von der Meldung getrennt.

Kopiervorlage, kein lauffaehiges Skript (Platzhalter <...> ersetzen). Der Kopf
ist die halbe Miete: er sagt der naechsten Sitzung, WARUM es die Schleife gibt,
was sie NICHT tut und wie man die Fehlerrichtung herstellt.

Drei Dinge sind Absicht und sollten beim Nachbauen nicht wegfallen:

1. `pruefen()` ist importierbar und gibt eine Liste zurueck - so kann ZWEI
   Mechanismen dieselbe Frage stellen (Hermes-Cron + Windows-Aufgabe). Eine
   nachgebaute zweite Formel prueft nur sich selbst.
2. `--datei` / die Umgebungsvariable machen die Fehlerrichtung herstellbar.
   Eine Richtung, die man nicht ohne Eingriff in echte Daten herstellen kann,
   wird nie geprueft.
3. Leere Ausgabe = gesund. Jede Zeile, die auch im Normalfall erscheint, macht
   die Wache wertlos.
"""
import argparse
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
STANDARD = HIER.parents[1] / "<unterordner>" / "<datei>"     # echte Quelle


def pruefen(quelle=None, zeitpunkt=None):
    """Liste deutscher Befundzeilen - leer, wenn alles in Ordnung ist.

    Nur lesend. Importierbar: der zweite Mechanismus ruft genau diese Funktion.
    """
    pfad = Path(quelle or os.environ.get("<NAME>_QUELLE") or STANDARD)
    try:
        roh = pfad.read_text(encoding="utf-8")
    except OSError as e:
        return ["<Name>: %s nicht lesbar (%s)" % (pfad, e)]
    befunde = []
    # ... messen, vergleichen, Befund anhaengen ...
    return befunde


def meldung(befunde):
    """Der Text, der verschickt wird. Leer = es wird nichts gesendet."""
    if not befunde:
        return ""
    return "\n".join(["<Name>: %d Befund(e)" % len(befunde)] +
                     ["- %s" % b for b in befunde[:8]] +
                     ["Nichts davon ist geaendert worden; der Waechter meldet nur."])


def main():
    ap = argparse.ArgumentParser(description="<was geprueft wird>")
    ap.add_argument("--quelle", help="andere Datei pruefen (Gegenprobe)")
    ap.add_argument("--alles", action="store_true",
                    help="auch ohne Befund die Zahlen zeigen (Abnahme)")
    args = ap.parse_args()
    befunde = pruefen(args.quelle)
    text = meldung(befunde)
    if text:
        print(text)
    elif args.alles:
        print("<Name>: kein Befund geprueft.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
