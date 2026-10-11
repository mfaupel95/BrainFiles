"""Phase B: HausSpurKlassikDonchianTrend (vektorisiert) gegen den Adapter A.

Die B-Fassung darf klassik-donchian-trend erst ersetzen, wenn Einstieg UND
Ausstieg Kerze fuer Kerze mit hausspur_regeln.signale uebereinstimmen
(gleichheit.vergleiche). Geprueft ab Kerze fenster-1 (=399): davor ist das
Haus-Fenster nicht voll, und Freqtrade handelt dort nie (startup 600).

Laeuft nur mit freqtrade (Container), wie test_hausspur.py:
  docker run --rm -v <Agenten/Handel>:/agenten/Handel:ro -v <Agenten/Bus>:/agenten/Bus:ro
      [-v <user_data/data>:/daten:ro -e HAUS_DATEN=/daten]
      --entrypoint python freqtradeorg/freqtrade:stable
      /agenten/Handel/freqtrade/tests/test_b_donchian_trend.py
Mit HAUS_DATEN werden zusaetzlich echte 4h-Futures-Kerzen (BTC/ETH/SOL) verglichen.
"""

import math
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HANDEL = Path(__file__).resolve().parents[2]
for _p in (HANDEL / "freqtrade" / "user_data" / "strategies", HANDEL / "freqtrade"):
    sys.path.append(str(_p))

try:
    import freqtrade  # noqa: F401  - nur DAS darf zum Ueberspringen fuehren
except ImportError as e:                                       # Host ohne freqtrade
    if __name__ == "__main__":
        print("OK (uebersprungen: freqtrade fehlt - %s)" % e)
        sys.exit(0)
    raise unittest.SkipTest("freqtrade fehlt: %s" % e)

import numpy as np                                             # noqa: E402
import pandas as pd                                            # noqa: E402
from HausSpurKlassikDonchianTrend import (                     # noqa: E402
    HausSpurKlassikDonchianTrend, ema_im_fenster)

sys.path.append(str(HANDEL))
import gleichheit                                              # noqa: E402
import hausspur_regeln as hr                                   # noqa: E402
import klassik_regeln as kr                                    # noqa: E402

NAME = "klassik_donchian_trend"
PAAR = "BTC/USDT:USDT"


def zufallsreihe(n=1400, saat=7):
    """Trendphasen mit Rauschen - erzeugt Ausbrueche in beide Richtungen."""
    rng = np.random.default_rng(saat)
    c, k = 100.0, []
    drift = 0.0
    for i in range(n):
        if i % 150 == 0:
            drift = rng.normal(0, 0.004)
        o = c
        c = max(1.0, c * (1 + drift + rng.normal(0, 0.01)))
        h, l = max(o, c) * (1 + abs(rng.normal(0, 0.004))), min(o, c) * (1 - abs(rng.normal(0, 0.004)))
        k.append([1_700_000_000_000 + i * 14_400_000, o, h, l, c, 1000.0])
    return k


def rahmen(k):
    return pd.DataFrame({
        "date": pd.to_datetime([z[0] for z in k], unit="ms", utc=True),
        "open": [z[1] for z in k], "high": [z[2] for z in k],
        "low": [z[3] for z in k], "close": [z[4] for z in k],
        "volume": [z[5] for z in k]})


def strategie():
    s = HausSpurKlassikDonchianTrend({"hausspur": {"name": NAME, "pfad": str(HANDEL)},
                                      "timeframe": "4h", "stake_currency": "USDT",
                                      "dry_run": True})
    s.dp = SimpleNamespace(runmode=SimpleNamespace(value="backtest"))
    s.bot_start()
    return s


def b_spalten(k):
    df = strategie().populate_indicators(rahmen(k), {"pair": PAAR})
    ein = [None if (v is None or v != v) else v for v in df["hs_ein"]]
    return df, ein


class EmaImFenster(unittest.TestCase):
    def test_gleich_haus_ema_am_fensterende(self):
        x = [z[4] for z in zufallsreihe(700)]
        v0 = ema_im_fenster(np.array(x), 200, 400, 0)
        v20 = ema_im_fenster(np.array(x), 200, 400, 20)
        for i in (399, 450, 699):
            e = kr.ema(x[i - 399:i + 1], 200)
            self.assertTrue(math.isclose(v0[i], e[-1], rel_tol=1e-12), i)
            self.assertTrue(math.isclose(v20[i], e[-21], rel_tol=1e-12), i)
        self.assertTrue(np.isnan(v0[398]))


class Gleichheit(unittest.TestCase):
    def _pruefe(self, k):
        ab = hr.fenster(hr.wachen(NAME)) - 1
        df, ein = b_spalten(k)
        self.assertEqual(gleichheit.vergleiche(k, NAME, ein, ab=ab), [])
        a = hr.signale(k, NAME, paar=PAAR, ab=ab)
        for i in range(ab, len(k)):
            self.assertEqual(bool(df["hs_aus_long"].iloc[i]), bool(a[i]["aus_long"]), i)
            self.assertEqual(bool(df["hs_aus_short"].iloc[i]), bool(a[i]["aus_short"]), i)
            self.assertEqual(df["hs_stop"].iloc[i], a[i]["stop"], i)
            self.assertEqual(df["hs_ziel"].iloc[i], a[i]["ziel"], i)
        return ein[ab:]

    def test_synthetische_reihen(self):
        longs = 0
        for saat in (1, 7, 42):
            longs += self._pruefe(zufallsreihe(1400, saat)).count("long")
        self.assertGreater(longs, 5)          # der Test sieht echte Einstiege

    @unittest.skipUnless(os.environ.get("HAUS_DATEN"), "HAUS_DATEN nicht gesetzt")
    def test_echte_kerzen(self):
        import pyarrow.feather as fe
        for basis in ("BTC", "ETH", "SOL"):
            t = fe.read_table(Path(os.environ["HAUS_DATEN"]) / "binance" / "futures"
                              / f"{basis}_USDT_USDT-4h-futures.feather").to_pandas()
            k = [[int(d.timestamp() * 1000), o, h, l, c, v] for d, o, h, l, c, v in zip(
                t.date, t.open, t.high, t.low, t.close, t.volume)]
            with self.subTest(basis=basis):
                self._pruefe(k)


class OptVorgabe(unittest.TestCase):
    def test_opt_ohne_parameterdatei_gleich_b(self):
        """HausSpurDonchianTrendOpt mit Vorgaben = B-Fassung (Spalten erst im Entry)."""
        from HausSpurDonchianTrendOpt import HausSpurDonchianTrendOpt
        k = zufallsreihe(1400, 7)
        df_b, _ = b_spalten(k)
        s = HausSpurDonchianTrendOpt({"hausspur": {"name": NAME, "pfad": str(HANDEL)},
                                      "timeframe": "4h", "stake_currency": "USDT",
                                      "dry_run": True})
        s.dp = SimpleNamespace(runmode=SimpleNamespace(value="backtest"))
        s.bot_start()
        df = s.populate_indicators(rahmen(k), {"pair": PAAR})
        self.assertNotIn("hs_ein", df.columns)
        df = s.populate_exit_trend(s.populate_entry_trend(df, {"pair": PAAR}), {"pair": PAAR})
        for spalte in ("hs_ein", "hs_aus_long", "hs_aus_short", "hs_stop", "hs_ziel"):
            pd.testing.assert_series_equal(df[spalte], df_b[spalte], check_names=False)
        self.assertEqual(s._signalwerte(PAAR, None), (5.0, 10.0))


if __name__ == "__main__":
    unittest.main()
