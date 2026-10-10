# tests/test_dashboard/test_quellen_spuren.py
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestGetSpuren(unittest.TestCase):

    def test_status_ok(self):
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": True, "hs": 45, "alter": 10}), "ok")

    def test_status_veraltet(self):
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": True, "hs": 45, "alter": 100}), "veraltet")

    def test_status_nicht_konfiguriert_keine_wachen(self):
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": None, "hs": None, "alter": 5}), "nicht_konfiguriert")

    def test_stale_alter_none(self):
        # alter=None (Spur nie im Log): weder Crash noch "veraltet" noch faelschlich gruen
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": True, "hs": 45, "alter": None}), "unbekannt")

    def test_alter_none_ohne_herzschlagpflicht_ist_ok(self):
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": True, "hs": 0, "alter": None}), "ok")

    def test_sammle_ohne_log_kein_crash(self):
        # sammle() wirft -> get_spuren() liefert leere Liste statt Crash
        from dashboard.quellen import spuren as mod
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(mod._ss, "sammle", side_effect=FileNotFoundError("dauerlauf.log")), \
             patch.object(mod, "_HIER", Path(tmp)):
            self.assertEqual(mod.get_spuren(), [])

    def test_fremdrepo_signal_angehaengt(self):
        from dashboard.quellen import spuren as mod
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "fremdrepos-signal-kraken.json").write_text(json.dumps([{
                "spur": "kraken_fremd", "erlaubt": True, "hs": 60, "fenster": "-",
                "frei": False, "order": [], "auto": False, "buch": {}, "alter": 1,
                "art": "fremd", "scharf": False}]), encoding="utf-8")
            with patch.object(mod, "_sammle_roh", return_value=[]), \
                 patch.object(mod, "_HIER", p):
                result = mod.get_spuren()
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["spur"], "kraken_fremd")


if __name__ == "__main__":
    unittest.main()
