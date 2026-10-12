# pragma pylint: disable=missing-docstring, invalid-name
# flake8: noqa: F401
# isort: skip_file
"""HausSpur - EINE Freqtrade-Strategie fuer alle Haus-Spuren.

Welche Spur, steht in der Bot-Konfiguration: `"hausspur": {"name": "klassik_ema",
"pfad": "/agenten/Handel"}`. Die Regel kommt aus Agenten/Handel/hausspur_regeln.py
(read-only gemountet, siehe bots.py mounts) - hier steht KEINE Regel, nur die
Uebersetzung DataFrame -> Kerzenliste -> Spalten. Spec:
Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md.

Stop und Ziel je Trade kommen aus der Signalkerze (Spalten hs_stop, hs_ziel):
fester Prozentsatz der Spur, ATR-Stop der Indikatorspuren, Range bei ORB.
"""

import sys
from pathlib import Path

from pandas import DataFrame, isna

from freqtrade.exceptions import OperationalException
from freqtrade.strategy import IStrategy, stoploss_from_open


class HausSpur(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "1h"                 # die Bot-Konfiguration setzt den echten
    stoploss = -0.99                 # echter Stop in custom_stoploss
    use_custom_stoploss = True
    minimal_roi = {"0": 100.0}       # echtes Ziel in custom_roi
    # custom_roi statt custom_exit (Review I3): ROI-Ausstiege fuellt der
    # Backtest zum Zielpreis wie das Haus; custom_exit erst zum Kerzenschluss
    # (gemessen: +6,08 % statt Ziel 5,0 % bei klassik_ema).
    use_custom_roi = True
    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True
    startup_candle_count = 600       # groesstes Haus-Fenster (macd_mtf)

    def bot_start(self, **kwargs) -> None:
        hs = self.config.get("hausspur") or {}
        name = hs.get("name")
        pfad = Path(hs.get("pfad", "/agenten/Handel"))
        if not (pfad / "hausspur_regeln.py").exists():
            raise OperationalException(
                f"HausSpur: {pfad}/hausspur_regeln.py fehlt - Mount von Agenten/ "
                f"nach /agenten (bots.py mounts) fehlt?")
        # ANHAENGEN, nicht vorne einfuegen (Review M8): Handel/freqtrade/ waere
        # sonst ein Namespace-Paket "freqtrade" vor dem echten.
        # Neue Prozesse (Hyperopt-Worker per forkserver) erben sys.path, laden
        # freqtrade aber frisch: ohne den echten Paketordner im Pfad gewinnt
        # dort der Namespace Handel/freqtrade (gemessen 11.10.2026). Ein
        # regulaeres Paket schlaegt einen Namespace an jeder Pfadposition.
        import freqtrade
        wurzel = str(Path(freqtrade.__file__).resolve().parents[1])
        for eintrag in (wurzel, str(pfad)):
            if eintrag not in sys.path:
                sys.path.append(eintrag)
        import hausspur_regeln as hr
        try:
            hr.spur(name)
        except KeyError as e:
            raise OperationalException(f"HausSpur: {e}") from e
        self.hr = hr
        self.hs_name = name
        self.hs_wachen = hr.wachen(name)
        self.nachrechnen = int(hs.get("nachrechnen", 3))

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        kerzen = [[int(d.timestamp() * 1000), o, h, l, c, v] for d, o, h, l, c, v in zip(
            dataframe["date"], dataframe["open"], dataframe["high"],
            dataframe["low"], dataframe["close"], dataframe["volume"])]
        laufend = self.dp.runmode.value in ("live", "dry_run")
        ab = max(0, len(kerzen) - self.nachrechnen) if laufend else 0
        werte = self.hr.signale(kerzen, self.hs_name, self.hs_wachen,
                                paar=metadata["pair"], ab=ab)
        dataframe["hs_ein"] = [x["einstieg"] if x else None for x in werte]
        dataframe["hs_aus_long"] = [bool(x and x["aus_long"]) for x in werte]
        dataframe["hs_aus_short"] = [bool(x and x["aus_short"]) for x in werte]
        dataframe["hs_stop"] = [x["stop"] if x else None for x in werte]
        dataframe["hs_ziel"] = [x["ziel"] if x else None for x in werte]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["hs_ein"] == "long", ["enter_long", "enter_tag"]] = (1, self.hs_name)
        dataframe.loc[dataframe["hs_ein"] == "short", ["enter_short", "enter_tag"]] = (1, self.hs_name)
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Review M5: Freqtrade nimmt keinen Einstieg, wenn in derselben Kerze ein
        # Ausstieg derselben Seite steht - und keinen Ausstieg, wenn ein Einstieg
        # steht. Das Haus steigt flach ein und offen aus. Darum hier nur der
        # konfliktfreie Ausstieg; den Konfliktfall loest custom_exit fuer offene
        # Trades (_konflikt_ausstieg).
        dataframe.loc[dataframe["hs_aus_long"] & (dataframe["hs_ein"] != "long"),
                      "exit_long"] = 1
        dataframe.loc[dataframe["hs_aus_short"] & (dataframe["hs_ein"] != "short"),
                      "exit_short"] = 1
        return dataframe

    def _konflikt_ausstieg(self, pair, trade):
        """Ausstieg eines offenen Trades in einer Kerze mit Ein- und Ausstieg (M5).

        Nur fuer Trades, die schon zu Beginn dieser Kerze offen waren - ein
        Trade, der erst auf genau dieses Einstiegssignal hin eroeffnet wurde,
        bleibt (im Haus war man da flach)."""
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or not len(df):
            return None
        zeile = df.iloc[-1]
        seite = "short" if trade.is_short else "long"
        if zeile["hs_ein"] != seite or not bool(zeile["hs_aus_" + seite]):
            return None
        if trade.open_date_utc > zeile["date"]:
            return None
        return "hs_aus_" + seite

    def _signalwerte(self, pair, trade):
        """(stop %, ziel %) der Signalkerze, einmal je Trade gemerkt."""
        stop = trade.get_custom_data("hs_stop")
        ziel = trade.get_custom_data("hs_ziel")
        if stop is not None and ziel is not None:
            return float(stop), float(ziel)
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        vorher = df[df["date"] < trade.open_date_utc]
        zeile = vorher.iloc[-1] if len(vorher) else None
        # isna statt x == x (Review M1): eine reine None-Spalte ist object-dtype,
        # float(None) wuerde werfen und die Position bliebe beim Platzhalter -0.99.
        stop = self.hr.STOP_VORGABE
        if zeile is not None and not isna(zeile["hs_stop"]):
            stop = float(zeile["hs_stop"])
        ziel = 2.0 * stop
        if zeile is not None and not isna(zeile["hs_ziel"]):
            ziel = float(zeile["hs_ziel"])
        trade.set_custom_data("hs_stop", stop)
        trade.set_custom_data("hs_ziel", ziel)
        return stop, ziel

    def _auf_schluss(self):
        """Variante `hausspur.ausloesung: "schluss"` (Messung 11.10.2026):
        Stop und Ziel loesen wie im Haus (T-202) nur auf dem Kerzenschluss aus,
        nicht schon, wenn ein Docht sie streift. Vorgabe bleibt "docht" -
        die strengere Fassung, die ein echter Stop an der Boerse auch hat."""
        return (self.config.get("hausspur") or {}).get("ausloesung") == "schluss"

    def custom_exit(self, pair, trade, current_time, current_rate,
                    current_profit, **kwargs):
        grund = self._konflikt_ausstieg(pair, trade)
        if grund or not self._auf_schluss():
            return grund
        stop, ziel = self._signalwerte(pair, trade)
        if current_profit <= -stop / 100.0:
            return "stop_schluss"
        if current_profit >= ziel / 100.0:
            return "ziel_schluss"
        return None

    def custom_stoploss(self, pair, trade, current_time, current_rate,
                        current_profit, after_fill, **kwargs):
        if self._auf_schluss():
            return -0.99              # Notbremse; der echte Stop sitzt in custom_exit
        stop, _ = self._signalwerte(pair, trade)
        return stoploss_from_open(-stop / 100.0, current_profit,
                                  is_short=trade.is_short, leverage=trade.leverage)

    def custom_roi(self, pair, trade, current_time, trade_duration, entry_tag,
                   side, **kwargs):
        if self._auf_schluss():
            return None
        _, ziel = self._signalwerte(pair, trade)
        return ziel / 100.0

    def leverage(self, pair, current_time, current_rate, proposed_leverage,
                 max_leverage, entry_tag, side, **kwargs) -> float:
        return 1.0

    # --- Schutzschicht wie moondev_basis.protections() ------------------------
    @property
    def protections(self):
        """Wortgleich aus moondev_basis.py (risk_agent als Freqtrade-Schutzschicht).

        Sperrt NEUE Einstiege nach zwei gerissenen Stops in 12 Kerzen oder bei
        5 % Ruecklauf in 72 Kerzen - schliesst nie eine laufende Position.
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
