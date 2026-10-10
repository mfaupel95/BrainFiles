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

import json
import os

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy

import frequenzbremse


class MoonDevBasis(IStrategy):
    """Basis fuer die kerzenfaehigen Moon-Dev-Agenten (nur Long, Spot)."""

    INTERFACE_VERSION = 3

    # Spot: kurze Seite braucht Futures (siehe Modul-Docstring).
    can_short: bool = False

    timeframe = "1h"

    # --- Frequenzbremse (T-197, 01.10.2026) -----------------------------------
    # Der erste Backtest war nicht wegen der Richtung negativ, sondern wegen der
    # ZAHL der Trades (3,23/Tag = ueber 240 % Kosten im Jahr). Die Regeln und
    # ihre Herkunft stehen in `frequenzbremse.py`; hier stehen nur die
    # Schalter. Sie kommen aus der Bot-Konfiguration (`moondev:`-Block),
    # damit derselbe Code vorher/nachher fahrbar ist.
    bremse: bool = False
    bremse_einstellungen: dict = {}
    # Zaehler der abgelehnten Einstiege je Grund - der Beleg, dass die Bremse
    # greift (und nicht nur die Zahlen anders aussehen).
    bremse_zaehler: dict = {}

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
    # ENTSCHEIDUNG Max 08.10.2026: trading-agent und marktlage-regime laufen
    # mit signal_ausstieg=false (in config.trading-agent.json / config.marktlage-
    # regime.json gesetzt, Bots neu gestartet). Der Default hier bleibt True,
    # damit ein fehlender Config-Eintrag die Regel nicht still umstellt.
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

        # Frequenzbremse: Schalter und Grenzen aus dem `moondev`-Block der
        # Bot-Konfiguration. Fehlt der Block, gelten die Haus-Zahlen aus
        # frequenzbremse.STANDARD - der Backtest "vorher" setzt sie aus.
        md = config.get("moondev") or {}
        bremse_cfg = dict(md.get("bremse_einstellungen") or {})
        if md.get("bremse") is not None:
            bremse_cfg["bremse"] = bool(md["bremse"])
        self.bremse_einstellungen = frequenzbremse.grenzen(bremse_cfg)
        self.bremse = bool(self.bremse_einstellungen.get("bremse", True))

    # --- Frequenzbremse: Anbindung an Freqtrade ------------------------------
    def _handelsgeschichte(self) -> list:
        """Die abgeschlossenen Trades als reine Rechnung fuer frequenzbremse.

        Freqtrade fuehrt sie im Trade-Objekt; hier werden nur die Felder
        herausgezogen, die die Regel braucht. Kein Journal, keine Datei - im
        Backtest ist der Trade-Speicher die Wahrheit, live dieselbe Quelle.
        """
        from freqtrade.persistence import Trade

        runden = []
        for t in Trade.get_trades_proxy(is_open=False):
            runden.append({
                "paar": t.pair,
                "auf_zeit": t.open_date_utc or t.open_date,
                "zu_zeit": t.close_date_utc or t.close_date,
                "grund": t.exit_reason,
                "ergebnis_usd": t.close_profit_abs or 0.0,
                "einsatz_usd": t.stake_amount or 0.0,
            })
        return runden

    def _zaehler_schreiben(self) -> None:
        """Die Ablehnungsgruende ablegen - sonst ist die Bremse unsichtbar."""
        pfad = os.path.join(self.config.get("user_data_dir", "."),
                            "backtest_results",
                            "bremse-%s.json" % self.__class__.__name__)
        try:
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w", encoding="utf-8", newline="") as f:
                json.dump({"strategie": self.__class__.__name__,
                           "einstellungen": self.bremse_einstellungen,
                           "abgelehnt_je_grund": self.bremse_zaehler},
                          f, ensure_ascii=False, indent=1, sort_keys=True)
        except OSError:
            pass

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                            rate: float, time_in_force: str, current_time,
                            entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """Die Bremse: darf JETZT in DIESES Paar eingestiegen werden?

        Aufgerufen von Freqtrade unmittelbar vor dem Einstieg - im Backtest
        wie live. Ein `False` verhindert nur den Einstieg; es schliesst keine
        Position (dieselbe Grenze wie beim Haus-Vorfilter: er schliesst nie,
        er verhindert nur neue).
        """
        if not self.bremse:
            return True
        erlaubt, grund, regel = frequenzbremse.urteil(
            self._handelsgeschichte(), current_time, pair, self.bremse_einstellungen)
        if not erlaubt:
            self.bremse_zaehler[regel] = self.bremse_zaehler.get(regel, 0) + 1
            if sum(self.bremse_zaehler.values()) % 100 == 0:
                self._zaehler_schreiben()
        return erlaubt

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