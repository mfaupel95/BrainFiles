"""Tests fuer scan.repos_scannen - lesen nur ein Wegwerf-Verzeichnis."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scan  # noqa: E402


def baue_repo(basis: Path, name: str, *, git=True, venv=False, node_modules=False,
              pyproject=False, package=None, cargo=False, makefile=False,
              readme=True) -> Path:
    d = basis / name
    d.mkdir(parents=True)
    if git:
        (d / ".git").mkdir()
    if venv:
        (d / ".venv" / "Scripts").mkdir(parents=True)
        (d / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
    if node_modules:
        (d / "node_modules").mkdir()
    if pyproject:
        (d / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    if package:
        (d / "package.json").write_text(package, encoding="utf-8")
    if cargo:
        (d / "Cargo.toml").write_text("[package]\nname = 'x'\n", encoding="utf-8")
    if makefile:
        (d / "Makefile").write_text("demo:\n\techo x\n", encoding="utf-8")
    if readme:
        (d / "README.md").write_text("# x\n", encoding="utf-8")
    return d


class ScanTest(unittest.TestCase):
    def test_venv_und_art(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "py-repo", venv=True, pyproject=True)
            baue_repo(basis, "js-repo", node_modules=True,
                      package='{"scripts": {"start": "node x.js"}}')
            baue_repo(basis, "rust-repo", cargo=True)
            baue_repo(basis, "doku-repo")
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertEqual(rs["py-repo"].art, "python")
            self.assertEqual(rs["py-repo"].venv, ".venv")
            self.assertTrue(rs["py-repo"].venv_python.is_file())
            self.assertEqual(rs["js-repo"].art, "node")
            self.assertTrue(rs["js-repo"].node_modules)
            self.assertIsNone(rs["js-repo"].venv)
            self.assertEqual(rs["rust-repo"].art, "rust")
            self.assertEqual(rs["doku-repo"].art, "doku")

    def test_sonderordner_und_nicht_repos(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "echtes-repo", git=True)
            (basis / "copilot-worktrees").mkdir()
            (basis / ".vscode").mkdir()
            (basis / "nur-eine-datei.txt").write_text("x", encoding="utf-8")
            namen = [r.ordner for r in scan.repos_scannen(basis)]
            self.assertEqual(namen, ["echtes-repo"])

    def test_ohne_git_ist_kein_repo(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "ohne-git", git=False, pyproject=True)
            self.assertEqual(scan.repos_scannen(basis), [])

    def test_readme_und_zurueckhaltung(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "mit-readme")
            baue_repo(basis, "ohne-readme", readme=False)
            (basis / "ohne-readme" / ".git" / "x").write_bytes(b"")
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertEqual(rs["mit-readme"].readme, "README.md")
            self.assertIsNone(rs["ohne-readme"].readme)
            self.assertIn("readme fehlt", rs["ohne-readme"].zurueckhaltung)

    def test_art_python_und_node(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "beides", pyproject=True, package='{"scripts": {}}',
                      node_modules=True)
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertEqual(rs["beides"].art, "python+node")

    def test_makefile_zaehlt_nicht_als_art(self):
        with tempfile.TemporaryDirectory() as t:
            basis = Path(t)
            baue_repo(basis, "mit-make", makefile=True, pyproject=True)
            rs = {r.ordner: r for r in scan.repos_scannen(basis)}
            self.assertEqual(rs["mit-make"].art, "python")
            self.assertTrue(rs["mit-make"].makefile)


if __name__ == "__main__":
    unittest.main()
