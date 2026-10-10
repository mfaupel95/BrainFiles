# dashboard/quellen/jobs.py - Hintergrundlaeufe mit Logdatei und SSE-Strom
from __future__ import annotations

import asyncio
import codecs
import os
import subprocess
import threading
from pathlib import Path

_laufende: dict[str, subprocess.Popen] = {}
_sperre = threading.Lock()


class JobLaeuftSchon(RuntimeError):
    """Fuer diesen Namen laeuft bereits ein Prozess."""


def starte(name: str, argv: list[str], cwd, logdatei: Path) -> None:
    """Startet argv (ohne Shell) und schreibt stdout+stderr in logdatei.

    Wirft JobLaeuftSchon, solange der vorige Lauf gleichen Namens noch lebt.
    """
    logdatei = Path(logdatei)
    logdatei.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    with _sperre:
        alt = _laufende.get(name)
        if alt is not None and alt.poll() is None:
            raise JobLaeuftSchon(name)
        with open(logdatei, "w", encoding="utf-8") as log:
            _laufende[name] = subprocess.Popen(
                argv, stdout=log, stderr=subprocess.STDOUT, cwd=str(cwd), env=env)


def _neues(logdatei: Path, pos: int, dec) -> tuple[str, int]:
    """Liest ab Byte-Position pos; gibt (Text, neue Position) zurueck."""
    if not logdatei.is_file():
        return "", pos
    with open(logdatei, "rb") as f:
        f.seek(pos)
        roh = f.read()
    return dec.decode(roh), pos + len(roh)


async def log_strom(name: str, logdatei: Path, intervall_s: float = 1.0, max_runden: int = 300):
    """Gibt neue Logzeilen als SSE-Events aus; endet mit [FERTIG] oder nach max_runden.

    Kennt der Server den Prozess nicht (Neustart, Seite neu geladen), wird der
    Stand der Datei einmal ausgegeben und der Strom beendet.
    """
    logdatei = Path(logdatei)
    pos = 0
    dec = codecs.getincrementaldecoder("utf-8")("replace")
    for _ in range(max_runden):
        proc = _laufende.get(name)
        fertig = proc is None or proc.poll() is not None
        text, pos = await asyncio.to_thread(_neues, logdatei, pos, dec)
        if text:
            yield {"data": text}
        if fertig:
            yield {"data": "\n[FERTIG]\n"}
            return
        await asyncio.sleep(intervall_s)
