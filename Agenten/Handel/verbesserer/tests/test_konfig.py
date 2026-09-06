import json
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parents[1]


class TestKonfig(unittest.TestCase):
    def test_konfig_hat_pflichtschluessel(self):
        k = json.loads((HIER / "konfig.json").read_text("utf-8"))
        for s in ("auto_anwenden", "such_budget", "oos_training_tage",
                  "oos_test_tage", "oos_schritt_tage", "segment_mindest_n",
                  "overfit_min_runden", "overfit_min_fenster",
                  "gebuehr_umstellung_datum", "llm"):
            self.assertIn(s, k)
        self.assertIs(k["auto_anwenden"], False)
        self.assertEqual(k["oos_training_tage"], 120)
        self.assertEqual(k["oos_test_tage"], 30)

    def test_spuren_spur1_vollstaendig(self):
        s = json.loads((HIER / "spuren.json").read_text("utf-8"))["spur1"]
        for p in ("journal", "zustand", "wachen", "berichte", "bewertung_datei"):
            self.assertIn(p, s)
        self.assertIn("watchlist", s["aenderbar"]["wachen.json"])

    def test_gebuehr_konstante(self):
        import sys
        sys.path.insert(0, str(HIER))
        import kosten
        self.assertEqual(kosten.GEBUEHR_PCT, 0.0005)
