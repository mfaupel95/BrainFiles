#!/usr/bin/env python3
"""Fibonacci-Retracement-Papierspur.

Signal aus Fibonacci-Retracement-Levels (phi=1.618):
  Einstieg bei 38.2% Retracement, Ziel bei 23.6%, Stop bei 76.4%.

Instrumente: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP (1H).
Buch: spur_buch.py. Kein Live-Zweig.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent


def _lade(pfad: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


for _ordner in (HIER, HANDEL / "scanner"):
    if str(_ordner) not in sys.path:
        sys.path.insert(0, str(_ordner))

okx = _lade(HANDEL / "scanner" / "okx.py", "okx_fib")
spur_buch = _lade(HANDEL / "spur_buch.py", "spur_buch_fib")
fib = _lade(HANDEL / "fibonacci_retracement.py", "fib_retrace_wkzg")


def quelle(w):
    daten = {}
    kurse = {}
    for inst in w.get("instrumente", ["BTC-USDT-SWAP"]):
        k = okx.kerzen(inst, anzahl=w.get("kerzen_anzahl", 100))
        if not k:
            continue
        daten[inst] = {"kerzen": k}
        kurse[inst] = k[-1][4]
    return daten, kurse, ""


def signal(daten_inst, w):
    """Fibonacci-Retracement-Signal: 'long', 'short', 'nichts' oder ''."""
    kerzen = daten_inst.get("kerzen", [])
    richtung, _, _ = fib.signal(kerzen, richtung="auto")
    return richtung


def main():
    p = argparse.ArgumentParser(description="Fibonacci-Retracement-Papierspur")
    p.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    p.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    p.add_argument("--live", action="store_const", dest="modus",
                   const="live")
    p.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    a = p.parse_args()
    modus = a.modus or "vorschau"
    if modus == "live":
        print("--live verweigert: Papierspur ohne Orderweg.")
        modus = "vorschau"
    return spur_buch.zyklus(HIER, quelle, signal, modus,
                            ereignis_name="handel/fib_retrace")


if __name__ == "__main__":
    sys.path.insert(0, str(HIER.parent.parent / "Bus"))
    import ereignis  # noqa: E402
    ereignis.lauf("handel/fib_retrace")
    sys.exit(main())
