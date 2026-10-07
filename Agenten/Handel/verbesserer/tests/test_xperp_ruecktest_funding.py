import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "xperp"))
import xperp_ruecktest as rt  # noqa: E402

ACHT_H = 8 * 3_600_000


def _pos(seite="long", ts=0):
    return {"inst": "AAA-X", "seite": seite, "nominal": 1000.0,
            "letzte_funding_ts": ts, "funding_summe": 0.0}


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
    SAETZE = {"AAA-X": [[0, 0.0001]]}

    def test_vor_8h_wird_nichts_gebucht(self):
        p = _pos()
        self.assertEqual(rt.funding_faellig(p, ACHT_H - 1, self.SAETZE), 0.0)
        self.assertEqual(p["letzte_funding_ts"], 0)

    def test_nach_8h_long_zahlt_bei_positivem_satz(self):
        p = _pos()
        self.assertAlmostEqual(rt.funding_faellig(p, ACHT_H, self.SAETZE), 0.1)
        self.assertEqual(p["letzte_funding_ts"], ACHT_H)
        self.assertAlmostEqual(p["funding_summe"], 0.1)

    def test_short_bekommt_bei_positivem_satz(self):
        p = _pos("short")
        self.assertAlmostEqual(rt.funding_faellig(p, ACHT_H, self.SAETZE), -0.1)

    def test_long_bekommt_bei_negativem_satz(self):
        p = _pos()
        self.assertAlmostEqual(
            rt.funding_faellig(p, ACHT_H, {"AAA-X": [[0, -0.0002]]}), -0.2)

    def test_mehrere_perioden_mit_je_eigenem_historischem_satz(self):
        p = _pos()
        saetze = {"AAA-X": [[0, 0.0001], [ACHT_H, 0.0002], [2 * ACHT_H, 0.0003]]}
        # Perioden bei 8h, 16h, 24h -> Saetze 0.0002, 0.0003 und der Satz
        # bei 24h (letzter <= 24h) = 0.0003 (kein Eintrag bei 3*ACHT_H).
        betrag = rt.funding_faellig(p, 3 * ACHT_H, saetze)
        self.assertAlmostEqual(betrag, 1000 * (0.0002 + 0.0003 + 0.0003))
        self.assertEqual(p["letzte_funding_ts"], 3 * ACHT_H)

    def test_fehlender_satz_wirft_statt_null_zu_buchen(self):
        p = _pos(ts=ACHT_H)
        with self.assertRaises(rt.FundingLuecke):
            rt.funding_faellig(p, 2 * ACHT_H, {"AAA-X": [[3 * ACHT_H, 0.0001]]})
        self.assertEqual(p["letzte_funding_ts"], ACHT_H)
        self.assertEqual(p["funding_summe"], 0.0)


if __name__ == "__main__":
    unittest.main()
