# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""Bot 3b: `MoonDevMarketRegime` MIT kurzer Seite (T-198, 01.10.2026).

WARUM ES DIESE DATEI GIBT
-------------------------
Alle drei portierten Bots waren long-only, weil `can_short = True` im Spot-Modus
nicht einmal laedt (`freqtrade/resolvers/strategy_resolver.py` verweigert es).
Die Uebertragung war damit die HALBE Regel. Von den drei Agenten hat genau EINER
eine belegte Short-Regel - `coingecko_agent` bzw. die Haus-Fassung
`Agenten/Handel/moondev_marktlage/wachen.json`:

    BTC long,  wenn BTC 24h mindestens +2 % steht UND mindestens 60 % der
    Messlatte im Plus liegen; short spiegelbildlich (-2 % und hoechstens 40 %).

`trading_agent` und `new_or_top_agent` haben keine - dort wird auch nichts
erfunden. Ein Short, den niemand beschrieben hat, waere eine neue Strategie und
nicht die Uebertragung dieser.

WAS FUER FUTURES NOETIG IST
---------------------------
`trading_mode: futures` und Futures-Daten der Paare in der Form
`BTC/USDT:USDT` (ccxt-Schreibweise). Der Backtest rechnet dann auch die
FUNDING-RATE mit - Freqtrade laedt sie beim `download-data --trading-mode
futures` als eigene Reihe mit. Das ist die Antwort auf die alte Absage in
`bots.json`, die "Freqtrade kenne keine Funding-Rate" (T-199): im SPOT-Backtest
stimmt das, im Futures-Backtest nicht.

MESSUNG, NICHT UMBAU: Diese Datei aendert nichts an den laufenden Bots. Sie ist
der Messgegenstand der Frage "was traegt die kurze Seite?".
"""

import numpy as np
import pandas as pd
from pandas import DataFrame

from MoonDevMarketRegime import MoonDevMarketRegime


class MoonDevMarketRegimeFutures(MoonDevMarketRegime):
    """Regime-Bot mit kurzer Seite (Futures). Quelle der Regel: siehe Modul oben."""

    # Erst mit trading_mode futures ladbar - im Spot-Modus verweigert
    # Freqtrade die Strategie (strategy_resolver).
    can_short: bool = True

    # Futures-Paare tragen das Settlement-Suffix (ccxt: BTC/USDT:USDT).
    BREITE_PAARE = [p.replace("/USDT", "/USDT:USDT")
                    for p in MoonDevMarketRegime.BREITE_PAARE]

    def __init__(self, config: dict) -> None:
        """Welche Seite wird gemessen? `moondev.seite` = beide|long|short.

        Die Messung der kurzen Seite braucht drei Laeufe derselben Strategie,
        nicht drei Strategien: nur lang, nur kurz, beide. Ohne diesen Schalter
        liesse sich nicht sagen, ob ein Unterschied von der kurzen Seite kommt
        oder von den Futures (Funding, Hebel, andere Kerzen).
        """
        super().__init__(config)
        seite = ((config.get("moondev") or {}).get("seite") or "beide").lower()
        self.seite = seite if seite in ("beide", "long", "short") else "beide"

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_short" not in dataframe.columns:
            dataframe["enter_short"] = 0
        if self.seite == "long":
            return dataframe
        if self.seite == "short" and "enter_long" in dataframe.columns:
            dataframe["enter_long"] = 0          # nur die kurze Seite messen
        # Spiegelbild der Haus-Regel: Leitkurs mindestens -2 % UND hoechstens
        # 40 % der Messlatte im Plus. Dieselbe Zahl, andere Richtung.
        dataframe.loc[
            (
                (dataframe["chg24"] <= -self.btc_schwelle_pct.value)
                & (dataframe["breite"] <= (1.0 - self.breite_oben.value))
                & (dataframe["breite_deckung"] >= self.mindest_deckung)
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if not self.signal_ausstieg:
            return dataframe
        # Regime vorbei: Leitkurs dreht ueber null oder die Breite erholt sich.
        dataframe.loc[
            (
                (~dataframe["chg24"].isna())
                & (
                    (dataframe["chg24"] > 0)
                    | (dataframe["breite"] > (1.0 - self.breite_oben.value / 2.0))
                )
            )
            & (dataframe["volume"] > 0),
            "exit_short",
        ] = 1
        return dataframe