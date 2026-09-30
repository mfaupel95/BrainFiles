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
    prozess: object | None = None   # Prozesshandle (Popen), fuer Warten/Beenden


def argv_ordner(pfad: Path, datei: Path | None = None) -> list[str]:
    """Ordner im Explorer zeigen - bei einer Werkzeugdatei die DATEI markieren."""
    if datei is not None:
        return ["explorer", f"/select,{datei}"]
    return ["explorer", str(pfad)]


# Windows Terminal oeffnet je Aufruf ein NEUES FENSTER - acht Klicks, acht
# Fenster. Gemessen am 30.09.2026: mit `-w 0` landet der Aufruf als TAB im
# vorhandenen Fenster (Fensterzahl 1 -> 1, Probe in Agenten/Hermes/cache/scratch/
# wt_probe.ps1); ohne vorhandenes Fenster legt `wt` eines an. Deshalb traegt
# JEDER Aufruf unten diesen Schalter - und nur hier wird er gebaut.
WT_FENSTER = ("-w", "0")


def argv_terminal(pfad: Path) -> list[str]:
    """Windows Terminal im Ordner oeffnen - als Tab im vorhandenen Fenster."""
    return ["wt.exe", *WT_FENSTER, "-d", str(pfad)]


def _cmd_zeile(cmd: list[str], log: Path | None) -> str:
    """Einen argv zu EINER cmd-Zeile machen (cmd braucht sie als ein Argument).

    Tokens mit Leerzeichen werden gequotet; `>`/`2>&1` versteht cmd selbst. Ist
    ein Log angegeben, geht die Ausgabe dorthin - der Tab schliesst sich gleich
    wieder, ohne Log waere die Ausgabe weg.
    """
    teile = [f'"{t}"' if " " in str(t) else str(t) for t in cmd]
    zeile = " ".join(teile)
    if log is not None:
        zeile += f' > "{log}" 2>&1'
    return zeile


def argv_befehl_im_terminal(pfad: Path, cmd: list[str], log: Path | None = None) -> list[str]:
    """Einen Befehl in einem Tab ausfuehren; `/c` schliesst ihn danach wieder.

    `/c` statt `/k` (Entscheidung Max, 30.09.2026): der Tab raeumt sich selbst
    weg, statt liegen zu bleiben. Damit die Ausgabe trotzdem da ist, wird sie
    bei angegebenem `log` mitgeschrieben - die Statuszeile nennt den Pfad.
    """
    return ["wt.exe", *WT_FENSTER, "-d", str(pfad),
            "cmd.exe", "/c", _cmd_zeile(cmd, log)]


def argv_bot_chat(bot: str, pfad: Path) -> list[str]:
    """Den Bot-Chat als Tab oeffnen (Chat bleibt offen - das ist eine Sitzung)."""
    argv, cwd = argv_bot(bot, pfad)
    return ["wt.exe", *WT_FENSTER, "-d", str(cwd), *argv]


def argv_bot_auftrag(bot: str, pfad: Path, auftrag: str) -> list[str]:
    """Den Repo-Bot mit einem fertigen Auftrag starten (Einzelauftrag, kein Chat)."""
    return ["wt.exe", *WT_FENSTER, "-d", str(pfad),
            "hermes", "-p", str(bot).lower(), "chat", "-q", str(auftrag)]


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
    # Windows loest ein RELATIVES Programm gegen das Arbeitsverzeichnis des
    # AUFRUFERS auf, nicht gegen `cwd` des Kindes. Ein Manifest-Eintrag wie
    # ".venv\\Scripts\\pythonw.exe" scheitert deshalb mit FileNotFoundError,
    # obwohl die Datei im Repo liegt - also hier gegen das Repo aufloesen.
    programm = Path(argv[0])
    if not programm.is_absolute():
        im_repo = cwd / programm
        if im_repo.exists():
            argv = [str(im_repo)] + argv[1:]
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
    return StartErgebnis(getattr(prozess, "pid", None), log, argv, None, prozess)


def doku_oeffnen(datei: Path, *, starter=None) -> str | None:
    """Die erste README im Standardprogramm oeffnen. Gibt den Fehlertext zurueck."""
    starter = starter or os.startfile  # type: ignore[attr-defined]
    try:
        starter(str(datei))
    except OSError as e:
        return f"{type(e).__name__}: {e}"
    return None
