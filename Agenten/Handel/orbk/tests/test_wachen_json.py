import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"

class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_papier(self):
        # orbk auf OKX-Perp migriert (15.10.2026, Auftrag Max). handel_erlaubt
        # bleibt false (Papier) bis Max live schaltet.
        self.assertIs(self.w["handel_erlaubt"], False)
        self.assertIs(self.w["freigabe"]["erfuellt"], False)

    def test_journal_zweitziel_gesetzt(self):
        ziel = self.w["journal_zweitziel"]
        self.assertIsInstance(ziel, str)
        self.assertTrue(ziel.strip())
        self.assertNotIn("G:", ziel, "G: ist dasselbe Gehaeuse wie die Platte")

    def test_pflichtfelder_da(self):
        for schluessel in ("risiko_pro_trade_usd", "ziel_modus", "hebel_deckel",
                           "letzter_einstieg_min_vor_schluss",
                           "mindest_marge_frei_usd",
                           "kill_switch_gesamt_usd", "herzschlag_max_minuten",
                           "okx_host"):
            self.assertIn(schluessel, self.w)

    def test_zwei_instrumente_vollstaendig(self):
        for inst in ("ETH_USDT", "BTC_USDT"):
            e = self.w["instrumente"][inst]
            for f in ("okx", "eroeffnung", "zone", "session_ende",
                      "spread_punkte", "punkt_wert_usdt"):
                self.assertIn(f, e)
            self.assertIn(inst, self.w["mindest_range_punkte"])
            self.assertIn(inst, self.w["max_range_punkte"])

    def test_ziel_modus_gueltig(self):
        self.assertIn(self.w["ziel_modus"], ("punkte", "r_vielfaches"))

    def test_keine_kraken_reste(self):
        # Seit der OKX-Umstellung darf kein Kraken-Spot-Feld mehr stehen.
        self.assertNotIn("kraken_host", self.w)
        for inst in self.w["instrumente"]:
            self.assertNotIn("kraken", self.w["instrumente"][inst])

if __name__ == "__main__":
    unittest.main()
