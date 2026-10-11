#!/usr/bin/env python3
"""Syntax-Tor: meldet, wenn eine VERSIONIERTE .py-Datei nicht mehr uebersetzt.

WARUM DIESE WACHE (11.10.2026)
------------------------------
Der unbeaufsichtigte Sweep `Agenten/Routinen/fremdarbeit-einziehen.ps1`
committet ruhende Fremdarbeit nach master, OHNE sie zu pruefen (die
Dokumentation sagt es selbst: "nicht von Hand geprueft"). Am 11.10.2026 hat er
in `Agenten/Handel/leitstand_nautilus.py` zwei Defekte nach master gebracht:
  - `getattr(obj, name, default, False)` an zwei Stellen - getattr nimmt
    hoechstens drei Argumente, `status()` warf bei JEDEM Aufruf TypeError
    (der Leitstand waere beim Oeffnen gestorben),
  - eine zweite Kraken-Node-Klasse, die den read-only-Kontrakt des Moduls
    brach und dieselbe PID-Datei wie der Prozesse-Reiter schrieb.

Ein `py_compile` haette Fall 1 NICHT gefunden (der Aufruf ist syntaktisch
gueltig, erst zur Laufzeit falsch). Deshalb prueft diese Wache MEHR als
Syntax:

  1. SYNTAX: jede versionierte .py uebersetzt (ast.parse). Findet Tippfehler,
     kaputte Indentation, halb geschriebene Dateien - die haeufigste Form von
     "eine Sitzung wurde mitten im Schreiben unterbrochen".
  2. ARGUMENTZAHL BEKANNTER BUILTINS: getattr/getattr-artige Aufrufe mit zu
     vielen Argumenten. Genau der Fall vom 11.10.2026, den py_compile durchlaesst.
  3. ROTER TESTLAUF: `Agenten/Handel/testlauf.py` meldet einen RUECKSCHRITT
     gegenueber der Basislinie (neue Fehler in einer Suite, die vorher gruen war).
     Das ist das eigentliche Netz: der Sweep hat die Leitstand-Suite rot
     committet, und niemand hat es gesehen.

Sie aendert NICHTS. MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts).
Dieselbe Feststellung hoechstens einmal je RUHE_STUNDEN.

Aufruf (Hermes-Cron, no_agent):
    python Agenten/Hermes/scripts/syntax-tor-wache.py
    python Agenten/Hermes/scripts/syntax-tor-wache.py --alle
    python Agenten/Hermes/scripts/syntax-tor-wache.py --nur-syntax
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]                       # scripts -> Hermes -> Agenten -> BrainFiles
MERK = HIER.parent / "cache" / "syntax-tor-wache.json"

RUHE_STUNDEN = 6.0
ZEITLIMIT_TESTLAUF = 3000        # 50 min. GEMESSEN 11.10.2026, voller Lauf:
                                 #   1398 s (EXIT 0, "Kein Rueckschritt", tests = 16)
                                 # - mit dem korrigierten 2100-s-Limit fuer die
                                 # tests-Suite. Vorher (tests bei 900 s gekappt):
                                 # 1051 s. Die Differenz ist genau der Rest, der
                                 # vorher abgeschnitten wurde.
                                 # 3000 s deckt 1398 s mit 115 % Luft - Absicht:
                                 # der Lauf ist datenabhaengig (drei Dauerlaeufe
                                 # und Spuren schreiben nebenher), die
                                 # tests-Suite allein schwankte an diesem Tag
                                 # zwischen 1444 und 1522 s.
                                 #
                                 # WARNUNG FUER DEN, DER HIER ETWAS SUCHT: eine
                                 # Suite, die 19 min lang KEINE Ausgabe zeigt,
                                 # haengt nicht - testlauf.py liest jede Suite mit
                                 # `stdout=subprocess.PIPE` und gibt ihren Text erst
                                 # nach ihrem Ende aus (Zeile 115). Wer im Log
                                 # stehenbleibt und die Prozess-CPU beobachtet,
                                 # sieht 0 % und haelt es fuer einen Haenger.
                                 # Gemessen 11.10.2026: die tests-Suite lief so
                                 # 19 min still und kam mit 16 Fehlern zurueck.
                                 # Der Cron laeuft alle 6 h - das passt.

# Ordner, deren .py nicht geprueft werden (Junctions, venvs, Fremd-Klone).
AUSLASSEN = {".venv", "__pycache__", "node_modules", "target", "logs",
             "daten", "cache", "state", "docs", ".git", "Modelle",
             "Werkstatt", "site", "Archiv", "_Backups", ".worktrees"}

# Builtins, deren Argumentzahl zur Laufzeit geprueft wird. Zu viele Argumente
# sind ein TypeError, den ast.parse nicht sieht.
MAX_ARGS = {
    "getattr": 3, "setattr": 3, "delattr": 2, "hasattr": 2,
    "isinstance": 2, "issubclass": 2, "int": 2, "float": 2,
    "round": 2, "divmod": 2, "pow": 3, "range": 3,
    "print": None, "sorted": None, "min": None, "max": None,   # beliebig viele
}


def _git(*args: str) -> str:
    try:
        p = subprocess.run(["git", "-C", str(WURZEL), *args],
                           capture_output=True, text=True, errors="replace",
                           timeout=180)
    except (OSError, subprocess.SubprocessError):
        return ""
    return p.stdout if p.returncode == 0 else ""


def versionierte_py() -> list[Path]:
    """Alle versionierten .py-Dateien unterhalb von Agenten/ (Textebene).

    ACHTUNG: `git ls-files A B` ist ein ODER ueber zwei Mustern, kein Filter -
    `git ls-files Agenten/ '*.py'` liefert ALLE Dateien unter Agenten/ und
    zusaetzlich jede .py der Wurzel (4693 statt 1168, gemessen 11.10.2026).
    Deshalb wird hier ueber die Wurzel-Muster gesucht und danach in Python
    gefiltert.
    """
    roh = _git("ls-files", "*.py")
    aus = []
    for zeile in roh.splitlines():
        p = zeile.strip()
        if not p.endswith(".py"):
            continue
        if not p.startswith("Agenten/"):
            continue
        teile = set(Path(p).parts)
        if teile & AUSLASSEN:
            continue
        aus.append(WURZEL / p)
    return aus


def pruefe_syntax(pfade: list[Path]) -> list[str]:
    """Jede Datei mit ast.parse uebersetzen. Rueckgabe: Befundzeilen."""
    befunde = []
    for p in pfade:
        try:
            quelle = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            befunde.append("%s: nicht lesbar (%s)" % (p.relative_to(WURZEL), e))
            continue
        try:
            ast.parse(quelle, filename=str(p))
        except SyntaxError as e:
            befunde.append("%s:%s: %s" % (p.relative_to(WURZEL), e.lineno, e.msg))
    return befunde


def pruefe_argumentzahl(pfade: list[Path]) -> list[str]:
    """Bekannte Builtins mit zu vielen Argumenten (der getattr-Fall)."""
    befunde = []
    for p in pfade:
        try:
            baum = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue          # Syntaxfehler meldet bereits pruefe_syntax
        for k in ast.walk(baum):
            if not isinstance(k, ast.Call):
                continue
            f = k.func
            if not isinstance(f, ast.Name) or f.id not in MAX_ARGS:
                continue
            grenze = MAX_ARGS[f.id]
            if grenze is None:
                continue
            # *args/**kwargs heben die Zaehlung auf - dann nicht melden.
            if any(isinstance(a, ast.Starred) for a in k.args):
                continue
            if any(kw.arg is None for kw in k.keywords):
                continue
            anzahl = len(k.args) + len(k.keywords)
            if anzahl > grenze:
                befunde.append(
                    "%s:%d: %s() mit %d Argumenten (hoechstens %d) - TypeError "
                    "zur Laufzeit" % (p.relative_to(WURZEL), k.lineno, f.id,
                                      anzahl, grenze))
    return befunde


def pruefe_testlauf() -> list[str]:
    """testlauf.py im Handel-Baum: Rueckschritt gegenueber der Basislinie."""
    lauf = WURZEL / "Agenten" / "Handel" / "testlauf.py"
    if not lauf.exists():
        return ["Agenten/Handel/testlauf.py fehlt - Testnetz nicht messbar"]
    py = WURZEL / "Agenten" / "Handel" / "scanner" / ".venv" / "Scripts" / "python.exe"
    if not py.exists():
        return ["scanner-venv fehlt (%s) - Testnetz nicht messbar" % py]
    try:
        p = subprocess.run([str(py), str(lauf)], cwd=str(lauf.parent),
                           capture_output=True, text=True, errors="replace",
                           timeout=ZEITLIMIT_TESTLAUF)
    except subprocess.TimeoutExpired:
        return ["testlauf.py: Zeitlimit %d s ueberschritten" % ZEITLIMIT_TESTLAUF]
    except OSError as e:
        return ["testlauf.py nicht startbar: %s" % e]

    if p.returncode == 0:
        return []
    aus = [z.strip() for z in p.stdout.splitlines() if z.startswith("SCHLECHTER")]
    if aus:
        return aus
    return ["testlauf.py exit %d ohne SCHLECHTER-Zeile:\n%s"
            % (p.returncode, (p.stdout or p.stderr)[-600:])]


def _merker() -> dict:
    try:
        return json.loads(MERK.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _schon_gemeldet(befund: str, merker: dict, jetzt: dt.datetime) -> bool:
    zuletzt = merker.get(befund)
    if not zuletzt:
        return False
    try:
        t = dt.datetime.fromisoformat(zuletzt)
    except ValueError:
        return False
    return (jetzt - t).total_seconds() < RUHE_STUNDEN * 3600


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--alle", action="store_true",
                    help="auch bei Gesundheit eine Zeile ausgeben")
    ap.add_argument("--nur-syntax", action="store_true",
                    help="ohne Testlauf (schnell, fuer Proben)")
    a = ap.parse_args()

    jetzt = dt.datetime.now(dt.timezone.utc)
    pfade = versionierte_py()

    befunde = pruefe_syntax(pfade)
    befunde += pruefe_argumentzahl(pfade)
    if not a.nur_syntax:
        befunde += pruefe_testlauf()

    merker = _merker()
    neu = [b for b in befunde if not _schon_gemeldet(b, merker, jetzt)]

    for b in befunde:
        merker[b] = jetzt.isoformat()
    # Alte Merker (> 7 Tage) aufraeumen, sonst waechst die Datei ewig.
    for k in list(merker):
        try:
            if (jetzt - dt.datetime.fromisoformat(merker[k])).days > 7:
                del merker[k]
        except ValueError:
            del merker[k]
    try:
        MERK.parent.mkdir(parents=True, exist_ok=True)
        MERK.write_text(json.dumps(merker, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    except OSError:
        pass

    if not neu:
        if a.alle:
            print("syntax-tor: %d Datei(en) geprueft, kein neuer Befund"
                  % len(pfade))
        return 0

    print("SYNTAX-TOR: %d neue(r) Befund(e)" % len(neu))
    for b in neu:
        print("  %s" % b)
    print()
    print("Hinweis: der unbeaufsichtigte Sweep fremdarbeit-einziehen committet")
    print("rohen Code ohne Pruefung. Diese Zeile ist der Ersatz dafuer.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
