# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""Gemeinsame Basis der Moon-Dev-Bots in Freqtrade.

WARUM DIESE DATEI EXISTIERT
---------------------------
Die Trading-Agenten aus `Werkstatt/Repos/moon-dev-ai-agents` sind ueberwiegend
DATENSAMMLER: `funding_agent` liest Funding-Raten, `whale_agent` das offene
Interesse, `liquidation_agent` Zwangsschluesse, `sentiment_agent` Schlagzeilen.
Freqtrade sieht ausschliesslich OHLCV-Kerzen des gehandelten Paares. Ein Agent,
dessen Eingang eine Fremdquelle ist, laesst sich deshalb NICHT als Freqtrade-
Strategie abbilden - die Zuordnung steht in `bots.json` mit Begruendung.

Portierbar ist, was sich aus der Kerze rechnen laesst. Diese Basis traegt, was
alle portierten Bots teilen:

* **Geometrie aus dem Haus.** Stop und Ziel kommen nicht aus dem Bot-Repo,
  sondern aus den Zahlen, die das Haus fuer dieselben Regeln schon fuehrt
  (`Agenten/Handel/moondev_*/wachen.json`): `stop_prozent` und
  `ziel_r_vielfaches 1.5`. Ziel = 1.5 x Stop-Abstand.
* **risk_agent als Schutzschicht.** Der Moon-Dev `risk_agent` begrenzt Verlust
  und Gewinn in einem 12-h-Fenster (+/-25 USD, +/-5 %). Freqtrade hat fuer
  genau diese Rolle eingebaute Schutzmechanismen; sie werden hier mit den
  Zahlen des risk_agent gesetzt statt mit erfundenen.

SPOT: Die kurze Seite fehlt hier ABSICHTLICH. `can_short=True` laesst sich im
Spot-Modus nicht einmal laden (freqtrade/resolvers/strategy_resolver.py:167
verweigert es). Die Agenten mit einer Short-Regel werden deshalb nach der
LONG-Seite abgebildet; die Short-Seite braucht `trading_mode: futures` und
steht als offener Punkt in TASKS.md. Eine halbe Regel ist ehrlicher als eine
erfundene zweite Haelfte.
"""

from datetime import datetime
from typing import Optional, Union

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy


class MoonDevBasis(IStrategy):
    """Basis fuer die kerzenfaehigen Moon-Dev-Agenten (nur Long, Spot)."""

    INTERFACE_VERSION = 3

    # Spot: kurze Seite braucht Futures (siehe Modul-Docstring).
    can_short: bool = False

    timeframe = "1h"

    # --- Geometrie (Haus-Zahlen, nicht geraten) -------------------------------
    # stop_prozent aus der jeweiligen wachen.json; Ziel = 1.5 R.
    stop_prozent: float = 6.0
    ziel_r_vielfaches: float = 1.5

    # Signal-Ausstieg an oder aus. Steht in der Konfiguration unter
    # `moondev.signal_ausstieg` und ist die gemessene Frage, nicht Geschmack:
    # im ersten Backtest ueber 400 Tage trugen ALLE DREI Bots ihren Verlust im
    # Signal-Ausstieg (trading-agent -174 %, topmovers -313 %, marktlage-regime
    # -42 %), waehrend die Geometrie aus Stop und Ziel positiv abschloss.
    # Aus (False) heisst: nur Stop, Ziel und die Schutzschicht entscheiden.
    signal_ausstieg: bool = True

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    def __init__(self, config: dict) -> None:
        """Stop und Ziel aus den Haus-Zahlen ableiten.

        Freqtrade liest `stoploss` und `minimal_roi` als Klassenattribute; sie
        werden hier EINMAL aus `stop_prozent`/`ziel_r_vielfaches` gerechnet,
        damit Stop und Ziel nicht auseinanderlaufen koennen. Eine Zahl im Code
        ist eine zweite Wahrheit - deshalb nur eine Eingangszahl.
        """
        super().__init__(config)
        stop = self.stop_prozent / 100.0
        self.stoploss = -stop
        # Ziel = 1.5 x Stop-Abstand, in Prozent vom Einstieg.
        self.minimal_roi = {"0": stop * self.ziel_r_vielfaches}
        # Schalter aus der Konfiguration. Fehlt er, bleibt es beim Stand der
        # Strategie - ein fehlender Eintrag darf keine Regel still umstellen.
        schalter = (config.get("moondev") or {}).get("signal_ausstieg")
        if schalter is not None:
            self.signal_ausstieg = bool(schalter)
        self.use_exit_signal = bool(self.signal_ausstieg)

    # --- risk_agent als Freqtrade-Schutzschicht ------------------------------
    @property
    def protections(self):
        """Die Tore des Moon-Dev `risk_agent` in Freqtrade-Sprache.

        Der risk_agent begrenzt Verlust UND Gewinn in einem 12-h-Fenster
        (`MAX_LOSS_USD/PERCENT 25/5`, `MAX_GAIN_USD/PERCENT 25/5`). Freqtrade
        kennt dafuer zwei eingebaute Waechter:

        * `StoplossGuard` - sperrt nach mehreren gerissenen Stops. Aus dem
          12-h-Fenster werden 12 Kerzen (1h). `trade_limit 2` ist die
          Uebertragung der Verlustgrenze: zwei volle Stops in 12 h sind rund
          das Doppelte des erlaubten Verlusts.
        * `MaxDrawdown` - sperrt bei `max_allowed_drawdown 0.05`, also genau
          `MAX_LOSS_PERCENT 5`. Rueckblick 72 Kerzen (3 Tage), damit ein
          langsames Abrutschen nicht durch das kurze Fenster faellt.

        Wichtig: die Schutzschicht sperrt NEUE Einstiege - sie schliesst nie
        eine laufende Position. Genau wie das Original.
        """
        return [
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 12,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": False,
                "only_per_side": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 72,
                "trade_limit": 5,
                "max_allowed_drawdown": 0.05,
                "stop_duration_candles": 24,
            },
        ]