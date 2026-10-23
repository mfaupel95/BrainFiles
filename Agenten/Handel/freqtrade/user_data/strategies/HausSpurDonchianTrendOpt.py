# pragma pylint: disable=missing-docstring, invalid-name
# flake8: noqa: F401
# isort: skip_file
"""HausSpurDonchianTrendOpt - klassik_donchian_trend mit Hyperopt-Raeumen.

Nur fuer Hyperopt/Walk-Forward (freqtrade/walkforward.py), nie als Bot. Die
Vorgaben der Parameter sind die Haus-Wachen; ohne Parameterdatei rechnet die
Klasse also genau wie HausSpurKlassikDonchianTrend (Test test_b_donchian_trend).

Hyperopt ruft populate_indicators EINMAL je Lauf, populate_entry_trend je
Epoche - deshalb entstehen alle parameterabhaengigen Spalten erst dort.
Das Haus-Fenster bleibt 400 Kerzen; trend_n + steigung_n <= 340 passt hinein.
"""

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

from HausSpurKlassikDonchianTrend import HausSpurKlassikDonchianTrend, donchian_spalten

OHNE_ZIEL = 1000.0


class HausSpurDonchianTrendOpt(HausSpurKlassikDonchianTrend):
    kanal_ein_n = IntParameter(10, 60, default=20, space="buy")
    trend_n = IntParameter(100, 300, default=200, space="buy")
    steigung_n = IntParameter(5, 40, default=20, space="buy")
    kanal_aus_n = IntParameter(5, 30, default=10, space="sell")
    stop_prozent = DecimalParameter(2.0, 10.0, default=5.0, decimals=1, space="sell")

    def _r(self):
        return float(self.hs_wachen.get("ziel_r_vielfaches") or 2.0)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        w = self.hs_wachen
        stop = float(self.stop_prozent.value)
        donchian_spalten(
            dataframe, self.hr.fenster(w),
            n_ein=self.kanal_ein_n.value, n_aus=self.kanal_aus_n.value,
            trend_n=self.trend_n.value, steigung=self.steigung_n.value,
            nur_long=bool(w.get("nur_long")), aus_ok=bool(w.get("ausstieg_bei_regel", True)),
            stop=stop, ziel=(self._r() * stop
                             if w.get("festes_ziel", True)
                             else OHNE_ZIEL))
        return super().populate_entry_trend(dataframe, metadata)

    def _signalwerte(self, pair, trade):
        # Je Epoche fest - nicht aus custom_data, sonst erbte ein Trade den
        # Stop einer frueheren Epoche.
        stop = float(self.stop_prozent.value)
        return stop, self._r() * stop
