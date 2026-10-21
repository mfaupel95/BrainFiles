#!/usr/bin/env python3
r"""Junction-Wache (no_agent) - meldet nur Verlust der Wurzel-Verweise,
leere Ausgabe = alles gut (Watchdog-Muster wie ausserhaus-frist-wache.py).

WARUM DIESE WACHE (11.10.2026, T-390)
-------------------------------------
Die Junctions `BrainFiles/Werkstatt -> O:\Werkstatt` und
`BrainFiles/Modelle -> O:\Modelle` sind zweimal innerhalb von 6 Tagen
verloren gegangen (05.10.2026 22:12, 11.10.2026 02:00): der Verweis wurde
durch einen echten, langsam wachsenden Schatten-Ordner ersetzt (Anfang 10.10.
18:47, 23 Eintraege beim Fund), alle Zugriffe ueber den BrainFiles-Pfad
liefen ins Leere (scanner-papier-stunde schlug stundenlang fehl).

Die konfig-doktor-wache prueft dieselben Verweise, aber nur alle 4 Stunden:
ein Verlust, der zwischen zwei Laeufen entsteht und repariert wird, faellt
durch ihr Fenster (heute: Verlust 02:00, Reparatur 02:20, naechster
konfig-doktor-Lauf 05:18 - unerkannt, obwohl die Reparatur-Sitzung ihn
dokumentiert hat). Diese Wache laeuft alle 10 Minuten.

GEPRUEFT WIRD JE VERWEIS:
1. Der Pfad existiert und ist EIN REPARSE-PUNKT (Junction/Symlink), kein
   echter Ordner. Ein Schatten-Ordner ist der Verlust in seiner haeufigsten
   Form - er sieht aus wie ein Ordner und wird von islink() uebersehen.
2. Das Ziel stimmt (O:\Werkstatt bzw. O:\Modelle) - ein Verweis auf ein
   anderes Laufwerk ist genauso kaputt, sieht aber gesund aus.
3. Das Ziel ist erreichbar und kein leerer/schmaler Schatten.
   (`Modelle` bleibt dabei reiner Lesestoff - dort wird keine Probedatei
   angelegt.)

Meldung: nur der Verlust, mit Wiederholungs-Sperre (derselbe Befund
hoechstens alle WIEDERHOLUNG_STUNDEN). Ein Fehler der Pruefung selbst ist
NIE ein leeres Ergebnis - er wird gemeldet, nicht verschwiegen.

Aufruf:
  python junction-wache.py                # Cron-Betrieb: nur Verluste
  python junction-wache.py --alle         # auch Gesundheit zeigen
  python junction-wache.py --json         # Zustand fuer Werkzeuge
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]                    # Agenten/Hermes/scripts -> BrainFiles
ZUSTAND = HIER.parent / "cache" / "junction-wache.json"

VERWEISE = {
    "Werkstatt": "O:\\Werkstatt",
    "Modelle": "O:\\Modelle",
}
# Inhalt-Mindestschwelle: ein Ziel mit weniger Eintraegen als erwartet ist
# entweder ein frisches leeres Ziel oder ein Schatten. Werkstatt traegt
# Dutzende Repos, Modelle mindestens blobs/ + manifests/.
MINDEST_EINTRAEGE = 3

WIEDERHOLUNG_STUNDEN = 12.0


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _merkdatei() -> dict:
    try:
        with open(ZUSTAND, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merken(d: dict) -> None:
    try:
        ZUSTAND.parent.mkdir(parents=True, exist_ok=True)
        with open(ZUSTAND, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError:
        pass                                    # Merken ist Komfort


def _kennung(text: str) -> str:
    """Schluessel eines Befunds OHNE Zahlen - ein wachsender Wert bleibt
