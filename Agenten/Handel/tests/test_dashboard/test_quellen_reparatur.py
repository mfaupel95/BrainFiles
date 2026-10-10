# tests/test_dashboard/test_quellen_reparatur.py
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestReparaturChecks(unittest.TestCase):

    def test_zombie_pid_erkannt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "dauerlauf.pid").write_text("99999\n", encoding="utf-8")
            from dashboard.quellen import reparatur as mod
            with patch.object(mod, "_HIER", p), \
                 patch("dashboard.quellen.prozesse._prozess_lebt", return_value=False):
                befunde = mod.alle_checks()
        self.assertIn("zombie_pid", [b["id"] for b in befunde])

    def test_kein_zombie_wenn_prozess_lebt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "dauerlauf.pid").write_text("1\n", encoding="utf-8")
            from dashboard.quellen import reparatur as mod
            with patch.object(mod, "_HIER", p), \
                 patch("dashboard.quellen.prozesse._prozess_lebt", return_value=True):
                befunde = mod.alle_checks()
        self.assertNotIn("zombie_pid", [b["id"] for b in befunde])

    def test_log_veraltet_erkannt(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            log = p / "dauerlauf.log"
            log.write_text("", encoding="utf-8")
            os.utime(log, (time.time() - 7200, time.time() - 7200))
            from dashboard.quellen import reparatur as mod
            with patch.object(mod, "_HIER", p):
                befunde = mod.alle_checks()
        self.assertIn("log_veraltet", [b["id"] for b in befunde])

    def test_fenster_offen_ohne_prozess(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            bis = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            (p / "freigabe_fenster.json").write_text(
                json.dumps({"xperp": {"offen_bis": bis}}), encoding="utf-8")
            from dashboard.quellen import reparatur as mod
            with patch.object(mod, "_HIER", p):
                befunde = mod.alle_checks()
        self.assertIn("fenster_offen_xperp", [b["id"] for b in befunde])

    def test_fix_zombie_loescht_pid_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            pid = p / "dauerlauf.pid"
            pid.write_text("99999\n", encoding="utf-8")
            from dashboard.quellen import reparatur as mod
            with patch.object(mod, "_HIER", p):
                r = mod.fix_ausfuehren("zombie_pid")
            self.assertTrue(r["ok"])
            self.assertFalse(pid.exists())

    def test_fix_unbekannt_meldet_fehler(self):
        from dashboard.quellen import reparatur as mod
        self.assertFalse(mod.fix_ausfuehren("gibt_es_nicht")["ok"])


if __name__ == "__main__":
    unittest.main()
