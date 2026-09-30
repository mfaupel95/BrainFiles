"""kursdaten: Cache-Logik ohne Netz (yfinance wird nie aufgerufen)."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

try:
    import pandas as pd
except ImportError:                                            # pragma: no cover
    pd = None

import kursdaten as kd  # noqa: E402

CSV = "Datum,Open,High,Low,Close\n2026-09-28,1,2,0.5,1.5\n2026-09-29,1.5,2.5,1,2\n"


@unittest.skipIf(pd is None, "pandas fehlt")
class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(kd, "DATEN_DIR", Path(self.tmp.name))
        p.start()
        self.addCleanup(p.stop)
        self.pfad = kd.cache_pfad("pltr")

    def _cache(self, alter_h):
        self.pfad.write_text(CSV, encoding="utf-8")
        t = time.time() - alter_h * 3600
        os.utime(self.pfad, (t, t))

    def test_pfad_ist_grossgeschrieben(self):
        self.assertEqual(self.pfad.name, "PLTR.csv")

    def test_alter_ohne_datei_ist_none(self):
        self.assertIsNone(kd.cache_alter_stunden(self.pfad))

    def test_alter_in_stunden(self):
        self._cache(5)
        self.assertAlmostEqual(kd.cache_alter_stunden(self.pfad), 5, delta=0.1)

    def test_frischer_cache_braucht_kein_netz(self):
        self._cache(1)
        with mock.patch.object(kd, "_laden_vom_netz",
                               side_effect=AssertionError("Netz!")):
            df, quelle = kd.laden("pltr")
        self.assertEqual(len(df), 2)
        self.assertTrue(quelle.startswith("Cache"))

    def test_veralteter_cache_wird_erneuert(self):
        self._cache(kd.CACHE_MAX_STUNDEN + 1)
        neu = pd.DataFrame({"Open": [1.0], "High": [2.0], "Low": [0.5],
                            "Close": [1.5]},
                           index=pd.DatetimeIndex(["2026-09-30"], name="Datum"))
        with mock.patch.object(kd, "_laden_vom_netz", return_value=neu):
            df, quelle = kd.laden("pltr")
        self.assertEqual(quelle, "abgerufen")
        self.assertEqual(len(df), 1)
        self.assertEqual(len(pd.read_csv(self.pfad)), 1)     # Cache ueberschrieben

    def test_netzausfall_nutzt_alten_cache_und_sagt_es(self):
        self._cache(kd.CACHE_MAX_STUNDEN + 5)
        with mock.patch.object(kd, "_laden_vom_netz",
                               side_effect=RuntimeError("down")):
            df, quelle = kd.laden("pltr", still=True)
        self.assertEqual(len(df), 2)
        self.assertIn("Abruf fehlgeschlagen", quelle)

    def test_netzausfall_ohne_cache_wirft(self):
        with mock.patch.object(kd, "_laden_vom_netz",
                               side_effect=RuntimeError("down")):
            with self.assertRaises(RuntimeError):
                kd.laden("pltr", still=True)

    def test_erzwungene_aktualisierung_ignoriert_frischen_cache(self):
        self._cache(1)
        neu = pd.DataFrame({"Open": [9.0], "High": [9.0], "Low": [9.0],
                            "Close": [9.0]},
                           index=pd.DatetimeIndex(["2026-09-30"], name="Datum"))
        with mock.patch.object(kd, "_laden_vom_netz", return_value=neu) as netz:
            _, quelle = kd.laden("pltr", erzwinge_aktualisierung=True)
        netz.assert_called_once()
        self.assertEqual(quelle, "abgerufen")


if __name__ == "__main__":
    unittest.main()
