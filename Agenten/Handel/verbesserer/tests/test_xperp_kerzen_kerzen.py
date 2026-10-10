import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_kerzen  # noqa: E402

K = [[1000, 1, 1, 1, 1, 1], [2000, 1, 1, 1, 1, 1]]


class TestKerzenCache(unittest.TestCase):
    def test_hole_1h_nutzt_kerzen_lang_und_cacht_je_granularitaet(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(xperp_kerzen.okxf, "kerzen_lang",
                                   return_value=K) as m:
                out = xperp_kerzen.hole("BTC-X", "1H", seiten=3, cache_dir=d)
            m.assert_called_once_with("BTC-X", "1H", 3)
            self.assertEqual(out, K)
            geladen, alter = xperp_kerzen.laden("BTC-X", "1H", cache_dir=d)
            self.assertEqual(geladen, K)
            self.assertIsNotNone(alter)

    def test_hole_1d_nutzt_kerzen_nicht_kerzen_lang(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(xperp_kerzen.okxf, "kerzen",
                                   return_value=K) as m:
                xperp_kerzen.hole("BTC-X", "1D", cache_dir=d)
            m.assert_called_once_with("BTC-X", "1D", 300)

    def test_verschiedene_granularitaeten_kollidieren_nicht_im_cache(self):
        with tempfile.TemporaryDirectory() as d:
            k4 = [[4000, 2, 2, 2, 2, 2]]
            with mock.patch.object(xperp_kerzen.okxf, "kerzen_lang",
                                   side_effect=[K, k4]):
                xperp_kerzen.hole("BTC-X", "1H", cache_dir=d)
                xperp_kerzen.hole("BTC-X", "4H", cache_dir=d)
            self.assertEqual(xperp_kerzen.laden("BTC-X", "1H", cache_dir=d)[0], K)
            self.assertEqual(xperp_kerzen.laden("BTC-X", "4H", cache_dir=d)[0], k4)

    def test_hole_funding_cacht_getrennt_von_kerzen(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(xperp_kerzen.okxf, "funding_historie",
                                   return_value=[[1000, 0.0001]]) as m:
                out = xperp_kerzen.hole_funding("BTC-X", seiten=4, cache_dir=d)
            m.assert_called_once_with("BTC-X", seiten=4)
            self.assertEqual(out, [[1000, 0.0001]])
            geladen, _ = xperp_kerzen.laden_funding("BTC-X", cache_dir=d)
            self.assertEqual(geladen, [[1000, 0.0001]])

    def test_leerer_abruf_ueberschreibt_den_cache_nicht(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(xperp_kerzen.okxf, "kerzen_lang",
                                   side_effect=[K, []]):
                xperp_kerzen.hole("BTC-X", "1H", cache_dir=d)
                out = xperp_kerzen.hole("BTC-X", "1H", cache_dir=d)
            self.assertEqual(out, K)

    def test_laden_ohne_cache_gibt_leere_liste_und_none(self):
        with tempfile.TemporaryDirectory() as d:
            k, alter = xperp_kerzen.laden("UNBEKANNT", "1H", cache_dir=d)
            self.assertEqual((k, alter), ([], None))


if __name__ == "__main__":
    unittest.main()
