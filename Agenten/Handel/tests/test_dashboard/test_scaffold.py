import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class Geruest(unittest.TestCase):
    def test_app_baut_ohne_crash(self):
        from dashboard.app import create_app
        self.assertEqual(create_app().title, "Omnitrade Dashboard")

    def test_lan_ohne_passwort_beendet_main(self):
        import subprocess
        r = subprocess.run([sys.executable, "-m", "dashboard", "--lan"], cwd=Path(__file__).resolve().parents[2],
                           capture_output=True, text=True, env={"PATH": "", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")})
        self.assertEqual(r.returncode, 1)
        self.assertIn("DASHBOARD_PASS", r.stderr)


if __name__ == "__main__":
    unittest.main()
