"""Die Wurzeln der Zentrale: welche Orte sie zeigt und was daraus eine Zeile wird.

Die Zentrale war bis 30.09.2026 auf `Werkstatt/Repos` festgelegt. Sie zeigt
jetzt drei **Bereiche** - jede mit eigenem Wurzelordner, eigener Sperrliste und
eigener Regel, was ueberhaupt eine Zeile bekommt:

| Kennung | Bereich | Wurzel | Regel |
|---|---|---|---|
| `repos` | REPOS | `Werkstatt/Repos` | nur Klone mit `.git` (wie bisher) |
| `werkstatt` | WERKSTATT | `Werkstatt` | Projekt- und Ablageordner; `Repos`/`Projekte` sind eigene Wurzeln |
| `handel` | HANDEL | `Agenten/Handel` | Spuren, Werkzeuge, Ausgabefelder |

Diese Datei kennt weder tkinter noch das Manifest - sie ist ohne Fenster
pruefbar (`tests/test_quellen.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Ordner, die in JEDER Wurzel keine Zeile bekommen: Interpreter, Caches und
# Editor-/Werkzeugzustand. Bewusst als Namen (nicht als Muster), damit eine
# Sperre nicht versehentlich ein echtes Projekt trifft.
UEBERALL_OHNE = frozenset(
    {
        ".git", ".venv", "venv", "__pycache__", "node_modules", ".vscode",
        ".pytest_cache", ".claude", ".devcontainer", ".docker", ".onchainos",
        ".mypy_cache", ".ruff_cache", "cache",
    }
)

# Dateiendungen, die als eigene Zeile erscheinen duerfen (nur in Wurzeln mit
# `dateien=True`). Ein .py ohne eigenen Einstieg wird NICHT gezeigt - sonst
# stuenden in Handel/ 91 Moduldateien neben 45 Ordnern.
DATEI_ENDUNGEN = (".py",)

# Kennzeichen eines Werkzeugs, das man wirklich aufrufen kann: es deklariert
# einen Einstieg UND nimmt Argumente entgegen. Wer eine CLI ohne argparse baut,
# kann sie mit 'datei hinzufuegen' im Manifest trotzdem sichtbar machen.
WERKZEUG_MERKMALE = ("__main__", "argparse")

# Ausnahmen von der Regel oben: Dateien, die einen eigenen Einstieg haben, aber
# keine Argumente auswerten - und die man trotzdem im Fenster sehen will (ein
# Fenster, eine Sonde, eine Kennzahlen-Tafel). Bewusst eine kurze, ausdrueckliche
# Liste: eine .py-Datei ohne Einstieg wird hier NICHT aufgenommen.
WERKZEUG_ZUSATZ = (
    "leitstand.py",                 # das grosse Fenster (Ueberwachen/Freigaben/Backtests)
    "pruefe_ratschen.py",           # Tafel: Herkunft der Drawdown-Ratsche je Spur
    "strategie_kennzahlen.py",      # t-Statistik und Stop-Vorschlag je Spur
    "kraken_abweisungs_sonde.py",   # Sonde: haelt eine Kraken-Abweisung als Zeugen fest
)


@dataclass(frozen=True)
class Wurzel:
    """Ein Ort, den die Zentrale zeigt."""

    kennung: str                 # "repos" - Schluessel im Manifest
    titel: str                   # Ueberschrift im Fenster (Versalien)
    erklaerung: str              # eine Zeile unter der Ueberschrift
    pfad_rel: str                # relativ zur BrainFiles-Wurzel
    nur_git: bool = False        # nur Ordner mit eigenem .git
    ohne: tuple[str, ...] = ()   # Namen, die hier keine Zeile bekommen (zusaetzlich zu UEBERALL_OHNE)
    tiefe: int = 1               # 1 = direkte Kinder, 2 = auch eine Ebene tiefer
    dateien: bool = False        # auch Werkzeug-Dateien in der Wurzel zeigen

    def pfad(self, brainfiles: Path) -> Path:
        return Path(brainfiles) / self.pfad_rel


# Die feste Reihenfolge im Fenster. REPOS zuerst: das ist der gewachsene Teil.
WURZELN: tuple[Wurzel, ...] = (
    Wurzel(
        kennung="repos",
        titel="REPOS",
        erklaerung="geklonte Fremd-Repos unter Werkstatt/Repos, je Repo ein Bot",
        pfad_rel="Werkstatt/Repos",
        nur_git=True,
        ohne=("copilot-worktrees",),
    ),
    Wurzel(
        kennung="werkstatt",
        titel="WERKSTATT",
        erklaerung="eigene Projekte, Datenfelder und Ablagen unter Werkstatt/",
        pfad_rel="Werkstatt",
        ohne=("Repos", "Projekte"),
    ),
    Wurzel(
        kennung="handel",
        titel="HANDEL",
        erklaerung="Spuren, Werkzeuge und Ausgaben unter Agenten/Handel",
        pfad_rel="Agenten/Handel",
        ohne=("docs", "tests", "daten", "daten.bak-20260919"),
        dateien=True,
    ),
)

# Die Projekte-Unterordner gehoeren in den Bereich WERKSTATT, stehen aber eine
# Ebene tiefer. Eigene Wurzel mit demselben Bereich - so bleiben Wurzel und
# Bereich getrennt und die Anzeige trotzdem flach.
PROJEKTE = Wurzel(
    kennung="projekte",
    titel="WERKSTATT · PROJEKTE",
    erklaerung="Datenfelder und Projektstaende unter Werkstatt/Projekte",
    pfad_rel="Werkstatt/Projekte",
)

# Anzeige-Reihenfolge der Wurzeln (die Kennung `projekte` haengt an WERKSTATT).
REIHENFOLGE: tuple[str, ...] = ("repos", "werkstatt", "projekte", "handel")

# Zuordnung Wurzel -> Bereich (Ueberschrift). Zwei Wurzeln koennen sich einen
# Bereich teilen: Werkstatt und Werkstatt/Projekte.
BEREICHE: dict[str, str] = {
    "repos": "REPOS",
    "werkstatt": "WERKSTATT",
    "projekte": "WERKSTATT",
    "handel": "HANDEL",
}

BEREICH_ERKLAERUNG: dict[str, str] = {
    "REPOS": "Fremd-Klone, je Repo ein Bot",
    "WERKSTATT": "eigene Projekte und Ablagen",
    "HANDEL": "Spuren, Werkzeuge, Ausgaben",
}


_NACH_KENNUNG = {w.kennung: w for w in (*WURZELN, PROJEKTE)}


def alle(brainfiles: Path) -> list[tuple[Wurzel, Path]]:
    """Alle Wurzeln mit aufgeloestem Pfad, in Anzeige-Reihenfolge."""
    return [(_NACH_KENNUNG[k], _NACH_KENNUNG[k].pfad(brainfiles)) for k in REIHENFOLGE]


def wurzel_von(kennung: str) -> Wurzel | None:
    """Die Wurzel zu einer Kennung - None, wenn das Manifest etwas Fremdes nennt."""
    return _NACH_KENNUNG.get(kennung)


def bereich(kennung: str) -> str:
    """Die Bereichs-Ueberschrift einer Wurzel-Kennung (unbekannt -> REPOS)."""
    return BEREICHE.get(kennung, "REPOS")
