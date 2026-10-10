# tests/test_dashboard/test_api_steuerung.py
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

MOCK_SPUREN = [
    {"spur": "xperp", "erlaubt": True, "hs": 45, "fenster": "zu",
     "frei": True, "order": ["handeln.py"], "auto": False,
     "buch": {}, "alter": 3, "art": "haus", "scharf": True, "status": "ok"},
]


def _client():
    from dashboard.app import create_app
    return TestClient(create_app(), base_url="http://localhost")


class TestSteuerungNotAus(unittest.TestCase):

    def test_steuerung_html_200(self):
        with patch("dashboard.quellen.spuren.get_spuren", return_value=MOCK_SPUREN), \
             patch("dashboard.quellen.prozesse.systemprozesse",
                   return_value=[{"name": "dauerlauf", "laeuft": False, "pid": None}]):
            resp = _client().get("/steuerung")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("xperp", resp.text)
        self.assertIn("/api/prozess/dauerlauf/start", resp.text)

    def test_not_aus_schreibt_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            spur_dir = p / "xperp"
            spur_dir.mkdir()
            (spur_dir / "wachen.json").write_text(
                json.dumps({"handel_erlaubt": True, "herzschlag_max_minuten": 45}),
                encoding="utf-8")
            with patch("dashboard.quellen.prozesse._HIER", p):
                resp = _client().post("/api/spur/xperp/notaus")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["ok"])
            d = json.loads((spur_dir / "wachen.json").read_text(encoding="utf-8"))
            self.assertFalse(d["handel_erlaubt"])

    def test_not_aus_fehlende_spur_meldet_fehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("dashboard.quellen.prozesse._HIER", Path(tmp)):
                resp = _client().post("/api/spur/gibtesnicht/notaus")
        self.assertFalse(resp.json()["ok"])


class TestProzessAktionen(unittest.TestCase):

    def test_start_ruft_system_starten(self):
        with patch("dashboard.quellen.prozesse.system_starten") as st:
            resp = _client().post("/api/prozess/dauerlauf/start")
        self.assertEqual(resp.status_code, 200)
        st.assert_called_once_with("dauerlauf")

    def test_stop_ruft_system_stoppen(self):
        with patch("dashboard.quellen.prozesse.system_stoppen") as sp:
            resp = _client().post("/api/prozess/omnitrade/stop")
        self.assertEqual(resp.status_code, 200)
        sp.assert_called_once_with("omnitrade")

    def test_unbekannter_prozess_wird_abgelehnt(self):
        with patch("dashboard.quellen.prozesse.system_starten") as st:
            resp = _client().post("/api/prozess/calc/start")
        self.assertEqual(resp.status_code, 404)
        st.assert_not_called()

    def test_fremde_origin_wird_abgelehnt(self):
        # CSRF: eine fremde Webseite darf keine Prozesse ueber localhost starten.
        with patch("dashboard.quellen.prozesse.system_starten") as st:
            resp = _client().post("/api/prozess/dauerlauf/start",
                                  headers={"Origin": "http://boese.example"})
        self.assertEqual(resp.status_code, 403)
        st.assert_not_called()

    def test_gleiche_origin_ist_erlaubt(self):
        with patch("dashboard.quellen.prozesse.system_starten"):
            resp = _client().post("/api/prozess/dauerlauf/start",
                                  headers={"Origin": "http://localhost"})
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
