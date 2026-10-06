#!/usr/bin/env python3
"""Recompute sign-corrected Runden/Treffer/Summe/f_max for mixed spuren from
the backtest journals, using the fixed kosten_wendepunkt pairing.

Grounding for T-230 doc corrections. Read-only; writes nothing.
"""
import csv, statistics, sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import kosten_wendepunkt as kw
import journalpaarung as jp

def paarung(pfad):
    # replicate kw.paarung / wendepunkt on the file directly
    with pfad.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    p = kw._paarung_form_b(rows)
    w = kw.wendepunkt(p["runden"]) if p["runden"] else None
    return p, w

def pick_best_lauf(spur):
    """Best lauf for a spur: most lines, else marke-anteil, else name (mirror backtest_stand)."""
    ordner = HIER / "daten" / "backtest" / spur
    if not ordner.is_dir():
        return None
    best, best_key = None, (-1, -1, "")
    for name in sorted(p.name for p in ordner.iterdir() if p.is_dir()):
        pfad = ordner / name / "handelsjournal.csv"
        if not pfad.is_file():
            continue
        with pfad.open(encoding="utf-8", newline="") as f:
            zeilen = sum(1 for _ in csv.reader(f)) - 1
        try:
            import replay
            marke = replay.auf_der_marke(pfad) if hasattr(replay, "auf_der_marke") else 0.0
        except Exception:
            marke = 0.0
        key = (zeilen, marke, name)
        if key > best_key:
            best_key, best = key, pfad
    return best

for spur in ["squeeze", "wavetrend"]:
    pfad = pick_best_lauf(spur)
    if not pfad:
        print(f"{spur}: kein Lauf")
        continue
    p, w = paarung(pfad)
    runden = p["runden"]
    if not runden:
        print(f"{spur}: keine Runden ({pfad})")
        continue
    treffer = sum(1 for r in runden if r[2] > 0)
    summe = sum(r[2] for r in runden)
    n = len(runden)
    q = treffer / n * 100 if n else 0
    print(f"{spur:12s} lauf={pfad}  runden={n}  treffer={treffer} ({q:.1f}%)  summe={summe:+.2f}  f_max={w['f_max'] if w else '?'}")
    print(f"    ohne_seite={p.get('ohne_seite')}  zwang={len(p.get('zwang', []))}")
