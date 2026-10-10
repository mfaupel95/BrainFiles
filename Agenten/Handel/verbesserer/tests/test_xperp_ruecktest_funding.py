import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

H = 3_600_000


def _pos(seite="long", ts=0):
    return {"inst": "AAA-X", "seite": seite, "nominal": 1000.0,
            "letzte_funding_ts": ts, "funding_summe": 0.0}


def _raster(schritt_h, bis_h, satz=0.0001, ab_h=0):
    return {"AAA-X": [[h * H, satz] for h in range(ab_h, bis_h + 1, schritt_h)]}


class TestSatzZuZeitpunkt(unittest.TestCase):
    def test_nimmt_den_letzten_satz_vor_dem_zeitpunkt(self):
        saetze = {"AAA-X": [[1000, 0.0001], [5000, 0.0003]]}
        self.assertEqual(rt.satz_zu_zeitpunkt(saetze, "AAA-X", 6000), 0.0003)

    def test_satz_genau_zum_zeitpunkt_zaehlt(self):
        saetze = {"AAA-X": [[1000, 0.0001], [5000, 0.0003]]}
        self.assertEqual(rt.satz_zu_zeitpunkt(saetze, "AAA-X", 5000), 0.0003)

    def test_kein_satz_vor_dem_zeitpunkt_wirft_funding_luecke(self):
        with self.assertRaises(rt.FundingLuecke):
            rt.satz_zu_zeitpunkt({"AAA-X": [[5000, 0.0003]]}, "AAA-X", 1000)

    def test_unbekanntes_instrument_wirft_funding_luecke(self):
        with self.assertRaises(rt.FundingLuecke):
            rt.satz_zu_zeitpunkt({}, "AAA-X", 1000)


class TestFundingFaellig(unittest.TestCase):
    def test_zwischen_zwei_abrechnungen_wird_nichts_gebucht(self):
        p = _pos()
        saetze = _raster(4, 100)
        self.assertEqual(rt.funding_faellig(p, 4 * H - 1, saetze), 0.0)
        self.assertEqual(p["funding_summe"], 0.0)

    def test_4h_takt_bucht_sechs_abrechnungen_in_24h(self):
        p = _pos()
        betrag = rt.funding_faellig(p, 24 * H, _raster(4, 100))
        self.assertAlmostEqual(betrag, 6 * 0.1)

    def test_8h_takt_bucht_drei_abrechnungen_in_24h(self):
        p = _pos()
        betrag = rt.funding_faellig(p, 24 * H, _raster(8, 100))
        self.assertAlmostEqual(betrag, 3 * 0.1)

    def test_1h_takt_wird_ebenfalls_aus_den_daten_abgeleitet(self):
        p = _pos()
        betrag = rt.funding_faellig(p, 24 * H, _raster(1, 100))
        self.assertAlmostEqual(betrag, 24 * 0.1)

    def test_short_bekommt_bei_positivem_satz(self):
        p = _pos("short")
        self.assertAlmostEqual(
            rt.funding_faellig(p, 8 * H, _raster(8, 100)), -0.1)

    def test_long_bekommt_bei_negativem_satz(self):
        p = _pos()
        self.assertAlmostEqual(
            rt.funding_faellig(p, 8 * H, _raster(8, 100, satz=-0.0002)), -0.2)

    def test_jede_abrechnung_wird_nur_einmal_gebucht(self):
        p = _pos()
        saetze = _raster(4, 100)
        a = rt.funding_faellig(p, 9 * H, saetze)
        b = rt.funding_faellig(p, 9 * H, saetze)
        c = rt.funding_faellig(p, 13 * H, saetze)
        self.assertAlmostEqual(a, 2 * 0.1)
        self.assertEqual(b, 0.0)
        self.assertAlmostEqual(c, 0.1)
        self.assertAlmostEqual(p["funding_summe"], 3 * 0.1)

    def test_historie_beginnt_nach_positionseroeffnung_wirft(self):
        p = _pos(ts=2 * H)
        with self.assertRaises(rt.FundingLuecke):
            rt.funding_faellig(p, 20 * H, _raster(4, 100, ab_h=8))
        self.assertEqual(p["funding_summe"], 0.0)

    def test_cache_endet_lange_vor_dem_zeitpunkt_wirft(self):
        p = _pos()
        with self.assertRaises(rt.FundingLuecke):
            rt.funding_faellig(p, 100 * H, _raster(4, 20))
        self.assertEqual(p["letzte_funding_ts"], 0)

    def test_unbekanntes_instrument_wirft(self):
        with self.assertRaises(rt.FundingLuecke):
            rt.funding_faellig(_pos(), 20 * H, {})


if __name__ == "__main__":
    unittest.main()
