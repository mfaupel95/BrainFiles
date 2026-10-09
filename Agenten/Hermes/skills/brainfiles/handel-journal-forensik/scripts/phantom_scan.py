#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phantom-Zeilen im Handelsjournal einer Spur finden (VORSCHAU, schreibt NICHTS).

Fingerabdruck des Alt-Bugs (vor dem Fix): nominal_usd == margin_usd in einer
schliessen-/verkauf_von_hand-/kill_switch-Zeile - der alte Code schrieb
Preis x Menge in BEIDE Felder und blahte damit den kumulierten Hoechststand
auf, gegen den der Kill-Switch seinen Ruecklauf misst.

Nutzung (aus dem Spurordner, mit dem Spur-Python):
    ../scanner/.venv/Scripts/python.exe scripts/phantom_scan.py --spur xperp
    ../scanner/.venv/Scripts/python.exe scripts/phantom_scan.py --spur xperp --boerse

--boerse fragt zusaetzlich die positions-history der Spur (okxf) je
Verdachtszeile ab und zeigt den echten realizedPnl - das ist die gleiche
Abfrage, die der Fix fuer die Entscheidung braucht. Erwartete Quelle ist die
Funktion `geschlossene_position` des Spur-okxf.

Regeln der Bewertung (destilliert aus der Sitzung 06.-09.10.2026):
  * qualle == 'boerse'  -> ehrlicher Wert = Einsatz + realizedPnl (anteilig)
  * keine Quelle / Netzfehler -> NEUTRAL (Einsatz zurueck), NIE raten
  * nicht jede Zeile mit dem Merkmal bildet eine Runde: ohne offene
    FIFO-Paarung faellt sie aus der Kurve heraus (liegen lassen).
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

SPUREN = {"xperp": "wachen_xperp"}

# Alle Spuren, die ein handelsjournal.csv fuehren und damit auf Phantome
# geprueft werden koennen. Wer die Liste erweitert, prueft die FFIFO-
# Paarungsidee: runden_aus_journal muss es fuer die Spur geben, oder die
# Zeilenliste ist nur eine Sicht.
ALLE_SPUREN = None  # None = automatisch: Ordner unter Agenten/Handel mit handelsjournal.csv


# Journal-Spalten der Haus-Spuren (xperp): zeit, modus, aktion, inst, pos_id,
# seite, familie, preis, kontrakte, nominal_usd, margin_usd, hebel, grund
AKTIONEN_SCHLIESSEN = {"schliessen", "verkauf", "VERKAUF", "AUSSTIEG", "verkauf_von_hand"}
AKTIONEN_EROEFFNEN = {"eroeffnen", "kauf", "KAUF", "EINSTIEG"}


def _f(x):
    try:
        return float(x or 0.0)
    except (TypeError, ValueError):
        return 0.0


def lade_journal(spur):
    pfad = os.path.join(spur, "handelsjournal.csv")
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fifo_paarung(zeilen):
    """Einstieg<->Ausstieg je Instrument (aelteste zuerst), wie runden_aus_journal."""
    offen = defaultdict(list)
    runden = []
    for z in zeilen:
        inst = z.get("inst", "")
        aktion = (z.get("aktion") or "").strip().lower()
        if aktion in AKTIONEN_EROEFFNEN:
            offen[inst].append(z)
        elif aktion in AKTIONEN_SCHLIESSEN:
            if offen.get(inst):
                e = offen[inst].pop(0)
                runden.append((e, z))
    return runden


def spuren_mit_journal(root):
    handel = os.path.join(root, "Agenten", "Handel")
    aus = []
    if not os.path.isdir(handel):
        return aus
    for name in sorted(os.listdir(handel)):
        p = os.path.join(handel, name)
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, "handelsjournal.csv")):
            aus.append(name)
    return aus


def phantom_zeilen(spur, boerse=False):
    hier = os.path.dirname(os.path.abspath(__file__))
    # Skill-Ordner: Agenten/Hermes/skills/brainfiles/<skill>/scripts.
    # Spurordner liegt relativ zur BrainFiles-Wurzel (6 Ebenen hoch von hier
    # inkl. scripts/, + Agenten/Handel/<spur>).
    root = os.path.abspath(os.path.join(hier, "..", "..", "..", "..", "..", ".."))
    spur_pfad = os.path.abspath(os.path.join(root, "Agenten", "Handel", spur))
    if not os.path.isdir(spur_pfad):
        print("Spurordner nicht gefunden: %s (--spur Name unter Agenten/Handel)"
              % spur_pfad)
        return 2
    sys.path.insert(0, spur_pfad)
    zeilen = lade_journal(spur_pfad)
    runden = fifo_paarung(zeilen)

    okxf = None
    if boerse:
        try:
            mod = __import__(SPUREN[spur])
            okxf = getattr(mod, "okxf", None)
        except Exception as e:                      # noqa: BLE001
            print("Boerse nicht verfuegbar (%s) - ohne Zeugen weiter" % e)

    print("Journal: %d Zeilen, %d FIFO-Runden" % (len(zeilen), len(runden)))
    print("%-16s %-26s %12s %12s %12s  %s"
          % ("Zeit", "Instrument", "nominal", "margin", "gv", "Grund"))

    offen = defaultdict(list)
    for z in zeilen:
        inst = z.get("inst", "")
        aktion = (z.get("aktion") or "").strip().lower()
        if aktion in AKTIONEN_EROEFFNEN:
            offen[inst].append(z)
        elif aktion in AKTIONEN_SCHLIESSEN:
            nomin = _f(z.get("nominal_usd"))
            marg = _f(z.get("margin_usd"))
            verdacht = abs(nomin - marg) < 1e-9 and marg != 0.0
            zeile = (z, offen[inst].pop(0)) if offen.get(inst) else (None, None)
            if verdacht:
                gv = 0.0
                einsatz = 0.0
                if zeile[0] is not None:
                    einsatz = _f(zeile[0].get("margin_usd"))
                    gv = marg - einsatz
                zusatz = ""
                if boerse and okxf:
                    erloes, quelle, anteil = "-", "-", "-"
                    try:
                        satz = okxf.geschlossene_position(inst, 0)
                        erloes, quelle, anteil = (satz.get("realizedPnl"),
                                                  "boerse", satz.get("closeTotalPos")) \
                            if satz else ("-", "kein Satz", "-")
                    except Exception as e:           # noqa: BLE001
                        erloes, quelle, anteil = "-", "fehler: %s" % e, "-"
                    zusatz = " | boerse pnl=%s quelle=%s close=%s" \
                             % (erloes, quelle, anteil)
                print("%-16s %-26s %12.2f %12.2f %12.2f  %-20s%s"
                      % (z.get("zeit", "")[:16], inst[:26], nomin, marg,
                         gv, (z.get("grund") or "")[:20], zusatz))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spur", default=None,
                    help="Spurname unter Agenten/Handel (Default: alle "
                         "mit handelsjournal.csv)")
    ap.add_argument("--boerse", action="store_true",
                    help="Boersenzeugen je Zeile abfragen (lesend)")
    args = ap.parse_args()
    hier = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(hier, "..", "..", "..", "..", "..", ".."))
    if args.spur:
        return phantom_zeilen(args.spur, boerse=args.boerse)
    rc = 0
    for name in spuren_mit_journal(root):
        print("\n=== %s ===" % name)
        r = phantom_zeilen(name, boerse=False)
        if r:
            rc = r
    return rc


if __name__ == "__main__":
    sys.exit(main())
