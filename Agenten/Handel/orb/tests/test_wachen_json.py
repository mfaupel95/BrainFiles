import json
import unittest
from pathlib import Path

WACHEN = Path(__file__).resolve().parent.parent / "wachen.json"


class TestWachenJson(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WACHEN.read_text(encoding="utf-8"))

    def test_start_gesperrt(self):
        self.assertIs(self.w["handel_erlaubt"], False)
        self.assertIsNone(self.w["instrument_aktiv"])
        self.assertIs(self.w["freigabe"]["erfuellt"], False)
        self.assertIsNone(self.w["journal_zweitziel"])

    def test_pflichtfelder_da(self):
        for schluessel in ("risiko_pro_trade_eur", "ziel_modus", "hebel_deckel",
                           "letzter_einstieg_min_vor_schluss", "mindest_marge_frei_eur",
                           "kill_switch_gesamt_eur", "herzschlag_max_minuten",
                           "oanda_host_papier", "oanda_host_live"):
            self.assertIn(schluessel, self.w)

    def test_drei_instrumente_vollstaendig(self):
        for inst in ("DE30_EUR", "US30_USD", "NAS100_USD"):
            e = self.w["instrumente"][inst]
            for f in ("oanda", "eroeffnung", "zone", "cash_close",
                      "spread_punkte", "punkt_wert_eur"):
                self.assertIn(f, e)
            self.assertIn(inst, self.w["mindest_range_punkte"])
            self.assertIn(inst, self.w["max_range_punkte"])

    def test_ziel_modus_gueltig(self):
        self.assertIn(self.w["ziel_modus"], ("punkte", "r_vielfaches"))
