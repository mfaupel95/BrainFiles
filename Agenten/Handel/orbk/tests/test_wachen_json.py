import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"

class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_gesperrt(self):
        # handel_erlaubt bleibt false (nur Papier). instrument_aktiv ist fuer
        # den laufenden ETH-Papiertest gesetzt - der Backtest ist weiter offen.
        self.assertIs(self.w["handel_erlaubt"], False)
        self.assertIs(self.w["freigabe"]["erfuellt"], False)
        self.assertIsNone(self.w["journal_zweitziel"])

    def test_pflichtfelder_da(self):
        for schluessel in ("risiko_pro_trade_usd", "ziel_modus", "hebel_deckel",
                           "letzter_einstieg_min_vor_schluss", "mindest_marge_frei_usd",
                           "kill_switch_gesamt_usd", "herzschlag_max_minuten",
                           "kraken_host"):
            self.assertIn(schluessel, self.w)

    def test_zwei_instrumente_vollstaendig(self):
        for inst in ("HYPE_USD", "HYPE_EUR"):
            e = self.w["instrumente"][inst]
            for f in ("kraken", "eroeffnung", "zone", "session_ende",
                      "spread_punkte", "punkt_wert_usd"):
                self.assertIn(f, e)
            self.assertIn(inst, self.w["mindest_range_punkte"])
            self.assertIn(inst, self.w["max_range_punkte"])

    def test_ziel_modus_gueltig(self):
        self.assertIn(self.w["ziel_modus"], ("punkte", "r_vielfaches"))

    def test_keine_okx_reste(self):
        self.assertNotIn("okx_host", self.w)
        for inst in self.w["instrumente"]:
            self.assertNotIn("okx", self.w["instrumente"][inst])

if __name__ == "__main__":
    unittest.main()