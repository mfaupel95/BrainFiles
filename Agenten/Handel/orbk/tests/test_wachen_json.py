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
        # daten zählen'). Der Backtest ist negativ / zu wenig Daten und wird
        # bewusst ignoriert; die Papierdaten zaehlen. Der Test stellt sicher,
        # dass niemand die Freigabe still zurueckdreht.
        self.assertIs(self.w["handel_erlaubt"], True)
        self.assertIs(self.w["freigabe"]["erfuellt"], True)

    def test_journal_zweitziel_gesetzt(self):
        # Bedingung 4. Bis 13.09.2026 stand hier assertIsNone - das Ziel ist
        # seit dem 13.09.2026 gesetzt (Q:), und handeln.py spiegelt nach jedem
        # Zyklus dorthin. Ein Ziel ist nicht der Nachweis: die Kopie zaehlt
        # (siehe zustand.json journal_zweitziel_ok).
        ziel = self.w["journal_zweitziel"]
        self.assertIsInstance(ziel, str)
        self.assertTrue(ziel.strip())
        self.assertNotIn("G:", ziel, "G: ist dasselbe Gehaeuse wie die Platte")

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