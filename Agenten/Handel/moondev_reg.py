"""
🌙 MoonDev-Agenten-Registrierung (T-262)

Jeder Agent (egal ob vom Treiber oder von der GUI gestartet) registriert
seine PID in einem gemeinsamen Ordner. Der Treiber-Waisenputzer liest dort
nach und lässt registrierte Prozesse in Ruhe.


Start eines Agents (am Anfang der main()-Funktion, AFTER Popen):
    from moondev_reg import registriere
    registriere()          # erstellt eine <pid>.moon-Datei

Das genügt – der Treiber liest alle <pid>.moon-Dateien aus dem Ordner
und behandelt deren PIDs als "behalten", unabhängig davon, wer den Prozess
gestartet hat.


Der Ordner:
    $TEMP/moondev_agenten/      (Windows: %TEMP%)
    darf von mehreren Prozessen gleichzeitig geschrieben werden (jeder
    schreibt nur seine eigene Datei, keine Konflikte).
"""
from __future__ import annotations
import os
import time
from pathlib import Path

# ---------------------------------------------------------------- Ordner
_TEMP = os.getenv("TEMP") or os.getenv("TMP") or (os.path.expanduser("~") + "\\AppData\\Local\\Temp")
ORDNER = Path(_TEMP) / "moondev_agenten"
ORDNER.mkdir(parents=True, exist_ok=True)


def _pid_datei() -> Path:
    return ORDNER / ("%d.moon" % os.getpid())


def registriere() -> Path:
    """Agent registriert sich im gemeinsamen Ordner (T-262)."""
    pfad = _pid_datei()
    try:
        pfad.write_text(
            "pid=%d\nstart=%.3f\n" % (os.getpid(), time.time()),
            encoding="utf-8",
        )
    except OSError:
        pass  # Ordner weg – Agent stirbt ohne Registrierung, das ist ok
    return pfad


def alle_registrierte_pids() -> set:
    """Alle PIDs, die sich aktuell im gemeinsamen Ordner registriert haben."""
    result: set = set()
    for p in ORDNER.glob("*.moon"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            erste = text.splitlines()[0] if text.splitlines() else ""
            if erste.startswith("pid="):
                result.add(int(weise := erste.split("=", 1)[1]))
        except (OSError, ValueError, IndexError):
            continue
    return result


# ---------------------------------------------------------------- Test
if __name__ == "__main__":
    pfad = registriere()
    print("Registriert als PID %d – Datei: %s" % (os.getpid(), pfad))
    print("Alle registrierten PIDs:", sorted(alle_registrierte_pids()))
