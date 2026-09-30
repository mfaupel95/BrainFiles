# pragma pylint: disable=missing-docstring, invalid-name
# flake8: noqa: F401
# isort: skip_file
"""Walk-Forward-Gegenprobe: die im ersten Halbjahr per Hyperopt gefundenen
Parameter (ema_fast=33, ema_slow=135, atr_mult=2.3), getestet im ungesehenen
zweiten Halbjahr. Erbt alles andere von EmaCrossStrategy."""
import talib.abstract as ta
from technical import qtpylib

from freqtrade.strategy import IntParameter, DecimalParameter
from ema_cross import EmaCrossStrategy


class EmaCrossH1(EmaCrossStrategy):
    INTERFACE_VERSION = 3

    # Im ersten Halbjahr (2025-09-29..2026-03-29) per SharpeHyperOptLoss
    # gefundene Parameter. Defaults gesetzt, damit self.<param>.value sie
    # liefert (buy_params als Klassenattribut ueberschreibt .value NICHT).
    ema_fast = IntParameter(low=20, high=100, default=33, space="buy", optimize=True, load=False)
    ema_slow = IntParameter(low=100, high=250, default=135, space="buy", optimize=True, load=False)
    atr_mult = DecimalParameter(low=1.0, high=5.0, default=2.3, decimals=1, space="sell", optimize=True, load=False)
