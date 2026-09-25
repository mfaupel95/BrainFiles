"""Schutz-Stop auf die POSITION einer laufenden OKX-Future-DCA setzen (25.09.2026).

WARUM NICHT DER BOT-STOP: `POST /api/v5/tradingBot/dca/amend-order-algo` heisst in
der OKX-Doku woertlich "Amend **spot** dca basic param" - fuer eine CONTRACT-DCA
(unsere Bots, `algoOrdType: contract_dca`) gibt es keinen Amend. Genau daher kam
`OKX 51291: The bot doesn't exist or has already stopped`: OKX sucht eine SPOT-DCA
mit dieser Kennung und findet keine. Der slPct einer laufenden Contract-DCA ist
also nicht setzbar (die Notiz vom 23.09.2026 stimmt, jetzt mit Grund).

Deshalb: ein bedingter Stop auf die POSITION (`/api/v5/trade/order-algo`,
reduceOnly) - dieselbe Mechanik wie scanner/xperp. Er stoert den Bot nicht:
er liegt UNTER der tiefsten Kaufstufe, die Leiter ist dann voll gefuellt und der
Bot kauft nicht mehr nach.

    python positions_schutz.py                 # Bericht, sendet nichts
    python positions_schutz.py --anwenden      # setzen
    python positions_schutz.py --nur <algoId> --anwenden
"""
import argparse
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.join(HIER, os.pardir, "scanner"))

import bots  # noqa: E402
import okx   # noqa: E402

PUFFER = 0.05          # 5 % unter die tiefste Kaufstufe
NOTFALL = 0.015        # Leiter ausgelaufen: 1,5 % unter den Kurs
ZUR_LIQ = 1.02         # mindestens 2 % ueber der Liquidation


def vorschlag(kurs, boden, liq):
    stop = (boden or kurs) * (1 - PUFFER)
    hinweis = []
    if stop >= kurs:
        stop = kurs * (1 - NOTFALL)
        hinweis.append("Leiter ausgelaufen - Reissleine 1,5 %% unter dem Kurs")
    if liq and stop <= liq * ZUR_LIQ:
        stop = liq * ZUR_LIQ
        hinweis.append("auf 2 %% ueber die Liquidation gezogen")
    if stop >= kurs:
        hinweis.append("ACHTUNG: Stop nicht unter dem Kurs - loest sofort aus")
    return round(stop, 10), hinweis


def position(inst):
    """Die offene Position zum Bot-Instrument.

    ACHTUNG: der BOT traegt eine Lieferkennung im Namen
    (`LTC-USD_UM_XPERP-310404`), die POSITION nicht (`LTC-USD_UM_XPERP`).
    Wer mit dem Bot-Namen sucht, findet nie eine Position.
    """
    d = okx._roh("/api/v5/account/positions?instType=FUTURES", "GET", None,
                 signiert=True)
    for p in d or []:
        kandidat = p.get("instId") or ""
        if float(p.get("pos") or 0) == 0:
            continue
        if kandidat == inst or inst.startswith(kandidat):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur", default=None)
    ap.add_argument("--anwenden", action="store_true")
    a = ap.parse_args()
    gesetzt = 0
    for bot in bots.dca_laufend():
        algo = str(bot.get("algoId"))
        if a.nur and algo != a.nur:
            continue
        inst = bot.get("instId")
        d = bots.dca_details(algo)
        kurs = bots.kurs(inst)
        plan = bots.stufen_plan(d.get("initPx"), bot.get("pxSteps"),
                                bot.get("pxStepsMult"), bot.get("maxSafetyOrds"))
        zyklen = bots.dca_zyklen(algo)
        cid = ""
        for z in zyklen:
            if z.get("currentCycle"):
                cid = z.get("cycleId") or ""
                break
        if not cid and zyklen:
            cid = zyklen[-1].get("cycleId") or ""
        grenze, _, _ = bots.letzte_kaufgrenze(
            bots.dca_orders(algo, cid) if cid else [], plan)
        liq = float(d.get("liqPx") or 0) or None
        stop, hinweis = vorschlag(kurs, grenze, liq)
        pos = position(inst)
        if not pos:
            print("%-22s %-6s keine offene Position - uebersprungen" % (inst, algo[-6:]))
            continue
        menge = abs(float(pos.get("pos") or 0))
        seite = "sell" if float(pos.get("pos") or 0) > 0 else "buy"
        ps = pos.get("posSide") or "net"
        koerper = {"instId": inst, "tdMode": (pos.get("mgnMode") or "isolated"),
                   "side": seite, "ordType": "conditional", "sz": ("%g" % menge),
                   "slTriggerPx": ("%g" % stop), "slOrdPx": "-1",
                   "reduceOnly": True}
        if ps not in ("net", "", None):
            koerper["posSide"] = ps
        print("%-22s %-6s Kurs %-10.6g Boden %-10.6g Liq %-10s -> Stop %-10.6g "
              "(%g Kontrakte) %s" % (inst, algo[-6:], kurs, grenze or 0, liq, stop,
                                     menge, "; ".join(hinweis)))
        if not a.anwenden:
            print("      Koerper: %s" % json.dumps(koerper, ensure_ascii=False))
            continue
        try:
            antwort = okx._roh("/api/v5/trade/order-algo", "POST", koerper,
                               signiert=True)
            print("      gesetzt: %s" % json.dumps(antwort, ensure_ascii=False)[:160])
            gesetzt += 1
        except Exception as e:                                  # noqa: BLE001
            print("      FEHLER: %s" % str(e)[:180])
    print("\n%d Stop(s) gesetzt." % gesetzt)


if __name__ == "__main__":
    sys.exit(main())