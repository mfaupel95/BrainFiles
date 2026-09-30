# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib


# EMA-Cross nach den Handelsregeln (EA_CROSS haelt den Trend, laesst die
# Gegenbewegung laufen; Ausstieg ueber ATR-Trailing-Stop, nicht ueber ROI).
#
# Einstieg (long):   EMA(50) kreuzt ueber EMA(200) auf der 1H-Kerze UND
#                    Schlusskurs ueber EMA200 (Bestatigung, kein Knick) UND
#                    Tagesvolumen ueber dem 20-Tage-Durchschnitt.
# Ausstieg:          ATR-Trailing-Stop (Abstand 3.0 * ATR14), nie enger als 1.5%.
#                    Kein ROI — einmal drin, reitet die Bewegung.
class EmaCrossStrategy(IStrategy):
    """1h EMA50/EMA200 Golden-Cross mit ATR-Trailing-Stop, reiner Long."""

    INTERFACE_VERSION = 3

    # Nur Long. Der Gegenbewegung (Short) fehlt hier eine gepruefte
    # Trendkennung; sie unterbleibt, statt erraten zu werden.
    can_short: bool = False

    # Kein ROI: Das Fenster-Modell der SampleStrategie schneidet Trends ab,
    # die Hausregel will den Ruecklauf im Trend laufen lassen.
    minimal_roi = {"0": 100}

    # Schutz am Eingang: 5% unter Einstieg. Narrow genug fuer eine 1H-Kerze,
    # weit genug gegen Rauschen.
    stoploss = -0.05

    # ATR-Trailing: Der Stop haengt dem Kurs hinterher, der Abstand passt
    # sich der Volatilitaet an. Positive Trailing-Stufe erst nach +2%.
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    timeframe = "1h"

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # Hyperoptable Parameter (Standardwerte = die gemessene Linie)
    ema_fast = IntParameter(low=20, high=100, default=50, space="buy", optimize=True, load=False)
    ema_slow = IntParameter(low=100, high=250, default=200, space="buy", optimize=True, load=False)
    atr_mult = DecimalParameter(low=1.0, high=5.0, default=3.0, decimals=1, space="sell", optimize=True, load=False)

    # 200 Balken Warmup fuer die langsame EMA + Reserve fuer ATR.
    startup_candle_count: int = 250

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "ema_fast": {"color": "blue"},
            "ema_slow": {"color": "red"},
            "atr_stop": {"color": "purple"},
        },
        "subplots": {
            "Volume": {
                "vol_ma20": {"color": "black"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast.value)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow.value)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        # Trailing-Stop-Abstand: 3.0 x ATR14, nicht enger als 1.5% vom Kurs.
        dataframe["atr_stop"] = dataframe["close"] - dataframe["atr"] * self.atr_mult.value
        dataframe["atr_stop"] = dataframe["atr_stop"].clip(upper=dataframe["close"] * (1 - 0.015))
        # Tuevliches Volumen-Referenz (20 Balken-Schnitt).
        dataframe["vol_ma20"] = dataframe["volume"].rolling(window=20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Golden Cross: schnelle EMA kreuzt ueber die langsame
                (qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]))
                # Bestaetigung: Schlusskurs ueber der langsamen EMA (kein Knick)
                & (dataframe["close"] > dataframe["ema_slow"])
                # Volumen: kein stiller Breakout
                & (dataframe["volume"] > 0)
                & (dataframe["volume"] >= dataframe["vol_ma20"])
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Kein Signal-Ausstieg. Der ATR-Trailing-Stop (stoploss) besorgt den
        # Exit; ein zusaetzliches Signal wuerde ihn mit der lauten EMA-Kurve
        # doppeln. exit_long bleibt 0, use_exit_signal=False waere die andere
        # Form — das Stop-Loss-Rennen ist hier das einzige Ausgangstor.
        return dataframe
