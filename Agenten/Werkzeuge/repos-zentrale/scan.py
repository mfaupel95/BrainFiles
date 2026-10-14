"""Platte lesen: welche Ordner in einer Wurzel liegen und was sie mitbringen.

Diese Datei kennt das Manifest NICHT. Sie sagt nur, was auf der Platte steht -
venv, node_modules, .git, README und die Einstiegsmerkmale, aus denen die Art
des Projekts folgt. Alles Weitere (Gruppe, Startbefehl, Bot) entscheidet
manifest.py.

Seit 30.09.2026 liest sie nicht mehr nur `Werkstatt`, sondern jede Wurzel
aus `quellen.py`. Zwei Regeln unterscheiden die Wurzeln:

- `nur_git=True` (Bereich REPOS): nur Ordner mit eigenem `.git` werden eine
  Zeile - eine Sammlung von Arbeitsbaeumen ohne Repo ist kein Projekt.
- `nur_git=False` (WERKSTATT, HANDEL): jeder Ordner wird eine Zeile, ausser er
  steht auf der Sperrliste (`quellen.UEBERALL_OHNE` plus wurzeleigene Namen).
  Dort liegen auch Datenfelder und Ausgabeordner, die man oeffnen will.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import quellen

# Ordner, die keine Repos sind: eine Sammlung von Arbeitsbaeumen ohne eigenes
# .git und ein Editor-Konfigurationsordner. Sie bekommen keine Zeile.
ORDNER_OHNE_REPO = {"copilot-worktrees", ".vscode"}
VENV_NAMEN = (".venv", "venv")
README_NAMEN = ("README.md", "README.MD", "readme.md", "README.rst", "README.txt")


@dataclass
class Repo:
    """Ein Verzeichnis ODER eine Werkzeugdatei in einer Wurzel."""

    ordner: str
    pfad: Path                 # das Verzeichnis (auch bei einer Datei: der Ordner darueber)
    art: str
    git: bool
    venv: str | None
    venv_python: Path | None
    node_modules: bool
    readme: str | None
    makefile: bool = False
    zurueckhaltung: list[str] = field(default_factory=list)
    wurzel: str = "repos"          # Kennung aus quellen.py
    pfad_rel: str = ""             # Pfad innerhalb der Wurzel (Schluessel im Manifest)
    datei: Path | None = None      # gesetzt, wenn die Zeile eine DATEI ist

    def __post_init__(self) -> None:
        if not self.pfad_rel:
            self.pfad_rel = self.ordner

    @property
    def ist_datei(self) -> bool:
        return self.datei is not None


def _art(d: Path) -> str:
    """Projektart aus den Merkmalsdateien. Ein Makefile ist kein eigener Typ.

    Die Reihenfolge ist fest (python, node, rust), nicht alphabetisch - damit
    dieselbe Kombination immer gleich heisst. Fehlt jedes Merkmal, entscheidet
    der Inhalt: eine Spur erkennt man an ihren Wachen, ein Datenfeld an seinen
    JSON-Dateien, eine Ablage an nichts davon.
    """
    merkmale = []
    if (d / "pyproject.toml").is_file() or (d / "requirements.txt").is_file():
        merkmale.append("python")
    if (d / "package.json").is_file():
        merkmale.append("node")
    if (d / "Cargo.toml").is_file():
        merkmale.append("rust")
    if merkmale:
        return "+".join(merkmale)
    if (d / "wachen.json").is_file() or (d / "handeln.py").is_file():
        return "spur"
    if (d / "docker-compose.yml").is_file() or (d / "Dockerfile").is_file():
        return "container"
    if any(d.glob("*.py")):
        return "python"
    if any(d.glob("*.md")):
        return "doku"
    if any(d.glob("*.json")):
        return "daten"
    return "ablage"


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
    """Was an diesem Ordner fehlt - nur Beobachtungen, keine Vermutungen."""
    hinweise = []
    if readme is None:
        hinweise.append("readme fehlt")
    return hinweise


def _ein_repo(d: Path, *, wurzel: str, pfad_rel: str) -> Repo:
    venv, venv_python = _venv(d)
    readme = _readme(d)
    return Repo(
        ordner=d.name,
        pfad=d.resolve(),
        art=_art(d),
        git=(d / ".git").is_dir(),
        venv=venv,
        venv_python=venv_python,
        node_modules=(d / "node_modules").is_dir(),
        readme=readme,
        makefile=(d / "Makefile").is_file(),
        zurueckhaltung=_zurueckhaltung(d, readme),
        wurzel=wurzel,
        pfad_rel=pfad_rel,
    )


def ist_werkzeug(datei: Path, rel: str = "") -> bool:
    """Ist diese Datei ein aufrufbares Werkzeug?

    Zwei Merkmale muessen zusammenkommen: ein eigener Einstieg (`__main__`) UND
    eine Argumentliste (`argparse`). Eine Moduldatei ohne beides ist kein
    eigenstaendiges Programm - sie als Zeile zu zeigen liesse das Fenster
    vollaufen (in Agenten/Handel liegen 91 .py-Dateien in der Wurzel, davon 57
    mit Einstieg).

    `rel` ist der Pfad innerhalb der Wurzel (mit "/"): steht er in
    `quellen.WERKZEUG_ZUSATZ`, gilt die Datei ohne weitere Pruefung als
    Werkzeug - so sind auch Dateien in Unterordnern erreichbar.
    """
    if rel and rel in quellen.WERKZEUG_ZUSATZ:
        return True
    if datei.suffix.lower() not in quellen.DATEI_ENDUNGEN:
        return False
    if datei.name in quellen.WERKZEUG_ZUSATZ:
        return True
    try:
        text = datei.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return all(merkmal in text for merkmal in quellen.WERKZEUG_MERKMALE)


def _datei_repo(datei: Path, *, wurzel: str, wurzel_pfad: Path, rel: str = "") -> Repo:
    """Eine Werkzeugdatei als Zeile.

    Das Arbeitsverzeichnis ist die WURZEL, nicht der Ordner der Datei: die
    Haus-Werkzeuge loesen ihre Pfade ueber `__file__` auf (`HIER =
    os.path.dirname(os.path.abspath(__file__))`), und das venv liegt in der
    Wurzel - so lautet jeder Aufruf gleich `.venv\\Scripts\\python.exe <pfad>`.
    """
    venv, venv_python = _venv(wurzel_pfad)
    return Repo(
        ordner=datei.name,
        pfad=Path(wurzel_pfad).resolve(),
        art="werkzeug",
        git=False,
        venv=venv,
        venv_python=venv_python,
        node_modules=(Path(wurzel_pfad) / "node_modules").is_dir(),
        readme=None,
        wurzel=wurzel,
        pfad_rel=rel or datei.name,
        datei=datei.resolve(),
    )


def ordner_scannen(
    basis: Path | str,
    *,
    wurzel: str = "repos",
    nur_git: bool = False,
    ohne: tuple[str, ...] | frozenset[str] = (),
    ohne_git: bool = False,
    dateien: bool = False,
) -> list[Repo]:
    """Alle Ordner einer Wurzel, alphabetisch. Gefiltert nach der Sperrliste.

    Mit `nur_git=True` (Bereich REPOS) kommen nur Ordner mit eigenem `.git`.
    Mit `ohne_git=True` (Bereich WERKSTATT seit 14.10.2026) werden Git-Klone
    uebersprungen - seit dem Umzug liegen die Klone direkt unter Werkstatt und
    gehoeren zum Bereich REPOS, nicht zur Ablage-Zeile.
    Mit `dateien=True` kommen zusaetzlich die Werkzeugdateien der Wurzel selbst
    dazu (`scan.ist_werkzeug`).
    """
    basis = Path(basis)
    if not basis.is_dir():
        return []
    gesperrt = set(quellen.UEBERALL_OHNE) | set(ohne)
    gefunden = []
    for d in sorted(basis.iterdir(), key=lambda p: p.name.lower()):
        if d.is_dir():
            if d.name in gesperrt or d.name.startswith("."):
                continue
            if nur_git and not (d / ".git").is_dir():
                continue
            if ohne_git and (d / ".git").is_dir():
                continue
            gefunden.append(_ein_repo(d, wurzel=wurzel, pfad_rel=d.name))
        elif dateien and ist_werkzeug(d, d.name):
            gefunden.append(
                _datei_repo(d, wurzel=wurzel, wurzel_pfad=basis, rel=d.name)
            )
    if dateien:
        # Werkzeuge in Unterordnern: nur die ausdruecklich genannten
        # (quellen.WERKZEUG_ZUSATZ). Eine Suche in allen Unterordnern wuerde in
        # Agenten/Handel das Fremdprojekt OpenAlice mit 130 Dateien einblenden.
        schon = {(r.wurzel, r.pfad_rel) for r in gefunden}
        for rel in quellen.WERKZEUG_ZUSATZ:
            if "/" not in rel or (wurzel, rel) in schon:
                continue
            datei = basis / Path(rel)
            if datei.is_file():
                gefunden.append(
                    _datei_repo(datei, wurzel=wurzel, wurzel_pfad=basis, rel=rel)
                )
    return sorted(gefunden, key=lambda r: r.ordner.lower())


def repos_scannen(basis: Path | str) -> list[Repo]:
    """Alle Git-Repos unter `basis`, alphabetisch. Nicht-Repos werden uebergangen.

    Der Weg von vor dem 30.09.2026 - er bleibt, weil Auswertungen und Tests ihn
    nutzen (das ist der Bereich REPOS).
    """
    return ordner_scannen(basis, wurzel="repos", nur_git=True, ohne=("copilot-worktrees",))


def tief_scannen(wurzel_obj: quellen.Wurzel, basis: Path | str) -> list[Repo]:
    """Eine Wurzel scannen - bei `tiefe >= 2` auch die Enkelordner.

    Zwei Ebenen entstehen dort, wo ein Ordner viele gleichartige Unterordner
    hat und selbst keine Merkmalsdatei traegt (`Werkstatt/Projekte/*`). Ein
    Elternordner behaelt seine Zeile nur, wenn er selbst etwas zeigt (README
    oder Merkmalsdatei) - sonst stuende er als leere Huelle neben seinen
    Kindern.
    """
    basis = Path(basis)
    ergebnis = ordner_scannen(
        basis, wurzel=wurzel_obj.kennung, nur_git=wurzel_obj.nur_git,
        ohne=wurzel_obj.ohne, ohne_git=wurzel_obj.ohne_git,
        dateien=wurzel_obj.dateien,
    )
    if wurzel_obj.tiefe <= 1 or not basis.is_dir():
        return ergebnis
    gesperrt = set(quellen.UEBERALL_OHNE) | set(wurzel_obj.ohne)
    huelle = set()
    for d in sorted(basis.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir() or d.name in gesperrt or d.name.startswith("."):
            continue
        kinder = [
            u
            for u in sorted(d.iterdir(), key=lambda p: p.name.lower())
            if u.is_dir() and u.name not in gesperrt and not u.name.startswith(".")
        ]
        if not kinder:
            continue
        huelle.add(d.name)
        for unter in kinder:
            ergebnis.append(
                _ein_repo(unter, wurzel=wurzel_obj.kennung, pfad_rel=f"{d.name}/{unter.name}")
            )
    return [
        r
        for r in ergebnis
        if r.ordner not in huelle or r.readme is not None or r.art not in ("ablage", "daten")
    ]
