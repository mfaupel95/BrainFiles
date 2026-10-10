"""Strategie HausSpur selbst - laeuft nur, wo freqtrade installiert ist (Container).

Review I4 (10.10.2026): vorher war nur der Quelltext geprueft. Hier laufen
bot_start, populate_indicators, Stop/Ziel und custom_roi gegen hausspur_regeln.

Aufruf im Container (Haus nur lesend):
  docker run --rm -v <Agenten/Handel>:/agenten/Handel:ro -v <Agenten/Bus>:/agenten/Bus:ro
      --entrypoint python freqtradeorg/freqtrade:stable
      /agenten/Handel/freqtrade/tests/test_hausspur.py
Ohne freqtrade (Host-venv) werden alle Faelle uebersprungen.
"""

import sys
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

HANDEL = Path(__file__).resolve().parents[2]
# Pfade nur ANHAENGEN: Handel/freqtrade/ waere vorne ein Namespace-Paket
# "freqtrade" und verdeckte das echte (Review M8).
for _p in (HANDEL / "freqtrade" / "user_data" / "strategies", HANDEL / "tests"):
    sys.path.append(str(_p))

try:
    import pandas as pd
    from freqtrade.exceptions import OperationalException
    from freqtrade.strategy import IStrategy
    from HausSpur import HausSpur
except ImportError as e:                                       # Host ohne freqtrade
    if __name__ == "__main__":
        print("OK (uebersprungen: freqtrade fehlt - %s)" % e)
        sys.exit(0)
    raise unittest.SkipTest("freqtrade fehlt: %s" % e)

sys.path.append(str(HANDEL))

import hausspur_regeln as hr                                   # noqa: E402
from test_hausspur_regeln import reihe                         # noqa: E402

PAAR = "BTC/USDT:USDT"


def rahmen(n=700):
    k = reihe(n)
    return k, pd.DataFrame({
        "date": pd.to_datetime([z[0] for z in k], unit="ms", utc=True),
        "open": [z[1] for z in k], "high": [z[2] for z in k],
        "low": [z[3] for z in k], "close": [z[4] for z in k],
        "volume": [z[5] for z in k]})


def strategie(name="klassik_ema", pfad=None, runmode="backtest", df=None):
    s = HausSpur({"hausspur": {"name": name, "pfad": str(pfad or HANDEL)},
                  "timeframe": "1h", "stake_currency": "USDT", "dry_run": True})
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value=runmode),
                           get_analyzed_dataframe=lambda pair, tf: (df, None))
    s.bot_start()
    return s


class Handel:
    """Attrappe eines Trades mit custom_data."""

    def __init__(self, open_date):
        self.open_date_utc = open_date
        self.is_short = False
        self.leverage = 1.0
        self.daten = {}

    def get_custom_data(self, k):
        return self.daten.get(k)

    def set_custom_data(self, k, v):
        self.daten[k] = v


class Laden(unittest.TestCase):
    def test_mount_fehlt_nennt_grund(self):
        with self.assertRaises(OperationalException) as cm:
            strategie(pfad="/gibtsnicht")
        self.assertIn("fehlt", str(cm.exception))

    def test_falscher_name_nennt_namen(self):
        with self.assertRaises(OperationalException) as cm:
            strategie(name="gibtsnicht")
        self.assertIn("gibtsnicht", str(cm.exception))


class Pfad(unittest.TestCase):
    def test_haus_verdeckt_freqtrade_nicht(self):
        """Review M8: bot_start darf Handel/ nicht VOR die site-packages stellen."""
        # macd_mtf: dessen handeln.py stellt Handel/ beim Import selbst nach
        # vorne (Haus-Code). Danach muss freqtrade weiter das echte Paket sein
        # und ein noch nie geladenes Untermodul ladbar bleiben.
        import importlib
        strategie(name="macd_mtf")
        import freqtrade
        self.assertNotIn(str(HANDEL), str(getattr(freqtrade, "__file__", "") or ""))
        sys.modules.pop("freqtrade.optimize.hyperopt_tools", None)
        importlib.import_module("freqtrade.optimize.hyperopt_tools")


class Spalten(unittest.TestCase):
    def test_backtest_wie_signale(self):
        k, df = rahmen()
        s = strategie()
        df = s.populate_indicators(df, {"pair": PAAR})
        erwartet = [x["einstieg"] if x else None for x in hr.signale(k, "klassik_ema", paar=PAAR)]
        self.assertEqual([None if v != v else v for v in df["hs_ein"]], erwartet)
        df = s.populate_entry_trend(df, {"pair": PAAR})
        self.assertEqual(int(df["enter_long"].fillna(0).sum()), erwartet.count("long"))

    def test_dry_run_nur_letzte_kerzen(self):
        k, df = rahmen()
        s = strategie(runmode="dry_run")
        df = s.populate_indicators(df, {"pair": PAAR})
        self.assertTrue(df["hs_stop"].iloc[:-3].isna().all())
        erwartet = hr.signale(k, "klassik_ema", paar=PAAR, ab=len(k) - 3)
        self.assertEqual(list(df["hs_stop"].iloc[-3:]), [x["stop"] for x in erwartet[-3:]])


class StopUndZiel(unittest.TestCase):
    def test_ziel_ueber_custom_roi_nicht_custom_exit(self):
        """Review I3: ROI fuellt der Backtest zum Zielpreis, custom_exit erst zum Schluss."""
        self.assertTrue(HausSpur.use_custom_roi)
        self.assertIs(HausSpur.custom_exit, IStrategy.custom_exit)

    def test_custom_roi_ist_ziel_der_signalkerze(self):
        k, df = rahmen()
        s = strategie(df=None)
        df = s.populate_indicators(df, {"pair": PAAR})
        s.dp.get_analyzed_dataframe = lambda pair, tf: (df, None)
        i = len(df) - 2
        t = Handel(df["date"].iloc[i] + timedelta(minutes=1))
        roi = s.custom_roi(PAAR, t, df["date"].iloc[-1], 60, "klassik_ema", "long")
        self.assertAlmostEqual(roi, df["hs_ziel"].iloc[i] / 100.0)
        self.assertEqual(t.get_custom_data("hs_stop"), df["hs_stop"].iloc[i])

    def test_ohne_signalzeile_vorgabe_statt_absturz(self):
        """Review M1: Signalkerze ohne Werte (Altposition) -> Vorgabestop, kein TypeError."""
        _k, df = rahmen()
        s = strategie()
        df = s.populate_indicators(df, {"pair": PAAR})
        df["hs_stop"] = None
        df["hs_ziel"] = None
        s.dp.get_analyzed_dataframe = lambda pair, tf: (df, None)
        t = Handel(df["date"].iloc[-1])
        self.assertEqual(s._signalwerte(PAAR, t), (hr.STOP_VORGABE, 2 * hr.STOP_VORGABE))
        wert = s.custom_stoploss(PAAR, t, df["date"].iloc[-1], 100.0, 0.0, False)
        self.assertLess(wert, 0.99)                # nicht der Platzhalter -0.99


if __name__ == "__main__":
    unittest.main()
