import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import okxf  # noqa: E402


def _seite(ts_liste):
    return [{"fundingTime": str(ts), "fundingRate": str(0.0001 * i)}
            for i, ts in enumerate(ts_liste, 1)]


class TestFundingHistorie(unittest.TestCase):
    def test_eine_seite_aufsteigend_sortiert(self):
        with mock.patch.object(
                okxf, "_mit_wiederholung",
                return_value=_seite([3000, 1000, 2000])) as m:
            out = okxf.funding_historie("BTC-USD_UM_XPERP-310620", seiten=1)
        self.assertEqual([r[0] for r in out], [1000, 2000, 3000])
        self.assertIn("instId=BTC-USD_UM_XPERP-310620", m.call_args[0][0])

    def test_mehrere_seiten_werden_zusammengefuehrt_und_entdoppelt(self):
        antworten = [_seite([4000, 3000]), _seite([2000, 1000])]
        with mock.patch.object(okxf, "_mit_wiederholung",
                              side_effect=antworten):
            out = okxf.funding_historie("BTC-USD_UM_XPERP-310620", seiten=2)
        self.assertEqual([r[0] for r in out], [1000, 2000, 3000, 4000])

    def test_folgeanfrage_blaettert_mit_after_ab_dem_aeltesten_stempel(self):
        antworten = [_seite([4000, 3000]), _seite([2000, 1000])]
        with mock.patch.object(okxf, "_mit_wiederholung",
                               side_effect=antworten) as m:
            okxf.funding_historie("BTC-USD_UM_XPERP-310620", seiten=2)
        self.assertIn("after=3000", m.call_args_list[1].args[0])
        self.assertNotIn("before=3000", m.call_args_list[1].args[0])

    def test_leere_antwort_beendet_das_blaettern(self):
        with mock.patch.object(okxf, "_mit_wiederholung",
                              side_effect=[_seite([1000]), []]):
            out = okxf.funding_historie("BTC-USD_UM_XPERP-310620", seiten=5)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
