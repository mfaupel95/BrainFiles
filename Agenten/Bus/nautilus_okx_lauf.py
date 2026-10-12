#!/usr/bin/env python3
"""Echte OKX-Kerzen durch die Signalgeber-Strategie (Nautilus) -> nautilus_intents.jsonl.

Nur in der Nautilus-Umgebung: Werkstatt/nautilus-venv/Scripts/python.exe nautilus_okx_lauf.py
          [--instrument BTC-USDC] [--bar 5m|1H|4H|1D] [--strategie ema|donchian] [--rein 55] [--raus 20] [--ziel Pfad] [--vorschau]
Holt die letzten abgeschlossenen Kerzen (oeffentlicher OKX-Markt, kein Schluessel), rechnet sie
im Backtest-Motor und haengt NUR die Kreuzung der juengsten Kerze an die Zieldatei an
(ts_event = Kerzenschluss, jede Kreuzung einmal). Aeltere Kreuzungen werden nicht nachgeholt:
der Bus wuerde sie als stale verwerfen. --vorschau schreibt nichts. Handelt nie.
"""
import json
import math
import os
import sys
import tempfile
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

from nautilus_trader.adapters.binance import BINANCE_VENUE
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, RiskEngineConfig
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider

from nautilus_signalgeber import (DonchianConfig, DonchianSignalgeber, Signalgeber,
                                  SignalgeberConfig)

BAR_S = {"1m": 60, "5m": 300, "15m": 900, "1H": 3600, "4H": 14400, "1D": 86400}
STANDARD_ZIEL = os.path.join(os.path.dirname(os.path.dirname(HIER)), "Werkstatt", "nautilus_intents.jsonl")


def kerzen(instrument, bar, n=300):
    url = "https://www.okx.com/api/v5/market/candles?instId=%s&bar=%s&limit=%d" % (instrument, bar, n)
    req = urllib.request.Request(url, headers={"User-Agent": "brainfiles/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.load(r)["data"]
    # neueste zuerst; nur abgeschlossene (confirm == "1"); aufsteigend sortieren
    fertig = [x for x in d if x[8] == "1"]
    return sorted(([int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])] for x in fertig))


def rechne(zeilen, bar_s, ziel_id, strategie="ema", rein=55, raus=20):
    """Backtest ueber die Kerzen; gibt die geschriebenen Absichtszeilen zurueck."""
    e = BacktestEngine(BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"),
                                            risk_engine=RiskEngineConfig(bypass=True)))
    e.add_venue(venue=BINANCE_VENUE, oms_type=OmsType.NETTING, account_type=AccountType.CASH,
                base_currency=None, starting_balances=[Money(1_000_000, USDT), Money(10, ETH)])
    inst = TestInstrumentProvider.ethusdt_binance()   # nur Rechentraeger; ziel_id benennt das Signal
    e.add_instrument(inst)
    spez = ("%d-DAY" % (bar_s // 86400) if bar_s % 86400 == 0 else "%d-HOUR" % (bar_s // 3600)
            if bar_s % 3600 == 0 else "%d-MINUTE" % (bar_s // 60))
    bt = BarType.from_str("ETHUSDT.BINANCE-%s-LAST-EXTERNAL" % spez)
    bars = []
    for ms, o, h, l, c in zeilen:
        close_ns = (ms // 1000 + bar_s) * 10**9
        bars.append(Bar(bt, Price(o, 2), Price(h, 2), Price(l, 2), Price(c, 2),
                        Quantity(1, 5), close_ns, close_ns))
    e.add_data(bars)
    pfad = os.path.join(tempfile.mkdtemp(), "i.jsonl")
    e.add_strategy(Signalgeber(SignalgeberConfig(instrument_id=inst.id, bar_type=bt,
                                                 ziel_id=ziel_id, intents_pfad=pfad)))
    e.run()
    e.dispose()
    if not os.path.exists(pfad):
        return []
    with open(pfad, encoding="utf-8") as f:
        return [json.loads(x) for x in f.read().splitlines()]


def main(argv):
    def opt(n, d):
        return argv[argv.index(n) + 1] if n in argv else d
    inst, bar = opt("--instrument", "BTC-USDC"), opt("--bar", "5m")
    ziel = opt("--ziel", STANDARD_ZIEL)
    strategie = opt("--strategie", "ema")
    rein, raus = int(opt("--rein", 55)), int(opt("--raus", 20))
    bar_s = BAR_S[bar]
    zeilen = kerzen(inst, bar)
    if len(zeilen) < 40:
        print("zu wenige Kerzen: %d" % len(zeilen))
        return 1
    letzter_schluss = (zeilen[-1][0] // 1000 + bar_s) * 10**9
    intents = rechne(zeilen, bar_s, inst + ".OKX", strategie, rein, raus)
    neu = [z for z in intents if z["ts_event"] == letzter_schluss]
    print("Kerzen: %d | Kreuzungen gesamt: %d | auf juengster Kerze: %d" % (len(zeilen), len(intents), len(neu)))
    if not neu or "--vorschau" in argv:
        print(json.dumps(neu, ensure_ascii=False) if neu else "keine neue Kreuzung")
        return 0
    bekannt = set()
    if os.path.exists(ziel):
        with open(ziel, encoding="utf-8") as f:
            bekannt = {json.loads(x).get("ts_event") for x in f.read().splitlines() if x.strip().startswith("{")}
    with open(ziel, "a", encoding="utf-8") as f:
        for z in neu:
            if z["ts_event"] not in bekannt:
                f.write(json.dumps(z) + "\n")
                print("geschrieben:", z)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
