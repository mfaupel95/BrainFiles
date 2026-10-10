# tests/test_dashboard/test_api_monitor.py
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HANDEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HANDEL))

from fastapi.testclient import TestClient  # noqa: E402

MOCK_SPUREN = [
    {"spur": "xperp", "erlaubt": True, "hs": 45, "fenster": "zu",
     "frei": True, "order": ["handeln.py"], "auto": False,
     "buch": {}, "alter": 3, "art": "haus", "scharf": True, "status": "ok"},
]


class TestMonitor(unittest.TestCase):

    def setUp(self):
        from dashboard.routen import monitor
        monitor._cache.clear()

    def _app(self):
        from dashboard.app import create_app
        return create_app()

    def test_monitor_html_liefert_200(self):
        with patch("dashboard.quellen.spuren.get_spuren", return_value=MOCK_SPUREN):
            resp = TestClient(self._app(), base_url="http://localhost").get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("xperp", resp.text)

    def test_monitor_maskiert_spurnamen(self):
        boese = [dict(MOCK_SPUREN[0], spur="<script>alert(1)</script>")]
        with patch("dashboard.quellen.spuren.get_spuren", return_value=boese):
            resp = TestClient(self._app(), base_url="http://localhost").get("/")
        self.assertNotIn("<script>alert(1)</script>", resp.text)

    def test_stream_liefert_drei_events(self):
        from dashboard.routen import monitor
        with patch("dashboard.quellen.spuren.get_spuren", return_value=MOCK_SPUREN), \
             patch.object(monitor, "_INTERVALL_S", 0.01), \
             patch.object(monitor, "_MAX_EVENTS", 3):
            with TestClient(self._app(), base_url="http://localhost").stream("GET", "/stream") as resp:
                events = [json.loads(z[5:].strip()) for z in resp.iter_lines()
                          if z.startswith("data:")]
        self.assertEqual(len(events), 3)
        self.assertIsInstance(events[0], list)
        self.assertEqual(events[0][0]["spur"], "xperp")

    def test_lan_ohne_pass_warnt(self):
        env = {k: v for k, v in os.environ.items() if k != "DASHBOARD_PASS"}
        r = subprocess.run([sys.executable, "-m", "dashboard", "--lan"], cwd=HANDEL,
                           capture_output=True, text=True, timeout=20, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DASHBOARD_PASS", r.stderr)


if __name__ == "__main__":
    unittest.main()
