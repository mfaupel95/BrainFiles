# tests/test_dashboard/test_nachbesserung.py - Fixes aus dem Gesamtreview
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

HANDEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HANDEL))

from fastapi.testclient import TestClient  # noqa: E402


def _app(**kw):
    from dashboard.app import create_app
    return create_app(**kw)


def _client(app=None):
    return TestClient(app or _app(), base_url="http://localhost")


class DnsRebinding(unittest.TestCase):

    def test_fremder_host_wird_abgelehnt(self):
        # Rebinding: Browser schickt Host=evil.example, Origin passend dazu.
        c = TestClient(_app(), base_url="http://evil.example:7788")
        with patch("dashboard.quellen.prozesse.system_starten") as st:
            r = c.post("/api/prozess/dauerlauf/start", headers={"Origin": "http://evil.example:7788"})
        self.assertEqual(r.status_code, 400)
        st.assert_not_called()
        self.assertEqual(c.get("/steuerung").status_code, 400)

    def test_localhost_mit_port_ist_erlaubt(self):
        c = TestClient(_app(), base_url="http://localhost:7788")
        with patch("dashboard.quellen.spuren.get_spuren", return_value=[]):
            self.assertEqual(c.get("/").status_code, 200)


class LanModus(unittest.TestCase):

    def test_lan_ohne_passwort_wirft(self):
        with self.assertRaises(ValueError):
            _app(lan=True, passwort="")

    def test_lan_schuetzt_auch_static(self):
        app = _app(lan=True, passwort="geheim")
        c = TestClient(app, base_url="http://192.168.0.5:7788")
        self.assertEqual(c.get("/static/style.css").status_code, 401)
        self.assertEqual(c.get("/stream").status_code, 401)
        gut = {"Authorization": "Basic " + base64.b64encode(b"x:geheim").decode()}
        self.assertEqual(c.get("/static/style.css", headers=gut).status_code, 200)
        schlecht = {"Authorization": "Basic " + base64.b64encode(b"x:falsch").decode()}
        self.assertEqual(c.get("/static/style.css", headers=schlecht).status_code, 401)


class DoppelStart(unittest.TestCase):

    def test_prozess_laeuft_schon_gibt_409(self):
        laeuft = [{"name": "dauerlauf", "laeuft": True, "pid": 1}, {"name": "omnitrade", "laeuft": False, "pid": None}]
        with patch("dashboard.quellen.prozesse.systemprozesse", return_value=laeuft), \
             patch("dashboard.quellen.prozesse.subprocess.Popen") as popen:
            r = _client().post("/api/prozess/dauerlauf/start")
        self.assertEqual(r.status_code, 409)
        popen.assert_not_called()

    def test_start_wenn_gestoppt(self):
        stand = [{"name": "dauerlauf", "laeuft": False, "pid": None}, {"name": "omnitrade", "laeuft": False, "pid": None}]
        with patch("dashboard.quellen.prozesse.systemprozesse", return_value=stand), \
             patch("dashboard.quellen.prozesse.subprocess.Popen") as popen:
            r = _client().post("/api/prozess/dauerlauf/start")
        self.assertEqual(r.status_code, 200)
        popen.assert_called_once()

    def test_job_laeuft_schon_gibt_409(self):
        from dashboard.quellen import jobs
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "a.log"
            jobs.starte("dopp", [sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp, logdatei=log)
            try:
                with self.assertRaises(jobs.JobLaeuftSchon):
                    jobs.starte("dopp", [sys.executable, "-c", "print(1)"], cwd=tmp, logdatei=log)
            finally:
                jobs._laufende["dopp"].kill()
                jobs._laufende["dopp"].wait()

    def test_backtest_route_gibt_409(self):
        from dashboard.quellen import jobs
        with patch("dashboard.quellen.jobs.starte", side_effect=jobs.JobLaeuftSchon("x")):
            r = _client().post("/api/backtest/run", data={"spur": "xperp", "tage": "30"})
        self.assertEqual(r.status_code, 409)

    def test_training_route_gibt_409(self):
        from dashboard.quellen import jobs
        with patch("dashboard.quellen.jobs.starte", side_effect=jobs.JobLaeuftSchon("x")):
            r = _client().post("/api/training/run", data={"spur": "spur1"})
        self.assertEqual(r.status_code, 409)


class StatusUnbekannt(unittest.TestCase):

    def test_ohne_herzschlag_beleg_ist_unbekannt(self):
        from dashboard.quellen.spuren import _status
        self.assertEqual(_status({"erlaubt": True, "hs": 45, "alter": None}), "unbekannt")

    def test_sammle_ohne_logdatei_echter_fall(self):
        from dashboard.quellen import spuren as mod
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(mod._ss, "HIER", Path(tmp)), patch.object(mod, "_HIER", Path(tmp)):
            erg = mod.get_spuren()
        self.assertIsInstance(erg, list)


class NotAus(unittest.TestCase):

    def _spur(self, tmp, inhalt: bytes):
        d = Path(tmp) / "xperp"
        d.mkdir()
        (d / "wachen.json").write_bytes(inhalt)
        return d / "wachen.json"

    def test_aendert_nur_das_flag_und_laesst_format(self):
        from dashboard.quellen import prozesse as mod
        orig = b'{\r\n  "handel_erlaubt": true,\r\n  "hs": 45\r\n}\r\n'
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._spur(tmp, orig)
            with patch.object(mod, "_HIER", Path(tmp)):
                r = mod.spur_not_aus("xperp")
            neu = pfad.read_bytes()
            reste = [p.name for p in Path(tmp, "xperp").iterdir()]
        self.assertTrue(r["ok"])
        self.assertEqual(neu, orig.replace(b"true", b"false"))
        self.assertEqual(reste, ["wachen.json"])

    def test_kaputtes_json_scheitert_laut(self):
        from dashboard.quellen import prozesse as mod
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._spur(tmp, b"{ kaputt")
            with patch.object(mod, "_HIER", Path(tmp)):
                r = mod.spur_not_aus("xperp")
            self.assertEqual(pfad.read_bytes(), b"{ kaputt")
        self.assertFalse(r["ok"])

    def test_fehlende_datei_gibt_404(self):
        with tempfile.TemporaryDirectory() as tmp, patch("dashboard.quellen.prozesse._HIER", Path(tmp)):
            r = _client().post("/api/spur/gibtesnicht/notaus")
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.json()["ok"])


