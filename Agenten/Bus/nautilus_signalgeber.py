"""Nautilus-Strategie, die NICHT handelt: sie schreibt EMA-Kreuzungen als Absichtszeilen.

Laeuft nur in einer Nautilus-Umgebung (Werkstatt/nautilus-venv). Je Kreuzung eine
JSON-Zeile in `intents_pfad`; adapter_nautilus.py liest sie und meldet sie an den Bus
(Schema + Tor). Die Strategie sendet keine Order und kennt keinen Orderweg.

Zeile: {"ts_event": <ns>, "instrument_id": ziel_id, "side": "BUY"|"SELL"}
  schneller EMA kreuzt ueber den langsamen -> BUY, darunter -> SELL
`ziel_id` ist die Bezeichnung, unter der das Signal weitergegeben wird (z. B. "BTC-USDC.OKX"),
unabhaengig vom Instrument, auf dem Nautilus rechnet (Backtest-Daten).
"""
import json

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import BarType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class SignalgeberConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    ziel_id: str
    intents_pfad: str
    fast_ema_period: int = 10
    slow_ema_period: int = 20


class Signalgeber(Strategy):
    def __init__(self, config: SignalgeberConfig) -> None:
        super().__init__(config)
        self.fast = ExponentialMovingAverage(config.fast_ema_period)
        self.slow = ExponentialMovingAverage(config.slow_ema_period)
        self._oben = None

    def on_start(self) -> None:
        self.register_indicator_for_bars(self.config.bar_type, self.fast)
        self.register_indicator_for_bars(self.config.bar_type, self.slow)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar) -> None:
        if not (self.fast.initialized and self.slow.initialized):
            return
        oben = self.fast.value > self.slow.value
        if self._oben is not None and oben != self._oben:
            self._schreibe(bar.ts_event, "BUY" if oben else "SELL")
        self._oben = oben

    def _schreibe(self, ts_ns, side) -> None:
        zeile = {"ts_event": int(ts_ns), "instrument_id": self.config.ziel_id, "side": side}
        with open(self.config.intents_pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile) + "\n")

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.config.bar_type)


class DonchianConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    ziel_id: str
    intents_pfad: str
    rein: int = 55
    raus: int = 20


class DonchianSignalgeber(Strategy):
    """Donchian-Ausbruch (Turtle): BUY, wenn der Schluss ueber dem hoechsten Schluss der letzten `rein`
    Kerzen liegt; SELL, wenn er unter dem tiefsten der letzten `raus` Kerzen liegt. Schreibt nur Absichten.
    Walk-forward/Vorab-Test: Werkstatt/trend_wenighandel.py (Variante B, 1D 55/20)."""

    def __init__(self, config: DonchianConfig) -> None:
        super().__init__(config)
        self._schluesse = []
        self._an = False

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar) -> None:
        c, s = float(bar.close), self._schluesse
        if not self._an and len(s) >= self.config.rein and c > max(s[-self.config.rein:]):
            self._an = True
            self._schreibe(bar.ts_event, "BUY")
        elif self._an and len(s) >= self.config.raus and c < min(s[-self.config.raus:]):
            self._an = False
            self._schreibe(bar.ts_event, "SELL")
        s.append(c)

    def _schreibe(self, ts_ns, side) -> None:
        zeile = {"ts_event": int(ts_ns), "instrument_id": self.config.ziel_id, "side": side}
        with open(self.config.intents_pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile) + "\n")

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.config.bar_type)
