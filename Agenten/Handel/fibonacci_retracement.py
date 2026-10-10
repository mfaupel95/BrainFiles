#!/usr/bin/env python3
"""Fibonacci-Retracement-Levels fuer Handelsspuren.

Berechnet Retracement-Levels aus Fibonacci-Zahlen (phi=1.618):
  23.6% (1/phi^3), 38.2% (1/phi^2), 50%, 61.8% (1/phi), 76.4% (1-1/phi^3), 100%

Verwendung:
  python fibonacci_retracement.py BTC-USDT-SWAP --vorschau
"""

from __future__ import annotations
import argparse
import json
import math
import os
import sys

PHI = (1 + math.sqrt(5)) / 2  # 1.618...
# Fibonacci-Retracement-Levels (Anteil der letzten Bewegung)
FIB_LEVELS = {
    0.236: "23.6%%",
    0.382: "38.2%%",
    0.500: "50%%",
    0.618: "61.8%%",
    0.764: "76.4%%",
}
SCHWELLE_EINSTIEG = 0.500   # bei 50% Retracement einsteigen
SCHWELLE_ZIEL = 0.236       # bei 23.6% Ziel setzen
SCHWELLE_STOP = 0.764       # bei 76.4% stoppen


def fib_preise(hoch: float, tief: float) -> dict[str, float]:
    """Fibonacci-Retracement-Preise zwischen Hoch und Tief berechnen.

    Args:
        hoch: Hoechstkurs der letzten Bewegung
        tief: Tiefstkurs der letzten Bewegung

    Returns:
        Dict level_name -> preis
    """
    spanne = hoch - tief
    if spanne <= 0:
        return {}
    return {name: tief + anteil * spanne
            for anteil, name in sorted(FIB_LEVELS.items())}


def retracement_stand(kurs: float, hoch: float, tief: float) -> float:
    """Wo steht der Kurs im Retracement? 0 = am Tief, 1 = am Hoch.

    Fuer long: steigender Markt, Retracement von oben.
    0 = vollstaendig retraced (am Tief), 1 = kein Retracement (am Hoch).
    """
    spanne = hoch - tief
    if spanne <= 0:
        return 0.5
    return max(0.0, min(1.0, (kurs - tief) / spanne))


def signal(kerzen: list, richtung: str = "auto"
           ) -> tuple[str, dict | None, str]:
    """Fibonacci-Retracement-Signal: Einstieg/Empfehlung aus Kerzen.

    Args:
        kerzen: Liste von (zeit_ms, open, high, low, close, volume)
        richtung: 'long', 'short', oder 'auto'

    Returns:
        (richtung, fib_preise_dict, grund)
    """
    if len(kerzen) < 5:
        return ("nichts", None, "zu wenig Kerzen")

    # Letzte Bewegung aus N Kerzen
    closes = [k[4] for k in kerzen[-50:]]
    highs = [k[2] for k in kerzen[-50:]]
    lows = [k[3] for k in kerzen[-50:]]

    kurs = closes[-1]
    hoch = max(highs)
    tief = min(lows)

    spanne = hoch - tief
    if spanne <= 0 or spanne / tief < 0.005:
        return ("nichts", None,
                "Spanne %.2f%% zu klein (<0.5%%)" % (spanne / tief * 100))

    # Richtung bestimmen
    if richtung == "auto":
        # Trend aus SMA10/SMA50
        sma10 = sum(closes[-10:]) / min(len(closes), 10)
        sma50 = sum(closes[-50:]) / min(len(closes), 50)
        if sma10 > sma50 * 1.005:
            richtung = "long"
        elif sma10 < sma50 * 0.995:
            richtung = "short"
        else:
            return ("nichts", None, "Seitwaerts (kein Trend)")

    preise = fib_preise(hoch, tief)
    stand = retracement_stand(kurs, hoch, tief)

    if richtung == "long":
        # Markt steigt, Retracement von oben messen
        # stand=1 am Hoch, stand=0 am Tief
        if stand <= SCHWELLE_EINSTIEG:
            # Zurückgekommen unter 38.2% → Einstieg
            grund = "long: Retracement %.1f%% unter Einstiegs-Schwelle %.0f%%" % (
                stand * 100, SCHWELLE_EINSTIEG * 100)
            return ("long", preise, grund)
        elif stand <= 0.5:
            return ("beobachten", preise,
                    "long: Retracement %.1f%% (zwischen 38.2 und 50)" % (stand * 100))
        else:
            return ("nichts", preise,
                    "long: kaum retraced (%.1f%%), warten" % (stand * 100))
    else:
        # short: Markt faellt, Retracement nach oben messen
        # stand=0 am Tief, stand=1 am Hoch
        if stand >= 1 - SCHWELLE_EINSTIEG:
            grund = "short: Erholung %.1f%% ueber Einstiegs-Schwelle %.0f%%" % (
                (1 - stand) * 100, SCHWELLE_EINSTIEG * 100)
            return ("short", preise, grund)
        elif stand >= 0.5:
            return ("beobachten", preise,
                    "short: Erholung %.1f%% (zwischen 50 und 61.8)" % ((1 - stand) * 100))
        else:
            return ("nichts", preise,
                    "short: kaum erholt (%.1f%%), warten" % ((1 - stand) * 100))


# ─── Kommandozeile ─────────────────────────────────────────────────
def _einrichtung() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fibonacci-Retracement-Levels")
    p.add_argument("instrument", nargs="?", default="BTC-USDT-SWAP")
    p.add_argument("--vorschau", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def main() -> int:
    args = _einrichtung().parse_args()
    # Kerzen ueber scanner/okx holen
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scanner"))
    import okx  # noqa: E402

    kerzen = okx.kerzen(args.instrument, anzahl=100)
    if not kerzen:
        preise = {}
        stand = 0.5
        grund = "keine Kerzen"
    else:
        closes = [k[4] for k in kerzen]
        kurs = closes[-1]
        hoch = max(k[2] for k in kerzen)
        tief = min(k[3] for k in kerzen)
        preise = fib_preise(hoch, tief)
        stand = retracement_stand(kurs, hoch, tief) if preise else 0.5
        grund = ""

    if args.json:
        print(json.dumps({
            "instrument": args.instrument,
            "kurs": closes[-1] if kerzen else 0,
            "hoch": hoch if kerzen else 0,
            "tief": tief if kerzen else 0,
            "spanne_pct": (hoch - tief) / tief * 100 if (kerzen and tief > 0) else 0,
            "retracement_stand": stand,
            "fib_levels": preise,
        }, indent=1, default=str))
    elif args.vorschau:
        print("Fibonacci-Retracement: %s" % args.instrument)
        print("  Kurs: %.2f | Hoch: %.2f | Tief: %.2f | Spanne: %.2f%%" % (
            closes[-1] if kerzen else 0, hoch if kerzen else 0,
            tief if kerzen else 0,
            (hoch - tief) / tief * 100 if (kerzen and tief > 0) else 0))
        print("  Retracement-Stand: %.1f%%" % (stand * 100))
        if preise:
            print("  Fibonacci-Levels:")
            for anteil in sorted(FIB_LEVELS):
                p = preise.get(FIB_LEVELS[anteil], 0)
                mark = " <<<" if abs(stand - anteil) < 0.03 else ""
                print("    %5s: %12.2f%s" % (FIB_LEVELS[anteil], p, mark))
        richtung, _, _ = signal(kerzen)
        print("  Signal: %s" % richtung)
    return 0


if __name__ == "__main__":
    sys.exit(main())