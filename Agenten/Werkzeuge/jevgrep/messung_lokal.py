"""Messung: wie lange braucht ein LOKALES Modell fuer eine jevgrep-Anfrage?

Baut einen realistischen Zustand aus echten Quelldateien (wie jevgrep ihn schickt,
gemessen 20.000-54.000 Zeichen), startet die Bruecke gegen ein Ollama-Modell, stellt
EINE Systemone-Anfrage und rechnet auf eine ganze Suche hoch.

Aufruf:  python messung_lokal.py <modell> [zeichen]
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]
QUELLEN = [WURZEL / "Agenten" / "Handel" / "scanner" / n
           for n in ("handeln.py", "okx.py", "wachen_pruefung.py", "lage.py")]


def zustand_bauen(zeichen: int) -> str:
    teile = []
    for p in QUELLEN:
        if p.is_file():
            teile.append("// %s\n%s" % (p.name, p.read_text(encoding="utf-8", errors="replace")))
    text = "\n".join(teile)
    return text[:zeichen]


def freier_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main() -> int:
    modell = sys.argv[1] if len(sys.argv) > 1 else "gemma-e4b-8k-64k:latest"
    zeichen = int(sys.argv[2]) if len(sys.argv) > 2 else 25000
    zustand = zustand_bauen(zeichen)
    port = freier_port()
    umg = dict(os.environ)
    umg.update({
        "JEVCREP_BRUECKE_PORT": str(port),
        "JEVCREP_BRUECKE_BASIS": "http://127.0.0.1:11434/v1",
        "JEVCREP_BRUECKE_MODELL": modell,
        "JEVCREP_BRUECKE_FRIST": "600",
        "JEVCREP_BRUECKE_PROTOKOLL": str(HIER / "cache-messung.log"),
        "PYTHONIOENCODING": "utf-8",
    })
    umg.pop("PYTHONHOME", None)
    umg.pop("PYTHONPATH", None)
    proc = subprocess.Popen([sys.executable, str(HIER / "jev_bruecke.py")], env=umg,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    basis = "http://127.0.0.1:%d" % port
    for _ in range(60):
        try:
            urllib.request.urlopen(basis + "/gesundheit", timeout=2).read()
            break
        except Exception:                                       # noqa: BLE001
            time.sleep(0.5)
    else:
        proc.kill()
        print("Bruecke kam nicht hoch")
        return 1

    fragen = {("q%d" % i): {"type": "noul", "instructions": t} for i, t in enumerate(
        ["Ist diese Datei relevant fuer die Frage, wann eine Position geschlossen wird?",
         "Zeigt sie eine Sperrfrist nach einem Ausstieg?",
         "Zeigt sie die Stop-Order an der Boerse?"], start=1)}
    koerper = json.dumps({"model": modell, "state": zustand, "questions": fragen}).encode()
    req = urllib.request.Request(basis + "/v1/systemone", data=koerper,
                                 headers={"content-type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            antwort = json.loads(r.read().decode("utf-8"))
        dauer = time.time() - t0
        print("Modell: %s | Zustand: %d Zeichen (~%d Token)"
              % (modell, len(zustand), len(zustand) // 3.5))
        print("Dauer je Anfrage: %.1f s" % dauer)
        print("Antwort:", json.dumps(antwort["answers"], ensure_ascii=False)[:200])
        for n, name in ((396, "Suche ueber 171 Dateien"), (60, "Suche ueber 66 Dateien")):
            einzeln = n * dauer
            print("  %s: %d Anfragen -> %.1f h nacheinander, %.1f h bei 4 gleichzeitig"
                  % (name, n, einzeln / 3600, einzeln / 4 / 3600))
    except Exception as e:                                      # noqa: BLE001
        print("Fehler nach %.1f s: %s: %s" % (time.time() - t0, type(e).__name__, e))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:                                       # noqa: BLE001
            proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())