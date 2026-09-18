"""Platte lesen: welche Repos liegen unter Werkstatt/Repos und was bringen sie mit.

Diese Datei kennt das Manifest NICHT. Sie sagt nur, was auf der Platte steht -
venv, node_modules, .git, README und die Einstiegsmerkmale, aus denen die Art
des Projekts folgt. Alles Weitere (Gruppe, Startbefehl, Bot) entscheidet
manifest.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Ordner, die keine Repos sind: eine Sammlung von Arbeitsbaeumen ohne eigenes
# .git und ein Editor-Konfigurationsordner. Sie bekommen keine Zeile.
ORDNER_OHNE_REPO = {"copilot-worktrees", ".vscode"}
VENV_NAMEN = (".venv", "venv")
README_NAMEN = ("README.md", "README.MD", "readme.md", "README.rst", "README.txt")


@dataclass
class Repo:
    """Ein Verzeichnis unter Werkstatt/Repos, das ein Git-Repo ist."""

    ordner: str
    pfad: Path
    art: str
    git: bool
    venv: str | None
    venv_python: Path | None
    node_modules: bool
    readme: str | None
    makefile: bool = False
    zurueckhaltung: list[str] = field(default_factory=list)


def _art(d: Path) -> str:
    """Projektart aus den Merkmalsdateien. Ein Makefile ist kein eigener Typ.

    Die Reihenfolge ist fest (python, node, rust), nicht alphabetisch - damit
    dieselbe Kombination immer gleich heisst.
    """
    merkmale = []
    if (d / "pyproject.toml").is_file() or (d / "requirements.txt").is_file():
        merkmale.append("python")
    if (d / "package.json").is_file():
        merkmale.append("node")
    if (d / "Cargo.toml").is_file():
        merkmale.append("rust")
    return "+".join(merkmale) if merkmale else "doku"


def _venv(d: Path) -> tuple[str | None, Path | None]:
    for name in VENV_NAMEN:
        py = d / name / "Scripts" / "python.exe"
        if py.is_file():
            return name, py
    return None, None


def _readme(d: Path) -> str | None:
    for name in README_NAMEN:
        if (d / name).is_file():
            return name
    return None


def _zurueckhaltung(d: Path, readme: str | None) -> list[str]:
    """Was an diesem Repo fehlt - nur Beobachtungen, keine Vermutungen."""
    hinweise = []
    if readme is None:
        hinweise.append("readme fehlt")
    return hinweise


def repos_scannen(basis: Path | str) -> list[Repo]:
    """Alle Git-Repos unter `basis`, alphabetisch. Nicht-Repos werden uebergangen."""
    basis = Path(basis)
    if not basis.is_dir():
        return []
    gefunden = []
    for d in sorted(basis.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir() or d.name in ORDNER_OHNE_REPO or d.name.startswith("."):
            continue
        if not (d / ".git").is_dir():
            continue
        venv, venv_python = _venv(d)
        readme = _readme(d)
        gefunden.append(
            Repo(
                ordner=d.name,
                pfad=d.resolve(),
                art=_art(d),
                git=True,
                venv=venv,
                venv_python=venv_python,
                node_modules=(d / "node_modules").is_dir(),
                readme=readme,
                makefile=(d / "Makefile").is_file(),
                zurueckhaltung=_zurueckhaltung(d, readme),
            )
        )
    return gefunden
