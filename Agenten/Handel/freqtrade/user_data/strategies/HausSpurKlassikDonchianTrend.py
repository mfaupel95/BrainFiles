# pragma pylint: disable=missing-docstring, invalid-name
# flake8: noqa: F401
# isort: skip_file
"""HausSpurKlassikDonchianTrend - Phase B: klassik_donchian_trend vektorisiert.

Dieselbe Regel wie klassik_regeln.einstieg_donchian_trend / ausstieg_donchian,
aber ueber das ganze DataFrame in einem Zug statt je Kerze ueber ein Fenster.
Zweck: schneller Backtest/Hyperopt. Der Adapter HausSpur bleibt die Referenz;
freqtrade/tests/test_b_donchian_trend.py prueft Kerze fuer Kerze die Gleichheit
(Spec Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md, Phase 2).

Die Falle: Die Haus-EMA200 ist KEINE durchgehende EMA. klassik_regeln rechnet
sie je Kerze im 400er-Fenster, gestartet mit dem SMA der ersten 200 Kerzen des
Fensters. `ema_im_fenster` bildet genau das ab: Startwert x (1-f)^m plus eine
gewichtete Summe der letzten m Schluesse (Faltung). Gueltig ab vollem Fenster
(Index fenster-1); davor NaN - Freqtrade handelt dort ohnehin nicht (startup).

Stop, Ziel, ROI, Schutzschicht und Ausloesung erbt die Klasse von HausSpur.
"""

import numpy as np
from pandas import DataFrame

from HausSpur import HausSpur


def ema_im_fenster(x, n, fenster, versatz=0):
    """Haus-EMA(n) an Position i-versatz, gerechnet im Fenster [i-fenster+1, i].

    Wie klassik_regeln.ema(k[i-fenster+1:i+1], n)[-1-versatz]: Start mit dem
    SMA der ersten n Werte des Fensters, danach m = fenster-n-versatz Schritte.
    """
    x = np.asarray(x, dtype=float)
    aus = np.full(len(x), np.nan)
    m = fenster - n - versatz
    if m < 0 or len(x) < fenster:
        return aus
    f = 2.0 / (n + 1)
    # Startwert: SMA der ersten n Werte des Fensters, das bei i endet.
    kum = np.concatenate(([0.0], np.cumsum(x)))
    i = np.arange(fenster - 1, len(x))
    start = i - fenster + 1
    saat = (kum[start + n] - kum[start]) / n
    # Gewichtete Summe der m Werte bis i-versatz: sum_t f(1-f)^t x[i-versatz-t].
    gewichte = f * (1 - f) ** np.arange(m)
    summe = np.convolve(x, gewichte)[:len(x)] if m else np.zeros(len(x))
    aus[i] = (1 - f) ** m * saat + summe[i - versatz]
    return aus


def donchian_spalten(dataframe, fenster, n_ein, n_aus, trend_n, steigung,
                     nur_long, aus_ok, stop, ziel):
    """Die hs_*-Spalten der Spur fuer frei gewaehlte Parameter (auch Hyperopt)."""
    h, l, c = dataframe["high"], dataframe["low"], dataframe["close"]
    e0 = ema_im_fenster(c.values, trend_n, fenster, 0)
    e_alt = ema_im_fenster(c.values, trend_n, fenster, steigung)
    hoch_ein = h.rolling(n_ein).max().shift(1).values
    tief_ein = l.rolling(n_ein).min().shift(1).values
    cv = c.values
    voll = ~np.isnan(e0)

    long = voll & (cv > hoch_ein) & (cv > e0) & (e0 > e_alt)
    short = voll & (cv < tief_ein) & (cv < e0) & (e0 < e_alt)
    if nur_long:
        short = np.zeros(len(cv), dtype=bool)
    ein = np.where(long, "long", np.where(short, "short", None))
    dataframe["hs_ein"] = np.where(voll, ein, None)

    tief_aus = l.rolling(n_aus).min().shift(1).values
    hoch_aus = h.rolling(n_aus).max().shift(1).values
    dataframe["hs_aus_long"] = voll & aus_ok & (cv < tief_aus)
    dataframe["hs_aus_short"] = voll & aus_ok & (cv > hoch_aus)
    dataframe["hs_stop"] = np.where(voll, stop, np.nan)
    dataframe["hs_ziel"] = np.where(voll, ziel, np.nan)
    return dataframe


class HausSpurKlassikDonchianTrend(HausSpur):

    def bot_start(self, **kwargs) -> None:
        self.config.setdefault("hausspur", {}).setdefault("name", "klassik_donchian_trend")
        super().bot_start(**kwargs)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        w = self.hs_wachen
        stop = float(w.get("stop_prozent") or self.hr.STOP_VORGABE)
        return donchian_spalten(
            dataframe, self.hr.fenster(w),
            n_ein=int(w.get("kanal_ein_n", 20)), n_aus=int(w.get("kanal_aus_n", 10)),
            trend_n=int(w.get("trend_n", 200)), steigung=int(w.get("steigung_n", 20)),
            nur_long=bool(w.get("nur_long")), aus_ok=bool(w.get("ausstieg_bei_regel", True)),
            stop=stop, ziel=float(w.get("ziel_r_vielfaches") or 2.0) * stop)
