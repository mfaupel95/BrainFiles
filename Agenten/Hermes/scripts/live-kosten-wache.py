#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache: keine scharfe Spur darf ihre Kosten nicht decken.

WARUM (Befund 14.10.2026, orbk): orbk wurde am 12.10.2026 live geschaltet
(handel_erlaubt=true, freigabe.erfuellt=true) auf Basis eines PUNKTEbuchs, das
keinen Einsatz fuehrt - dort ist die Gebuehr nicht abziehbar. Real zahlt die
Spur auf Kraken 0,6 % je Seite = 1,2 % je Runde, verdient aber nur f_max
+0,06 % je Runde. Jede Live-Runde verlor 1,14 %. Das Punktebuch zeigte
+0,180 R/Runde und sah gesund aus.

REGEL: Eine Spur, die live handeln darf (Orderweg im Code UND
handel_erlaubt=true), muss ihre Kosten decken: f_max (die Gebuehr je Runde,
bei der die gemessene Trefferquote nur noch die Nullinie trifft) muss groesser
sein als die gesetzte Gebuehr je Runde (2 x gebuehr_taker). Wer darunter
liegt, verliert bei JEDER Runde an Gebuehren - unabhaengig von der
Trefferquote. Das ist keine Stichprobenfrage, sondern eine Rechenfrage.

Gemeldet wird NUR, was neu ist (Merkdatei): eine Spur, die neu unter die
Kostendeckung faellt, oder eine, die sich erholt. Leere Ausgabe = nichts
senden (Watchdog-Muster).

Aufruf (Hermes-Cron, no_agent):
    python live-kosten-wache.py            # alle scharfen Spuren pruefen
    python live-kosten-wache.py --jetzt    # zeigen, nichts schreiben
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
HANDEL = HERMES.parents[0] / "Handel"
CACHE = HERMES / "cache"
MERK = CACHE / "live-kosten-wache.json"

# Mindest-Rundenzahl, ab der f_max ueberhaupt eine Aussage traegt. Darunter
# ist das Buch zu klein - dann wird NICHT gemeldet (kein Befund, kein Alarm).
MINDEST_RUNDEN = 8


def _lade_spuren_stand():
    """sammle('scharf') aus spuren_stand.py - die EINE Live-Erkennung."""
    sys.path.insert(0, str(HANDEL))
    import spuren_stand  # noqa: PLC0415
    return spuren_stand.sammle("scharf")


def _f_max(spur: str):
    """(runden, f_max) aus kosten_wendepunkt - None, wenn nicht messbar."""
    sys.path.insert(0, str(HANDEL))
    import kosten_wendepunkt as kw  # noqa: PLC0415
    pfad = HANDEL / spur / "handelsjournal.csv"
    if not pfad.is_file():
        return None
    try:
        p = kw.paarung(pfad)
        w = kw.wendepunkt(p["runden"])
    except Exception:                                          # noqa: BLE001
        return None
    if not w:
        return None
    return w["runden"], w["f_max"]


def _gebuehr_runde(spur: str):
    """2 x gebuehr_taker in Prozent je Runde - None, wenn nicht gesetzt."""
    w = HANDEL / spur / "wachen.json"
    if not w.is_file():
        return None
    try:
        d = json.loads(w.read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return None
    geb = d.get("gebuehr_taker")
    if not geb or geb <= 0:
        return None
    return 2.0 * float(geb) * 100.0


def pruefe():
    """Liste der Befunde: [{spur, runden, f_max, geb_runde, text}, ...]."""
    befund = []
    for e in _lade_spuren_stand():
        spur = e["spur"]
        fm = _f_max(spur)
        if not fm:
            continue                       # kein Journal / keine messbare Runde
        runden, f_max = fm
        if runden < MINDEST_RUNDEN:
            continue                       # zu klein - kein Befund
        geb = _gebuehr_runde(spur)
        if geb is None:
            continue                       # keine Gebuehr gesetzt - nicht beurteilbar
        if f_max <= 0:
            befund.append(dict(spur=spur, runden=runden, f_max=f_max,
                                geb_runde=geb,
                                text="verliert schon bei 0 %% Gebuehr (f_max %.2f %%)"
                                     % f_max))
        elif f_max < geb:
            befund.append(dict(spur=spur, runden=runden, f_max=f_max,
                                geb_runde=geb,
                                text="f_max %.2f %% < Gebuehr %.2f %% je Runde - "
                                     "verliert %.2f %% je Runde"
                                     % (f_max, geb, geb - f_max)))
    return befund


def diff(befund, alt):
    """(neu, erholt) gegen den Merkstand - reine Funktion, damit pruefbar.

    `alt` ist {spur: text} des letzten Laufs. Neu = Spur mit anderem Text
    (oder neu aufgetaucht); erholt = Spur, die im letzten Lauf dabei war und
    jetzt nicht mehr.
    """
    neu = [b for b in befund if alt.get(b["spur"]) != b["text"]]
    erholt = [s for s in alt if s not in {b["spur"] for b in befund}]
    return neu, erholt


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--jetzt", action="store_true",
                   help="zeigen, nichts schreiben")
    a = p.parse_args()

    befund = pruefe()
    if not befund:
        return 0                            # leere Ausgabe = nichts senden

    # Merkdatei: nur NEUES melden (gleiche Feststellung nicht wiederholen).
    alt = {}
    if MERK.is_file():
        try:
            alt = json.loads(MERK.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            alt = {}
    neu, erholt = diff(befund, alt)

    if a.jetzt:
        for b in befund:
            print("%s: %s" % (b["spur"], b["text"]))
        if erholt:
            print("erholt: %s" % ", ".join(erholt))
        return 0

    if not neu and not erholt:
        return 0

    zeilen = []
    for b in neu:
        zeilen.append("LIVE-KOSTEN %s (%d Runden): %s"
                      % (b["spur"], b["runden"], b["text"]))
    if erholt:
        zeilen.append("LIVE-KOSTEN erholt: %s deckt seine Kosten wieder"
                      % ", ".join(erholt))
    print("\n".join(zeilen))

    # Merkstand schreiben (nur wenn nicht --jetzt).
    neu_stand = {b["spur"]: b["text"] for b in befund}
    CACHE.mkdir(exist_ok=True)
    MERK.write_text(json.dumps(neu_stand, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
