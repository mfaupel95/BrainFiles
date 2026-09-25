"""Einem LAUFENDEN OKX-Grid einen Schutz-Stop setzen (T-077, 25.09.2026).

Warum ein eigenes Werkzeug: `anpassen.py` kann nur DCA-Bots
(`/dca/amend-order-algo` mit slPct). Ein Grid kennt kein `slPct` - es kennt
`slTriggerPx`, eine PREIS-Schwelle, und einen anderen Endpunkt
(`/grid/amend-order-algo`, am 25.09.2026 mit einer erfundenen algoId bewiesen:
`OKX 51291` = Endpunkt da, Signatur und Host richtig).

Die Zahl wird GERECHNET, nicht geraten (Hausregel: Abstand in ATR-Einheiten):

    Kandidat   = Kurs - 1,5 x ATR(14, Tageskerzen)
    Obergrenze = 0,99 x Bandboden (minPx)   - ein Stop IM Band wuerde das
                                              Gitter bei normalem Lauf toeten
    Untergrenze = 1,15 x Liquidation        - ein Stop nahe der Liquidation
                                              schuetzt nichts mehr

Der Stop ist Katastrophenschutz, kein Rauschfilter: bei einem Instrument, das
8,6 % am Tag laeuft (ZEC, gemessen 25.09.2026), waere der Bandboden (0,5 ATR
entfernt) in Tagen erreicht, ohne dass etwas kaputt ist.

Aufruf:
    python grid_schutz.py                  # Bericht je laufendem Grid, aendert nichts
    python grid_schutz.py --preis 1350 --anwenden     # setzen (braucht --anwenden)
    python grid_schutz.py --nur <algoId>
"""
import argparse
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import bots  # noqa: E402

assert bots.__file__.startswith(HIER), bots.__file__

ATR_VIELFACHES = 1.5
RAND_UNTEN = 0.99      # unter dem Bandboden
ABSTAND_ZUR_LIQ = 1.15  # mindestens 15 % ueber der Liquidation


def atr(inst, tage=14):
    """ATR aus Tageskerzen - reine Standardbibliothek, keine Indikatordatei."""
    kerzen = bots.kerzen(inst, "1D", tage + 10) or []
    if len(kerzen) < tage + 2:
        return None
    hoch = [float(k[2]) for k in kerzen]
    tief = [float(k[3]) for k in kerzen]
    schluss = [float(k[4]) for k in kerzen]
    tr = [max(hoch[i] - tief[i], abs(hoch[i] - schluss[i - 1]),
              abs(tief[i] - schluss[i - 1])) for i in range(1, len(kerzen))]
    if len(tr) < tage:
        return None
    return sum(tr[-tage:]) / tage


def vorschlag(inst, kurs, atr_wert, min_px, liq_px):
    """(preis, begruendung, warnung) - immer unter dem Band, immer ueber der Liq."""
    if not atr_wert:
        return None, "kein ATR (zu wenig Kerzen)", "ohne ATR wird nichts gesetzt"
    kandidat = kurs - ATR_VIELFACHES * atr_wert
    obergrenze = min_px * RAND_UNTEN
    untergrenze = (liq_px or 0) * ABSTAND_ZUR_LIQ
    warnung = None
    preis = min(kandidat, obergrenze)
    if untergrenze and preis < untergrenze:
        warnung = ("1,5 ATR (%s) liegt unter dem Schutzrand %s = 1,15 x Liquidation "
                   "- Stop auf den Rand gezogen" % (round(kandidat, 2), round(untergrenze, 2)))
        preis = untergrenze
    grund = ("Kurs %s - 1,5 x ATR %s = %s, gedeckelt auf %s (0,99 x Bandboden %s), "
             "Rand zur Liquidation %s" % (round(kurs, 2), round(atr_wert, 2),
                                          round(kandidat, 2), round(obergrenze, 2),
                                          min_px, round(untergrenze, 2)))
    return round(preis, 1), grund, warnung


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur", default=None, help="nur diese algoId")
    ap.add_argument("--preis", type=float, default=None,
                    help="fester Triggerpreis statt der Rechnung")
    ap.add_argument("--anwenden", action="store_true", help="wirklich senden")
    a = ap.parse_args()

    laufend = bots.grid_laufend()
    if not laufend:
        print("kein laufendes Grid")
        return 0
    geaendert = 0
    for algo in laufend:
        algo_id = str(algo.get("algoId"))
        if a.nur and algo_id != a.nur:
            continue
        d = bots.grid_details(algo_id)
        inst = d.get("instId")
        if d.get("state") != "running":
            print("%s: nicht running (%s) - uebersprungen" % (algo_id, d.get("state")))
            continue
        kurs = bots.kurs(inst)
        min_px = float(d.get("minPx") or 0)
        liq = float(d.get("liqPx") or 0)
        wert = atr(inst)
        preis, grund, warnung = vorschlag(inst, kurs, wert, min_px, liq)
        alt = d.get("slTriggerPx") or "(leer)"
        print("\n%s  %s  %s" % (algo_id, inst, d.get("direction")))
        print("  jetzt: slTriggerPx=%s | Band %s-%s | Liq %s | Einsatz %s"
              % (alt, d.get("minPx"), d.get("maxPx"), d.get("liqPx"), d.get("investment")))
        if a.preis:
            preis, grund = a.preis, "fester Preis von Hand (%s)" % a.preis
        print("  soll : slTriggerPx=%s" % preis)
        print("        %s" % grund)
        if warnung:
            print("  WARNUNG: %s" % warnung)
        if not a.anwenden:
            print("        (Trockenlauf - nichts gesendet)")
            continue
        antwort = bots.sende("/api/v5/tradingBot/grid/amend-order-algo",
                             {"algoId": algo_id, "instId": inst,
                              "slTriggerPx": str(preis), "slOrdPx": "-1"})
        print("        gesendet: %s" % json.dumps(antwort, ensure_ascii=False)[:200])
        nach = bots.grid_details(algo_id)
        print("        Gegenprobe: slTriggerPx=%s / slOrdPx=%s"
              % (nach.get("slTriggerPx"), nach.get("slOrdPx")))
        geaendert += 1
    print("\n%s Grid(s) angefasst." % geaendert)
    return 0


if __name__ == "__main__":
    sys.exit(main())