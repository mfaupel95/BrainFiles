"""Zustandswaechter fuer EINEN omnitrade-Lauf: meldet ORDERS, nicht Kerzen.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe = nichts
geaendert**. Merkdatei je Lauf, damit derselbe Befund nicht zweimal kommt.

WARUM EIGENS, obwohl `omnitrade-lauf-wache.py` existiert: jene meldet
Laufzustand - tot, stehend, leerer Statusordner. Sie sagt nichts, wenn ein
Lauf eine Order PLATZIERT. Genau das ist die Beobachtung, die am 05.10.2026
fehlte (Auftrag "beobachte"): ein Lauf laeuft, zeigt `sell`, und die
Position aendert sich still - ohne dass irgendetwas davon in Telegram ankommt.

GEMESSEN (05.10.2026, 11:35): BTCUSDC / ema_cross_20_50.omni / PID 73440,
304 Kerzen, `last_signal: sell`, `orders_placed: 0`, `net_quantity: 0.0`.
Ein `sell` bei leerer Position ist richtig - es gibt nichts zu verkaufen. Der
Unterschied zwischen "Signal" und "Order" ist genau das, was man melden muss.

WAS GEMELDET WIRD (nur Aenderungen seit dem letzten Lauf):
  * neue Order (`orders_placed` steigt, oder eine neue Zeile in
    `recent_orders` erscheint) -> mit Instrument, Seite, Menge, Kurs
  * `net_quantity` weicht ab -> das ist die POSITION, die wichtigste Zahl
  * `last_signal` wechselt -> nur beim Wechsel, nicht je Kerze
  * der Lauf stirbt oder bleibt stehen -> mit Alter, in Minuten
  * der Lauf ist zurueck auf derselben Position (Laufende) -> nach 6 h Ruhe

NICHT gemeldet: jeder Kurs, jede Kerze, `candles_seen`. Eine Wache, die bei
jedem Takt schreibt, wird abgelesen und dann abgeschaltet - sie ist dann fuer
genau die Stoerung blind, die sie finden sollte.

Aufruf:
    python Agenten/Hermes/scripts/omnitrade-order-wache.py
    python ... --alle                 # alle Laeufe, nicht nur live.json
    python ... --merken                # Zustand schreiben, nichts melden
    python ... --immer                 # auch ohne Aenderung ausgeben (Test)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                       # scripts -> Hermes -> Agenten -> BrainFiles
CACHE = HIER.parent.parent / "cache"           # Agenten/Hermes/cache

# Wie alt eine Statusdatei sein darf, bis der Lauf als tot gilt. Die Datei wird
# NUR beim Verarbeiten einer Kerze geschrieben - live.json (der Hauptlauf) laeuft
# auf 1d-Kerzen, nicht auf 15 min. Eine feste 45-min-Grenze erklaerte dort am
# 11.10.2026 einen gesunden Lauf fuer tot (639 min alt, Grenze 45, lief weiter;
# die autoritative Pruefung setzt die Grenze auf 60 h). Darum waechst die Grenze
# mit dem Kerzenabstand aus der Datei selbst - derselbe Mechanismus wie
# `omnitrade_bridge.altersgrenze_s` (der schon den 30.09.2026-Fall geloest hat).
TOT_MINUTEN = 45     # Untergrenze (Fallback, wenn kein Abstand ableitbar)
VIELFACHES = 2.5     # so oft darf der Kerzenabstand vergehen, bevor es haengt


def altersgrenze_min(d):
    """Altersgrenze in Minuten, gewachsen mit dem Kerzenabstand der Datei.
    Identisch zu omnitrade_bridge.altersgrenze_s, nur in Minuten."""
    kerzen = (d or {}).get("recent_candles") or []
    zeiten = []
    for k in kerzen:
        if isinstance(k, dict) and isinstance(k.get("time_ms"), (int, float)):
            zeiten.append(float(k["time_ms"]))
    if len(zeiten) < 2:
        return float(TOT_MINUTEN)
    zeiten.sort()
    abst = sorted(b - a for a, b in zip(zeiten, zeiten[1:]) if b > a)
    if not abst:
        return float(TOT_MINUTEN)
    i_s = abst[len(abst) // 2] / 1000.0  # Median, Luecke zaehlt nicht
    return max(float(TOT_MINUTEN), VIELFACHES * i_s / 60.0)
# Nach wie viel Stunden Ruhe ein gesunder Lauf einmal "läuft weiter" meldet.
MELDEN_NACH_STILLE_H = 6

ORDNER = WURZEL / "Werkstatt" / "omnitrade" / "status"


def _zahl(v, default=0.0):
    if v in (None, "", "-"):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def laeufe(alle=True):
    """Die Statusdateien als Liste. `live.json` zuerst - sie ist der Lauf, den
    `omnitrade.cmd start` schreibt, und der Default fuer `omnitrade.cmd`."""
    if not ORDNER.is_dir():
        return []
    muster = "live*.json" if alle else "live.json"
    dateien = sorted(ORDNER.glob(muster),
                     key=lambda p: (p.name != "live.json", p.stat().st_mtime),
                     reverse=False)
    aus = []
    for p in dateien:
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        aus.append((p, d))
    return aus


def jetzt_ms():
    return int(time.time() * 1000)


def kennung(pfad, d):
    """Der Name, unter dem der Lauf gemerkt wird. Die PID ist nicht
    brauchbar - sie wechselt beim Neustart, und dann waere jeder Lauf neu."""
    return "%s|%s" % (pfad.name, d.get("script", "?"))


def schnappschuss(pfad, d):
    """Nur die Felder, auf die sich der Vergleich stuetzt."""
    return {
        "pid": d.get("pid"),
        "state": d.get("state"),
        "orders_placed": int(_zahl(d.get("orders_placed"))),
        "net_quantity": round(_zahl(d.get("net_quantity")), 8),
        "last_signal": d.get("last_signal") or "",
        "letzte_order": (d.get("recent_orders") or [{}])[-1] if d.get("recent_orders") else {},
        "aktualisiert": pfad.stat().st_mtime,
    }


def vergleiche(alt, neu, pfad, grenze_min: float = TOT_MINUTEN):
    """Was sich gegenueber dem letzten Lauf geaendert hat. Leer heisst:
    nichts zu melden."""
    zeilen = []
    name = pfad.name
    if alt is None:
        return []                      # der erste Lauf merkt nur, er meldet nicht

    # 1. Tod / Stehen - vor allem anderen, weil es das Wichtigste ist.
    alter_s = (zeit() - neu["aktualisiert"]) / 60.0
    if alter_s > grenze_min:
        zeilen.append("omnitrade %s: seit %.0f min kein Lebenszeichen "
                      "(Grenze %.0f min) - PID %s"
                      % (name, alter_s, grenze_min, neu.get("pid")))
        return zeilen

    # 2. Orders - die eigentliche Beobachtung.
    alt_orders = int(alt.get("orders_placed") or 0)
    if neu["orders_placed"] > alt_orders:
        o = neu.get("letzte_order") or {}
        zeilen.append(
            "omnitrade %s: %d Order(s) mehr (%d -> %d)%s"
            % (name, neu["orders_placed"] - alt_orders,
               alt_orders, neu["orders_placed"],
               ("  letzte: %s %.4f @ %.4f" % (o.get("side", "?"),
                                              _zahl(o.get("sz")),
                                              _zahl(o.get("px")))) if o else ""))

    # 3. Netto-Position. Die Zahl, an der man merkt, ob der Lauf handelt.
    if abs(_zahl(neu["net_quantity"]) - _zahl(alt.get("net_quantity"))) > 1e-9:
        zeilen.append("omnitrade %s: Netto-Position %.6f -> %.6f"
                      % (name, _zahl(alt.get("net_quantity")),
                         neu["net_quantity"]))

    # 4. Signalwechsel - nur beim Wechsel.
    if (alt.get("last_signal") or "") != (neu.get("last_signal") or ""):
        zeilen.append("omnitrade %s: Signal %s -> %s"
                      % (name, alt.get("last_signal") or "-",
                         neu.get("last_signal") or "-"))

    # 5. Lauf gestartet (neue PID bei gleichem Lauf).
    if alt.get("pid") and neu.get("pid") and alt["pid"] != neu["pid"]:
        zeilen.append("omnitrade %s: Lauf neu (PID %s -> %s)"
                      % (name, alt["pid"], neu["pid"]))

    # 6. Zustand gekippt (running -> stopped/error).
    if alt.get("state") != neu.get("state"):
        zeilen.append("omnitrade %s: Zustand %s -> %s"
                      % (name, alt.get("state"), neu.get("state")))
    return zeilen


def _datei_name(k):
    """Ein MERKDATEI-Name je Lauf.

    `k` enthaelt den Skriptnamen aus der Statusdatei, und der sieht aus wie
    `strategien\\ema_cross_20_50.omni`. Ein Backslash darin ist auf Windows ein
    ORDNERTRENNER - der erste Lauf endete in
    `FileNotFoundError: ...\\strategien\\ema_cross_20_50.omni.json`, weil der
    Zwischenordner nicht existiert. Deshalb wird alles, was kein Buchstabe,
    keine Ziffer und kein Bindestrich ist, zu `_`; der Name bleibt lesbar und
    ist eindeutig (zwei Skripte, die sich nur im Trennzeichen unterscheiden,
    gibt es nicht).
    """
    sicher = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in k)
    while "__" in sicher:
        sicher = sicher.replace("__", "_")
    return "%s.json" % sicher


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="omnitrade: meldet neue Orders und Positionsaenderungen.")
    ap.add_argument("--alle", action="store_true",
                    help="alle live*.json, nicht nur live.json")
    ap.add_argument("--merken", action="store_true",
                    help="Zustand schreiben, nichts melden")
    ap.add_argument("--immer", action="store_true",
                    help="auch ohne Aenderung ausgeben (Testlauf)")
    ap.add_argument("--verzeichnis", default=None, help="Statusordner (Test)")
    args = ap.parse_args(argv)

    global ORDNER, CACHE
    if args.verzeichnis:
        ORDNER = Path(args.verzeichnis)
        CACHE = Path(args.verzeichnis).parent / "_merksdateien"

    CACHE.mkdir(parents=True, exist_ok=True)
    meldungen = []
    for pfad, d in laeufe(args.alle):
        k = kennung(pfad, d)
        datei = CACHE / ("omnitrade-order-" + _datei_name(k))
        alt = None
        if datei.exists():
            try:
                with open(datei, encoding="utf-8") as f:
                    alt = json.load(f)
            except (OSError, ValueError):
                alt = None
        neu = schnappschuss(pfad, d)
        grenze_min = altersgrenze_min(d)   # kerzenabhaengig, kein festes 45 min
        if args.merken:
            pass
        else:
            meldungen += vergleiche(alt, neu, pfad, grenze_min)
        neu["gemerkt_am"] = zeit()
        if not args.merken or True:
            with open(datei, "w", encoding="utf-8") as f:
                json.dump(neu, f, ensure_ascii=False, indent=2)

    if args.immer:
        for pfad, d in laeufe(args.alle):
            s = schnappschuss(pfad, d)
            meldungen.append(
                "omnitrade %s: PID %s %s Kerzen %d | Signal %s | Orders %d | "
                "Netto %.6f | %.0f min alt"
                % (pfad.name, s["pid"], d.get("symbol", "?"),
                   int(_zahl(d.get("candles_seen"))), s["last_signal"],
                   s["orders_placed"], s["net_quantity"],
                   (zeit() - s["aktualisiert"]) / 60.0))
    for z in meldungen:
        print(z)
    return 0


def zeit():
    return time.time()


if __name__ == "__main__":
    sys.exit(main())