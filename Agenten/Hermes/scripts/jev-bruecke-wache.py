"""Wache fuer die jev-Bruecke: laeuft sie, und wenn nicht, startet sie sie.

Bauart nach Haus-Muster (wie bus-waechter/gateway-waechter): leere Ausgabe = nichts
senden. Gemeldet wird nur, wenn die Bruecke gestartet wurde oder nicht hochkommt.

Aufruf:  python jev-bruecke-wache.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent                  # Agenten/Hermes/scripts
WURZEL = HIER.parents[2]
BRUECKE = WURZEL / "Agenten" / "Werkzeuge" / "jevgrep" / "jev_bruecke.py"
LOG = WURZEL / "Agenten" / "Hermes" / "cache" / "jev-bruecke-starts.log"
PORT = 8742
BASIS = "https://api.inceptionlabs.ai/v1"
MODELL = "mercury-2.5"
GRACEFRIST_S = 25


def gesundheit(frist: float = 4.0) -> dict | None:
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/gesundheit" % PORT, timeout=frist) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:                                           # noqa: BLE001
        return None


def starten() -> int | None:
    umg = dict(os.environ)
    umg.update({
        "JEVCREP_BRUECKE_PORT": str(PORT),
        "JEVCREP_BRUECKE_BASIS": BASIS,
        "JEVCREP_BRUECKE_MODELL": MODELL,
        "JEVCREP_BRUECKE_FRIST": "300",
        "PYTHONIOENCODING": "utf-8",
    })
    umg.pop("PYTHONHOME", None)
    umg.pop("PYTHONPATH", None)
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0)
    try:
        p = subprocess.Popen([sys.executable, str(BRUECKE)], env=umg, cwd=str(BRUECKE.parent),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, creationflags=flags)
    except OSError as e:
        print("jev-Bruecke liess sich nicht starten: %s" % e)
        return None
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write("%s gestartet, PID %d\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), p.pid))
    except OSError:
        pass
    return p.pid


def main() -> int:
    zustand = gesundheit()
    if zustand and zustand.get("ok"):
        return 0                                    # laeuft - leise bleiben
    pid = starten()
    if pid is None:
        return 1
    ende = time.time() + GRACEFRIST_S
    while time.time() < ende:
        time.sleep(2)
        zustand = gesundheit()
        if zustand and zustand.get("ok"):
            print("jev-Bruecke war aus und laeuft wieder (PID %d, Modell %s)."
                  % (pid, zustand.get("modell")))
            return 0
    print("jev-Bruecke wurde gestartet (PID %d), antwortet aber nach %d s nicht - "
          "Protokoll: %s" % (pid, GRACEFRIST_S, LOG))
    return 1


if __name__ == "__main__":
    sys.exit(main())