"""Verbesserer: Runden mit Kaufzeit vor dem Stichtag zaehlen im Befund nicht.

Gleicher Grund und gleicher Stichtag wie auswertung_alle.GUELTIG_AB: der
Scanner nahm bis 03.10.2026 den Vortagesberichts-Preis als Einstieg. Ein
Segment- und Permutationstest auf diesen Runden misst den Rechenfehler.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import auswerter  # noqa: E402

STICHTAG = "2026-10-02T22:23:13+00:00"
KOPF = "zeit,modus,aktion,inst,usd,grund\n"
# A: vor dem Fix komplett   B: Kauf VOR, Verkauf NACH dem Fix   C: nach dem Fix
JOURNAL = KOPF + (
    "2026-09-19T02:50:00+00:00,papier,kauf,AAA-USDC,100,score 70\n"
    "2026-09-19T03:05:00+00:00,papier,verkauf,AAA-USDC,115,ziel\n"
    "2026-10-02T20:00:00+00:00,papier,kauf,BBB-USDC,100,score 70\n"
    "2026-10-04T10:00:00+00:00,papier,verkauf,BBB-USDC,130,ziel\n"
    "2026-10-03T08:00:00+00:00,papier,kauf,CCC-USDC,100,score 70\n"
    "2026-10-04T08:00:00+00:00,papier,verkauf,CCC-USDC,94,stop\n"
)
KONF = {"segment_mindest_n": 1, "gebuehr_umstellung_datum": "2026-09-06"}


class StichtagTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "journal.csv").write_text(JOURNAL, encoding="utf-8")
        (self.d / "berichte").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def befund(self, **extra):
        spur = {"name": "t", "journal": str(self.d / "journal.csv"),
                "berichte": str(self.d / "berichte"), **extra}
        return auswerter.befund(spur, KONF, self.d / "aus")

    def test_ohne_stichtag_wie_vorher(self):
        b = self.befund()
        self.assertEqual(b["runden_gesamt"], 3)
        self.assertEqual(b["runden_vor_stichtag"], 0)
        self.assertIsNone(b["gueltig_ab"])

    def test_nur_kauf_nach_dem_stichtag_zaehlt(self):
        b = self.befund(gueltig_ab=STICHTAG)
        self.assertEqual(b["runden_gesamt"], 1)           # nur C
        self.assertEqual(b["runden_vor_stichtag"], 2)     # A und B, ausgewiesen
        # Das Segment 'grund' kennt nur noch den Stop von C.
        self.assertEqual(list(b["segmente"]["grund"]), ["stop"])

    def test_runde_ohne_lesbare_kaufzeit_gilt_als_nicht_belegt(self):
        self.assertTrue(auswerter.vor_stichtag({"kaufzeit": None}, STICHTAG))
        self.assertTrue(auswerter.vor_stichtag({"kaufzeit": "kaputt"}, STICHTAG))
        self.assertFalse(auswerter.vor_stichtag(
            {"kaufzeit": "2026-10-03T08:00:00+00:00"}, STICHTAG))

    def test_stichtag_ist_zeitzonenfest(self):
        # 03.10. 00:30 +02:00 = 02.10. 22:30 UTC -> NACH dem Stichtag.
        self.assertFalse(auswerter.vor_stichtag(
            {"kaufzeit": "2026-10-03T00:30:00+02:00"}, STICHTAG))
        self.assertTrue(auswerter.vor_stichtag(
            {"kaufzeit": "2026-10-03T00:10:00+02:00"}, STICHTAG))

    def test_spuren_json_traegt_den_stichtag_fuer_spur1_nicht_fuer_spur3(self):
        s = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
        self.assertEqual(s["spur1"]["gueltig_ab"], STICHTAG)
        self.assertNotIn("gueltig_ab", s["spur3"])


if __name__ == "__main__":
    unittest.main()
