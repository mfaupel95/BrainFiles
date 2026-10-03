"""Was sich die Zentrale merkt: Schrift, Dichte, Fenstergroesse, Filter.

Die Einstellungen liegen als JSON neben dem Werkzeug (`einstellungen.json`) und
sind **Laufzeitstand** - sie gehoeren nicht in die Versionierung (dieselbe Regel
wie `breite-reihe.jsonl` und `skillsbot.kontext.json`). Fehlt die Datei oder ist
sie kaputt, gilt `STANDARD`; ein unbrauchbarer Wert faellt EINZELN auf seinen
Standard zurueck, die uebrigen bleiben. Nie eine Ausnahme nach aussen.

Diese Datei kennt kein tkinter - sie ist ohne Fenster pruefbar.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# Schriftgroessen, die das Fenster anbietet. 8 ist die kleinste lesbare Groesse
# in Consolas, 16 die groesste, die mit 6 Spalten noch in ein Full-HD-Fenster
# passt (gemessen mit messprobe.py).
SCHRIFT_MIN = 8
SCHRIFT_MAX = 16

# Dichte: der Faktor auf die Zeilenhoehe. Die Schrift bleibt, nur der Abstand
# aendert sich - so passen auf einen Bildschirm 30 statt 20 Zeilen, ohne dass
# etwas kleiner wird.
DICHTEN = {"kompakt": 0.85, "normal": 1.0, "gross": 1.3}

# Fenstergroessen als Vorgaben. "bildschirm" nimmt die Bildschirmgroesse minus
# Rand (die Rechnung macht fenster.py, hier steht nur der Name).
FENSTERGROESSEN = {
    "klein": (1100, 700),
    "mittel": (1400, 900),
    "gross": (1700, 1050),
    "bildschirm": (0, 0),
}

STANDARD: dict = {
    "schrift": 11,
    "dichte": "normal",
    "fenster": "mittel",
    "bereich": "Alle Bereiche",
    "gruppe": "Alle Gruppen",
    "text": "",             # der zuletzt eingetippte Suchtext
    "filter": [],
    "spalten": {},          # Spaltenbreiten, die der Benutzer selbst gezogen hat
    "sortierung": "",       # Spaltenkennung, nach der sortiert wird
}

# Erlaubte Filter-Kennzeichen (die Chips im Fenster). Die Reihenfolge IST die
# Anzeige-Reihenfolge. Ein unbekanntes Kennzeichen in der Datei faellt weg -
# sonst traegt das Fenster einen Filter, den es nicht mehr gibt.
FILTER_KENNZEICHEN = (
    "auffaellig",       # Gruppe NEU oder FEHLT
    "startbar",         # Startbefehl belegt und Abhaengigkeiten da
    "mit_start",        # irgendein Startbefehl belegt (auch wenn etwas fehlt)
    "mit_bot",          # Bot-Profil vorhanden
    "fremd",            # fremdes Material (FREMD-Liste)
    "eigen",            # NICHT fremd
    "handel",           # Bereich HANDEL
    "spuren",           # Handels-Spuren im Betrieb (dauerlauf.SPUREN)
    "scharf",           # Handels-Spur mit Orderweg UND handel_erlaubt
    "ohne_start",       # kein Startbefehl belegt
)


def bereinigen(werte) -> dict:
    """Nur bekannte Schluessel, nur gueltige Werte - sonst der Standard.

    Ein kaputter Wert darf nie das Fenster verhindern: er wird still durch den
    Standard ersetzt. Deshalb wird hier NICHT geworfen und nicht geloggt - der
    Aufrufer sieht am Ergebnis, was angekommen ist.
    """
    roh = werte if isinstance(werte, dict) else {}
    sauber = dict(STANDARD)

    schrift = roh.get("schrift")
    if isinstance(schrift, bool) or not isinstance(schrift, (int, float)):
        sauber["schrift"] = STANDARD["schrift"]
    else:
        sauber["schrift"] = max(SCHRIFT_MIN, min(SCHRIFT_MAX, int(schrift)))

    for schluessel, erlaubt in (("dichte", DICHTEN), ("fenster", FENSTERGROESSEN)):
        wert = roh.get(schluessel)
        sauber[schluessel] = wert if wert in erlaubt else STANDARD[schluessel]

    for schluessel in ("bereich", "gruppe", "sortierung", "text"):
        wert = roh.get(schluessel)
        sauber[schluessel] = str(wert) if isinstance(wert, str) else STANDARD[schluessel]

    filter_ = roh.get("filter")
    if isinstance(filter_, (list, tuple)):
        sauber["filter"] = [
            str(f) for f in filter_ if str(f) in FILTER_KENNZEICHEN
        ]
        # doppelte Kennzeichen entfernen, Reihenfolge der Tabelle behalten
        sauber["filter"] = [k for k in FILTER_KENNZEICHEN if k in sauber["filter"]]

    spalten = roh.get("spalten")
    if isinstance(spalten, dict):
        sauber["spalten"] = {
            str(k): int(v) for k, v in spalten.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and 20 <= float(v) <= 4000
        }
    return sauber


def laden(pfad: Path | str) -> dict:
    """Einstellungen lesen; fehlende oder kaputte Datei gibt die Standards."""
    pfad = Path(pfad)
    if not pfad.is_file():
        return dict(STANDARD)
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return dict(STANDARD)
    return bereinigen(roh)


def speichern(pfad: Path | str, werte: dict) -> bool:
    """Einstellungen schreiben (erst in eine Nebendatei, dann umbenennen).

    Ein direktes Schreiben koennte eine halbe Datei hinterlassen, wenn der
    Rechner genau dazwischen ausgeht - und die naechste Sitzung faende dann
    keine Einstellungen mehr. `os.replace` ist unter Windows atomar.
    """
    pfad = Path(pfad)
    daten = bereinigen(werte)
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=str(pfad.parent),
            prefix=pfad.name + ".", suffix=".tmp", newline="\n",
        ) as f:
            json.dump(daten, f, indent=2, ensure_ascii=False)
            f.write("\n")
            name = f.name
        os.replace(name, pfad)
        return True
    except OSError:
        return False


def dichte_faktor(name: str) -> float:
    """Der Zeilenhoehen-Faktor einer Dichte (unbekannt -> 1.0)."""
    return float(DICHTEN.get(name, 1.0))


def fenster_masse(name: str, bildschirm: tuple[int, int] = (1920, 1080)) -> tuple[int, int]:
    """Die Wunschgroesse eines Fenster-Presets.

    "bildschirm" bekommt die Bildschirmgroesse minus Rand - so liegt das Fenster
    auch auf einem kleinen Monitor vollstaendig im Bild. Unbekanntes Preset gibt
    "mittel".
    """
    breite, hoehe = FENSTERGROESSEN.get(name, FENSTERGROESSEN["mittel"])
    if (breite, hoehe) == (0, 0):
        return (max(900, bildschirm[0] - 60), max(600, bildschirm[1] - 100))
    return (breite, hoehe)