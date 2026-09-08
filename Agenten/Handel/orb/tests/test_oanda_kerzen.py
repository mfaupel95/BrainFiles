import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import oanda

FIX = Path(__file__).resolve().parent / "fixtures"


class TestKerzen(unittest.TestCase):
    def setUp(self):
        self.seiten = [json.loads((FIX / "candles_seite1.json").read_text()),
                       json.loads((FIX / "candles_seite2.json").read_text())]
        self.aufrufe = []

        def fake(url, *, method="GET", body=None):
            self.aufrufe.append(url)
            return self.seiten[len(self.aufrufe) - 1] if len(self.aufrufe) <= 2 else {"candles": []}

        self._alt = oanda._roh_json
        oanda._roh_json = fake
        oanda.token = lambda: "tok"

    def tearDown(self):
        oanda._roh_json = self._alt

    def test_paginiert_und_entfernt_unvollstaendige(self):
        k = oanda.kerzen("DE30_EUR",
                         von=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
                         bis=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc))
        zeiten = [c["zeit"] for c in k]
        # 07:00, 07:15, 07:30, 07:45 - die 08:00 (complete:false) ist raus
        self.assertEqual(len(k), 4)
        self.assertEqual(zeiten, sorted(zeiten))
        self.assertEqual(len(set(zeiten)), 4)  # 07:30 nicht doppelt
        self.assertTrue(all(c["complete"] for c in k))
        self.assertIsInstance(k[0]["o"], float)
        self.assertGreaterEqual(len(self.aufrufe), 2)  # hat paginiert

    def test_cache_wird_geschrieben_und_gelesen(self):
        cache = FIX.parent / "_tmp_cache"
        cache.mkdir(exist_ok=True)
        for f in cache.glob("*.json"):
            f.unlink()
        args = dict(von=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
                    bis=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc),
                    cache_dir=cache)
        oanda.kerzen("DE30_EUR", **args)
        vorher = len(self.aufrufe)
        oanda.kerzen("DE30_EUR", **args)          # zweiter Lauf: aus dem Cache
        self.assertEqual(len(self.aufrufe), vorher)  # kein weiterer Netzaufruf
