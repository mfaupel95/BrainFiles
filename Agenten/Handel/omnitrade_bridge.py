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
# Untergrenze fuer "veraltet". Die Datei wird NUR beim Verarbeiten einer Kerze
# geschrieben - bei `--interval 1h` also stuendlich. Eine feste 5-Minuten-Grenze
# hat am 30.09.2026 einen gesunden stuendlichen Lauf fuer tot erklaert (und die
# Handelszentrale zeigte "kein Lebenszeichen", waehrend er lief). Darum waechst
# die Grenze mit dem Kerzenabstand aus der Datei selbst.
VERALTET_S = 300
VIELFACHES = 2.5  # so oft darf der Kerzenabstand vergehen, bevor es ein Haenger ist


def pfad():
    return os.environ.get("OMNITRADE_STATUS") or os.path.normpath(STANDARD)


def intervall_s(daten):
    """Kerzenlaenge in Sekunden aus den mitgeschriebenen Kerzen.
    None, wenn nicht ableitbar (alte Staende, zu wenige Kerzen)."""
    kerzen = (daten or {}).get("recent_candles") or []
    zeiten = []
    for k in kerzen:
        if isinstance(k, dict) and isinstance(k.get("time_ms"), (int, float)):
            zeiten.append(float(k["time_ms"]))
    if len(zeiten) < 2:
        return None
    zeiten.sort()
    abst = sorted(b - a for a, b in zip(zeiten, zeiten[1:]) if b > a)
    if not abst:
        return None
    return abst[len(abst) // 2] / 1000.0  # Median, damit eine Luecke nicht zaehlt


def altersgrenze_s(daten, vielfaches=VIELFACHES):
    """Altersgrenze fuer die Statusdatei: Untergrenze, sonst mit dem
    Kerzenabstand gewachsen."""
    i = intervall_s(daten)
    if i is None:
        return float(VERALTET_S)
    return max(float(VERALTET_S), vielfaches * i)


def lage(datei=None, jetzt_ms=None, veraltet_s=None):
    """Status-Dokument plus `ok`, `alter_s`, `fehler`, `datei`. Wirft nie.
    `veraltet_s=None` heisst: Grenze aus dem Kerzenabstand der Datei."""
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
    grenze = altersgrenze_s(daten) if veraltet_s is None else float(veraltet_s)
    ergebnis["altersgrenze_s"] = grenze
    if daten.get("state") in ("starting", "running") and ergebnis["alter_s"] > grenze:
        ergebnis["fehler"] = "veraltet: seit %d min kein Lebenszeichen (Grenze %d s)" % (
            ergebnis["alter_s"] // 60, grenze)
        return ergebnis
    ergebnis["ok"] = True
    return ergebnis


if __name__ == "__main__":
    json.dump(lage(), sys.stdout, indent=2, ensure_ascii=False)
    print()
