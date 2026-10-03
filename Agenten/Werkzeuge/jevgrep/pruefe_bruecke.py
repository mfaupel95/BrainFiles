"""Prueft eine LAUFENDE jev-Bruecke mit einem realistischen Zustand.

Aufruf:  python pruefe_bruecke.py [port] [zeichen]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]
QUELLEN = [WURZEL / "Agenten" / "Handel" / "scanner" / n
           for n in ("handeln.py", "okx.py", "wachen_pruefung.py", "lage.py")]


def zustand(zeichen: int) -> str:
    text = "\n".join(
        "// %s\n%s" % (p.name, p.read_text(encoding="utf-8", errors="replace"))
        for p in QUELLEN if p.is_file()
    )
    return text[:zeichen]


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8742
    zeichen = int(sys.argv[2]) if len(sys.argv) > 2 else 25000
    basis = "http://127.0.0.1:%d" % port
    try:
        with urllib.request.urlopen(basis + "/gesundheit", timeout=5) as r:
            print("Bruecke:", r.read().decode("utf-8").strip())
    except Exception as e:                                      # noqa: BLE001
        print("Bruecke auf Port %d nicht erreichbar: %s" % (port, e))
        return 1
    z = zustand(zeichen)
    fragen = {"q1": {"type": "noul",
                     "instructions": "Zeigt das, wann eine Position geschlossen wird?"},
              "q2": {"type": "noul",
                     "instructions": "Zeigt das eine Sperrfrist nach einem Ausstieg?"}}
    koerper = json.dumps({"model": "bruecke", "state": z, "questions": fragen}).encode()
    req = urllib.request.Request(basis + "/v1/systemone", data=koerper,
                                 headers={"content-type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.loads(r.read().decode("utf-8"))
        print("Zustand: %d Zeichen (~%d Token) | Dauer: %.1f s"
              % (len(z), len(z) // 3.5, time.time() - t0))
        print("Antwort:", json.dumps(d.get("answers"), ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print("HTTP %s nach %.1f s: %s" % (e.code, time.time() - t0,
                                           e.read().decode("utf-8", "replace")[:300]))
        return 1
    except Exception as e:                                      # noqa: BLE001
        print("Fehler nach %.1f s: %s: %s" % (time.time() - t0, type(e).__name__, e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())