import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"

class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_live_aktiv(self):
        # handel_erlaubt=True und freigabe.erfuellt=True seit 12.10.2026
        # (Auftrag Max: 'Live pfad anbinden. Backtest außer acht lassen,
        # daten zählen'). Der Backtest ist negativ und wird bewusst ignoriert;
        # die Papierdaten zaehlen. backtest_bestanden bleibt ehrlich false.
        # Der Test stellt sicher, dass niemand die Freigabe still zurueckdreht.
        self.assertIs(self.w["handel_erlaubt"], True)
        self.assertIs(self.w["freigabe"]["erfuellt"], True)
        self.assertIs(self.w["freigabe"]["backtest_bestanden"], False)
        self.assertIn(self.w["instrument_aktiv"], ("BTC_USDT", "ETH_USDT"))
        self.assertTrue(self.w["journal_zweitziel"])

    def test_pflichtfelder_da(self):
        for schluessel in ("risiko_pro_trade_usdt", "ziel_modus", "hebel_deckel",
                           "letzter_einstieg_min_vor_schluss", "mindest_marge_frei_usdt",
                           "kill_switch_gesamt_usdt", "herzschlag_max_minuten",
                           "okx_host"):
            self.assertIn(schluessel, self.w)

    def test_zwei_instrumente_vollstaendig(self):
        for inst in ("BTC_USDT", "ETH_USDT"):
            e = self.w["instrumente"][inst]
            for f in ("okx", "eroeffnung", "zone", "session_ende",
                      "spread_punkte", "punkt_wert_usdt"):
                self.assertIn(f, e)
            self.assertIn(inst, self.w["mindest_range_punkte"])
            self.assertIn(inst, self.w["max_range_punkte"])

    def test_ziel_modus_gueltig(self):
        self.assertIn(self.w["ziel_modus"], ("punkte", "r_vielfaches"))

    def test_keine_oanda_reste(self):
        self.assertNotIn("oanda_host_papier", self.w)
        for inst in self.w["instrumente"]:
            self.assertNotIn("oanda", self.w["instrumente"][inst])

if __name__ == "__main__":
    unittest.main()