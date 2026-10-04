#!/usr/bin/env python3
"""Take-Profit in Stufen und Schutz-Stop fuer EINE OKX-Position.

REIN LESEND im Trockenlauf (Vorgabe). Erst `--anwenden` schreibt.

Warum als Werkzeug und nicht als drei Aufrufe: eine gestufte TP ist eine
MENGENRECHNUNG. Bei 1368 Stuecken und drei Stufen muss die Summe der
Teilmengen EXAKT die Position sein - ein Rest von 0,0001 Stuecken ist eine
Order, die OKX ablehnt, und ein Rest von 12 Stuecken ist eine Position ohne
Schutz, weil der Stop nur auf den Rest zeigt. Genau dieser Fall ist am
04.10.2026 live messbar: HYPE hat 34 Stuecke Position und einen Stop ueber
22.

ZWEI TORE (Hausregel okx-bots-bewachen):
  Tor 1  in diesem Skript: kein `--anwenden`, kein Schreiben
  Tor 2  die Menge wird gegen die BOERSE geprueft, nie gegen das Hausbuch -
         das BuchMON kannte keinen Stop, die Boerse auch nicht (es trug
         `fremdposition_uebernommen` und war damit eine Behauptung)

EIGENER ORDERWEG statt `okx.stop_setzen`: das ist fest auf `tdMode: cash`
und `side: sell` verdrahtet (Scanner-Spot-Benutzung). Eine XPERP-Position
ist `tdMode: cross|isolated`, und die Seite folgt der Position. Ein
`tdMode: cash` auf einem Perpetual wird abgelehnt - und ein stillschweigend
falsch gesetzter Schutz ist schlimmer als keiner.

MERKSATZ zur Reihenfolge: der Stop wird VOR den TP-Stufen gesetzt. Eine
TP-Stufe ohne Stop ist eine Position, die beim naechsten Neustart des
Algo-Bestands nackt dasteht.

ZU DEN STUFEN: gleichverteilt zwischen Einstand und Ziel, jede genau
1/n der Menge. Eine risikogewichtete Staffelung (frueher Stufen naeher am
Einstieg) loest bei einem 0,03-USD-Instrument nichts, weil die Gebuehr
0,05 % je Seite den ersten Abstand frisst.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HIER, "scanner")


def lade(name):
    p = os.path.join(SCANNER, name + ".py")
    spec = importlib.util.spec_from_file_location("okxtp_" + name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


okx = lade("okx")


def zahl(v, default=0.0):
    if v in (None, "", "-"):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def position(inst):
    """Die Position aus der BOERSE."""
    roh = okx._roh("/api/v5/account/positions?instType=FUTURES", signiert=True)
    for p in roh or []:
        if p.get("instId") == inst:
            return p
    return None


def bestaetigte(inst):
    """Alle Algo-Posten dieser Position, lesend. `ordType=conditional`
    liefert Stop- UND Ziel-Orders; die TP-Orders liegen je nach Setzung in
    `oco`, deshalb werden beide Endpunkte gelesen und zusammengefuehrt."""
    r = okx._roh("/api/v5/trade/orders-algo-pending?ordType=conditional",
                 signiert=True)
    for o in r or []:
        if o.get("instId") == inst:
            yield {
                "algoId": o.get("algoId"), "side": o.get("side"),
                "sz": zahl(o.get("sz")),
                "slTriggerPx": zahl(o.get("slTriggerPx"), None),
                "tpTriggerPx": zahl(o.get("tpTriggerPx"), None),
                "state": o.get("state"), "art": "conditional",
            }
    r2 = okx._roh("/api/v5/trade/orders-algo-pending?ordType=oco", signiert=True)
    for o in r2 or []:
        if o.get("instId") == inst:
            yield {
                "algoId": o.get("algoId"), "side": o.get("side"),
                "sz": zahl(o.get("sz")),
                "slTriggerPx": zahl(o.get("slTriggerPx"), None),
                "tpTriggerPx": zahl(o.get("tpTriggerPx"), None),
                "state": o.get("state"), "art": "oco",
            }


def stufen(einstieg, ziel_pct, anzahl):
    """N Trigger zwischen Einstand und Ziel, gleichverteilt.

    ZURUECK als FLOAT, nicht als String. Als `%.10g` formatiert liess sich die
    Zahl im Bericht gut an, kam aber im naechsten Aufruf als `str` an und
    liess `preis * m` mit `TypeError: must be real number, not str` abbrechen
    (gemessen 04.10.2026). Die Formatierung gehoert in die Ausgabe, nicht in
    die Rechnung - `algo_setzen` formatiert ohnehin selbst mit `str(preis)`."""
    if einstieg <= 0 or ziel_pct <= 0 or anzahl < 1:
        return []
    return [einstieg * (1 + ziel_pct * i / anzahl / 100.0)
            for i in range(1, anzahl + 1)]


def aufteilen(menge, teile=3):
    """Ganzzahlige Aufteilung, die SUMMIERT genau die Position ergibt.

    Der Rest wandert auf die FRUEHEN Stufen, nicht auf die letzte: ein Rest auf
    der letzten hiesse, dass die Restmenge bis zum letzten TP ungeschuetzt
    bleibt."""
    menge = int(round(menge))
    if menge < teile:
        return None
    basis, rest = divmod(menge, teile)
    out = [basis + (1 if i < rest else 0) for i in range(teile)]
    assert sum(out) == menge, "Aufteilung geht nicht auf: %s != %d" % (out, menge)
    return out


def oco_setzen(inst, td_mode, side, menge, stop, ziel):
    """Ein OCO: Stop UND Ziel an einem Order.

    Warum OCO und nicht zwei bedingte Orders: bei zwei getrennten Orders kann
    das Ziel feuern und die Position teilweise schliessen, waehrend der Stop
    auf die ALT-Menge zeigt und beim naechsten Nachkauf eine fremde Position
    mitverkauft. Genau das ist am 04.10.2026 messbar: HYPE trug einen
    22er- und einen 12er-Stop nebeneinander (34 Stuecke Position, beide
    Schutz - aber keiner mehr passend), QUANT zwei 181er/174er-Stops fuer
    333 Stuecke (355 geschuetzt = 107 %).

    OKX `POST /api/v5/trade/order-algo` mit `ordType: oco` verlangt BEIDE
    Preise in EINEM Koerper; `slOrdPx: -1` und `tpOrdPx: -1` bedeuten
    Marktausloesung (bei einem Momentum-Ausbruch verpasst ein Limitpreis
    genau den Move, der ihn ausgeloest hat)."""
    body = {"instId": inst, "tdMode": td_mode, "side": side,
            "ordType": "oco", "sz": str(int(menge)),
            "slTriggerPx": str(stop), "slOrdPx": "-1",
            "tpTriggerPx": str(ziel), "tpOrdPx": "-1"}
    d = okx._roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"]


def algo_setzen(inst, td_mode, side, menge, ausloeser, preis):
    """Eine bedingte Order. `ausloeser` ist 'sl' (Stop) oder 'tp' (Ziel).

    Der Koerper folgt OKX `POST /api/v5/trade/order-algo`:
      - `slOrdPx: -1` = Ausstieg zum Marktkurs beim Stop (das ist der Notaus)
      - `tpOrdPx: -1` = Ausstieg zum Marktkurs beim Ziel
    Ein TP zum Limitkurs waere bewusst NICHT gesetzt: bei einem
    Momentum-Ausbruch verpasst der Limit preis genau den Move, der ihn
    ausgeloest hat.
    """
    body = {"instId": inst, "tdMode": td_mode, "side": side,
            "ordType": "conditional", "sz": str(menge)}
    if ausloeser == "sl":
        body["slTriggerPx"] = str(preis)
        body["slOrdPx"] = "-1"
    else:
        body["tpTriggerPx"] = str(preis)
        body["tpOrdPx"] = "-1"
    d = okx._roh("/api/v5/trade/order-algo", "POST", body, signiert=True)
    return d[0]["algoId"]


def haupt(inst, stop_pct, ziel_pct, n_stufen, anwenden=False):
    p = position(inst)
    if not p:
        print("FEHLER: keine offene Position fuer %s (Boerse, instType=FUTURES)"
              % inst)
        return 2
    pos = zahl(p.get("pos"))
    if pos == 0:
        print("FEHLER: %s hat pos=0 - nichts zu sichern" % inst)
        return 2

    einstieg = zahl(p.get("avgPx"))
    marke = zahl(p.get("markPx"))
    liq = zahl(p.get("liqPx"))
    td_mode = p.get("mgnMode") or "isolated"
    seite = "long" if pos > 0 else "short"
    menge = abs(int(round(pos)))
    richtung = 1.0 if seite == "long" else -1.0
    # Bei isolated steht tdMode auf 'isolated'; OKX erwartet das so.
    td = "cross" if td_mode == "cross" else "isolated"

    print("POSITION (Boerse, nicht Hausbuch)")
    print("  %s  %s  Menge %d  Hebel %.0f  tdMode %s"
          % (inst, seite, menge, zahl(p.get("lever")), td))
    print("  Einstand %.8g | Marke %.8g | Liquidation %.8g"
          % (einstieg, marke, liq))
    print("  UPL %.2f (%.2f%%) | Marge %.2f | Notional %.2f"
          % (zahl(p.get("upl")), zahl(p.get("uplRatio")) * 100,
             zahl(p.get("margin")), zahl(p.get("notionalUsd"))))

    posten = list(bestaetigte(inst))
    schutz_seite = "sell" if seite == "long" else "buy"
    geschuetzt = sum(o["sz"] for o in posten
                     if o["side"] == schutz_seite and o["slTriggerPx"])
    print()
    print("VORHANDENE POSTEN: %d" % len(posten))
    for o in posten:
        was = ("Stop %.8g" % o["slTriggerPx"]) if o["slTriggerPx"] else \
              ("Ziel %.8g" % o["tpTriggerPx"] if o["tpTriggerPx"] else "-")
        print("  %-20s %-4s %-18s Menge %8.0f  %s  %s"
              % (o["algoId"], o["side"], was, o["sz"], o["state"], o["art"]))
    print("  Durch Stop geschuetzt: %.0f von %d = %.0f%%"
          % (geschuetzt, menge, 100.0 * geschuetzt / menge))
    if geschuetzt < menge:
        print("  ACHTUNG: %.0f Stuecke OHNE Schutz" % (menge - geschuetzt))

    stop = einstieg * (1 - richtung * stop_pct / 100.0)
    if marke and liq:
        abstand = (stop - liq) * richtung / marke * 100.0
        print()
        print("STOP")
        print("  %.2f%% vom Einstand -> %.8g" % (stop_pct, stop))
        print("  Abstand Stop -> Liquidation: %.2f%%" % abstand)
        if abstand <= 0:
            print("  GESPERRT: der Stop liegt auf oder unter der "
                  "Liquidationsmarke. Er wuerde nie greifen.")
            return 1
        if seite == "long" and stop >= marke:
            print("  GESPERRT: der Stop liegt ueber dem Kurs - sofort faellig.")
            return 1

    # Modus "aufstocken": die Luecke mit DEN PREISEN des bestehenden OCO
    # absichern. Der bestehende Preis ist der Beleg, dass die Position vom
    # Haus gesetzt wurde - ein neu gerechneter Preis waere eine zweite
    # Wahrheit neben der ersten.
    vorhandene_stops = [o for o in posten if o["slTriggerPx"] and o["side"] == schutz_seite
                        and o["sz"] > 0]
    vorhandene_ziele = [o for o in posten if o["tpTriggerPx"] and o["side"] == schutz_seite
                        and o["sz"] > 0]

    # Die Stufentabelle gibt es nur, wenn die Position GANZ ungeschuetzt ist.
    # Bei einer bestehenden Absicherung laeuft der Aufstock-Pfad weiter unten
    # mit den Preisen des vorhandenen Orders - eine neu gerechnete Tabelle
    # waere dann eine zweite, konkurrierende Wahrheit ueber dieselbe Position.
    mengen = preise = None
    if geschuetzt == 0:
        mengen = aufteilen(menge, n_stufen)
        if mengen is None:
            print("  GESPERRT: %d Stuecke lassen sich nicht in %d Stufen teilen."
                  % (menge, n_stufen))
            return 1
        preise = stufen(einstieg, ziel_pct, n_stufen)
        print()
        print("TAKE-PROFIT IN %d STUFEN" % n_stufen)
        print("  %-6s %-14s %-10s %10s %12s"
              % ("Stufe", "Trigger", "Abstand", "Menge", "Erloes USD"))
        for i, (preis, m) in enumerate(zip(preise, mengen), 1):
            print("  %-6d %-14.8g %9.2f%% %10d %12.2f"
                  % (i, preis, ziel_pct * i / n_stufen, m, preis * m))
        print("  Summe %d Stuecke = Position %d | Erloes gesamt %.2f USD"
              % (sum(mengen), menge,
                 sum(pp * mm for pp, mm in zip(preise, mengen))))

    luecke = menge - geschuetzt
    if luecke > 0 and vorhandene_stops:
        ref = vorhandene_stops[0]
        ziel_ref = vorhandene_ziele[0] if vorhandene_ziele else None
        print()
        print("AUFSTOCKEN (Luecke %.0f Stuecke)" % luecke)
        print("  uebernommene Preise aus algoId %s:" % ref["algoId"])
        print("    Stop %.8g  |  %s"
              % (ref["slTriggerPx"],
                 ("Ziel %.8g" % ziel_ref["tpTriggerPx"]) if ziel_ref else "kein Ziel am Order"))
        print("  Abstand Stop -> Einstand: %.2f%%  |  Kurs -> Stop: %.2f%%"
              % ((ref["slTriggerPx"] / einstieg - 1) * 100 * richtung,
                 (ref["slTriggerPx"] / marke - 1) * 100 * richtung))
        if ziel_ref:
            print("  Abstand Kurs -> Ziel: %.2f%%"
                  % ((ziel_ref["tpTriggerPx"] / marke - 1) * 100 * richtung))
        print("  Nach dem Aufstocken: %.0f von %d geschuetzt (%.0f%%)"
              % (geschuetzt + luecke, menge, 100.0 * (geschuetzt + luecke) / menge))

    if not anwenden:
        print()
        print("TROCKENLAUF - nichts gesendet.")
        if luecke > 0 and vorhandene_stops:
            # Aufstock-Pfad: EINE OCO-Order ueber die Luecke, mit den
            # Preisen des vorhandenen Orders. Zwei getrennte Orders (Stop
            # und Ziel) koennten sich ueberschneiden, wenn das Ziel feuert -
            # ein OCO kann pro Stueck nur einmal ausloesen.
            print("  AUFSTOCKEN (OCO): tdMode %s, %s %.0f Stuecke, Stop %.8g%s"
                  % (td, schutz_seite, luecke, ref["slTriggerPx"],
                     (" / Ziel %.8g" % ziel_ref["tpTriggerPx"]) if ziel_ref else ""))
        elif geschuetzt == 0:
            print("  Stop:        tdMode %s, %s %.0f Stuecke @ %.8g (Marktausloesung)"
                  % (td, schutz_seite, menge, stop))
            for i, (preis, m) in enumerate(zip(preise, mengen), 1):
                print("  TP-Stufe %d:  tdMode %s, %s %d Stuecke @ %.8g (Marktausloesung)"
                      % (i, td, schutz_seite, m, preis))
        else:
            print("  Position ist bereits vollstaendig geschuetzt - nichts zu tun.")
        print()
        print("Mit --anwenden wird gesendet." +
              (" Der Aufstock-OCO wird als EINE Order gesetzt." if luecke > 0 and vorhandene_stops
               else " Der Stop ZUERST, dann die Stufen."))
        return 0

    print()
    print("AUSFUEHREN (--anwenden)")
    if geschuetzt < menge:
        fehlend = menge - geschuetzt
        if vorhandene_stops and vorhandene_ziele:
            aid = oco_setzen(inst, td, schutz_seite, int(fehlend),
                             vorhandene_stops[0]["slTriggerPx"],
                             vorhandene_ziele[0]["tpTriggerPx"])
            print("  AUFSTOCKEN OCO: %.0f Stuecke, Stop %.8g / Ziel %.8g -> algoId %s"
                  % (fehlend, vorhandene_stops[0]["slTriggerPx"],
                     vorhandene_ziele[0]["tpTriggerPx"], aid))
        else:
            aid = algo_setzen(inst, td, schutz_seite, int(fehlend), "sl", stop)
            print("  Stop %.0f Stuecke @ %.8g -> algoId %s" % (fehlend, stop, aid))
    for i, (preis, m) in enumerate(zip(preise, mengen), 1):
        aid = algo_setzen(inst, td, schutz_seite, m, "tp", preis)
        print("  TP-Stufe %d: %d Stuecke @ %.8g -> algoId %s" % (i, m, preis, aid))
    print()
    print("NACHPRUEFEN - die Bestaetigung ist nicht der Beleg:")
    for o in bestaetigte(inst):
        was = ("Stop %.8g" % o["slTriggerPx"]) if o["slTriggerPx"] else \
              ("Ziel %.8g" % o["tpTriggerPx"] if o["tpTriggerPx"] else "-")
        print("  %-20s %-4s %-18s %8.0f  %s" % (o["algoId"], o["side"], was,
                                                o["sz"], o["state"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Stop + gestufter Take-Profit fuer eine OKX-Position "
                    "(Trockenlauf als Vorgabe).")
    ap.add_argument("inst", help="instId, z. B. MON-USD_UM_XPERP-310711")
    ap.add_argument("--stop-pct", type=float, default=2.5,
                    help="Stop-Abstand unter dem Einstand in Prozent (Vorgabe 2.5)")
    ap.add_argument("--ziel-pct", type=float, default=5.0,
                    help="oberes Take-Profit in Prozent ueber dem Einstand (Vorgabe 5.0)")
    ap.add_argument("--stufen", type=int, default=3, help="Anzahl TP-Stufen (Vorgabe 3)")
    ap.add_argument("--anwenden", action="store_true",
                    help="Wirklich setzen (Vorgabe: Trockenlauf)")
    args = ap.parse_args(argv)
    return haupt(args.inst, args.stop_pct, args.ziel_pct, args.stufen, args.anwenden)


if __name__ == "__main__":
    sys.exit(main())