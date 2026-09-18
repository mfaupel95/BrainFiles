"""Kommandos bauen und ausfuehren. Kennt kein tkinter und kein Manifest-Layout.

Regeln, die hier durchgesetzt werden:
- Jeder Befehl ist eine argv-Liste, nie eine Shell-Zeichenkette (kein shell=True).
- Ein Start ohne belegten Befehl startet nichts und sagt warum.
- Die Ausgabe jedes Starts landet in einer Logdatei - das ist der Beleg.
- Ein fehlendes Programm ist ein Fehlertext, kein Absturz.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

UNSICHERE_ZEICHEN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class StartErgebnis:
    """Was ein Startversuch ergeben hat."""

    pid: int | None
    log: Path
    argv: list[str] = field(default_factory=list)
    fehler: str | None = None


def argv_ordner(pfad: Path) -> list[str]:
    """Ordner im Explorer zeigen."""
    return ["explorer", str(pfad)]


def argv_terminal(pfad: Path) -> list[str]:
    """Windows Terminal im Ordner oeffnen (wt.exe ist auf diesem Rechner da)."""
    return ["wt.exe", "-d", str(pfad)]


def argv_bot(bot: str, pfad: Path) -> tuple[list[str], Path]:
    """Der Bot-Chat: Profilnamen klein, Arbeitsverzeichnis = Repo."""
    return ["hermes", "-p", str(bot).lower(), "chat"], Path(pfad)


def log_pfad(log_ordner: Path, name: str, jetzt: datetime) -> Path:
    """Logdatei je Start. Der Name wird entschaerft - kein Pfad, kein Aufstieg."""
    sauber = UNSICHERE_ZEICHEN.sub("_", str(name)).strip("_")
    sauber = re.sub(r"\.{2,}", "_", sauber).strip(".")  # kein "..", kein Endpunkt
    return Path(log_ordner) / f"{sauber or 'start'}-{jetzt:%Y%m%d-%H%M}.log"


def ereignis_anhaengen(log: Path, text: str) -> None:
    """Eine Zeile an eine bestehende Logdatei haengen (z. B. Exit-Code)."""
    try:
        with open(log, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {text}\n")
    except OSError:
        pass


def start_ausfuehren(
    zeile,
    log_ordner: Path | str,
    *,
    popen=subprocess.Popen,
    jetzt: datetime | None = None,
) -> StartErgebnis:
    """Den Startbefehl einer Zeile ausfuehren. Startet nur, was belegt ist."""
    jetzt = jetzt or datetime.now()
    log = log_pfad(Path(log_ordner), getattr(zeile, "ordner", "start"), jetzt)
    argv = list(getattr(zeile, "start", None) or [])
    if not argv:
        return StartErgebnis(None, log, [], "kein Startbefehl belegt")

    repo = getattr(zeile, "repo", None)
    cwd = Path(repo.pfad) if repo is not None else Path(".")
    Path(log_ordner).mkdir(parents=True, exist_ok=True)
    try:
        with open(log, "ab") as f:
            f.write(
                f"# {zeile.ordner} {jetzt:%Y-%m-%d %H:%M:%S} "
                f"cwd={cwd} argv={argv}\n".encode("utf-8")
            )
            prozess = popen(
                argv,
                cwd=str(cwd),
                stdout=f,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
        return StartErgebnis(None, log, argv, f"{type(e).__name__}: {e}")
    return StartErgebnis(getattr(prozess, "pid", None), log, argv)


def doku_oeffnen(datei: Path, *, starter=None) -> str | None:
    """Die erste README im Standardprogramm oeffnen. Gibt den Fehlertext zurueck."""
    starter = starter or os.startfile  # type: ignore[attr-defined]
    try:
        starter(str(datei))
    except OSError as e:
        return f"{type(e).__name__}: {e}"
    return None
