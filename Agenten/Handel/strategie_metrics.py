"""
strategy_metrics.py – Kennzahlen, Freigabe-Regeln und Risiko-Steuerung
für Maximilians Krypto-Strategien (Grid, DCA, Scalping, Swing, Futures).

Basis: Formelblatt pyquantnews.com, mit Korrekturen:
  * Sortino: Downside-Deviation über ALLE Perioden (min(0, r - MAR)), nicht Std der Verlusttage
  * VaR: P(Verlust > VaR) = 1 - alpha (Blatt schreibt "= alpha")
  * MAE = MAXIMUM Adverse Excursion, richtungsabhängig (Short: P_max - P_entry)
  * Expectancy: AWR/ALR sind Beträge (Ø Gewinn/Verlust), keine Ratios
  * Annualisierung: Krypto handelt 365 Tage -> periods_per_year=365 (Tagesdaten)

Nur numpy/pandas. Aufruf `python strategy_metrics.py` führt Selbsttest + Demo aus.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

log = logging.getLogger("strategy_metrics")


# ---------------------------------------------------------------- Hilfen
def _returns(r: Iterable[float]) -> np.ndarray:
    a = np.asarray(list(r) if not isinstance(r, (np.ndarray, pd.Series)) else r, dtype=float)
    a = a[~np.isnan(a)]
    if a.size < 2:
        raise ValueError("Mindestens 2 Renditewerte nötig.")
    return a


def _rf_per_period(rf_annual: float, ppy: int) -> float:
    return (1 + rf_annual) ** (1 / ppy) - 1


# ---------------------------------------------------------------- Kennzahlen
def sharpe(returns, rf_annual: float = 0.0, ppy: int = 365) -> float:
    """Annualisierte Sharpe Ratio aus periodischen Renditen."""
    r = _returns(returns) - _rf_per_period(rf_annual, ppy)
    sd = r.std(ddof=1)
    return float("nan") if sd == 0 else float(r.mean() / sd * np.sqrt(ppy))


def sortino(returns, mar_annual: float = 0.0, ppy: int = 365) -> float:
    """Annualisierte Sortino Ratio; Downside-Deviation über alle Perioden (korrekte Definition)."""
    r = _returns(returns) - _rf_per_period(mar_annual, ppy)
    dd = np.sqrt(np.mean(np.minimum(r, 0.0) ** 2))
    return float("inf") if dd == 0 else float(r.mean() / dd * np.sqrt(ppy))


def var_historical(returns, alpha: float = 0.95) -> float:
    """Historischer VaR als positive Verlustzahl (Anteil). P(Verlust > VaR) = 1 - alpha."""
    r = _returns(returns)
    return float(-np.quantile(r, 1 - alpha))


def cvar_historical(returns, alpha: float = 0.95) -> float:
    """Expected Shortfall: Ø Verlust in den schlechtesten (1-alpha) Perioden."""
    r = _returns(returns)
    q = np.quantile(r, 1 - alpha)
    tail = r[r <= q]
    return float(-tail.mean())


def equity_curve(returns, start: float = 1.0) -> np.ndarray:
    return start * np.cumprod(1 + _returns(returns))


def drawdown_series(equity: Sequence[float]) -> np.ndarray:
    """Drawdown je Zeitpunkt: (Peak - aktuell) / Peak, Werte 0..1."""
    e = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(e)
    return (peak - e) / peak


def max_drawdown(equity: Sequence[float]) -> float:
    return float(drawdown_series(equity).max())


def cagr(equity: Sequence[float], ppy: int = 365) -> float:
    e = np.asarray(equity, dtype=float)
    years = (len(e) - 1) / ppy
    if years <= 0 or e[0] <= 0:
        return float("nan")
    return float((e[-1] / e[0]) ** (1 / years) - 1)


def calmar(returns, ppy: int = 365) -> float:
    """CAGR / MaxDD. Hinweis: Branchenüblich über 36 Monate – kurze Historien überschätzen."""
    eq = np.concatenate([[1.0], equity_curve(returns)])
    mdd = max_drawdown(eq)
    return float("inf") if mdd == 0 else cagr(eq, ppy) / mdd


def expectancy(trade_pnl: Sequence[float]) -> dict:
    """Erwartungswert je Trade (in PnL-Einheit, NACH Gebühren übergeben!)."""
    p = np.asarray(trade_pnl, dtype=float)
    if p.size == 0:
        raise ValueError("Keine Trades.")
    wins, losses = p[p > 0], p[p <= 0]
    wr = wins.size / p.size
    avg_win = wins.mean() if wins.size else 0.0
    avg_loss = -losses.mean() if losses.size else 0.0
    exp = wr * avg_win - (1 - wr) * avg_loss
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else float("inf")
    return {"trades": int(p.size), "winrate": wr, "avg_win": avg_win,
            "avg_loss": avg_loss, "expectancy": exp, "profit_factor": pf,
            # Standardfehler -> ist die Expectancy überhaupt von 0 unterscheidbar?
            "t_stat": float(p.mean() / (p.std(ddof=1) / np.sqrt(p.size))) if p.size > 1 and p.std(ddof=1) > 0 else float("nan")}


def mae_mfe(entry: float, highs: Sequence[float], lows: Sequence[float], side: str = "long") -> tuple[float, float]:
    """Maximum Adverse/Favorable Excursion als Anteil vom Einstieg, richtungsabhängig."""
    hi, lo = float(np.max(highs)), float(np.min(lows))
    if side == "long":
        mae, mfe = (entry - lo) / entry, (hi - entry) / entry
    elif side == "short":
        mae, mfe = (hi - entry) / entry, (entry - lo) / entry
    else:
        raise ValueError("side muss 'long' oder 'short' sein")
    return max(mae, 0.0), max(mfe, 0.0)


# ---------------------------------------------------------------- Strategie-Profile
@dataclass
class StrategyProfile:
    """Freigabe-Schwellen = ANNAHMEN als Startwerte, nicht gesicherte Branchenwerte."""
    name: str
    min_trades: int
    min_sharpe: float
    min_sortino: float
    min_calmar: float
    max_mdd: float            # Anteil, z. B. 0.20
    max_cvar95_daily: float   # Anteil des Strategie-Kapitals
    min_t_stat: float = 2.0   # Expectancy statistisch > 0
    leverage: float = 1.0
    notes: str = ""


PROFILES: dict[str, StrategyProfile] = {
    "grid":     StrategyProfile("Grid (Kraken, Spot)", 100, 1.0, 1.5, 1.0, 0.20, 0.04,
                                notes="Hohe Winrate normal – entscheidend ist CVaR/MaxDD bei Trendausbruch aus der Range."),
    "dca":      StrategyProfile("DCA (langfristig)", 12, 0.5, 0.7, 0.3, 0.60, 0.08, min_t_stat=0.0,
                                notes="Kein Trade-Edge-System: Expectancy/t-Stat nicht sinnvoll, Vergleich gegen Buy&Hold."),
    "scalping": StrategyProfile("Scalping", 300, 1.5, 2.0, 1.5, 0.15, 0.03,
                                notes="Gebühren + Slippage dominieren – Expectancy nur NETTO bewerten."),
    "swing":    StrategyProfile("Swing (4h/Daily)", 50, 1.0, 1.4, 1.0, 0.25, 0.05,
                                notes="Wenige Trades -> großer Schätzfehler; Walk-Forward nötig."),
    "futures":  StrategyProfile("Futures (OKX, erst Simulation)", 150, 1.2, 1.8, 1.2, 0.20, 0.04, leverage=3.0,
                                notes="MAE muss deutlich unter Liquidationsabstand bleiben; Funding-Kosten einrechnen."),
}


@dataclass
class Report:
    profile: str
    metrics: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)

    @property
    def approved(self) -> bool:
        return all(self.checks.values())

    def __str__(self) -> str:
        lines = [f"== {self.profile}: {'FREIGEGEBEN' if self.approved else 'NICHT freigegeben'} =="]
        lines += [f"  {k:<16}{v: .4f}" if isinstance(v, float) else f"  {k:<16}{v}" for k, v in self.metrics.items()]
        lines += [f"  [{'OK' if ok else 'X '}] {k}" for k, ok in self.checks.items()]
        return "\n".join(lines)


def evaluate(key: str, daily_returns, trade_pnl=None, trade_mae=None, ppy: int = 365, rf_annual: float = 0.0) -> Report:
    """Strategie gegen ihr Profil prüfen. daily_returns: Renditen des Strategie-Kapitals."""
    p = PROFILES[key]
    r = _returns(daily_returns)
    eq = np.concatenate([[1.0], equity_curve(r)])
    m = {"sharpe": sharpe(r, rf_annual, ppy), "sortino": sortino(r, rf_annual, ppy),
         "calmar": calmar(r, ppy), "cagr": cagr(eq, ppy), "max_dd": max_drawdown(eq),
         "var95": var_historical(r), "cvar95": cvar_historical(r)}
    c = {f"Sharpe >= {p.min_sharpe}": m["sharpe"] >= p.min_sharpe,
         f"Sortino >= {p.min_sortino}": m["sortino"] >= p.min_sortino,
         f"Calmar >= {p.min_calmar}": m["calmar"] >= p.min_calmar,
         f"MaxDD <= {p.max_mdd:.0%}": m["max_dd"] <= p.max_mdd,
         f"CVaR95 <= {p.max_cvar95_daily:.0%}": m["cvar95"] <= p.max_cvar95_daily}
    if trade_pnl is not None:
        e = expectancy(trade_pnl)
        m.update({k: e[k] for k in ("trades", "winrate", "expectancy", "profit_factor", "t_stat")})
        c[f"Trades >= {p.min_trades}"] = e["trades"] >= p.min_trades
        c["Expectancy > 0 (netto)"] = e["expectancy"] > 0
        if p.min_t_stat > 0:
            c[f"t-Stat >= {p.min_t_stat}"] = e["t_stat"] >= p.min_t_stat
    if trade_mae is not None and p.leverage > 1:
        liq = 1 / p.leverage  # grobe Näherung ohne Maintenance Margin -> reale Liquidation früher!
        mae95 = float(np.quantile(trade_mae, 0.95))
        m["mae95"] = mae95
        c[f"MAE95 < 50% Liq-Abstand ({liq / 2:.1%})"] = mae95 < liq / 2
    return Report(p.name, m, c)


# ---------------------------------------------------------------- Risiko-Steuerung (live)
def position_size_cvar(capital: float, risk_budget: float, cvar_per_unit: float) -> float:
    """Positionsgröße so, dass erwarteter Tail-Verlust (CVaR) = risk_budget * capital."""
    if cvar_per_unit <= 0:
        raise ValueError("cvar_per_unit muss > 0 sein")
    return capital * risk_budget / cvar_per_unit


def stop_from_mae(winner_mae: Sequence[float], quantile: float = 0.9) -> float:
    """Stop-Abstand aus MAE der GEWINNER-Trades: Gewinner gehen selten weiter ins Minus."""
    return float(np.quantile(np.asarray(winner_mae, dtype=float), quantile))


def drawdown_throttle(current_dd: float, max_dd: float) -> float:
    """Exposure-Faktor 0..1: voll bis 50 % des DD-Limits, linear runter, 0 am Limit (Kill-Switch)."""
    if current_dd >= max_dd:
        return 0.0
    half = max_dd / 2
    return 1.0 if current_dd <= half else float(1 - (current_dd - half) / half)


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> None:
    r = np.array([0.01, -0.02, 0.015, -0.005, 0.02, -0.01])
    assert abs(max_drawdown([100, 120, 90, 130, 104]) - 0.25) < 1e-12
    assert expectancy([10, -5, 10, -5])["expectancy"] == 2.5
    mae, mfe = mae_mfe(100, [110], [95], "short")
    assert abs(mae - 0.10) < 1e-12 and abs(mfe - 0.05) < 1e-12
    assert cvar_historical(r, 0.8) >= var_historical(r, 0.8)
    assert sortino(r) > sharpe(r) or np.isclose(sortino(r), sharpe(r))
    assert drawdown_throttle(0.05, 0.20) == 1.0 and drawdown_throttle(0.20, 0.20) == 0.0
    assert abs(drawdown_throttle(0.15, 0.20) - 0.5) < 1e-12
    print("Selbsttest OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _selftest()
    rng = np.random.default_rng(42)
    demo_r = rng.normal(0.0012, 0.02, 730)           # 2 Jahre Tagesrenditen (synthetisch!)
    demo_pnl = rng.normal(4, 40, 400)                # 400 Trades, netto
    demo_mae = np.abs(rng.normal(0.03, 0.02, 400))
    for k in ("grid", "futures"):
        print(evaluate(k, demo_r, demo_pnl, demo_mae), "\n")
    print("Stop aus MAE (90 %):", f"{stop_from_mae(demo_mae[demo_pnl > 0]):.2%}")
    print("Positionsgröße CVaR:", f"{position_size_cvar(10_000, 0.01, cvar_historical(demo_r)):.0f} EUR")
