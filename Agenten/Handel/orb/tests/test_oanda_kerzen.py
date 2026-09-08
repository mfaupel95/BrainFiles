import json
import unittest
import urllib.parse
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


class TestKerzenLuecke(unittest.TestCase):
    """Zwei disjunkte Abrufe duerfen die Luecke dazwischen NICHT als abgedeckt
    markieren - ein spaeterer Abruf in die Luecke muss ins Netz gehen."""

    def setUp(self):
        laden = lambda name: json.loads((FIX / name).read_text())
        self.nach_von = {
            "2025-07-15T07:00:00Z": laden("candles_bereichA.json"),
            "2025-07-15T08:30:00Z": laden("candles_bereichB.json"),
            "2025-07-15T07:45:00Z": laden("candles_luecke.json"),
        }
        self.aufrufe = []

        def fake(url, *, method="GET", body=None):
            self.aufrufe.append(url)
            frm = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["from"][0]
            return self.nach_von.get(frm, {"candles": []})

        self._alt = oanda._roh_json
        oanda._roh_json = fake
        oanda.token = lambda: "tok"
        self.cache = FIX.parent / "_tmp_cache"
        self.cache.mkdir(exist_ok=True)
        for p in self.cache.glob("*.json"):
            p.unlink()

    def tearDown(self):
        oanda._roh_json = self._alt
        for p in self.cache.glob("*.json"):
            p.unlink()

    def _hol(self, h0, m0, h1, m1):
        return oanda.kerzen(
            "DE30_EUR",
            von=datetime(2025, 7, 15, h0, m0, tzinfo=timezone.utc),
            bis=datetime(2025, 7, 15, h1, m1, tzinfo=timezone.utc),
            cache_dir=self.cache)

    def test_luecke_zwischen_disjunkten_abrufen_wird_nachgeholt(self):
        self._hol(7, 0, 7, 30)     # Bereich A  -> [07:00, 07:30)
        self._hol(8, 30, 9, 0)     # Bereich B  -> [08:30, 09:00), disjunkt zu A
        vorher = len(self.aufrufe)
        k = self._hol(7, 45, 8, 15)  # faellt in die Luecke zwischen A und B
        self.assertGreater(len(self.aufrufe), vorher)  # hat nachgeholt, nicht faelschlich uebersprungen
        self.assertEqual([c["zeit"] for c in k], [
            datetime(2025, 7, 15, 7, 45, tzinfo=timezone.utc),
            datetime(2025, 7, 15, 8, 0, tzinfo=timezone.utc)])

    def test_echte_teilmenge_eines_abrufs_bleibt_ohne_netz(self):
        self._hol(7, 0, 7, 30)     # holt [07:00, 07:30)
        vorher = len(self.aufrufe)
        k = self._hol(7, 0, 7, 15)   # echte Teilmenge -> kein weiterer Netzaufruf
        self.assertEqual(len(self.aufrufe), vorher)
        self.assertEqual([c["zeit"] for c in k],
                         [datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc)])
