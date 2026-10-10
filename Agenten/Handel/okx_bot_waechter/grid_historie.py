"""Geschlossene OKX-Contract-Grids auswerten - die zweite Haelfte des Waechter-Urteils.

`waechter.py`/`analyse.py` lesen nur laufende Bots. Genau die Bots, deren ERGEBNIS
man auswerten will, sind aber geschlossen und damit unsichtbar. Dieser Leser
holt sie: `GET /api/v5/tradingBot/grid/orders-algo-history?algoOrdType=contract_grid`.

Je Grid: Seite, Laufzeit, Netzgewinn, Richtungsgewinn, Stop vorhanden ja/nein,
Marktbewegung waehrend der Lebensdauer. Rein lesend, wie der uebrige Bericht.

Woher die Felder kommen (gemessen 08.10.2026 an der echten Antwort):

* `gridProfit`  = realisierter NETZgewinn (die abgeschlossenen Grid-Runden)
* `totalPnl`    = Gesamtergebnis; RICHTUNGSgewinn = totalPnl - gridProfit
                 (die offene Positionsbewegung plus Funding/Gebuehren)
* `slTriggerPx` = boersenseitiger Stop; leer = keiner gesetzt
* `cTime`/`uTime` = Lebensdauer
* Marktbewegung: erste gegen letzte Tageskerze im Lebensfenster des Grids

Aufruf (aus diesem Ordner):
    python grid_historie.py             # alle 63 geschlossenen Grids
    python grid_historie.py --kurz      # je Grid eine Zeile
    python grid_historie.py --zahl      # nur die Summen (fuer den Waechter-Bericht)
"""
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)
import bots  # noqa: E402


def jetzt():
    return datetime.now(timezone.utc)


def jz(ms):
    """OKX-Zeit (Millisekunden seit Epoche) als lesbarer Text."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).strftime("%d.%m. %H:%M")
    except (TypeError, ValueError):
        return "-"


def f(x, stellen=6):
    """Kurszahl ohne Exponentialschreibweise - 1e-05 liest niemand."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "-"
    if v == 0:
        return "0"
    if abs(v) >= 1000:
        return "%.2f" % v
    if abs(v) >= 1:
        return "%.4f" % v
    return ("%." + str(stellen) + "f") % v


def _z(ms):
    try:
        return int(ms)
    except (TypeError, ValueError):
        return None


def laufzeit_tage(g):
    """Lebensdauer in Tagen aus cTime/uTime; None, wenn eines fehlt."""
    a, b = _z(g.get("cTime")), _z(g.get("uTime"))
    if not a or not b:
        return None
    return (b - a) / (1000.0 * 86400.0)


def richtungsgewinn(g):
    """Richtungsgewinn = Gesamtergebnis - Netzgewinn (reine Funktion).

    Laden-oder-raten-Regel: `gridProfit` ist der realisierte Netzgewinn der
    abgeschlossenen Grid-Runden; `totalPnl` das Gesamtergebnis. Die Differenz
    ist die Positionsbewegung (plus Funding/Gebuehren). Fehlt eine der beiden
    Zahlen, ist das Ergebnis unbekannt - keine Null erfinden.
    """
    try:
        gesamt = float(g.get("totalPnl"))
        netz = float(g.get("gridProfit"))
    except (TypeError, ValueError):
        return None
    return gesamt - netz


def stop_vorhanden(g):
    """True, wenn ein boersenseitiger Stop gesetzt ist (slTriggerPx nicht leer)."""
    return bool((g.get("slTriggerPx") or "").strip())


def marktbewegung(g, kerzen):
    """Marktbewegung waehrend der Lebensdauer in Prozent.

    `kerzen` sind die Tageskerzen des Instruments (aufsteigend, [ts,o,h,l,c,v]).
    Genommen wird die erste Schlusskerze im Lebensfenster gegen die letzte
    Schlusskerze davor - ein Grid, das nur Stunden lief, hat mit Tageskerzen
    oft keine messbare Bewegung (None, kein Fehler).
    """
    a, b = _z(g.get("cTime")), _z(g.get("uTime"))
    if not a or not b or not kerzen:
        return None
    erster = letzter = None
    for k in kerzen:
        try:
            ts = int(k[0])
        except (TypeError, ValueError, IndexError):
            continue
        if ts < a:
            continue
        if ts > b:
            break
        if erster is None:
            erster = float(k[4])
        letzter = float(k[4])
    if erster is None or erster <= 0 or letzter is None:
        return None
    return (letzter / erster - 1.0) * 100.0


