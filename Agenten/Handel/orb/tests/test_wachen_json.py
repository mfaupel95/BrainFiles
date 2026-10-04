import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"

class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_gesperrt(self):
        # Handelserlaubnis und Freigabe bleiben gesperrt: der Backtest ist fuer
        # beide Instrumente negativ (EV -45.1 / -3.7 Pkt je Runde), es gibt
        # keinen Live-Pfad im Code. Was der Papierlauf BRAUCHT, ist dagegen
        # gesetzt: ein Instrument und ein Spiegelziel (Bedingung 4).
        # handel_erlaubt steht auf False: Auftrag Max 21.09.2026 gilt nur fuer
        # sechs andere Spuren; ORB bleibt reine Papierspur. Die Spur
        # hat aber KEINEN Orderaufruf im Code - der Schalter allein handelt
        # nicht. Der Test prueft, dass der Wert False bleibt und
        # niemand ihn still aufmacht (nur wachen_orb.sperre_zu kippt ihn).
        self.assertIs(self.w["handel_erlaubt"], False)
        self.assertIs(self.w["freigabe"]["erfuellt"], False)
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