#!/usr/bin/env python3
"""Liest ein Freqtrade-Ergebnisarchiv und zaehlt die Trades je Paar.

Zweck: die GEDRUCKTE Ergebnisse-Tabelle kann ein Paar doppelt oder unvollstaendig
zeigen (Filter-/Anzeigeartefakt). Die Wahrheit steht im Archiv. Vor JEDER Meldung
ueber Paarlisten oder Trade-Zahlen hier nachzaehlen - eine doppelte Zeile in der
Anzeige ist kein Datenfehler.

Aufruf (aus dem freqtrade-Ordner):
    python scripts/backtest_archiv_lesen.py                     # neuestes Archiv
    python scripts/backtest_archiv_lesen.py --alle              # alle, aelteste zuerst
    python scripts/backtest_archiv_lesen.py <ordner-mit-zips>

Nur Standardbibliothek, kein Netz, schreibt nichts.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import zipfile
from collections import Counter

VORGABE = "user_data/backtest_results"


def archiv_lesen(pfad: str) -> dict:
    z = zipfile.ZipFile(pfad)
    namen = [n for n in z.namelist()
             if n.endswith(".json") and "config" not in n.lower()]
    if not namen:
        raise SystemExit("kein Ergebnis-JSON im Archiv %s" % pfad)
    d = json.loads(z.read(namen[0]))
    strategien = d.get("strategy") or {}
    if not strategien:
        raise SystemExit("%s hat keinen 'strategy'-Block (Meta-Datei?) - anderes "
                         "Archiv waehlen" % os.path.basename(pfad))
    name = next(iter(strategien))
    return {
        "datei": os.path.basename(pfad),
        "strategie": name,
        "trades": strategien[name].get("trades", []),
        "fenster": "%s -> %s" % (d.get("backtest_start"), d.get("backtest_end")),
    }


def bericht(e: dict) -> None:
    trades = e["trades"]
    je_paar = Counter(t["pair"] for t in trades)
    print("Archiv:     %s" % e["datei"])
    print("Strategie:  %s" % e["strategie"])
    print("Fenster:    %s" % e["fenster"])
    print("Trades:     %d ueber %d Paare" % (len(trades), len(je_paar)))
    summe = sum(je_paar.values())
    print("Summenprobe: %d == %d -> %s" % (summe, len(trades),
          "ok" if summe == len(trades) else "FEHLER"))
    for paar, n in je_paar.most_common():
        print("  %-14s %4d" % (paar, n))


def main() -> int:
    ordner, alle = VORGABE, "--alle" in sys.argv
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            ordner = a
    dateien = sorted(glob.glob(os.path.join(ordner, "*.zip")), key=os.path.getmtime)
    if not dateien:
        print("kein Archiv in %s" % ordner)
        return 1
    for pfad in (dateien if alle else dateien[-1:]):
        try:
            bericht(archiv_lesen(pfad))
        except SystemExit as fehler:
            print("uebersprungen: %s" % fehler)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
