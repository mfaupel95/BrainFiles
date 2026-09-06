import json
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import auswerter  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


class TestAuswerter(unittest.TestCase):
    def setUp(self):
        import wachen_pruefung as wp
        self.runden = auswerter.anreichern(
            wp.runden_aus_journal(FIX / "journal_klein.csv"), FIX)

    def test_anreichern_setzt_score_aus_bericht(self):
        btc = [r for r in self.runden if r["inst"] == "BTC-USDT"][0]
        self.assertAlmostEqual(btc["score"], 72.0, 1)

    def test_segment_stop_schlechter_als_ziel(self):
        s = auswerter.segmente(self.runden, mindest_n=1)
        self.assertLess(s["grund"]["stop"]["mittel_gv"],
                        s["grund"]["ziel"]["mittel_gv"])

    def test_permutationstest_deterministisch(self):
        doge = [r for r in self.runden if r["inst"] == "DOGE-USDT"]
        rest = [r for r in self.runden if r["inst"] != "DOGE-USDT"]
        p1 = auswerter.permutationstest(doge, rest, seed=1)
        p2 = auswerter.permutationstest(doge, rest, seed=1)
        self.assertEqual(p1, p2)

    def test_befund_nur_ab_mindest_n(self):
        s = auswerter.segmente(self.runden, mindest_n=8)
        # DOGE hat nur 4 Runden -> kein Eintrag als Befund-Kandidat
        self.assertNotIn("DOGE-USDT", s.get("inst", {}))

    def test_befund_schreibt_datei(self, tmp=None):
        import tempfile
        d = Path(tempfile.mkdtemp())
        konf = {"segment_mindest_n": 1, "gebuehr_umstellung_datum": "2026-01-01"}
        spur = {"journal": str(FIX / "journal_klein.csv"),
                "berichte": str(FIX), "_name": "spur1"}
        auswerter.befund(spur, konf, d)
        raus = list(d.glob("*-befund-spur1.json"))
        self.assertEqual(len(raus), 1)
        self.assertIn("segmente", json.loads(raus[0].read_text("utf-8")))

    def test_anreichern_nimmt_einstiegstag(self):
        # Kauf 2026-08-10 (score 71.0), Verkauf 2026-08-14 (score 55.0).
        # Mit journal_pfad muss der Einstiegstag-Bericht gezogen werden.
        import wachen_pruefung as wp
        j = FIX / "journal_zweitage.csv"
        runden = auswerter.anreichern(
            wp.runden_aus_journal(j), FIX, journal_pfad=j)
        self.assertEqual(len(runden), 1)
        self.assertEqual(runden[0]["score"], 71.0)


if __name__ == "__main__":
    unittest.main()
