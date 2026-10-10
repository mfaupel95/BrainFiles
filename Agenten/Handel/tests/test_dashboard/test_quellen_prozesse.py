# tests/test_dashboard/test_quellen_prozesse.py
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TestSpurNotAus(unittest.TestCase):

    def test_not_aus_setzt_handel_erlaubt_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            spur_dir = p / "xperp"
            spur_dir.mkdir()
            wachen = spur_dir / "wachen.json"
            wachen.write_text(json.dumps({"handel_erlaubt": True, "herzschlag_max_minuten": 45}),
                              encoding="utf-8")
            from dashboard.quellen import prozesse as mod
            with patch.object(mod, "_HIER", p):
                result = mod.spur_not_aus("xperp")
            self.assertTrue(result["ok"])
            d = json.loads(wachen.read_text(encoding="utf-8"))
            self.assertFalse(d["handel_erlaubt"])

    def test_not_aus_fehlende_wachen_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "xperp").mkdir()
            from dashboard.quellen import prozesse as mod
            with patch.object(mod, "_HIER", p):
                result = mod.spur_not_aus("xperp")
            self.assertFalse(result["ok"])
            self.assertIn("wachen.json", result["meldung"])

    def test_not_aus_lehnt_pfadtricks_ab(self):
        # Der Spurname kommt aus der URL: nie aus dem Handel-Ordner hinausschreiben.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "handel"
            p.mkdir()
            fremd = Path(tmp) / "fremd"
            fremd.mkdir()
            (fremd / "wachen.json").write_text(json.dumps({"handel_erlaubt": True}), encoding="utf-8")
            from dashboard.quellen import prozesse as mod
            with patch.object(mod, "_HIER", p):
                for boese in ("../fremd", "..\fremd", "a/b", ""):
                    self.assertFalse(mod.spur_not_aus(boese)["ok"], boese)
            self.assertTrue(json.loads((fremd / "wachen.json").read_text(encoding="utf-8"))["handel_erlaubt"])

    def test_systemprozesse_gibt_liste_zurueck(self):
        from dashboard.quellen import prozesse as mod
        with patch.object(mod, "_pid_dauerlauf", return_value=None), \
             patch.object(mod, "_omnitrade_laeuft", return_value=False):
            result = mod.systemprozesse()
        self.assertIsInstance(result, list)
        self.assertTrue(any(p["name"] == "dauerlauf" for p in result))


class TestSystemProzessLaeuft(unittest.TestCase):

    def test_dauerlauf_laeuft_wenn_pid_lebt(self):
        from dashboard.quellen import prozesse as mod
        with patch.object(mod, "_pid_dauerlauf", return_value=1234), \
             patch.object(mod, "_prozess_lebt", return_value=True), \
             patch.object(mod, "_omnitrade_laeuft", return_value=False):
            result = mod.systemprozesse()
        dl = next(p for p in result if p["name"] == "dauerlauf")
        self.assertTrue(dl["laeuft"])


if __name__ == "__main__":
    unittest.main()
