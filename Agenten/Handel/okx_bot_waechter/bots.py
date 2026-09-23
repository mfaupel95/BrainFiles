"""Zugang zu den ECHTEN OKX-Bots (Future DCA, Future Grid) - lesend, plus zwei Tore.

Woher die Zahlen kommen (alles gemessen am 23.09.2026, nicht aus der Doku geraten):

* `GET /api/v5/tradingBot/dca/ongoing-list?algoOrdType=contract_dca`
  -> je Bot: algoId, instId, direction, lever, investmentAmt/investmentCcy,
     initOrdAmt, safetyOrdAmt, maxSafetyOrds, pxSteps, pxStepsMult, volMult,
     pnlRatio, totalPnl, state.
* `GET /api/v5/tradingBot/dca/position-details?algoId=&algoOrdType=contract_dca`
  -> avgPx, initPx, liqPx, sz, notionalUsd, upl, tpPx, slPx (leer = KEIN Stop),
     fillSafetyOrds (wie viele Sicherungskaeufe schon gefuellt sind).
* `GET /api/v5/tradingBot/dca/cycle-list?algoId=&algoOrdType=contract_dca`
  -> cycleId je Zyklus (die Orderliste BRAUCHT sie: ohne cycleId antwortet OKX
     mit `51000 Parameter cycleId error`).
* `GET /api/v5/tradingBot/dca/orders?algoId=&algoOrdType=contract_dca&cycleId=`
  -> die einzelnen Auftraege eines Zyklus mit `px` - daraus faellt die TIEFSTE
     Kaufstufe heraus, und die ist die "letzte kaufbare Grenze".
* `GET /api/v5/tradingBot/grid/orders-algo-pending?algoOrdType=contract_grid`
  -> gridNum, maxPx, minPx, direction, lever, investment, pnlRatio, state.
* `GET /api/v5/tradingBot/grid/orders-algo-details?algoId=&algoOrdType=contract_grid`
  -> dieselben Felder plus liqPx, slTriggerPx, tpTriggerPx.
* `GET /api/v5/market/ticker?instId=` -> last.

FALLE 1: `scanner/okx._roh()` schickt sein `body` als REQUEST-BODY (fuer POST).
Bei GET gehoeren die Parameter in den PFAD - und der Pfad MIT Query wird
signiert. Ein Parameter im body eines GET kommt nie an: OKX antwortet dann
"Parameter algoOrdType can not be empty", obwohl er uebergeben aussah.

FALLE 2: Der Schluessel muss zum HOST passen. okx._live_basis() liest OKX_BASE
mit Registry-Rueckfall; ein EEA-Schluessel am globalen Host ergibt 50119
("API key doesn't exist"), obwohl der Schluessel lebt.

Die beiden Schreibwege (`stop`, `anlegen`) sind hier NUR als Funktionen
vorhanden - sie werden von waechter.py/bauen.py ausschliesslich hinter den
Toren aus wachen.json aufgerufen. bots.py selbst fragt kein Tor ab.
"""
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
SCANNER = os.path.join(HANDEL, "scanner")

if SCANNER not in sys.path:
    sys.path.insert(0, SCANNER)
import okx  # noqa: E402

assert okx.__file__.startswith(SCANNER), okx.__file__

DCA = "contract_dca"
GRID = "contract_grid"


# --- Transport --------------------------------------------------------------

def hole(pfad):
    """Signierter GET. Parameter gehoeren in den Pfad (siehe FALLE 1)."""
    return okx._roh(pfad, "GET", None, signiert=True)


def sende(pfad, body):
    """Signierter POST."""
    return okx._roh(pfad, "POST", body, signiert=True)


def host():
    return okx._live_basis()


def schluessel_da():
    return okx.schluessel_vorhanden()


# --- Lesen: Bots ------------------------------------------------------------

def dca_laufend():
    return hole("/api/v5/tradingBot/dca/ongoing-list?algoOrdType=%s" % DCA) or []


def grid_laufend():
    return hole("/api/v5/tradingBot/grid/orders-algo-pending?algoOrdType=%s" % GRID) or []


def spot_dca_laufend():
    return hole("/api/v5/tradingBot/dca/ongoing-list?algoOrdType=spot_dca") or []


def dca_details(algo):
    d = hole("/api/v5/tradingBot/dca/position-details?algoId=%s&algoOrdType=%s"
             % (algo, DCA))
    return (d or [{}])[0]


def dca_zyklen(algo):
    return hole("/api/v5/tradingBot/dca/cycle-list?algoId=%s&algoOrdType=%s"
                % (algo, DCA)) or []


def dca_orders(algo, cycle_id):
    return hole("/api/v5/tradingBot/dca/orders?algoId=%s&algoOrdType=%s&cycleId=%s"
                % (algo, DCA, cycle_id)) or []


def grid_details(algo):
    d = hole("/api/v5/tradingBot/grid/orders-algo-details?algoId=%s&algoOrdType=%s"
             % (algo, GRID))
    return (d or [{}])[0]


def kurs(inst):
    t = hole("/api/v5/market/ticker?instId=%s" % inst)
    return float(t[0]["last"]) if t else None


