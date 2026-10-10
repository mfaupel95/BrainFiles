#!/usr/bin/env python3
"""Dateischwund ueber die versionierte Textebene des ganzen Baums (T-100).

WARUM: `dateischwund-wache.py` bewacht nur `Agenten/Hermes/scripts/`,
`dateischwund-wache-handel.py` nur die `.py`-Dateien in `Agenten/Handel/`.
Der T-100-Fall (eine versionierte Datei verschwindet, `fremdarbeit-einziehen`
committet die Loeschung nach 30 Minuten) kann aber ueberall passieren - in
`MaxHirn/Wissen/`, `Agenten/Routinen/`, `Agenten/Werkzeuge/`, `Agenten/Bus/`.

Diese Wache deckt den GANZEN versionierten Baum ab, ohne teuer zu sein: sie
liest NICHT den Dateibaum (das braeuchte ueber den ganzen Baum Minuten),
sondern die GIT-SOLL-Liste (`git ls-files`) - die versionierte Textebene, die
T-100 schuetzen soll. Das sind ~2600 Dateien, kein `rglob` ueber .venv/daten.

Sie prueft ZWEI Soll-Zustaende (wie die scripts-Wache):
  1. Git-Soll: jede Datei in HEAD, die im Arbeitsbaum fehlt.
  2. Merkliste: jede Datei, die beim letzten Lauf da war und jetzt fehlt
     (faengt noch nicht committete Dateien).

Sie aendert NICHTS. MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts).
Dieselbe Feststellung hoechstens einmal je RUHE_STUNDEN.

Aufruf (Hermes-Cron, no_agent, alle 15 Minuten):
    python Agenten/Hermes/scripts/dateischwund-wache-baum.py
    python Agenten/Hermes/scripts/dateischwund-wache-baum.py --alle
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]                       # scripts -> Hermes -> Agenten -> BrainFiles
MERK = HIER.parent / "cache" / "dateischwund-wache-baum.json"

RUHE_STUNDEN = 6.0

# Ordner, die NICHT zur versionierten Textebene gehoeren (Junctions, .venv,
# Daten). `git ls-files` liefert sie ohnehin nicht - diese Liste ist nur die
# Absicherung, falls ein Pfad durchrutscht.
AUSLASSEN = {".venv", "__pycache__", "node_modules", "target", "logs",
             "daten", "cache", "state", "docs", ".git", "Modelle", "Werkstatt"}


def _git(*args: str) -> str:
    try:
        p = subprocess.run(["git", "-C", str(WURZEL), *args],
                           capture_output=True, text=True, errors="replace",
                           timeout=120)
    except (OSError, subprocess.SubprocessError):
        return ""
    return p.stdout if p.returncode == 0 else ""


def git_soll() -> set:
    """Alle versionierten Dateien (relativ zur Wurzel)."""
    roh = _git("ls-files")
    return {z.strip() for z in roh.splitlines() if z.strip()}


def _kennung(pfad: Path) -> tuple:
    try:
        roh = pfad.read_bytes()
    except OSError:
        return (-1, "")
    import hashlib
    return (len(roh), hashlib.sha256(roh).hexdigest()[:16])


def _lade() -> dict:
    try:
        d = json.loads(MERK.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _speichere(d: dict) -> None:
    try:
        MERK.parent.mkdir(parents=True, exist_ok=True)
        MERK.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    except OSError:
        pass


def _faellig(gemeldet: dict, schluessel: str, jetzt: dt.datetime) -> bool:
    alt = gemeldet.get(schluessel)
    if not alt:
        return True
    try:
        wann = dt.datetime.fromisoformat(alt)
    except (ValueError, TypeError):
        return True
    return (jetzt - wann).total_seconds() >= RUHE_STUNDEN * 3600


def pruefe(jetzt: dt.datetime | None = None) -> tuple:
    """Rein rechnend: (Befundzeilen, neuer Merkstand). Schreibt nichts."""
    jetzt = jetzt or dt.datetime.now()
    alt = _lade()
    vorher = alt.get("stand") or {}
    gemeldet = alt.get("gemeldet") or {}

    soll = git_soll()
    # Merkliste: nur Dateien, die wir wirklich beobachten (versioniert ODER
    # beim letzten Lauf da). Nicht-versionierte Dateien, die nie da waren,
    # sind kein Befund.
    nachher = {}
    for rel in soll:
        voll = WURZEL / rel
        if not voll.exists():
            continue
        if any(t in AUSLASSEN for t in Path(rel).parts):
            continue
        nachher[rel] = _kennung(voll)

    befunde = []

    # 1) Git-Soll: in HEAD, aber nicht auf der Platte
    for rel in sorted(soll):
        if any(t in AUSLASSEN for t in Path(rel).parts):
            continue
        if not (WURZEL / rel).exists():
            befunde.append((
                "git:" + rel,
                "FEHLT, steht aber in HEAD: %s - die Routine fremdarbeit-einziehen "
                "committet das nach 30 Minuten als Loeschung. Zurueckholen: "
                "git checkout HEAD -- %s" % (rel, rel)))

    # 2) Merkliste: beim letzten Lauf da, jetzt weg
    for rel, wert in sorted(vorher.items()):
        if rel in nachher:
            continue
        befunde.append((
            "merk:" + rel,
            "verschwunden seit dem letzten Lauf: %s (war %s B)" % (rel, wert[0])))

    # 3) Datei noch da, Inhalt aber leer geworden (halber Schreibvorgang)
    for rel, wert in sorted(nachher.items()):
        alt_wert = vorher.get(rel)
        if alt_wert and alt_wert[0] > 0 and wert[0] == 0:
            befunde.append((
                "leer:" + rel,
                "auf 0 Byte zusammengefallen: %s (war %s B) - abgebrochener "
                "Schreibvorgang" % (rel, alt_wert[0])))

    neue = []
    for schluessel, text in befunde:
        if _faellig(gemeldet, schluessel, jetzt):
            neue.append(text)
            gemeldet[schluessel] = jetzt.isoformat(timespec="seconds")
    for schluessel in list(gemeldet):
        art, _, rel = schluessel.partition(":")
        if art == "merk" and rel in nachher:
            del gemeldet[schluessel]

    neuer_stand = {"stand": nachher, "gemeldet": gemeldet,
                   "lauf": jetzt.isoformat(timespec="seconds")}
    return neue, neuer_stand


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Dateischwund ueber die versionierte Textebene (T-100)")
    ap.add_argument("--alle", action="store_true",
                    help="Lage immer ausgeben, auch ohne Befund")
    ap.add_argument("--jetzt", default=None,
                    help="Bezugszeit (ISO) - nur fuer Gegenproben")
    a = ap.parse_args(argv)

    jetzt = None
    if a.jetzt:
        try:
            jetzt = dt.datetime.fromisoformat(a.jetzt)
        except ValueError:
            jetzt = None

    neue, neuer_stand = pruefe(jetzt=jetzt)
    _speichere(neuer_stand)

    anzahl = len(neuer_stand["stand"])
    if not neue and not a.alle:
        return 0

    print("Dateischwund-Wache (Baum) %s - %d versionierte Datei(en) beobachtet"
          % (dt.datetime.now().strftime("%d.%m. %H:%M"), anzahl))
    if neue:
        for z in neue:
            print("  - " + z)
        print("  Nichts wurde geaendert - diese Wache holt nichts zurueck und "
              "loescht nichts.")
    else:
        print("  kein Befund: kein Git-Soll offen, keine Datei seit dem "
              "letzten Lauf verschwunden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
