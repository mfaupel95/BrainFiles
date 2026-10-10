import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

SEITEN = ["monitor", "steuerung", "backtest", "training", "prognosen", "reparatur"]
VERZ = Path(__file__).resolve().parents[2] / "dashboard"


class Vorlagen(unittest.TestCase):

    def _env(self):
        from jinja2 import Environment, FileSystemLoader
        return Environment(loader=FileSystemLoader(str(VERZ / "templates")), autoescape=True)

    def test_jede_seite_markiert_ihren_nav_punkt(self):
        env = self._env()
        for s in SEITEN:
            html = env.get_template(f"{s}.html").render()
            href = "/" if s == "monitor" else f"/{s}"
            self.assertIn(f'<a href="{href}" class="aktiv">', html, s)

    def test_style_enthaelt_catppuccin_token(self):
        css = (VERZ / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn("--base:    #1e1e2e", css)


if __name__ == "__main__":
    unittest.main()