def kerzen(inst, bar="1D", anzahl=365):
    """Tageskerzen des Instruments, aufsteigend ([ts, o, h, l, c, vol]).

    Die XPERP-Instrumente haben nur ihre eigene Lebensdauer an Historie - ein
    Bot auf einem 310718-Kontrakt sieht also weniger als 365 Tage. Was fehlt,
    fehlt ehrlich (die Auswertung nennt die Zahl der Kerzen mit).
    """
    return okx.kerzen(inst, bar, anzahl)


# --- Rechnen (reine Funktionen, ohne Netz testbar) ---------------------------

def kaufstufen(orders):
    """Die Kaufpreise eines DCA-Zyklus, aufsteigend - die TIEFSTE ist die Grenze.

    Ausgeschlossen werden Verkaufsauftraege (die Zielorder hat side='sell'):
    der Zielkurs ist keine Kaufstufe. Auftraege ohne Preis fallen weg.
    """
    raus = []
    for o in orders or []:
        if (o.get("side") or "").lower() == "sell":
            continue
        try:
            px = float(o.get("px") or 0)
        except (TypeError, ValueError):
            continue
        if px > 0:
            raus.append(px)
    return sorted(raus)


def stufen_plan(init_px, px_steps, px_steps_mult, max_safety):
    """Die geplanten Kaufstufen aus dem Bot-Plan, OHNE Orderabruf.

    Stufe k (1..n) liegt bei init * (1 - pxSteps * sum(mult^(i-1), i=1..k)).
    Gegenprobe am echten Bot (UNI 23.09.2026): initPx 10.4408, pxSteps 0.0072,
    mult 1, n 11 -> 9.6138, und genau dieser Preis stand als tiefste Order
    (9.613) in der Auftragsliste.
    """
    try:
        init = float(init_px)
        schritt = float(px_steps)
        mult = float(px_steps_mult or 1) or 1.0
        n = int(max_safety)
    except (TypeError, ValueError):
        return []
    if init <= 0 or n <= 0 or schritt <= 0:
        return []
    raus, faktor_summe = [], 0.0
    for k in range(1, n + 1):
        faktor_summe += schritt * (mult ** (k - 1))
        preis = init * (1.0 - faktor_summe)
        if preis > 0:
            raus.append(preis)
    return raus


def letzte_kaufgrenze(orders, plan_stufen):
    """Die tiefste belegte Kaufstufe; sonst die tiefste geplante Stufe.

    Die belegte Stufe ist die Messung (sie kommt von der Boerse), der Plan die
    Auskunft darueber, was der Bot ueberhaupt noch kaufen WIRD. Beide werden
    zurueckgegeben, damit der Bericht sie vergleichen kann.
    """
    stufen = kaufstufen(orders)
    belegt = stufen[0] if stufen else None
    geplant = min(plan_stufen) if plan_stufen else None
    if belegt is not None and geplant is not None:
        # Der tiefere von beiden ist die harte Grenze: liegt die belegte Stufe
        # unter dem Plan, hat der Bot den Plan schon ausgereizt.
        return min(belegt, geplant), belegt, geplant
    return (belegt if belegt is not None else geplant), belegt, geplant


def liq_abstand(kurs, liq_px):
    """Prozent zwischen Kurs und Liquidationspreis (positiv = Luft)."""
    try:
        k, l = float(kurs), float(liq_px)
    except (TypeError, ValueError):
        return None
    if k <= 0 or l <= 0:
        return None
    return abs(k - l) / k * 100.0


def munition(max_safety, gefuellt):
    """Wie viele Sicherungskaeufe noch moeglich sind."""
    try:
        return max(0, int(max_safety) - int(gefuellt or 0))
    except (TypeError, ValueError):
        return None


# --- Schreiben (nur hinter den Toren) ---------------------------------------

def dca_stoppen(algo, stop_art="1"):
    """1 = Positionen am Markt schliessen, 2 = Positionen behalten."""
    return sende("/api/v5/tradingBot/dca/stop",
                 {"algoId": str(algo), "algoOrdType": DCA, "stopType": str(stop_art)})


def grid_stoppen(algo, inst, stop_art="1"):
    """Der Rumpf ist eine LISTE, nicht ein Objekt."""
    return sende("/api/v5/tradingBot/grid/stop-order-algo",
                 [{"algoId": str(algo), "instId": inst,
                   "algoOrdType": GRID, "stopType": str(stop_art)}])


def dca_anlegen(body):
    return sende("/api/v5/tradingBot/dca/create", body)


def grid_anlegen(body):
    return sende("/api/v5/tradingBot/grid/order-algo", body)


# --- Vorschlagsdaten --------------------------------------------------------

def grid_ai_param(inst, richtung="long", dauer="14D"):
    d = hole("/api/v5/tradingBot/grid/ai-param?instId=%s&algoOrdType=%s"
             "&direction=%s&duration=%s" % (inst, GRID, richtung, dauer))
    return (d or [{}])[0]


def grid_anzahl(inst, min_px, max_px, lever, richtung="long"):
    d = hole("/api/v5/tradingBot/grid/grid-quantity?instId=%s&algoOrdType=%s"
             "&maxPx=%s&minPx=%s&lever=%s&direction=%s&runType=1"
             % (inst, GRID, max_px, min_px, lever, richtung))
    return (d or [{}])[0]


if __name__ == "__main__":
    print("Host:", host(), "| Schluessel:", schluessel_da())
    print(json.dumps(dca_laufend(), ensure_ascii=False)[:400])