# dashboard/quellen/jobs.py - Hintergrundlaeufe mit Logdatei und SSE-Strom
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

_laufende: dict[str, subprocess.Popen] = {}


def starte(name: str, argv: list[str], cwd, logdatei: Path) -> None:
    """Startet argv (ohne Shell) und schreibt stdout+stderr in logdatei."""
    logdatei = Path(logdatei)
    logdatei.parent.mkdir(parents=True, exist_ok=True)
    with open(logdatei, "w", encoding="utf-8") as log:
        _laufende[name] = subprocess.Popen(
            argv, stdout=log, stderr=subprocess.STDOUT, cwd=str(cwd))


async def log_strom(name: str, logdatei: Path, intervall_s: float = 1.0, max_runden: int = 300):
    """Gibt neue Logzeilen als SSE-Events aus; endet mit [FERTIG] oder nach max_runden."""
    logdatei = Path(logdatei)
    pos = 0
    for _ in range(max_runden):
        proc = _laufende.get(name)
        fertig = proc is not None and proc.poll() is not None
        if logdatei.is_file():
            text = logdatei.read_text(encoding="utf-8", errors="replace")
            if len(text) > pos:
                yield {"data": text[pos:]}
                pos = len(text)
        if fertig:
            yield {"data": "\n[FERTIG]\n"}
            return
        await asyncio.sleep(intervall_s)
