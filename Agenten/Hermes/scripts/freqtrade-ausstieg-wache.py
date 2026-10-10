#!/usr/bin/env python3
"""freqtrade-ausstieg-wache.py — meldet neue geschlossene Trades der Bots
trading-agent (8081) und marktlage-regime (8083) mit ihrem Exit-Grund.

Zweck: beobachten, ob der Schalter signal_ausstieg=false (Entscheidung Max
08.10.2026) wirkt — neue Trades sollen NICHT mehr mit exit_reason=exit_signal
enden, sondern nur ueber Stop/Ziel/Schutzschicht.

Watchdog-Muster: leere Ausgabe = nichts zu melden. Merkdatei in
Agenten/Hermes/cache/freqtrade-ausstieg-wache.json (Laufzeitstand, nicht
versioniert). Zugangsdaten kommen aus den Aufsatz-Configs, werden nie
ausgegeben.

Aufruf: python freqtrade-ausstieg-wache.py [--vorschau]
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "..", "cache")
MERK = os.path.join(CACHE, "freqtrade-ausstieg-wache.json")

# (port, aufsatz-config, bot-name)
BOTS = [
    (8081, "config.trading-agent.json", "trading-agent"),
    (8083, "config.marktlage-regime.json", "marktlage-regime"),
]


def _api(port, aufsatz, pfad):
    """Liest die API-Zugangsdaten aus der Aufsatz-Config und ruft die API."""
    ud = os.path.join(HIER, "..", "..", "Handel", "freqtrade", "user_data")
    cfg = json.load(open(os.path.join(ud, aufsatz), encoding="utf-8"))
    api = cfg.get("api_server", {})
    u, p = api.get("username"), api.get("password")
    req = urllib.request.Request(f"http://127.0.0.1:{port}{pfad}")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{u}:{p}".encode()).decode())
    return json.load(urllib.request.urlopen(req, timeout=15))


def _lade_merk():
    if os.path.exists(MERK):
        try:
            return json.load(open(MERK, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _schreibe_merk(merk):
    os.makedirs(CACHE, exist_ok=True)
    tmp = MERK + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(merk, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MERK)


def _meldung(bot, trade):
    grund = trade.get("exit_reason") or "?"
    profit = trade.get("profit_abs", 0)
    pct = trade.get("profit_ratio", 0) * 100
    paar = trade.get("pair", "?")
    tid = trade.get("trade_id", "?")
    offen = "OFFEN" if trade.get("is_open") else "geschlossen"
    return (f"{bot}: Trade #{tid} {paar} {offen} | Exit: {grund} | "
            f"{profit:+.2f} USDT ({pct:+.2f}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vorschau", action="store_true", help="nur anzeigen, nichts merken")
    args = ap.parse_args()

    merk = _lade_merk()
    zeilen = []
    fehler = []

    for port, aufsatz, bot in BOTS:
        try:
            r = _api(port, aufsatz, "/api/v1/trades?limit=50")
        except Exception as e:
            fehler.append(f"{bot}: API nicht erreichbar ({e})")
            continue
        trades = r.get("trades", [])
        if not trades:
            continue
        letzte_id = merk.get(bot, {}).get("letzte_trade_id", 0)
        # neue geschlossene Trades (id > letzte_id), aelteste zuerst
        neu = sorted([t for t in trades if t.get("trade_id", 0) > letzte_id],
                     key=lambda t: t.get("trade_id", 0))
        for t in neu:
            zeilen.append(_meldung(bot, t))
        merk[bot] = {"letzte_trade_id": max(t.get("trade_id", 0) for t in trades)}

    if fehler:
        zeilen.append("; ".join(fehler))

    if args.vorschau:
        print("\n".join(zeilen) if zeilen else "keine neuen Trades (rein lesend)")
        return 0

    if zeilen:
        _schreibe_merk(merk)
        print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