def auswerte(g, kerzen):
    """Eine Zeile fuer ein geschlossenes Grid - reine Funktion, ohne Netz testbar."""
    richtung = (g.get("direction") or "").lower()
    seite = {"long": "LONG", "short": "SHORT"}.get(richtung, richtung or "-")
    netz = g.get("gridProfit")
    gesamt = g.get("totalPnl")
    return {
        "algoId": str(g.get("algoId") or ""),
        "inst": g.get("instId"),
        "seite": seite,
        "laufzeit_tage": laufzeit_tage(g),
        "seit": jz(g.get("cTime")),
        "bis": jz(g.get("uTime")),
        "netzgewinn": float(netz) if netz not in (None, "") else None,
        "richtungsgewinn": richtungsgewinn(g),
        "gesamt": float(gesamt) if gesamt not in (None, "") else None,
        "stop": stop_vorhanden(g),
        "markt_pct": marktbewegung(g, kerzen),
        "invest": float(g.get("investment") or 0),
        "hebel": g.get("actualLever") or g.get("lever") or "-",
        "arbitrage": g.get("arbitrageNum"),
        "grid_num": g.get("gridNum"),
    }


# --- Lesen -----------------------------------------------------------------

def geschlossene():
    """Alle geschlossenen Contract-Grids (Historie-Endpunkt)."""
    return bots.hole("/api/v5/tradingBot/grid/orders-algo-history?algoOrdType=%s"
                     % bots.GRID) or []


def zeilen(alle=None):
    """Alle Zeilen; Kerzen je Instrument werden EINMAL geholt (Cache)."""
    alle = geschlossene() if alle is None else alle
    cache = {}
    raus = []
    for g in alle:
        inst = g.get("instId") or ""
        if inst and inst not in cache:
            try:
                cache[inst] = bots.kerzen(inst, "1D", 400) or []
            except Exception:
                cache[inst] = []
        raus.append(auswerte(g, cache.get(inst, [])))
    return raus


# --- Bericht ---------------------------------------------------------------

def summen(z):
    """Netz-, Richtungs- und Gesamtergebnis ueber alle Grids (nur belegte Werte)."""
    netz = sum(x["netzgewinn"] for x in z if x.get("netzgewinn") is not None)
    richtung = sum(x["richtungsgewinn"] for x in z if x.get("richtungsgewinn") is not None)
    gesamt = sum(x["gesamt"] for x in z if x.get("gesamt") is not None)
    invest = sum(x.get("invest") or 0 for x in z)
    ohne_stop = sum(1 for x in z if not x["stop"])
    n = len(z)
    return {"n": n, "netz": netz, "richtung": richtung, "gesamt": gesamt,
            "invest": invest, "ohne_stop": ohne_stop}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    kurz = "--kurz" in argv
    nur_zahl = "--zahl" in argv

    try:
        alle = zeilen()
    except Exception as e:
        print("FEHLER: %s: %s" % (type(e).__name__, str(e)[:200]))
        return 1
    if not alle:
        print("Keine geschlossenen Contract-Grids in der Historie.")
        return 0

    z = summen(alle)
    print("Geschlossene Contract-Grids  %s  (%d Stueck, Host %s)" % (
        jetzt().strftime("%d.%m.%Y %H:%M UTC"), z["n"], bots.host()))
    for x in alle:
        teile = [
            "%s %s" % (x["seite"], x["inst"] or "?"),
            "%.2f T" % x["laufzeit_tage"] if x.get("laufzeit_tage") is not None else "Laufzeit -",
            "Netz %+.2f" % (x["netzgewinn"] if x.get("netzgewinn") is not None else 0),
            "Richt %+.2f" % (x["richtungsgewinn"] if x.get("richtungsgewinn") is not None else 0),
            "Ges %+.2f" % (x["gesamt"] if x.get("gesamt") is not None else 0),
            "Markt %+s%%" % (f(x["markt_pct"], 1) if x.get("markt_pct") is not None else "-"),
        ]
        if not x["stop"]:
            teile.append("OHNE STOP")
        if not kurz:
            teile.append("algo %s" % x["algoId"])
        print(" | ".join(teile))
    print("-" * 70)
    print("SUMME Netz %+.2f | Richtung %+.2f | Gesamt %+.2f | Einsatz %.2f | %d ohne Stop"
          % (z["netz"], z["richtung"], z["gesamt"], z["invest"], z["ohne_stop"]))
    if nur_zahl:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
