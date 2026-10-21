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


class EnsembleConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    ziel_id: str
    intents_pfad: str
    bars_pro_tag: int = 6          # 4H-Kerzen
    vola_ziel: float = 0.40        # Ziel-Volatilitaet p. a.
    size_max: float = 0.25         # size_pct bei Volllast (Deckel des Tores)


class EnsembleSignalgeber(Strategy):
    """Ensemble-Donchian nach Zarattini/Pagani/Barbon (SFI 25-80), Long-only, Vola-skaliert.

    Neun Donchian-Modelle (Lookback 5..360 Tage; rein ueber Max(n), raus unter Min(n/2)); Gewicht =
    Anteil der Modelle im Markt * min(1, Ziel-Vola / 30-Tage-Vola). Der Bus kennt nur long/flat:
    BUY (mit size_pct = Gewicht * size_max) beim Wechsel 0 -> >0, SELL beim Wechsel >0 -> 0.
    Teilweises Auf-/Abstocken innerhalb einer offenen Position wird NICHT gemeldet (Abweichung von der
    Auswertung Werkstatt/trend_ensemble.py, Variante H2). Schreibt nur Absichten."""

    LOOKBACKS = (5, 10, 20, 30, 60, 90, 150, 250, 360)

    def __init__(self, config: EnsembleConfig) -> None:
        super().__init__(config)
        self._c = []
        self._an = {n: False for n in self.LOOKBACKS}
        self._im_markt = False

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar_type)

    def _gewicht(self) -> float:
        c, f = self._c, self.config.bars_pro_tag
        for n in self.LOOKBACKS:
            rein, raus = n * f, max(2, n * f // 2)
            if len(c) <= rein:
                continue
            if not self._an[n] and c[-1] > max(c[-rein - 1:-1]):
                self._an[n] = True
            elif self._an[n] and len(c) > raus and c[-1] < min(c[-raus - 1:-1]):
                self._an[n] = False
        anteil = sum(self._an.values()) / len(self.LOOKBACKS)
        fenster = 30 * f
        if len(c) <= fenster:
            return 0.0
        r = [c[i] / c[i - 1] - 1 for i in range(len(c) - fenster, len(c))]
        m = sum(r) / len(r)
        vola = (sum((x - m) ** 2 for x in r) / len(r)) ** 0.5 * (365 * f) ** 0.5
        return anteil * (min(1.0, self.config.vola_ziel / vola) if vola > 0 else 0.0)

    def on_bar(self, bar) -> None:
        self._c.append(float(bar.close))
        w = self._gewicht()
        if w > 0 and not self._im_markt:
            self._im_markt = True
            self._schreibe(bar.ts_event, "BUY", round(min(w * self.config.size_max, self.config.size_max), 4))
        elif w <= 0 and self._im_markt:
            self._im_markt = False
            self._schreibe(bar.ts_event, "SELL", None)

    def _schreibe(self, ts_ns, side, size_pct) -> None:
        zeile = {"ts_event": int(ts_ns), "instrument_id": self.config.ziel_id, "side": side}
        if size_pct is not None:
            zeile["size_pct"] = size_pct
        with open(self.config.intents_pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(zeile) + "\n")

    def on_stop(self) -> None:
        self.unsubscribe_bars(self.config.bar_type)
