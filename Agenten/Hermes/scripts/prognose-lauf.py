"""Haelt den Prognose-Bericht frisch - die QUELLE, nicht die Spur.

Warum es diesen Lauf gibt: `omniquant` liest `prognose_berichte/neuester.json`
und handelt nur, wenn der Bericht juenger als 26 h ist. Die Spur ist also nicht
kaputt, sie HUNGERT: ohne Lauf gibt es kein Signal. Am 23.09.2026 war der letzte
Bericht sieben Tage alt (16.09. 20:35), deshalb stand omniquant seit dem 17.09.
still - und `kraken/scan.py` schreibt denselben Bericht fuer seinen Papierzweig.
Fuer `prognose.py` gab es weder Cron noch geplante Aufgabe: ein Handwerkzeug,
das niemand ruft.

Dieser Lauf ruft es still auf (`--ohne-meldung`): Bericht schreiben, nichts
senden. Melden darf er nur, was zaehlt - die TREFFER. Findet die Prognose
nichts, bleibt die Ausgabe leer und der Cron sendet nichts (Watchdog-Muster,
wie radar-sammeln.py).

Rueckgabe: 0 = Bericht frisch, 1 = echter Fehler.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))      # BrainFiles
HANDEL = os.path.join(WURZEL, "Agenten", "Handel")
PYTHON = os.path.join(HANDEL, "scanner", ".venv", "Scripts", "python.exe")
BERICHT = os.path.join(HANDEL, "prognose_berichte", "neuester.json")
FRIST_S = 1800


def _umgebung() -> dict:
    env = dict(os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["MAXHIRN_ROUTINE"] = "1"      # kein Sitzungsfenster, keine Rueckfragen
    return env


def _bericht_lesen() -> dict:
    try:
        with open(BERICHT, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:                                               # noqa: BLE001
        return {}


def main() -> int:
    if not os.path.exists(PYTHON):
        print("Prognose-Lauf: Python fehlt (%s)" % PYTHON)
        return 1
    # Zwei Fassungen: streng (Hauptarm omniquant, kraken-Papierzweig) und weit
    # (Schattenarm omniquant_weit). Beide still, beide in derselben Datei-Familie.
    fassungen = [("", "neuester.json"), ("weit", "neuester.weit.json")]
    for fassung, datei in fassungen:
        umg = _umgebung()
        if fassung:
            umg["PROGNOSE_FASSUNG"] = fassung
        ziel = os.path.join(HANDEL, "prognose_berichte", datei)
        try:
            p = subprocess.run([PYTHON, "prognose.py", "--ohne-meldung"], cwd=HANDEL,
                               env=umg, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=FRIST_S)
        except Exception as e:                                      # noqa: BLE001
            print("Prognose-Lauf (%s) fehlgeschlagen: %s" % (fassung or "streng", e))
            return 1
        if p.returncode not in (0, 1):
            aus = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
            print("Prognose-Lauf (%s) brach ab (Rueckgabe %d):\n%s"
                  % (fassung or "streng", p.returncode, "\n".join(aus[-8:])))
            return 1
        frisch = os.path.getmtime(ziel) if os.path.exists(ziel) else 0
        if frisch < time.time() - 300:
            print("Prognose-Lauf: Bericht %s nicht erneuert (%s)"
                  % (fassung or "streng", ziel))
            return 1

    # prognose.py gibt 1 zurueck, wenn es KEINE Treffer gibt - das ist kein Fehler.
    if p.returncode not in (0, 1):
        aus = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        print("Prognose-Lauf brach ab (Rueckgabe %d):\n%s"
              % (p.returncode, "\n".join(aus[-8:])))
        return 1

    d = _bericht_lesen()
    if not d.get("erzeugt"):
        print("Prognose-Lauf: kein Bericht geschrieben (%s)" % BERICHT)
        return 1

    treffer = d.get("treffer") or []
    # Die weiche Fassung mitlesen: sie versorgt den Schattenarm omniquant_weit.
    try:
        with open(os.path.join(HANDEL, "prognose_berichte", "neuester.weit.json"),
                  encoding="utf-8") as fh:
            weit = (json.load(fh).get("treffer") or [])
    except Exception:                                               # noqa: BLE001
        weit = []
    if not treffer and not weit:
        return 0                                   # leere Ausgabe = nichts senden
    zeilen = ["Prognose %s: streng %d, weit %d Treffer von %s Maerkten"
              % (str(d.get("erzeugt"))[:16], len(treffer), len(weit),
                 d.get("maerkte_geprueft"))]
    for t in (treffer or weit)[:6]:
        zeilen.append("  %-12s %-5s Score %s  Stop %s  Ziel %s"
                      % (t.get("inst"), t.get("richtung"), t.get("score"),
                         t.get("stop"), t.get("ziel")))
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())