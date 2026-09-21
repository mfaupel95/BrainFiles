#!/usr/bin/env python3
"""Zeigt, woran mosaics Einstieg gerade haengt - rein lesend.

WARUM: `handeln.py --vorschau` nennt bei mosaic nur die Sperren des Live-Wegs,
nicht den Kandidatenstand. Wenn die Spur live ist und keine Order kommt, sieht
das aus wie "tut nichts" - in Wahrheit wartet sie auf drei Bedingungen:

  1. 4H-Bias:   die letzte 4H-Kerze muss gruen sein (Long-Top-Down),
  2. 30M-Zone:  der Kurs muss eine Nachfragezone beruehren (Swing-Tiefs der
                letzten Kerzen, mit Puffer),
  3. 5M-Shift:  ein Structure-Shift nach oben (Schluss ueber dem letzten
                relevanten Swing-Hoch).

Dieses Werkzeug rechnet genau diese drei Schichten je Instrument und sagt, an
welcher es scheitert - mit Abstand in Prozent, damit "wie weit weg" messbar ist.

Es schreibt NICHTS (kein Journal, kein Zustand; pruefe_einstieg wird bewusst
nicht gerufen - das bucht). Aufruf aus dem mosaic-Ordner:

    python tor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import handeln as h                                              # noqa: E402

ANZAHL_4H = 60
ANZAHL_30M = 120
ANZAHL_5M = 120


def schichtstand(inst, w):
    """Die drei Schichten eines Instruments - ohne zu buchen."""
    k4 = h.lade_kerzen(inst, "4H", ANZAHL_4H)
    k30 = h.lade_kerzen(inst, "30m", ANZAHL_30M)
    k5 = h.lade_kerzen(inst, "5m", ANZAHL_5M)
    if not k4 or not k30 or not k5:
        return {"inst": inst, "fehler": "keine Kerzen"}

    kurs = h._schluss(k5, -1)
    bias = h.bias_4h(k4, w)
    zone = h.nachfrage_zone(k30, w)
    beruehrt = h.zone_beruehrt(k30, w, zone) if zone else False
    # Dasselbe Fenster wie structure_shift (struktur_shift_kerzen_5m, Standard
    # 30) und ohne die letzte Kerze - sonst zeigt das Werkzeug ein anderes
    # Swing-Hoch an, als das Tor prueft.
    fenster = int(w.get("struktur_shift_kerzen_5m", 30))
    hoch = h.letztes_relevantes_swing_hoch(k5[:-1], fenster)
    shift = h.structure_shift(k5, w)
    sig = h.signal(k4, k30, k5, w)
    return {"inst": inst, "kurs": kurs, "bias": bool(bias), "zone": zone,
            "beruehrt": bool(beruehrt), "swing_hoch": hoch, "shift": bool(shift),
            "signal": bool(sig), "k4": k4[-1], "k30": k30[-1], "k5": k5[-1]}


def main() -> int:
    w = h.lade_wachen()
    print("mosaic-Tor  (Instrumente: %s)" % ", ".join(w.get("instrumente", [])))
    print("Schwellen (wachen.json): Schwung-Kerzen 30M=%s | Beruehrungs-Kerzen "
          "30M=%s | Shift-Kerzen 5M=%s | Mindest-Trendkerzen 4H=%s"
          % (w.get("zone_schwung_kerzen_30m"), w.get("zone_beruehrung_kerzen_30m"),
             w.get("struktur_shift_kerzen_5m"), w.get("trend_min_kerzen_4h")))
    print()
    offen = []
    for inst in w.get("instrumente", []):
        s = schichtstand(inst, w)
        if s.get("fehler"):
            print("%-10s %s" % (inst, s["fehler"]))
            continue
        zone = s["zone"]
        print("%-10s Kurs %10.4f" % (inst, s["kurs"]))
        print("   1) 4H-Bias %s" % ("ERFUELLT (letzte Kerze gruen)" if s["bias"]
                                    else "offen - letzte 4H-Kerze ist rot"))
        if zone:
            oben, unten = max(zone), min(zone)
            abstand = (s["kurs"] / oben - 1) * 100 if s["kurs"] > oben else \
                      (s["kurs"] / unten - 1) * 100
            print("   2) 30M-Zone %s  [%.4f .. %.4f]  Abstand %+.2f%%"
                  % ("BERUEHRT" if s["beruehrt"] else "wartet", unten, oben, abstand))
        else:
            print("   2) 30M-Zone: keine Nachfragezone gefunden")
        if s["swing_hoch"]:
            print("   3) 5M-Shift %s  (Swing-Hoch %.4f, Kurs %+.2f%% davon)"
                  % ("ERFUELLT" if s["shift"] else "offen", s["swing_hoch"],
                     (s["kurs"] / s["swing_hoch"] - 1) * 100))
        else:
            print("   3) 5M-Shift: kein relevantes Swing-Hoch")
        print("   -> %s" % ("SIGNAL - die Spur kauft beim naechsten Zyklus"
                            if s["signal"] else "kein Einstieg"))
        print()
        if not s["signal"]:
            fehlt = [n for n, ok in (("Bias", s["bias"]), ("Zone", s["beruehrt"]),
                                     ("Shift", s["shift"])) if not ok]
            offen.append((inst, ", ".join(fehlt) or "Signal-Auswertung"))
    if offen:
        print("Es fehlt: " + " | ".join("%s: %s" % (i, f) for i, f in offen))
    else:
        print("Alle Instrumente stehen im Signal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
