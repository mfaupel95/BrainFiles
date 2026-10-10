# tests/test_dashboard/test_api_sekundaer.py - Backtest, Training, Prognosen, Reparatur
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HANDEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HANDEL))

from fastapi.testclient import TestClient  # noqa: E402


def _client():
    from dashboard.app import create_app
    return TestClient(create_app(), base_url="http://localhost")


class TestJobs(unittest.TestCase):

    def test_job_laeuft_und_meldet_fertig(self):
        import asyncio
        from dashboard.quellen import jobs
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "x.log"
            jobs.starte("t", [sys.executable, "-c", "print('hallo')"], cwd=tmp, logdatei=log)
            teile = []

            async def sammeln():
                async for ev in jobs.log_strom("t", log, intervall_s=0.05, max_runden=200):
                    teile.append(ev["data"])
            asyncio.run(sammeln())
        text = "".join(teile)
        self.assertIn("hallo", text)
        self.assertIn("[FERTIG]", text)


class TestBacktest(unittest.TestCase):

    def test_seite_200(self):
        with patch("dashboard.quellen.spuren.get_spuren", return_value=[]):
            self.assertEqual(_client().get("/backtest").status_code, 200)

    def test_run_startet_ruecktest_als_skript(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/backtest/run", data={"spur": "xperp", "tage": "30"})
        self.assertEqual(r.status_code, 200)
        argv = st.call_args.args[1]
        self.assertTrue(argv[1].endswith("xperp_ruecktest.py"))
        self.assertEqual(argv[2:], ["--tage", "30"])

    def test_run_unbekannte_spur_abgelehnt(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/backtest/run", data={"spur": "--evil", "tage": "30"})
        self.assertEqual(r.status_code, 400)
        st.assert_not_called()

    def test_run_tage_ausserhalb_abgelehnt(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/backtest/run", data={"spur": "xperp", "tage": "100000"})
        self.assertEqual(r.status_code, 422)
        st.assert_not_called()

    def test_run_fremde_origin_abgelehnt(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/backtest/run", data={"spur": "xperp", "tage": "30"},
                               headers={"Origin": "http://boese.example"})
        self.assertEqual(r.status_code, 403)
        st.assert_not_called()


class TestTraining(unittest.TestCase):

    def test_seite_200(self):
        self.assertEqual(_client().get("/training").status_code, 200)

    def test_run_startet_lauf_py_ohne_kerzenabruf(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/training/run", data={"spur": "spur1"})
        self.assertEqual(r.status_code, 200)
        argv = st.call_args.args[1]
        self.assertTrue(argv[1].endswith("lauf.py"))
        self.assertEqual(argv[2:], ["--spur", "spur1", "--ohne-kerzen-abruf"])

    def test_run_unbekannte_spur_abgelehnt(self):
        with patch("dashboard.quellen.jobs.starte") as st:
            r = _client().post("/api/training/run", data={"spur": "../x"})
        self.assertEqual(r.status_code, 400)
        st.assert_not_called()


class TestPrognosen(unittest.TestCase):

    def test_liest_dict_und_liste_und_ueberspringt_venv(self):
        from dashboard.routen import prognosen
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "a").mkdir()
            (p / "a" / "prognose.json").write_text(json.dumps({"richtung": "long"}), encoding="utf-8")
            (p / "b").mkdir()
            (p / "b" / "prognose.json").write_text(json.dumps([{"richtung": "short"}]), encoding="utf-8")
            (p / ".venv" / "x").mkdir(parents=True)
            (p / ".venv" / "x" / "prognose.json").write_text("{}", encoding="utf-8")
            with patch.object(prognosen, "_HIER", p):
                erg = prognosen._prognosen_lesen()
        richtungen = sorted(e["richtung"] for e in erg)
        self.assertEqual(richtungen, ["long", "short"])

    def test_seite_200(self):
        with patch("dashboard.routen.prognosen._prognosen_lesen", return_value=[]):
            self.assertEqual(_client().get("/prognosen").status_code, 200)


class TestReparaturRoute(unittest.TestCase):

    def test_seite_zeigt_befund(self):
        befund = [{"id": "zombie_pid", "titel": "Zombie-PID", "beschreibung": "x", "behebbar": True}]
        with patch("dashboard.quellen.reparatur.alle_checks", return_value=befund):
            r = _client().get("/reparatur")
        self.assertEqual(r.status_code, 200)
        self.assertIn("/api/repair/zombie_pid", r.text)

    def test_repair_ruft_fix(self):
        with patch("dashboard.quellen.reparatur.fix_ausfuehren", return_value={"ok": True, "meldung": "m"}) as f:
            r = _client().post("/api/repair/zombie_pid")
        self.assertTrue(r.json()["ok"])
        f.assert_called_once_with("zombie_pid")

    def test_repair_fremde_origin_abgelehnt(self):
        with patch("dashboard.quellen.reparatur.fix_ausfuehren") as f:
            r = _client().post("/api/repair/zombie_pid", headers={"Origin": "http://boese.example"})
        self.assertEqual(r.status_code, 403)
        f.assert_not_called()


if __name__ == "__main__":
    unittest.main()
