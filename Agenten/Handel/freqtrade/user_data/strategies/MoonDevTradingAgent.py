# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""Bot 1: Moon-Dev `trading_agent` als Freqtrade-Strategie.

QUELLE
------
`Werkstatt/moon-dev-ai-agents/src/agents/trading_agent.py`. Der Agent
legt dem Sprachmodell genau vier Dinge vor (TRADING_PROMPT, Zeilen 8-14):

  1. Price action relative to MA20 and MA40
  2. RSI levels and trend
  3. Volume patterns
  4. Recent price movements

und die Haus-Fassung desselben Agenten rechnet sie deterministisch in
`_indikatoren()` (dieselbe Datei): `ma20`, `ma40`, `rsi14`,
`volumen_trend_6zu6`, `24h_hoch`/`24h_tief`. Genau diese vier Punkte werden
hier uebersetzt - das Sprachmodell faellt weg, weil es nichts hinzufuegt,
was nachrechenbar waere (die Kriterien sind vollstaendig da).

UEBERTRAGUNG (jede Zeile ist eine Entscheidung, keine Auslegung)
----------------------------------------------------------------
* Punkt 1 - `close > ma20 > ma40`: Preis ueber beiden Mittelwerten, die
  schnelle ueber der langsamen. Das ist die uebliche Lesart von "preis
  relativ zu MA20 und MA40" und die einzige, die beide Zahlen benutzt.
* Punkt 2 - `45 <= rsi14 <= 70`: Trend, aber nicht ueberhitzt. Unter 45 ist
  der Aufwaertstrend nicht bestaetigt, ueber 70 ist der Zug meist abgefahren.
* Punkt 3 - `volumen(6) > volumen(6).shift(6)`: die letzten sechs Kerzen
  tragen mehr Volumen als die sechs davor. Das ist `volumen_trend_6zu6 > 0`
  aus der Haus-Fassung.
* Punkt 4 - `close > close.shift(24)`: der Kurs steht ueber dem Stand von
  vor 24 Stunden (dieselbe Spanne wie `24h_hoch`/`24h_tief`).

AUSSTIEG
--------
Signal-Ausstieg bei `close < ma20` (der Trend ist gebrochen) oder
`rsi14 > 78` (ueberhitzt, der Agent nennt RSI ausdruecklich als Trendmass).
Dazu Stop und Ziel aus der Basis (6 %, 1.5 R = 9 %).
"""

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IntParameter

from moondev_basis import MoonDevBasis


class MoonDevTradingAgent(MoonDevBasis):
    """MA20/MA40-Trend mit RSI- und Volumenbestaetigung (Quelle: trading_agent)."""

    # Geometrie: die Haus-Spur, die dieselbe Regel fuehrt (moondev_marktlage),
    # steht auf stop_prozent 6.0. Das Fenster hier ist aber nicht das
    # Marktregime, sondern der Einzelkurs - deshalb 6 % wie in den
    # wachen.json der Feed-Spuren (5.0-8.0), nicht der Regime-Wert.
    stop_prozent: float = 6.0

    # 40 fuer ma40, plus Reserve fuer RSI und das 24-Kerzen-Fenster.
    startup_candle_count: int = 60

    # Hyperoptbare Schwellen. Defaults = die oben begruendeten Werte,
    # `load=False`, damit ein Backtest nicht still eine alte Hyperopt-Datei
    # zieht (Falle im Skill freqtrade-strategie, Abschnitt "Fallen").
    rsi_min = IntParameter(35, 55, default=45, space="buy", optimize=True, load=False)
    rsi_max = IntParameter(60, 80, default=70, space="buy", optimize=True, load=False)

    plot_config = {
        "main_plot": {"ma20": {"color": "blue"}, "ma40": {"color": "red"}},
        "subplots": {
            "RSI": {"rsi14": {"color": "purple"}},
            "Volumen": {"vol6": {"color": "black"}},
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ma20"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["ma40"] = ta.SMA(dataframe, timeperiod=40)
        dataframe["rsi14"] = ta.RSI(dataframe, timeperiod=14)
        # Volumen-Trend: die letzten 6 Kerzen gegen die 6 davor.
        dataframe["vol6"] = dataframe["volume"].rolling(6).mean()
        dataframe["vol6_vor"] = dataframe["vol6"].shift(6)
        # Punkt 4: Stand von vor 24 Stunden (24 Kerzen a 1h).
        dataframe["close_24h_vor"] = dataframe["close"].shift(24)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ma20"])           # Punkt 1
                & (dataframe["ma20"] > dataframe["ma40"])          # Punkt 1
                & (dataframe["rsi14"] >= self.rsi_min.value)       # Punkt 2
                & (dataframe["rsi14"] <= self.rsi_max.value)       # Punkt 2
                & (dataframe["vol6"] > dataframe["vol6_vor"])      # Punkt 3
                & (dataframe["close"] > dataframe["close_24h_vor"])  # Punkt 4
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.signal_ausstieg:
            return dataframe
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["ma20"])
                | (dataframe["rsi14"] > 78)
            )
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe