# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""Bot 2: Moon-Dev `new_or_top_agent` als Freqtrade-Strategie.

QUELLE
------
`Werkstatt/Repos/moon-dev-ai-agents/src/agents/new_or_top_agent.py` holt bei
CoinGecko die Top-Gewinner der letzten 24 Stunden (250 nach Marktkapital) und
die zuletzt gelisteten Coins und legt beides einem Sprachmodell vor
(`RECOMMENDATION: BUY/SELL/DO NOTHING`). Die Haus-Fassung derselben Regel steht
in `Agenten/Handel/moondev_topmovers/wachen.json`:

    Long bei einer 24h-Aenderung zwischen +8 % und +40 % und mindestens
    20 Mio USD Tagesvolumen. Ueber +40 % gilt der Zug als abgefahren,
    unter +8 % ist kein Momentum da.

UEBERTRAGUNG
------------
* 24h-Aenderung = `close / close.shift(24) - 1` (24 Kerzen a 1h).
* Tagesvolumen in USD = Summe von `volume * close` ueber 24 Kerzen. Binance
  liefert das Volumen in der BASIS-Waehrung, deshalb die Multiplikation mit
  dem Schlusskurs - eine rohe Volumenzahl waere je Coin unvergleichbar.
* Band und Volumenschwelle sind die Haus-Zahlen 8 % / 40 % / 20 Mio USD.

WAS SICH AENDERT, UND WARUM DAS EHRLICH IST
-------------------------------------------
Der Agent durchsucht den GANZEN Markt (250 Coins). Freqtrade kennt keine
Marktrangliste - der Bestand kommt aus der `pairlist` der jeweiligen
Bot-Konfiguration. Der Bot sucht also in einem kleineren Teich (die liquidesten
USDT-Paare der Boerse, siehe `bots.json`), wendet dort aber dieselbe Regel an.
Die Regel ist portiert, der Suchraum ist kleiner; das steht so in der
Zuordnungstabelle und wird nicht als dasselbe ausgegeben.

AUSSTIEG
--------
* `chg24 > 40 %` - der Zug ist abgefahren (woertlich die Haus-Regel).
* `chg24 < 2 %`  - das Momentum ist weg; die Regel lebt von der Bewegung.
* Dazu Stop und Ziel aus der Basis (8 %, 1.5 R = 12 %).
"""

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter

from moondev_basis import MoonDevBasis


class MoonDevTopMovers(MoonDevBasis):
    """24h-Momentum in einem Band, mit Volumenschwelle (Quelle: new_or_top_agent)."""

    # Haus-Zahlen aus moondev_topmovers/wachen.json.
    stop_prozent: float = 8.0

    # 24 Kerzen fuer den Rueckblick, plus Reserve.
    startup_candle_count: int = 48

    mindest_plus = DecimalParameter(0.02, 0.20, default=0.08, decimals=2,
                                    space="buy", optimize=True, load=False)
    hoechst_plus = DecimalParameter(0.25, 0.80, default=0.40, decimals=2,
                                    space="buy", optimize=True, load=False)
    mindest_volumen_usd = DecimalParameter(
        5_000_000.0, 100_000_000.0, default=20_000_000.0, decimals=0,
        space="buy", optimize=True, load=False)

    plot_config = {
        "main_plot": {"chg24": {"color": "green"}},
        "subplots": {
            "Volumen USD": {"vol24_usd": {"color": "black"}},
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["close_24h_vor"] = dataframe["close"].shift(24)
        dataframe["chg24"] = dataframe["close"] / dataframe["close_24h_vor"] - 1
        # Volumen in USD, nicht in Basis-Einheiten.
        dataframe["vol_usd"] = dataframe["volume"] * dataframe["close"]
        dataframe["vol24_usd"] = dataframe["vol_usd"].rolling(24).sum()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["chg24"] >= self.mindest_plus.value)
                & (dataframe["chg24"] <= self.hoechst_plus.value)
                & (dataframe["vol24_usd"] >= self.mindest_volumen_usd.value)
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
                # Zug abgefahren oder Momentum weg - beides steht in der Regel.
                (dataframe["chg24"] > self.hoechst_plus.value)
                | (dataframe["chg24"] < 0.02)
            )
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe