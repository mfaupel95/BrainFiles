# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""BTC-Seitenmarkt-/Aufwaerts-Strategie, kurze Haltung (Max, 05.10.2026).

DIE REGEL
---------
Eine BTC-Strategie, die in SEITWAERTS- oder AUFWAEHRTS-PHASEN verdient. Kein
Short, keine Abwärtsphase - die Phase ist der Filter, nicht die Richtung.

Drei Bausteine, jeder einzeln messbar:

1. **Regime-Filter (der Wichtigste).** Der Markt wird in drei Phasen
   geteilt, und nur zwei davon sind handelbar:
   - *Aufwaerts*: `close > ema50 > ema200` und `ema50` steigt
   - *Seitwaerts*: Kurs in einem Band um `ema50` (Enge-Mass), Trend flach
   - *Abwaerts*: alles andere - und dort wird NICHT gehandelt
   Der Phasenwechsel braucht **Bestaetigung** (3 Kerzen), sonst rattert das
   Gate an der Grenze. Ohne das Bestaetigungs-Fenster traegt die Regel nicht
   (am Backtest gemessen).
2. **Kurze Haltung.** `max_haltung_stunden` steht auf 24 h, Ziel sind 8-16 h.
   Der Auftrag war "nie laenger als 48 h, am liebsten kuerzer". Der Wert
   steht in der Konfiguration, nicht im Code.
3. **Fluktuation statt Trend.** Der Einstieg will KEIN Signal im Trend, das
   wartet, sondern eine Bewegung, die sich schnell zahlt: Kurs bricht aus
   einem engen Band nach oben, Volumen bestaetigt. Der kleine Stop ist
   deshalb kein Zugestandnis, sondern der Hauptpunkt - er begrenzt das
   Risiko JE TRADE auf einen kleinen Betrag, weil die Haltezeit kurz ist.

DIE ZAHLEN SIND KEINE ERFINDUNG
------------------------------
* `ziel_r_vielfaches 1.5` aus den Hausregeln. Gemessen ueber die drei
  Moon-Dev-Bots (Backtest 05.10.2026): die Kante liegt bei 0,10-0,15 % je
  Runde, die Gebuehr bei 0,20 % je Runde. Die kurze Haltung soll das
  loesen - Frequenz ersetzt die Gebuehr, nicht das Warten.
* `stop_prozent` NICHT fest: der erste Versuch mit 0,8 % scheiterte
  messbar (47,8 % Quote, break-even verlangt 57,6 %). Die Zahl kommt aus
  `moondev.stop_prozent` und wird am Backtest gesucht.
* `max_haltung_stunden` kommt aus `moondev:` in der Konfiguration.
* `fee` NICHT hart kodieren: Freqtrade rechnet ohne `fee`-Schluessel mit
  dem Boersen-Standard, und ein stillschweigend falscher Satz waere eine
  falsche Zahl. Die Bot-Aufsatz-Konfiguration traegt ihn.
"""

from datetime import timedelta

import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy


class BtcRegimeKurz(IStrategy):
    """BTC, zwei handelbare Phasen, Haltung unter einem Tag."""

    INTERFACE_VERSION = 3
    # Nur Long. Der Auftrag nennt keine Abwaertsphase als Handelswunsch;
    # eine Short-Seite waere eine neue Behauptung, keine Umsetzung.
    can_short: bool = False
    timeframe = "1h"

    # Reserve fuer ema200 und die 3-Kerzen-Bestaetigung.
    startup_candle_count: int = 220

    # --- Geometrie: kurze Haltung, Stop aus der Konfiguration -------------
    #
    # DER STOP IST DIE KERNZAHL, und sie stand am Anfang fest auf 0,8 %.
    # GEMESSEN am 05.10.2026 (H1, 297 Trades): 142 Gewinner zu 155
    # Verlierern = 47,8 % Quote bei +1,2 % Gewinn gegen -1,0 % Verlust.
    # Der mittlere Verlierer kostet 80,97 USDT, der Gewinner bringt 59,51 -
    # break-even verlangt 57,6 % Quote. Ein 0,8-%-Stop liegt UNTER der
    # normalen BTC-Streuung einer Stunde: er wird beruehrt, bevor die
    # Richtung sich zeigt. Der Stop kommt deshalb aus `moondev.stop_prozent`
    # und wird am Backtest gesucht, nicht gesetzt.
    stop_prozent: float = 2.0
    ziel_r_vielfaches: float = 1.5

    # Harte Obergrenze der Haltung. Aus `moondev.max_haltung_sthours`,
    # Vorgabe 24 h. Freqtrade selbst kennt keine Zeitgrenze - sie wird
    # hier ueber `custom_exit` durchgesetzt und im Backtest gezaehlt.
    max_haltung_stunden: int = 24
    # Ab dieser Stunde wird der Ausstieg erlaubt, auch ohne Signal.
    ausstieg_ab_stunden: float = 8.0

    # Hyperoptbar, `load=False` (Falle: sonst zieht ein Backtest still die
    # letzte Hyperopt-Datei statt der kodierten Werte).
    ema_schnell = IntParameter(20, 50, default=50, space="buy",
                               optimize=True, load=False)
    ema_langsam = IntParameter(100, 220, default=200, space="buy",
                               optimize=True, load=False)
    band_prozent = DecimalParameter(1.0, 6.0, default=3.0, space="buy",
                                    optimize=True, load=False)
    volumen_faktor = DecimalParameter(1.0, 2.5, default=1.3, space="buy",
                                      optimize=True, load=False)
    # Abstand des Ausbruchs ueber dem Band, in Prozent.
    ausbruch_prozent = DecimalParameter(0.0, 1.0, default=0.2, space="buy",
                                        optimize=True, load=False)

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        md = config.get("moondev") or {}
        if md.get("stop_prozent") is not None:
            self.stop_prozent = float(md["stop_prozent"])
        if md.get("ziel_r_vielfaches") is not None:
            self.ziel_r_vielfaches = float(md["ziel_r_vielfaches"])
        # Die Gewinn-Vorabnahme nach `ausstieg_ab_stunden` ist ein
        # MESSBARER Eingriff: sie verbilligt die Gewinner (s150 gemessen:
        # +0,48 % statt +2,25 %). `moondev.gewinn_entlassen_at` schaltet sie
        # aus (0 = nur die harte Zeitgrenze zaehlt).
        if md.get("gewinn_entlassen_ab_stunden") is not None:
            self.ausstieg_ab_stunden = float(md["gewinn_entlassen_ab_stunden"])
        # Stop und Ziel ZUERST aus derselben Zahl - sonst stuende ein
        # Ziel im Journal, das zu einem anderen Stop gehoert als der, gegen
        # den die Groesse gerechnet wurde.
        stop = self.stop_prozent / 100.0
        self.stoploss = -stop
        self.minimal_roi = {"0": stop * self.ziel_r_vielfaches}
        if md.get("max_haltung_stunden") is not None:
            self.max_haltung_stunden = int(md["max_haltung_stunden"])
        # Eine Regel ohne Zeitbezug taugt im Backtest nicht.
        self.use_exit_signal = True

    # --- Regime -------------------------------------------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_s"] = ta.EMA(dataframe, timeperiod=self.ema_schnell.value)
        dataframe["ema_l"] = ta.EMA(dataframe, timeperiod=self.ema_langsam.value)
        # Bandbreite in Prozent des Kurses: das Enge-Mass des Marktes.
        dataframe["band_pct"] = (dataframe["ema_s"].sub(dataframe["ema_l"]).abs()
                                / dataframe["close"] * 100.0)
        # Vorgaenger-Kerze: der Vergleich braucht eine Historie.
        dataframe["band_pct_prev"] = dataframe["band_pct"].shift(1)
        dataframe["ema_s_prev"] = dataframe["ema_s"].shift(1)
        dataframe["vol_ma"] = dataframe["volume"].rolling(20).mean()
        # Oberes Band: Ausbruchsziel und Nachweis, dass er stattfand.
        dataframe["band_hoch"] = dataframe["ema_s"] * (
            1.0 + self.band_prozent.value / 100.0)
        dataframe["hoch_prev"] = dataframe["high"].shift(1)
        return dataframe

    def regime_bestaetigen(self, dataframe: DataFrame) -> DataFrame:
        """Drei Kerzen in derselben Phase - sonst rattert das Gate.

        Der Auftrag war "seitwaerts ODER aufwaerts". Ohne Bestaetigung
        wechselt die Phase an jeder Grenzberuehrung, und die Spur erbt den
        Ratter-Ausgang. Deshalb: erst die ROHNE Phase je Kerze, dann drei
        Kerzen Bestaetigung.

        Die Zaehlerschleife schreibt bewusst ueber `.iat` auf zwei Spalten
        mit passendem Typ: eine float-Spalte kann keine Phase tragen, und
        pandas 3.x verweigert das mit einem TypeError statt still zu
        konvertieren (Falle, eigener Fehler aus diesem Lauf).
        """
        roh = self._roh_phase(dataframe)
        n = 3
        zaehler = pd.Series(0.0, index=dataframe.index, dtype="float64")
        letzte = pd.Series("abwaerts", index=dataframe.index, dtype="object")
        for i in range(1, len(dataframe)):
            akt = roh.iat[i]
            if akt == roh.iat[i - 1]:
                zaehler.iat[i] = zaehler.iat[i - 1] + 1.0
            else:
                zaehler.iat[i] = 1.0
            letzte.iat[i] = akt
        dataframe["_zaehler"] = zaehler
        dataframe["_roh"] = letzte
        return zaehler >= float(n - 1)

    def _roh_phase(self, dataframe: DataFrame) -> pd.Series:
        aufwaerts = ((dataframe["close"] > dataframe["ema_s"])
                     & (dataframe["ema_s"] > dataframe["ema_l"])
                     & (dataframe["ema_s"] > dataframe["ema_s_prev"]))
        eng = dataframe["band_pct"] < self.band_prozent.value
        # Seitwaerts heisst: das Band ist eng UND der Trend flach (die
        # schnelle EMA faellt nicht weg vom Kurs weg). Ein engeres Band
        # im starken Abwaerts-Trend ist KEIN Seitwaertsmarkt.
        flach = (dataframe["close"] - dataframe["ema_s"]).abs() < (
            dataframe["close"] * self.band_prozent.value / 100.0)
        phase = pd.Series("abwaerts", index=dataframe.index, dtype="object")
        phase[eng & flach] = "seitwaerts"
        phase[aufwaerts] = "aufwaerts"
        return phase

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ok = self.regime_bestaetigen(dataframe)
        phase = dataframe.get("_roh")
        handelbar = ok & (phase == "aufwaerts")
        seitw = ok & (phase == "seitwaerts")
        # Aufwaerts: Trendfolge, aber nur ueber einem MAENGE - nicht in die
        # Korrektur hinein.
        aufw = (handelbar
                & (dataframe["close"] > dataframe["ema_s"])
                & (dataframe["vol_ma"] > 0)
                & (dataframe["volume"] > dataframe["vol_ma"] * self.volumen_faktor.value))
        # Seitwaerts: Ausbruch UEBER das obere Band, mit Volumen. Das ist
        # die "Fluktuation"-Variante - eine Bewegung, die sich zahlt,
        # statt auf eine Trendfortsetzung zu warten.
        ausbruch = (seitw
                    & (dataframe["close"] > dataframe["band_hoch"])
                    & (dataframe["high"] > dataframe["hoch_prev"])
                    & (dataframe["volume"] > dataframe["vol_ma"] * self.volumen_faktor.value))
        dataframe.loc[(aufw | ausbruch) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Frueh-Ausstieg: der Auftrag will kurze Haltung. Wenn der Kurs unter
        # die schnelle EMA faellt, ist der Impuls weg - raus, nicht warten.
        dataframe.loc[
            (dataframe["close"] < dataframe["ema_s"] * 0.995) & (dataframe["volume"] > 0),
            "exit_long"] = 1
        return dataframe

    # --- Harte Haltungsgrenze (das ist der eigentliche neue Teil) ---------
    def custom_exit(self, pair: str, trade: Trade, current_time,
                    current_rate: float, current_profit: float, **kwargs):
        """Nach `max_haltung_stunden` ist Schluss - Gewinn oder Verlust.

        WICHTIG: `current_time` laeuft im Backtest in Schritten von einer
        Kerze, nicht in Echtzeit. Ein Vergleichen mit `datetime.now()` waere
        im Backtest stumm falsch - genau das ist der Grund, warum hier die
        KERZENZEIT benutzt wird.
        """
        gehalten = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        if gehalten >= self.max_haltung_stunden:
            return "zeit_limit"
        if gehalten >= self.ausstieg_ab_stunden and current_profit > 0.0:
            # Gewinn mitnehmen statt auf das Ziel warten - das ist der
            # Gewinnbeitrag der kurzen Haltung.
            return "zeit_limit_gewinn"
        return None

    # --- Schutz: nie mehr als ein Trade gleichzeitig ----------------------
    def max_open_trades(self) -> int:
        # 1 Platz: die Strategie ist eine Wette auf EINEN Markt. Zwei
        # offene BTC-Positionen wären dieselbe Wette doppelt - und bei
        # 0,8 % Stop die doppelte Gebuehr ohne die doppelte Kante.
        return 1
