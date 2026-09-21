#!/usr/bin/env python3
"""Zaehlt die Ausstiege beliebiger Schattenbuch-Arme und meldet erst an der
Mindest-Schwelle (Watchdog-Muster).

Leere Ausgabe = nichts senden (no_agent-Cron liefert stdout nur, wenn etwas
drinsteht). Sobald ALLE Arme >= MINDEST Ausstiege haben, wird eine Meldung
ausgegeben. Danach still bis zum naechsten Vielfachen von SCHRITT (30, 40,
50, ...), damit nicht jeder Trophy-Tick dieselbe Zahl spammt.

Aufrufbeispiele (invoke through the `terminal` tool):
  python schattenbuch-ausstiege-zaehler.py --ordner <spur> --arme knapp weit
  python schattenbuch-ausstiege-zaehler.py --ordner <spur> --arme A B C \
      --mindest 20 --schritt 5 --name "demo-spur"

Externe Abhaengigkeit: nur die Standardbibliothek (csv, os, argparse).
"""
import argparse
import csv
import os
import sys

DEFAULT_ARME = ("handelsjournal.knapp.csv", "handelsjournal.weit.csv")


def zaehle_ausstiege(pfad):
    """Anzahl der geschlossenen Positionen in einem Arm-Journal."""
    try:
        with open(pfad, encoding="utf-8") as fh:
            return sum(1 for z in csv.DictReader(fh)
                       if z.get("aktion") == "schliessen")
    except FileNotFoundError:
        return 0


def haupt(spur, arme, mindest, schritt, name):
    zaehler = {arm: zaehle_ausstiege(os.path.join(spur, arm)) for arm in arme}
    min_n = min(zaehler.values())
    if min_n < mindest:
        return ""  # noch nicht genug, nichts senden
    schwelle = (min_n // schritt) * schritt
    if schwelle < mindest:
        return ""
    detail = ", ".join("%s=%d" % (k, v) for k, v in zaehler.items())
    return ("Schattenbuch %s: %d Ausstiege je Arm erreicht (%s). "
            "Auswertung faellig: <spur>/auswertung.py --pfad "
            "handelsjournal.<arm>.csv gegen das Hauptbuch."
            % (name, schwelle, detail))


def main():
    parser = argparse.ArgumentParser(
        description="Schattenbuch-Ausstiege zaehlen, erst an der Schwelle melden.")
    parser.add_argument("--ordner", required=True,
                        help="Spurenordner (z.B. Agenten/Handel/spiegel)")
    parser.add_argument("--arme", nargs="+", default=DEFAULT_ARME,
                        help="Arm-Journaldateien (default: %s)" % ", ".join(DEFAULT_ARME))
    parser.add_argument("--mindest", type=int, default=30,
                        help="Mindestanzahl Ausstiege JE Arm, sonst still")
    parser.add_argument("--schritt", type=int, default=10,
                        help="Erst bei 30 melden, dann 40, 50, ...")
    parser.add_argument("--name", default=os.path.basename(os.path.normpath(os.path.dirname(""))),
                        help="Anzeigename der Schattenbuch-Gruppe")
    args = parser.parse_args()
    meldung = haupt(args.ordner, tuple(args.arme), args.mindest,
                    args.schritt, args.name)
    if meldung:
        print(meldung)


if __name__ == "__main__":
    main()
