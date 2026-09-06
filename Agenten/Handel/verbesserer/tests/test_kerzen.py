import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import kerzen  # noqa: E402


class FakeAntwort:
    def __init__(self, text):
        self._t = text.encode()
    def read(self):
        return self._t
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class TestKerzen(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        # OKX liefert absteigend, neueste zuerst; zwei Seiten a 2 Kerzen
        self.seiten = [
            '{"code":"0","data":[["1700200000000","4","4","4","4","9"],'
            '["1700100000000","3","3","3","3","9"]]}',
            '{"code":"0","data":[["1700000000000","2","2","2","2","9"],'
            '["1699900000000","1","1","1","1","9"]]}',
            '{"code":"0","data":[]}',
        ]
        self.i = 0
        def fake_urlopen(req, timeout=0):
            s = self.seiten[min(self.i, len(self.seiten) - 1)]
            self.i += 1
            return FakeAntwort(s)
        kerzen.urllib.request.urlopen = fake_urlopen

    def tearDown(self):
        self.tmp.cleanup()

    def test_hole_stitcht_und_sortiert_aufsteigend(self):
        k = kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        self.assertEqual([r[4] for r in k], [1.0, 2.0, 3.0, 4.0])
        self.assertTrue(all(k[j][0] < k[j + 1][0] for j in range(len(k) - 1)))

    def test_hole_schreibt_cache(self):
        kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        d = json.loads((self.dir / "BTC-USDT.json").read_text("utf-8"))
        self.assertEqual(len(d["kerzen"]), 4)
        self.assertIn("geholt", d)

    def test_laden_ohne_cache(self):
        self.assertEqual(kerzen.laden("XXX", cache_dir=self.dir), ([], None))

    def test_laden_gibt_alter(self):
        kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        k, alter = kerzen.laden("BTC-USDT", cache_dir=self.dir)
        self.assertEqual(len(k), 4)
        self.assertLess(alter, 1.0)

    def test_hole_leere_antwort_behaelt_cache(self):
        # Erfolgreicher OKX-Abruf mit leerem data-Feld darf einen vorhandenen
        # Cache nicht mit {"kerzen": []} ueberschreiben.
        vorhanden = [[1699900000000 + i * 100000, 1.0, 1.0, 1.0, 1.0, 9.0]
                     for i in range(5)]
        (self.dir / "BTC-USDT.json").write_text(json.dumps(
            {"geholt": "2020-01-01T00:00:00+00:00", "kerzen": vorhanden}),
            "utf-8")
        orig = kerzen._seite
        kerzen._seite = lambda *a, **k: []
        try:
            k = kerzen.hole("BTC-USDT", tage=10, cache_dir=self.dir)
        finally:
            kerzen._seite = orig
        d = json.loads((self.dir / "BTC-USDT.json").read_text("utf-8"))
        self.assertEqual(len(d["kerzen"]), 5)
        self.assertEqual(len(k), 5)
        self.assertEqual(k, vorhanden)
