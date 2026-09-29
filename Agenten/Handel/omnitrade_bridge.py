"""Bruecke zu omnitrade (Rust, `Werkstatt/omnitrade`) - rein lesend.

WARUM DIESE DATEI EXISTIERT
---------------------------
`omnitrade live --status-file PFAD` schreibt seit 29.09.2026 laufend eine
kleine JSON-Datei (Schema 1, `omnitrade-cli/src/status.rs`): Zustand, Kerzen,
letzter Kurs und Signal, Orders. Die Handelszentrale zeigt sie im Reiter
"omnitrade" an. Es gibt keinen Socket und keinen Steuerkanal.

RAHMEN
------
* **Nur lesen.** Die Datei wird geoeffnet und gelesen, nie geschrieben.
  omnitrade schreibt atomisch (tmp + rename), halbe Dateien gibt es nicht.
* **Pfad** aus `OMNITRADE_STATUS`, sonst `Werkstatt/omnitrade/status/live.json`
  relativ zu BrainFiles. Kein absoluter Pfad im Code.
* **Nie ein Absturz.** `lage()` liefert bei fehlender, kaputter oder
  veralteter Datei `ok: False` mit Grund.

Aufruf:  python omnitrade_bridge.py      -> Lage als JSON
"""

import json
import os
import sys
import time

HANDEL = os.path.dirname(os.path.abspath(__file__))
STANDARD = os.path.join(HANDEL, "..", "..", "Werkstatt", "omnitrade", "status",
                        "live.json")
SCHEMA = 1
# Ohne Kerze kommt trotzdem nach jeder Kerze ein Schreibvorgang; bei 1m-Kerzen
# ist eine Datei, die 5 Minuten stillsteht, verdaechtig.
VERALTET_S = 300


def pfad():
    return os.environ.get("OMNITRADE_STATUS") or os.path.normpath(STANDARD)


def lage(datei=None, jetzt_ms=None, veraltet_s=VERALTET_S):
    """Status-Dokument plus `ok`, `alter_s`, `fehler`, `datei`. Wirft nie."""
    datei = datei or pfad()
    ergebnis = {"ok": False, "datei": datei, "fehler": "", "alter_s": None}
    try:
        with open(datei, "r", encoding="utf-8") as f:
            daten = json.load(f)
    except FileNotFoundError:
        ergebnis["fehler"] = "keine Statusdatei (omnitrade live laeuft nicht)"
        return ergebnis
    except (OSError, ValueError) as e:
        ergebnis["fehler"] = "Statusdatei unlesbar: %s" % e
        return ergebnis
    if not isinstance(daten, dict):
        ergebnis["fehler"] = "Statusdatei unlesbar: kein Objekt"
        return ergebnis
    ergebnis.update(daten)
    ergebnis["ok"] = False
    if daten.get("schema") != SCHEMA:
        ergebnis["fehler"] = "unbekanntes Schema %r" % daten.get("schema")
        return ergebnis
    jetzt_ms = time.time() * 1000 if jetzt_ms is None else jetzt_ms
    try:
        ergebnis["alter_s"] = max(0.0, (jetzt_ms - float(daten.get("updated_ms"))) / 1000)
    except (TypeError, ValueError):
        ergebnis["fehler"] = "Statusdatei ohne updated_ms"
        return ergebnis
    if daten.get("state") in ("starting", "running") and ergebnis["alter_s"] > veraltet_s:
        ergebnis["fehler"] = "veraltet: seit %d min kein Lebenszeichen" % (
            ergebnis["alter_s"] // 60)
        return ergebnis
    ergebnis["ok"] = True
    return ergebnis


if __name__ == "__main__":
    json.dump(lage(), sys.stdout, indent=2, ensure_ascii=False)
    print()