dieselbe Feststellung. Ziffernfolgen werden als GANZE FOLGE ersetzt."""
    ohne_zahlen = re.sub(r"[0-9]+", "#", text)
    return hashlib.sha1(ohne_zahlen.encode("utf-8")).hexdigest()[:12]


def _ist_verweis(p) -> bool:
    """Reparse-Punkt? os.path.islink liefert fuer Windows-JUNCTIONS False -
    verlaesslich ist nur FILE_ATTRIBUTE_REPARSE_POINT (0x400)."""
    try:
        st = os.lstat(str(p))
    except OSError:
        return False
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & 0x400) or os.path.islink(str(p))


def _normalisiert(pfad: str) -> str:
    s = str(pfad).strip().strip('"').strip("'")
    if s.startswith("\\\\?\\"):
        s = s[4:]
    s = s.replace("/", "\\")
    while len(s) > 3 and s.endswith("\\"):
        s = s[:-1]
    return s.lower()


def verweis_lage(wurzel, name: str, ziel: str, mindest_eintraege=MINDEST_EINTRAEGE) -> str:
    """'' wenn gesund, sonst Klartext-Befund. Nie werfen."""
    p = Path(wurzel) / name
    if not p.exists():
        return "%s fehlt ganz (erwartet: Verweis auf %s)" % (name, ziel)

    if not _ist_verweis(p):
        # Schatten-Ordner: der haeufigste Verlust. Eintraege zaehlen fuer den
        # Bericht (leer vs. gewachsen), ohne den Ordner zu durchsuchen.
        try:
            anzahl = sum(1 for _ in os.scandir(str(p)))
        except OSError:
            anzahl = -1
        return ("%s ist KEIN Verweis mehr, sondern ein echter Ordner "
                "(%d Eintraege) - erwartet: Verweis auf %s"
                % (name, anzahl, ziel))

    # Verweis da - zeigt er auf das richtige Ziel?
    try:
        tatsaechlich = os.readlink(str(p))
    except OSError as e:
        return "%s: Ziel nicht lesbar (%s)" % (name, e)
    if _normalisiert(tatsaechlich) != _normalisiert(ziel):
        return "%s zeigt auf %s statt auf %s" % (name, tatsaechlich, ziel)

    # Ziel erreichbar und nicht leer?
    try:
        anzahl = sum(1 for _ in os.scandir(str(p)))
    except OSError as e:
        return ("%s zeigt ins Leere - Ziel %s nicht erreichbar (%s)"
                % (name, ziel, e))
    if anzahl < mindest_eintraege:
        # Ein Verweis auf ein (fast) leeres Ziel ist verdaechtig: das echte
        # Werkstatt traegt Dutzende Repos, der echte Modelle-Ordner blobs/
        # und manifests/. Ein Schatten mit 2 Eintraegen waere sonst still.
        return ("%s zeigt auf ein (fast) leeres Ziel (%d Eintraege) - "
                "erwartet waren mindestens %d" % (name, anzahl, mindest_eintraege))
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alle", action="store_true",
                    help="auch Gesundheit zeigen")
    ap.add_argument("--json", action="store_true", help="Zustand als JSON")
    a = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    befunde = []
    lagen = {}
    for name, ziel in VERWEISE.items():
        text = verweis_lage(WURZEL, name, ziel)
        lagen[name] = "" if not text else text
        if text:
            befunde.append(text)

    jetzt = time.time()
    merk = _merkdatei()
    gesendet = merk.get("gesendet") or {}
    neu, wiederholt = [], 0
    for b in befunde:
        k = _kennung(b)
        letzte = gesendet.get(k)
        if letzte and (jetzt - float(letzte)) < WIEDERHOLUNG_STUNDEN * 3600:
            wiederholt += 1
            continue
        neu.append(b)
        gesendet[k] = jetzt
    _merken({"gesendet": gesendet, "stand": _jetzt(), "lagen": lagen})

    if a.json:
        print(json.dumps({"befunde": befunde, "neu": neu,
                          "wiederholt": wiederholt, "lagen": lagen,
                          "stand": _jetzt()}, ensure_ascii=False, indent=2))
        return 0

    if not befunde:
        if a.alle:
            print("junction-wache: %d Verweis(e) gesund (Werkstatt, Modelle)"
                  % len(VERWEISE))
        return 0

    if not neu:
        if a.alle:
            print("junction-wache: %d Befund(e), alle innerhalb der "
                  "Merkfrist schon gemeldet" % len(befunde))
        return 0

    zeilen = ["junction-wache: Junction-Verlust (%d Befund(e))" % len(neu)]
    for b in neu:
        zeilen.append("  - " + b)
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
