"""Sonde fuer Inception Mercury 2.5 als jevgrep-Richter.

Misst mit ECHTEM Zustand (Quelltext) und echten noul-Fragen: Antwortzeit, Antwortform
und Plausibilitaet. Der Schluessel kommt aus INCEPTION_API_KEY (Prozessumgebung, sonst
Registry) und wird nie ausgegeben.

Aufruf:  python sonde_mercury.py [zeichen]
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]
BASIS = "https://api.inceptionlabs.ai/v1"
MODELL = "mercury-2.5"
QUELLEN = [WURZEL / "Agenten" / "Handel" / "scanner" / n
           for n in ("handeln.py", "okx.py", "wachen_pruefung.py", "lage.py")]
ANWEISUNG = (
    "Du bist ein Relevanz-Richter fuer Quelltext. Du bekommst einen ZUSTAND "
    "(Quelltext) und mehrere FRAGEN mit Kennungen. Beantworte jede Frage einzeln: "
    "Wie wahrscheinlich ist es, dass dieser Zustand fuer die Frage relevant ist? "
    "Antworte AUSSCHLIESSLICH mit JSON: {\"answers\": {\"<kennung>\": 0.0}} "
    "mit Zahlen von 0.0 bis 1.0. Jede Kennung muss vorkommen."
)


def schluessel() -> tuple[str | None, str]:
    for n in ("INCEPTION_API_KEY", "INCEPTION_KEY", "MERCURY_API_KEY"):
        w = os.environ.get(n)
        if w:
            return w.strip(), "Prozessumgebung " + n
    try:
        import winreg
    except ImportError:
        return None, ""
    for n in ("INCEPTION_API_KEY", "INCEPTION_KEY", "MERCURY_API_KEY"):
        for wurzel in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(wurzel, "Environment") as k:
                    w, _ = winreg.QueryValueEx(k, n)
            except OSError:
                continue
            if isinstance(w, str) and w.strip():
                return w.strip(), "Registry " + n
    return None, ""


def zustand(zeichen: int) -> str:
    text = "\n".join(
        "// %s\n%s" % (p.name, p.read_text(encoding="utf-8", errors="replace"))
        for p in QUELLEN if p.is_file()
    )
    return text[:zeichen]


def frage(key: str, z: str, fragen: dict, frist: float = 300) -> None:
    koerper = {
        "model": MODELL,
        "messages": [{"role": "system", "content": ANWEISUNG},
                     {"role": "user", "content": "ZUSTAND:\n%s\n\nFRAGEN:\n%s\n\nAntworte mit JSON."
                      % (z, "\n".join("- %s: %s" % (k, v["instructions"])
                                      for k, v in fragen.items()))}],
        "temperature": 0,
        "stream": False,
    }
    req = urllib.request.Request(BASIS + "/chat/completions",
                                 data=json.dumps(koerper).encode("utf-8"),
                                 headers={"content-type": "application/json",
                                          "authorization": "Bearer " + key},
                                 method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=frist) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        inhalt = (d["choices"][0]["message"].get("content") or "")
        print("Zustand %d Zeichen | %.1f s | Antwort: %s"
              % (len(z), time.time() - t0, inhalt.strip()[:220].replace("\n", " ")))
        try:
            print("   als JSON gelesen:", json.loads(inhalt.strip().strip("`").replace("json\n", "", 1)))
        except ValueError:
            print("   (kein reines JSON - die Bruecke faellt auf Fliesstext-Auswertung zurueck)")
    except urllib.error.HTTPError as e:
        print("HTTP %s nach %.1f s: %s" % (e.code, time.time() - t0,
                                           e.read().decode("utf-8", "replace")[:200]))
    except Exception as e:                                      # noqa: BLE001
        print("Fehler nach %.1f s: %s: %s" % (time.time() - t0, type(e).__name__, e))


def main() -> int:
    zeichen = int(sys.argv[1]) if len(sys.argv) > 1 else 25000
    key, quelle = schluessel()
    if not key:
        print("Kein Inception-Schluessel gefunden (INCEPTION_API_KEY).")
        return 1
    print("Schluessel aus %s (%d Zeichen, Wert nicht angezeigt)" % (quelle, len(key)))
    fragen = {
        "q1": {"instructions": "Zeigt das, wann eine offene Position geschlossen wird?"},
        "q2": {"instructions": "Zeigt das eine Sperrfrist nach einem Ziel-Ausstieg?"},
        "q3": {"instructions": "Zeigt das eine Stop-Order an der Boerse?"},
    }
    print("--- grosser Zustand (%d Zeichen) ---" % zeichen)
    frage(key, zustand(zeichen), fragen)
    print("--- kleiner Zustand (3.000 Zeichen) ---")
    frage(key, zustand(3000), fragen)
    return 0


if __name__ == "__main__":
    sys.exit(main())