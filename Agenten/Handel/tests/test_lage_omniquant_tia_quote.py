"""Regression: Omniquant-Live-Kurs muss aus dem tatsaechlichen Venue kommen."""
import os
import sys
import types
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import lage  # noqa: E402


class OmniquantVenueKursTest(unittest.TestCase):
    def test_kraken_futures_uses_pair_usd_not_okx_tia_try_and_hides_mismatched_stop(self):
        position = {
            "inst": "TIA-TRY",
            "paar": "PF_TIAUSD",
            "boerse": "kraken_futures",
            "seite": "long",
            "einstieg": 0.6143,
            "stop": 28.684576562576204,
            "nominal": 149.8892,
            "eroeffnet": "2026-10-20",
        }
        calls = []

        class OkxFake:
            @staticmethod
            def letzter_kurs(inst):
                calls.append(("okx", inst))
                return 28.4

        class KrakenFuturesFake:
            @staticmethod
            def letzter_kurs(symbol):
                calls.append(("kraken_futures", symbol))
                return 0.5654

        fake_package = types.ModuleType("nautilus_kraken")
        fake_package.__path__ = []
        setattr(fake_package, "kraken_futures", KrakenFuturesFake)
        z = {"modus": "live", "positionen": [position]}

        with patch.object(lage, "_lies", side_effect=lambda path, default=None: z if "zustand" in path else {}), \
             patch.object(lage, "_buch", return_value=[]), \
             patch.object(lage, "_bilanz", return_value=None), \
             patch.dict(sys.modules, {
                 "okx": OkxFake,
                 "nautilus_kraken": fake_package,
                 "nautilus_kraken.kraken_futures": KrakenFuturesFake,
             }):
            result = lage.spur_omniquant()

        row = result["positionen"][0]
        self.assertEqual(row["kurs"], 0.5654)
        self.assertAlmostEqual(row["vh"], (0.5654 / 0.6143 - 1) * 100, places=6)
        self.assertIsNone(row["stop"])
        self.assertIn("PF_TIAUSD", row["kurs_warnung"])
        import tagesbericht
        text = tagesbericht.zeile_position(row, "USD")
        self.assertIn("DATENHINWEIS", text)
        self.assertNotIn("Stop gerissen", text)
        self.assertEqual(calls, [("kraken_futures", "PF_TIAUSD")])


if __name__ == "__main__":
    unittest.main()
