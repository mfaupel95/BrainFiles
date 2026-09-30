# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""Bot 3: Moon-Dev `coingecko_agent` als Freqtrade-Strategie (Marktregime).

QUELLE
------
`Werkstatt/Repos/moon-dev-ai-agents/src/agents/coingecko_agent.py` ist ein
Drei-Agenten-System (technische Analyse, Fundamentalanalyse, Token-Extraktor),
das ueber CoinGecko-Marktdaten laeuft und alle 30 Minuten eine Runde dreht.
Die Haus-Fassung derselben Absicht steht in
`Agenten/Handel/moondev_marktlage/wachen.json`:

    BTC long, wenn BTC 24h mindestens +2 % steht UND mindestens 60 % der
    Top-100-Coins im Plus liegen; short spiegelbildlich (-2 % und hoechstens
    40 %). Dazwischen kein Geschaeft.

Das ist die portierbare Substanz: ein REGIME aus Leitkurs und Marktbreite.
Der Rest des Agenten (Prosa der drei Agenten, Token-Extraktion) faellt weg -
er traegt keine Zahl, die man nachrechnen koennte.

MARKTBREITE OHNE COINGECKO
--------------------------
Die Breite ("Anteil der Coins im Plus") braucht mehr als ein Paar. Freqtrade
kann das: `informative_pairs` laedt beliebige andere Paare der Boerse mit, und
`merge_informative_pair` haengt sie OHNE Vorausschau an jede Kerze (der
Mergesatz verschiebt die Informationskerze um ein Intervall nach vorn). So
entsteht dieselbe Kennzahl aus Boersendaten statt aus einem CoinGecko-Ranking.

`BREITE_PAARE` ist deshalb die Messlatte des Regimes und nicht der Bestand des
Bots - der Bot handelt nur BTC. Es sind die liquidesten USDT-Paare; sie
wachsen und fallen mit der Boerse, nicht mit einem Datenanbieter.

FAIL CLOSED
-----------
Fehlt die Breite (keine informative Kerze), faellt KEIN Einstieg. Eine
unvollstaendig gemessene Breite darf nie als "Markt ist breit" durchgehen -
dieselbe Regel wie bei `breite.py` im Haus, nur hier in der Strategie.
"""

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, merge_informative_pair

from moondev_basis import MoonDevBasis


class MoonDevMarketRegime(MoonDevBasis):
    """BTC-Regime aus Leitkurs und Marktbreite (Quelle: coingecko_agent)."""

    stop_prozent: float = 6.0

    # Regime wechselt langsamer als ein Einzelkurs: kein Signal-Ausstieg,
    # es tragen Stop, Ziel und die Regime-Umkehr.
    startup_candle_count: int = 60

    # Die Messlatte der Breite. Wer sie aendert, misst eine andere Kennzahl.
    BREITE_PAARE = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "LINK/USDT", "DOT/USDT",
        "LTC/USDT", "ATOM/USDT",
    ]

    # Haus-Zahlen aus moondev_marktlage/wachen.json.
    btc_schwelle_pct = DecimalParameter(0.005, 0.06, default=0.02, decimals=3,
                                        space="buy", optimize=True, load=False)
    breite_oben = DecimalParameter(0.40, 0.80, default=0.60, decimals=2,
                                   space="buy", optimize=True, load=False)
    mindest_deckung = 0.8

    def informative_pairs(self):
        """Die Paare der Marktbreite als informative Paare auf demselben Rahmen."""
        paare = self.config.get("exchange", {}).get("pair_whitelist") or []
        return [(p, self.timeframe) for p in self.BREITE_PAARE if p not in paare]

    def _breite(self, dataframe: DataFrame, pair: str) -> DataFrame:
        """Anteil der Paare mit positiver 24h-Aenderung, je Kerze.

        Liefert zwei Spalten: `breite` (Anteil) und `breite_deckung` (Anteil
        der Paare, die ueberhaupt eine Zahl beigetragen haben). Beide werden
        gebraucht - ohne die Deckung waere ein fehlendes Paar ein Ja-Stimme.
        """
        spalten = []
        i = 0
        for p in self.BREITE_PAARE:
            if p == pair:
                continue
            inf = self.dp.get_pair_dataframe(pair=p, timeframe=self.timeframe)
            if inf is None or inf.empty or "close" not in inf:
                continue
            inf = inf[["date", "close"]].copy()
            # 24h-Aenderung DIESES Paares, dann nur das Vorzeichen.
            inf["ueber"] = (
                (inf["close"] / inf["close"].shift(24) - 1).gt(0).astype(float)
            )
            # merge_informative_pair haengt das Suffix an JEDEN Spaltennamen
            # (informative_decorator._prepare_informative_pair:354) - die
            # Zielspalte heisst deshalb 'ueber_<suffix>', nicht '<suffix>'.
            suffix = f"b{i}"
            spalte = f"ueber_{suffix}"
            gemischt = merge_informative_pair(
                dataframe, inf, self.timeframe, self.timeframe,
                ffill=True, append_timeframe=False, suffix=suffix,
            )
            dataframe[spalte] = gemischt[spalte]
            spalten.append(spalte)
            i += 1

        if not spalten:
            dataframe["breite"] = np.nan
            dataframe["breite_deckung"] = 0.0
            return dataframe
        block = dataframe[spalten]
        dataframe["breite"] = block.mean(axis=1)
        dataframe["breite_deckung"] = block.notna().mean(axis=1)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["close_24h_vor"] = dataframe["close"].shift(24)
        dataframe["chg24"] = dataframe["close"] / dataframe["close_24h_vor"] - 1
        dataframe = self._breite(dataframe, metadata["pair"])
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["chg24"] >= self.btc_schwelle_pct.value)
                & (dataframe["breite"] >= self.breite_oben.value)
                & (dataframe["breite_deckung"] >= self.mindest_deckung)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self.signal_ausstieg:
            return dataframe
        # Regime vorbei: Leitkurs dreht unter die Schwelle oder die Breite
        # bricht ein. Beides ist dieselbe Zahl, die den Einstieg geoeffnet hat.
        dataframe.loc[
            (
                (~dataframe["chg24"].isna())
                & (
                    (dataframe["chg24"] < 0)
                    | (dataframe["breite"] < self.breite_oben.value / 2)
                )
            )
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe