#!/usr/bin/env python3
"""Tote Konstanten finden: definiert, aber nie gelesen.

Eine Abbruchbedingung, die als Konstante definiert und im Kommentar als
Sicherung beschrieben ist, aber im Code nirgands geprueft wird, behauptet
eine Grenze, die es nicht gibt. Das ist kein Schoenheitsfehler: das Ding,
das sie schuetzen soll, laeuft weiter (gemessen: eine Oberflaeche, deren
Nutzereinstellung nach EINEM Takt wieder ueberschrieben wurde).

Das ist eine Sweep, keine Diagnose: jeder Treffer ist ein Kandidat. Zwei
Gegenvorpruefungen, bevor er in den Bericht geht:

  * Wird der Name in einem DOCSTRING nur ERWAEHNT? Dann ist die Erwaehnung
    kein Gebrauch - aber sie zeigt, was der Autor beabsichtigte. Das ist ein
    Befund, weil die naechste Pflege der Erwaehnung folgt.
  * Wird er dynamisch gelesen (`getattr`, `globals()`, ein dict aus Namen)?
    Dann zaehlt ein naechster Lauf mit `getattr` als Treffer.

Nutzung (aus der Repo-Wurzel, Pfade relativ):

    python scripts/tote_konstanten.py <datei.py> [datei2.py ...]
    python scripts/tote_konstanten.py --breite Agenten/Handel

Ohne Argumente: alle eigenen `.py` unter `--breite` (Standard: die
aktuellen `.py` neben dem Skript). Fremd-Klone und venvs werden
uebersprungen, weil ihre Konventionen nicht unsere sind.

Exitcode 0 = keine tote Konstante, 1 = mindestens eine.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys

# Ordner, deren Inhalt nicht dem Haus untersteht.
UEBERSPRINGEN = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "installs",
    "state-snapshots", "site-packages", ".archive", "target", "build",
    "dist", ".mypy_cache", ".pytest_cache",
}

# Namen, die auf eine Abbruchbedingung hindeuten - nur ein Lesezeichen fuer
# den Bericht, nie ein Filter: die Liste entscheidet nichts, sie faerbt nur.
ABBRUCH_WOERTER = ("MAX", "LIMIT", "GRENZE", "MAXIMAL", "CAP", "STOE")


def sammle_konstanten(pfad: str):
    """(Name, Zeile) aller Modulkonstanten mit Grossbuchstaben."""
    try:
        with open(pfad, "rb") as f:
            baum = ast.parse(f.read(), filename=pfad)
    except (OSError, SyntaxError, ValueError):
        return None
    raus = []
    for kind in baum.body:
        if not isinstance(kind, ast.Assign):
            continue
        for ziel in kind.targets:
            if (isinstance(ziel, ast.Name) and ziel.id.isupper()
                    and ziel.id.isidentifier()):
                raus.append((ziel.id, kind.lineno))
    return raus


def name_vorkommen(pfad: str, name: str):
    """Wo der Name vorkommt: (Zeilenliste, in_docstring)."""
    with open(pfad, encoding="utf-8", errors="replace") as f:
        zeilen = f.readlines()
    treffer = []
    nur_doc = True
    doc_bereiche = _docstrings(zeilen)
    for i, z in enumerate(zeilen, start=1):
        if name in z:
            treffer.append(i)
            if not _in_docstring(i, doc_bereiche):
                nur_doc = False
    return treffer, nur_doc


def _docstrings(zeilen):
    """Zeilen, die zu einem Docstring gehoeren (grob, ueber Quotes)."""
    bereiche = []
    i = 0
    while i < len(zeilen):
        z = zeilen[i]
        for marker in ('"""', "'''"):
            pos = z.find(marker)
            if pos >= 0:
                rest = z[pos + 3:]
                if marker in rest:
                    break
                j = i + 1
                while j < len(zeilen) and marker not in zeilen[j]:
                    j += 1
                bereiche.append((i + 1, min(j + 1, len(zeilen))))
                i = j
                break
        i += 1
    return bereiche


def _in_docstring(zeile: int, bereiche) -> bool:
    return any(a <= zeile <= b for a, b in bereiche)


def pruefe(pfad: str):
    konst = sammle_konstanten(pfad)
    if not konst:
        return []
    befunde = []
    for name, zeile in konst:
        treffer, nur_doc = name_vorkommen(pfad, name)
        # Definition selbst zaehlt nicht als Gebrauch.
        gebraucht = [t for t in treffer if t != zeile]
        if not gebraucht:
            befunde.append((name, zeile, "definiert, NIRGENDS gelesen"))
        elif nur_doc:
            befunde.append((name, zeile,
                            "nur im Docstring erwaehnt - die Erwaehnung "
                            "beschreibt eine Sicherung, die der Code nicht hat"))
    return befunde


def dateien_sammeln(basis: str):
    for wurzel, ordner, namen in os.walk(basis):
        ordner[:] = [o for o in ordner
                     if o not in UEBERSPRINGEN and not o.startswith(".")]
        for n in namen:
            if n.endswith(".py"):
                yield os.path.join(wurzel, n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pfade", nargs="*", help="Dateien oder Ordner")
    ap.add_argument("--breite", help="Ordner rekursiv pruefen")
    args = ap.parse_args()

    ziele = []
    for p in args.pfade or ([args.breite] if args.breite else []):
        if os.path.isdir(p):
            ziele.extend(dateien_sammeln(p))
        elif p.endswith(".py"):
            ziele.append(p)
    if not ziele:
        ziele = [os.path.abspath(__file__)]

    alle = []
    for p in ziele:
        for name, zeile, grund in pruefe(p):
            alle.append((p, name, zeile, grund))

    if not alle:
        print("Keine tote Konstante in %d Datei(en)." % len(ziele))
        return 0
    print("TOTE KONSTANTEN in %d Datei(en) - jede behauptet eine "
          "Sicherung, die es nicht gibt:" % len({a[0] for a in alle}))
    print()
    nach_datei = {}
    for datei, name, zeile, grund in alle:
        nach_datei.setdefault(datei, []).append((name, zeile, grund))
    for datei, eintraege in sorted(nach_datei.items()):
        print("%s" % datei)
        for name, zeile, grund in sorted(eintraege, key=lambda x: x[1]):
            marke = " (Abbruchgrenze?)" if any(
                w in name for w in ABBRUCH_WOERTER) else ""
            print("   Z.%-5d %-34s %s%s" % (zeile, name, grund, marke))
    print()
    print("Gegenprobe je Kandidat: Wird der Name dynamisch gelesen "
          "(getattr/globals)? Steht die beabsichtigte Grenze im Docstring?")
    return 1


if __name__ == "__main__":
    sys.exit(main())