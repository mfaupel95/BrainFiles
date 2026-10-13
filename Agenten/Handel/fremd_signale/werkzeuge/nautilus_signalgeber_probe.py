"""Rauchtest: Signalgeber im Nautilus-Backtest (synthetische Minutenkerzen), schreibt Absichtszeilen.
Aufruf: Werkstatt/nautilus-venv/Scripts/python.exe Werkstatt/nautilus_signalgeber_probe.py <repo-pfad>
"""
import os, sys, tempfile
from decimal import Decimal
repo = sys.argv[1]
sys.path.insert(0, os.path.join(repo, "Agenten", "Bus"))
import pandas as pd
from nautilus_trader.adapters.binance import BINANCE_VENUE
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, RiskEngineConfig
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.objects import Money
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_signalgeber import Signalgeber, SignalgeberConfig

pfad = os.path.join(tempfile.mkdtemp(), "intents.jsonl")
e = BacktestEngine(BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"), risk_engine=RiskEngineConfig(bypass=True)))
e.add_venue(venue=BINANCE_VENUE, oms_type=OmsType.NETTING, account_type=AccountType.CASH, base_currency=None,
            starting_balances=[Money(1_000_000, USDT), Money(10, ETH)])
inst = TestInstrumentProvider.ethusdt_binance()
e.add_instrument(inst)
import math
from nautilus_trader.model.data import Bar
from nautilus_trader.model.objects import Price, Quantity
bt = BarType.from_str("ETHUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL")
bars = []
t0 = 1_791_000_000 * 10**9
for i in range(600):
    p = 2000 + 80 * math.sin(i / 25) + 5 * math.sin(i / 3)
    pr = Price(p, 2)
    bars.append(Bar(bt, pr, pr, pr, pr, Quantity(10, 5), t0 + i * 60 * 10**9, t0 + i * 60 * 10**9))
e.add_data(bars)
e.add_strategy(Signalgeber(SignalgeberConfig(instrument_id=inst.id,
    bar_type=BarType.from_str("ETHUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"),
    ziel_id="ETH-USDC.OKX", intents_pfad=pfad)))
e.run()
n = len(open(pfad).read().splitlines()) if os.path.exists(pfad) else 0
print("Absichtszeilen:", n, pfad)
print(open(pfad).read()[:300] if n else "keine")
e.dispose()
