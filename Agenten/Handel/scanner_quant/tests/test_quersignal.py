import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "quersignal.py"
SPEC = importlib.util.spec_from_file_location("quersignal", MODULE_PATH)
quersignal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quersignal)


class ZeitParserTest(unittest.TestCase):
    def test_datum_ohne_uhrzeit_ist_nicht_fuer_frische_signale_nutzbar(self):
        parsed = quersignal._parse_time("2026-10-22")
        self.assertIsNone(parsed)

    def test_naive_zeit_wird_als_utc_vereinheitlicht(self):
        parsed = quersignal._parse_time("2026-10-22T12:00:00")
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.tzinfo, timezone.utc)


class PapierbuchTest(unittest.TestCase):
    def test_nur_frische_papierpositionen_mit_zeitstempel_werden_gemeldet(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "spur"
            folder.mkdir()
            (folder / "wachen.json").write_text(
                json.dumps({"herzschlag_max_minuten": 180}), encoding="utf-8")
            state = {
                "modus": "papier",
                "letzter_lauf": now.isoformat(),
                "positionen": [
                    {"inst": "BTC-USDC", "seite": "long",
                     "eroeffnet": (now - timedelta(minutes=20)).isoformat()},
                    {"inst": "ETH-USDC", "seite": "long",
                     "eroeffnet": now.date().isoformat()},
                    {"inst": "SOL-USDC", "seite": "long", "modus": "live",
                     "eroeffnet": now.isoformat()},
                    {"inst": "XRP-USDC", "seite": "short",
                     "eroeffnet": (now - timedelta(minutes=20)).isoformat()},
                ],
            }
            (folder / "zustand.json").write_text(
                json.dumps(state), encoding="utf-8")
            with mock.patch.object(quersignal, "_active_traces",
                                   return_value={"spur": "spur"}):
                entries, stale, skipped, count = quersignal._recent_paper_entries(
                    root, 1.0)

        self.assertEqual(count, 1)
        self.assertEqual((stale, skipped), ([], 0))
        self.assertEqual([(e["symbol"], e["side"]) for e in entries],
                         [("BTC-USDC", "long"), ("XRP-USDC", "short")])

    def test_dedupliziert_stufen_derselben_spur_symbolrichtung(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "spur"
            folder.mkdir()
            (folder / "wachen.json").write_text("{}", encoding="utf-8")
            opened = (now - timedelta(minutes=10)).isoformat()
            state = {"modus": "papier", "letzter_lauf": now.isoformat(),
                     "positionen": [
                         {"inst": "BTC-USDC", "seite": "long",
                          "eroeffnet": opened, "stufe": 1},
                         {"inst": "BTC-USDC", "seite": "long",
                          "eroeffnet": opened, "stufe": 2},
                     ]}
            (folder / "zustand.json").write_text(
                json.dumps(state), encoding="utf-8")
            with mock.patch.object(quersignal, "_active_traces",
                                   return_value={"spur": "spur"}):
                entries, _, _, _ = quersignal._recent_paper_entries(root, 1.0)
        self.assertEqual(len(entries), 1)


class MarktTorTest(unittest.TestCase):
    def test_quant_bericht_erhoeht_das_live_tor_nicht(self):
        row = {"score": 61, "verhaeltnis": 1.6,
               "kennzahlen": {"volatilitaet_pa": 1.0},
               "quant": {"quant_score": 10, "zu_gedehnt": False}}
        watch = {"mindest_score": 60, "max_volatilitaet_pa": 2.0,
                 "mindest_chance_risiko": 1.5}
        self.assertTrue(quersignal._scanner_gate(
            row, watch, {"aktiv": True, "modus": "bericht",
                         "mindest_quant_score": 60}))

    def test_quant_tor_wird_nur_im_tor_modus_zusaetzlich_geprueft(self):
        row = {"score": 61, "verhaeltnis": 1.6,
               "kennzahlen": {"volatilitaet_pa": 1.0},
               "quant": {"quant_score": 10, "zu_gedehnt": False}}
        watch = {"mindest_score": 60, "max_volatilitaet_pa": 2.0,
                 "mindest_chance_risiko": 1.5}
        self.assertFalse(quersignal._scanner_gate(
            row, watch, {"aktiv": True, "modus": "tor",
                         "mindest_quant_score": 60}))


if __name__ == "__main__":
    unittest.main()
