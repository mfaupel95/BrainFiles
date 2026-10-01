#!/usr/bin/env python3
"""T-197/T-198: die Backtest-Protokolle zu EINER Tabelle zusammenfassen.

Liest `logs/bt-<variante>-<bot>.txt` (Ausgabe von messung-frequenzbremse.sh)
und gibt je Lauf eine Zeile aus: Trades, Trades je Tag, Ergebnis in Prozent und
USDT, Trefferquote, groesster Rueckgang, Handelsvolumen und - daraus gerechnet -
die Gebuehren. Die Gebuehr steht nicht im Protokoll, wohl aber das Volumen und
der Satz ("Using fee 0.1000%"); sie wird zweimal genommen (Kauf und Verkauf).

Aufruf:  ./.venv/Scripts/python.exe messung-auswerten.py [<bot> ...]
"""

from __future__ import annotations

import glob
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
PROTOKOLLE = os.path.join(HIER, "logs")


def _zahl(text):
    if text is None:
        return None
    text = text.replace("\u202f", "").replace(",", "")
    treffer = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(treffer.group(0)) if treffer else None


def _feld(inhalt, label, muster=r"([^\u2502]+)"):
    """Wert aus einer Tabellenzeile '│ Label │ Wert │'."""
    m = re.search(r"\u2502\s*%s\s*\u2502\s*%s\u2502" % (re.escape(label), muster),
                  inhalt)
    return m.group(1).strip() if m else None


def lies(pfad):
    with open(pfad, encoding="utf-8", errors="replace") as f:
        inhalt = f.read()
    d = {"datei": os.path.basename(pfad)}

    tages = _feld(inhalt, "Total/Daily Avg Trades")
    d["trades"] = _zahl(tages)
    m = re.search(r"(\d+)\s*/\s*(\d+(?:\.\d+)?)", tages or "")
    d["je_tag"] = float(m.group(2)) if m else None

    d["profit_pct"] = _zahl(_feld(inhalt, "Total profit %"))
    d["profit_usdt"] = _zahl(_feld(inhalt, "Absolute profit"))
    d["volumen_usdt"] = _zahl(_feld(inhalt, "Total trade volume"))

    dd = _feld(inhalt, "Absolute drawdown")
    m = re.search(r"\((\d+(?:\.\d+)?)%\)", dd or "")
    d["dd_pct"] = float(m.group(1)) if m else None

    m = re.search(r"Using fee (\d+(?:\.\d+)?)%", inhalt)
    d["gebuehr_pct_seite"] = float(m.group(1)) if m else None
    if d["volumen_usdt"] is not None and d["gebuehr_pct_seite"] is not None:
        d["gebuehren_usdt"] = round(d["volumen_usdt"] * d["gebuehr_pct_seite"]
                                    / 100.0 * 2, 2)
    else:
        d["gebuehren_usdt"] = None

    m = re.search(r"\u2502\s*Mo?o?n?Dev\w*\s*\u2502\s*(\d+)\s*\u2502[^\u2502]*\u2502"
                  r"[^\u2502]*\u2502[^\u2502]*\u2502[^\u2502]*\u2502\s*(\d+)\s+"
                  r"\d+\s+(\d+)\s+([\d.]+)", inhalt)
    d["treffer_pct"] = float(m.group(4)) if m else None
    d["gewinn"] = int(m.group(2)) if m else None
    d["verlust"] = int(m.group(3)) if m else None

    d["kein_ergebnis"] = "Backtesting" not in inhalt and "STRATEGY SUMMARY" not in inhalt
    return d


def zeile(d):
    def fmt(w, n=1):
        return "-" if w is None else ("%%.%df" % n) % w
    return ("| %-28s | %6s | %6s | %8s | %11s | %8s | %7s | %10s | %7s |"
            % (d["datei"].replace("bt-", "").replace(".txt", ""),
               fmt(d["trades"], 0), fmt(d["je_tag"], 2), fmt(d["profit_pct"], 2),
               fmt(d["profit_usdt"], 0), fmt(d["treffer_pct"], 1),
               fmt(d["dd_pct"], 1), fmt(d["gebuehren_usdt"], 0),
               fmt(d["volumen_usdt"], 0)))


def main(argv):
    bot = argv[1] if len(argv) > 1 else ""
    muster = os.path.join(PROTOKOLLE, "bt-*-%s.txt" % bot if bot else "bt-*.txt")
    dateien = sorted(glob.glob(muster))
    if not dateien:
        print("keine Protokolle unter %s" % muster)
        return 1
    kopf = ("| %-28s | %6s | %6s | %8s | %11s | %8s | %7s | %10s | %7s |"
            % ("Lauf", "Trades", "/Tag", "Profit %", "Profit USDT", "Treffer %",
               "DD %", "Gebuehr USD", "Vol USD"))
    print(kopf)
    print("|" + "-" * 30 + "|" + ("-" * 8 + "|") * 8)
    for p in dateien:
        print(zeile(lies(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))