"""kraken_kerzen.py: dieselbe hole()/laden()-Form wie kerzen.py, aber ueber
kraken.kerzen() statt OKX history-candles."""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "kraken"))
import kraken_kerzen  # noqa: E402


def _reihen(n):
    return [[i * 86400000, 1.0 + i, 1.0 + i, 1.0 + i, 1.0 + i, 9.0]
            for i in range(n)]


class TestKrakenKerzen(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hole_schreibt_cache_und_liefert_kerzen(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)):
            k = kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        self.assertEqual(len(k), 5)
        d = json.loads((self.dir / "XXBTZEUR.json").read_text("utf-8"))
        self.assertEqual(len(d["kerzen"]), 5)
        self.assertIn("geholt", d)

    def test_laden_ohne_cache(self):
        self.assertEqual(kraken_kerzen.laden("XXX", cache_dir=self.dir),
                         ([], None))

    def test_laden_gibt_alter(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)):
            kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        k, alter = kraken_kerzen.laden("XXBTZEUR", cache_dir=self.dir)
        self.assertEqual(len(k), 5)
        self.assertLess(alter, 1.0)

    def test_hole_leere_antwort_behaelt_cache(self):
        vorhanden = _reihen(3)
        (self.dir / "XXBTZEUR.json").write_text(json.dumps(
            {"geholt": "2020-01-01T00:00:00+00:00", "kerzen": vorhanden}),
            "utf-8")
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=[]):
            k = kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        self.assertEqual(k, vorhanden)

    def test_hole_ruft_kraken_mit_intervall_1440(self):
        with mock.patch.object(kraken_kerzen.kraken, "kerzen",
                               return_value=_reihen(5)) as m:
            kraken_kerzen.hole("XXBTZEUR", 5, cache_dir=self.dir)
        m.assert_called_once_with("XXBTZEUR", intervall=1440, anzahl=5)


if __name__ == "__main__":
    unittest.main()