class Strom(unittest.TestCase):

    def test_cache_ein_sammle_fuer_alle_clients(self):
        from dashboard.routen import monitor
        monitor._cache.clear()
        zaehler = []

        def fake():
            zaehler.append(1)
            return [{"spur": "x"}]
        with patch("dashboard.quellen.spuren.get_spuren", side_effect=fake):
            async def lauf():
                return await asyncio.gather(*(monitor._aktuell() for _ in range(5)))
            asyncio.run(lauf())
        self.assertEqual(len(zaehler), 1)

    def test_log_strom_ohne_prozess_endet(self):
        from dashboard.quellen import jobs
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "alt.log"
            log.write_text("Rest vom letzten Lauf\n", encoding="utf-8")
            teile = []

            async def sammeln():
                async for ev in jobs.log_strom("kein-prozess-xyz", log, intervall_s=0.01, max_runden=1000):
                    teile.append(ev["data"])
            t0 = time.time()
            asyncio.run(sammeln())
        self.assertLess(time.time() - t0, 2)
        self.assertIn("Rest vom letzten Lauf", "".join(teile))
        self.assertIn("[FERTIG]", "".join(teile))

    def test_job_log_ist_utf8(self):
        from dashboard.quellen import jobs
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "u.log"
            jobs.starte("utf", [sys.executable, "-c", "print('Größe ä')"], cwd=tmp, logdatei=log)
            jobs._laufende["utf"].wait()
            self.assertIn("Größe ä", log.read_text(encoding="utf-8"))


class EventLoopFrei(unittest.TestCase):

    def test_reparatur_und_prognosen_blockieren_loop_nicht(self):
        import threading
        namen = []

        def langsam(*a, **k):
            namen.append(threading.current_thread().name)
            return []
        with patch("dashboard.quellen.reparatur.alle_checks", side_effect=langsam), \
             patch("dashboard.routen.prognosen._prognosen_lesen", side_effect=langsam):
            _client().get("/reparatur")
            _client().get("/prognosen")
        self.assertEqual(len(namen), 2)
        self.assertTrue(all(n.startswith("asyncio_") for n in namen), namen)  # to_thread-Pool


if __name__ == "__main__":
    unittest.main()
