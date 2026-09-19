"""Die Empfehlungs-CSV des MoonDev-trading-Agenten auswerten.

Der trading_agent exportiert nach jedem Zyklus seine Papier-Urteile als CSV
(moondev_trading_empfehlungen.csv, Kopf: zeit,token,aktion,confidence,begruendung).
Dieses Skript macht daraus eine Lesart: Verteilung der Aktionen, je Token,
mit Konfidenz-Mittel und -Streuung, ueber den Zeitraum der Datei.

Was es NICHT ist: eine Handel-Bilanz. Es gibt keine echten Orders (Freigabe
fehlt), also kein G/V - die Urteile sind Beobachtung, kein Ergebnis.

Aufruf (aus dem Handel-Ordner):
    scanner/.venv/Scripts/python.exe auswertung_trading.py
    scanner/.venv/Scripts/python.exe auswertung_trading.py --csv <pfad>
    scanner/.venv/Scripts/python.exe auswertung_trading.py --token FART
"""

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HANDEL = Path(__file__).resolve().parent
DEFAULT_CSV = HANDEL / "moondev_trading_empfehlungen.csv"


def lade(zeilen):
    """CSV-zeilen zu Datensaetzen; Fehler werden geworfen, nichts geraten."""
    daten = []
    for n, zeile in enumerate(zeilen, start=1):
        # Kopfzeile (zeit,token,aktion,confidence,begruendung) ist keine Zeile.
        if zeile and zeile[0] == "zeit":
            continue
        if len(zeile) < 4:
            raise ValueError("Zeile %d: zu wenige Spalten" % n)
        daten.append({
            "zeit": zeile[0].strip(),
            "token": zeile[1].strip(),
            "aktion": zeile[2].strip().upper(),
            "confidence": _zahl(zeile[3], n),
            "begruendung": zeile[4].strip() if len(zeile) > 4 else "",
        })
    return daten


def _zahl(text, n):
    try:
        return float(text)
    except (TypeError, ValueError):
        raise ValueError("Zeile %d: confidence '%s' ist keine Zahl" % (n, text))


def verteilung(daten, token_filter=None):
    """Gesamtzahlen und je Token: Anzahl je Aktion + Konfidenz."""
    if token_filter:
        # Teilstring auf dem angezeigten (18-Zeichen-)Namen, case-insensitiv.
        daten = [d for d in daten
                 if token_filter.lower() in d["token"][:18].lower()]
    gesamt_anzahl = Counter(d["aktion"] for d in daten)
    gesamt_conf = [d["confidence"] for d in daten]

    je_token = defaultdict(list)
    for d in daten:
        je_token[d["token"]].append(d)

    zeilen = []
    for token in sorted(je_token):
        rows = je_token[token]
        zaehler = Counter(r["aktion"] for r in rows)
        confs = [r["confidence"] for r in rows]
        zeilen.append({
            "token": token[:18],
            "n": len(rows),
            "zufall": zaehler.get("NOTHING", 0),
            "kauf": zaehler.get("BUY", 0),
            "verkauf": zaehler.get("SELL", 0),
            "conf_mittel": statistics.fmean(confs) if confs else 0.0,
            "conf_min": min(confs) if confs else 0.0,
            "conf_max": max(confs) if confs else 0.0,
        })
    return daten, gesamt_anzahl, gesamt_conf, zeilen


def haupt(csv_pfad, token_filter=None):
    if not Path(csv_pfad).exists():
        print("CSV fehlt: %s" % csv_pfad)
        return 2
    with open(csv_pfad, newline="", encoding="utf-8") as f:
        daten = lade(csv.reader(f))

    if not daten:
        print("Keine Empfehlungen in %s" % csv_pfad)
        return 1
    daten, gesamt, confs, zeilen = verteilung(daten, token_filter)
    if not daten:
        print("Kein Treffer fuer --token '%s' in %s" % (token_filter, csv_pfad))
        return 1

    zeit = [d["zeit"] for d in daten]
    print("Quelle: %s" % csv_pfad)
    print("Umfang: %d Urteile, %s .. %s, %d Tokens" % (
        len(daten), zeit[0], zeit[-1], len(zeilen)))
    print("Gesamt: BUY %d | SELL %d | NOTHING %d | Confidence mittel %.1f "
          "(min %.0f / max %.0f)" % (
              gesamt.get("BUY", 0), gesamt.get("SELL", 0),
              gesamt.get("NOTHING", 0),
              statistics.fmean(confs) if confs else 0.0,
              min(confs) if confs else 0.0,
              max(confs) if confs else 0.0))
    print()
    print("%-20s %4s %6s %6s %7s  %8s" % (
        "token", "n", "kauf", "verk", "nichts", "conf.mittel"))
    for z in zeilen:
        print("%-20s %4d %6d %6d %7d  %8.1f  (%.0f..%.0f)" % (
            z["token"], z["n"], z["kauf"], z["verkauf"], z["zufall"],
            z["conf_mittel"], z["conf_min"], z["conf_max"]))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(DEFAULT_CSV), help="Pfad zur CSV")
    ap.add_argument("--token", default=None, help="nur ein Token filtern")
    a = ap.parse_args()
    sys.exit(haupt(a.csv, a.token))