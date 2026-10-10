#!/usr/bin/env python3
"""Konfig-Doktor-Wache (no_agent) - meldet nur KRITISCH, leere Ausgabe = nichts.

WARUM DIESE WACHE EXISTIERT (05.10.2026)
----------------------------------------
Am 05.10.2026 um 22:12:52 war die Junction `BrainFiles/Werkstatt -> O:/Werkstatt`
durch einen echten, fast leeren Ordner ersetzt. Folge: alle 49 Repos, omnitrade,
OmniRoute und die Projekte waren ueber den BrainFiles-Pfad unsichtbar;
`omnitrade.cmd` meldete "keine Statusdatei", Repos-Zentrale und Repo-Bots lasen
ins Leere. Auf O: lag alles unversehrt - nur der Verweis war weg. Aufgefallen ist
es zufaellig in einer Sitzung, die den omnitrade-Stand pruefen wollte. Es gab
KEINE Wache dafuer, obwohl der konfig-doktor `LAUFZEIT-JUNCTION-*` als KRITISCH
kennt - nur rief ihn niemand auf.

DREI ZEUGEN, ABSICHTLICH
------------------------
1. DIREKTER VERWEIS-TEST (schnell, ohne Fremdprozess): fuer jeden erwarteten
   Verweis wird geprueft, dass er existiert, ein Reparse-Punkt ist und das Ziel
   ERREICHBAR ist. Das faengt den Vorfall oben in Millisekunden und funktioniert
   auch, wenn der Doktor selbst defekt ist.
2. ZIEL- UND SCHREIBTEST (07.10.2026): Zeuge 1 prueft nur, DASS ein Verweis da
   ist. Ein Verweis auf das FALSCHE Ziel oder ein Verweis, den die Werkzeuge
   nicht durchlaufen, kam darin nicht vor. Beides ist vorgekommen:
   `HERMES_WRITE_SAFE_ROOT` stand nur auf BrainFiles, der Schreibpruefer loeste
   den Reparse-Punkt auf `O:\\` auf und lehnte JEDEN Schreibzugriff in die Repos
   ab - lesen ging, schreiben nicht. Und die Bots legen ihre `.env` aus einer
   Vorlage an, in der der Wert noch fehlt; faellt er dort heraus, faellt die
   Sandbox auf den Standard zurueck und die Repos sind wieder zu.
   Deshalb: Ziel gegen den Erwartungswert vergleichen, einen echten Schreibtest
   durch den BrainFiles-Pfad fahren, und pruefen, dass JEDE Hermes-`.env` den
   Werkstatt-Pfad traegt.
3. KONFIG-DOKTOR (`Agenten/Routinen/konfig-doktor.ps1 -Kurz -OhneExtern`):
   breiter Blick (Regelpaare, Junction-Modul, Plattenplatz, Ballast). Gemeldet
   wird NUR KRITISCH - WARNUNGEN und HINWEISE sind fuer eine Wache Rauschen.

Ein Fehler der Pruefung ist NIE ein leeres Ergebnis: faellt der Doktor aus
(Exitcode 2, Zeitueberschreitung, unlesbare Ausgabe), wird das gemeldet, nicht
verschwiegen. Eine leere Ausgabe bedeutet genau eines: alles geprueft, nichts
KRITISCH.

Aufruf:
  python konfig-doktor-wache.py            # Cron-Betrieb: nur Befunde
  python konfig-doktor-wache.py --immer    # auch bei Gesundheit eine Zeile
  python konfig-doktor-wache.py --json     # Zustand fuer Werkzeuge

Merksatz: die Merkdatei traegt den Befund OHNE Zahlen, damit ein wachsender
Wert dieselbe Feststellung bleibt und nicht jede Stunde neu meldet. Ziffern
werden dabei als GANZE FOLGE ersetzt (nicht je Ziffer) - sonst macht '3' -> '#'
und '99' -> '##' aus derselben Feststellung zwei verschiedene Kennungen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent.parent          # Agenten/Hermes/scripts -> BrainFiles
DOKTOR = WURZEL / "Agenten" / "Routinen" / "konfig-doktor.ps1"
ZUSTAND = HIER.parent / "cache" / "konfig-doktor-wache.json"

# Erwartete Verweise: Name -> Ziel. Ein fehlender oder toter Verweis ist ein
# KRITISCHER Befund, weil daran ganze Baeume haengen (Repos, Modelle).
VERWEISE = {
    "Werkstatt": "O:\\Werkstatt",
    "Modelle": "O:\\Modelle",
}

# Verweise, die zusaetzlich einen Schreibtest bekommen. Nur die, in die
# Werkzeuge wirklich schreiben: in die Repos unter Werkstatt. `Modelle` ist
# reiner Lesestoff - dort waere eine Probedatei nur Ballast.
SCHREIBTEST = ("Werkstatt",)

HERMES_HOME = HIER.parent                    # Agenten/Hermes
DOKTOR_FRIST_S = 180.0      # der Kurz-Lauf braucht ~8 s; 180 s ist Luft
WIEDERHOLUNG_H = 12         # derselbe Befund hoechstens alle 12 h melden


def _powershell() -> str:
    sysroot = os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(sysroot, "System32", "WindowsPowerShell", "v1.0",
                        "powershell.exe")


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _merkdatei() -> dict:
    try:
        with open(Path(ZUSTAND), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _merken(d: dict) -> None:
    try:
        ziel = Path(ZUSTAND)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with open(ziel, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError:
        pass


def _kennung(text: str) -> str:
    """Schluessel eines Befunds OHNE Zahlen - ein wachsender Wert bleibt
dieselbe Feststellung. Ziffernfolgen werden als GANZE FOLGE ersetzt."""
    ohne_zahlen = re.sub(r"[0-9]+", "#", text)
    return hashlib.sha1(ohne_zahlen.encode("utf-8")).hexdigest()[:12]


# --- Zeuge 1: die Verweise selbst ------------------------------------------

def _ist_verweis(p) -> bool:
    """Ist der Pfad ein Reparse-Punkt (Junction ODER Symlink)?

    WICHTIG: `os.path.islink` liefert fuer eine Windows-JUNCTION False. Wer nur
    darauf prueft, haelt jede Junction fuer einen echten Ordner und ueberspringt
    still jede weitere Pruefung. Verlaesslich ist nur das Datei-Attribut
    FILE_ATTRIBUTE_REPARSE_POINT (0x400)."""
    try:
        st = os.lstat(str(p))
    except OSError:
        return False
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & 0x400) or os.path.islink(str(p))


def verweis_lage(wurzel, name: str, ziel: str) -> str:
    """'' wenn gesund, sonst ein Klartext-Befund. Nie werfen."""
    p = Path(wurzel) / name
    if not p.exists():
        return "%s fehlt ganz (erwartet: Verweis auf %s)" % (name, ziel)
    try:
        os.lstat(str(p))
    except OSError as e:
        return "%s nicht lesbar (%s)" % (name, e)
    if not _ist_verweis(p):
        try:
            anzahl = sum(1 for _ in os.scandir(str(p)))
        except OSError:
            anzahl = -1
        return ("%s ist KEIN Verweis mehr, sondern ein echter Ordner "
                "(%d Eintraege) - erwartet: Verweis auf %s"
                % (name, anzahl, ziel))
    try:
        os.listdir(str(p))
    except OSError as e:
        return ("%s zeigt ins Leere - Ziel %s nicht erreichbar (%s)"
                % (name, ziel, e))
    return ""


# --- Zeuge 2: Ziel, Schreibtest, .env-Lage ----------------------------------

def _normalisiert(pfad: str) -> str:
    """Vergleichsform eines Windows-Pfads: ohne \\\\?\\-Praefix, ohne Schraegstrich
am Ende, klein geschrieben."""
    s = str(pfad).strip().strip('"').strip("'")
    if s.startswith("\\\\?\\"):
        s = s[4:]
    s = s.replace("/", "\\")
    while len(s) > 3 and s.endswith("\\"):
        s = s[:-1]
    return s.lower()


def ziel_lage(wurzel, name: str, ziel: str) -> str:
    """Zeigt der Verweis auf das ERWARTETE Ziel? '' wenn gesund. Nie werfen.

    Zeuge 1 fragt nur, ob ueberhaupt ein Verweis da ist. Ein Verweis auf ein
    anderes Laufwerk ist genauso kaputt, sieht aber gesund aus."""
    p = Path(wurzel) / name
    if not p.exists():
        return ""                      # fehlt ganz - Zeuge 1 meldet das schon
    try:
        if not _ist_verweis(p):
            return ""                  # echter Ordner - Zeuge 1 meldet das schon
        tatsaechlich = os.readlink(str(p))
    except OSError as e:
        return "%s: Ziel nicht lesbar (%s)" % (name, e)
    if _normalisiert(tatsaechlich) != _normalisiert(ziel):
        return ("%s zeigt auf %s statt auf %s"
                % (name, tatsaechlich, ziel))
    return ""


def schreibtest(wurzel, name: str, ziel: str) -> str:
    """Ein echter Schreibtest DURCH den BrainFiles-Pfad. '' wenn gesund.

    Der Pfad geht bewusst ueber den Verweis, nicht direkt ueber das Ziel: nur so
    zeigt sich, ob ein Werkzeug, das den Reparse-Punkt aufloest, danach noch
    innerhalb seiner Sandbox liegt. Genau daran scheiterte das Schreiben in die
    Repos, waehrend Lesen und Terminal weiterkamen."""
    p = Path(wurzel) / name
    if not p.exists() or not _ist_verweis(p):
        return ""                      # nichts zu testen - Zeuge 1 meldet es
    probe = p / ".wache-schreibtest.tmp"
    try:
        probe.write_text("wache", encoding="utf-8")
    except OSError as e:
        return ("%s ist nicht beschreibbar (%s) - Werkzeuge mit Schreib-Sandbox "
                "koennen dort nichts anlegen" % (name, e))
    try:
        probe.unlink()
    except OSError:
        return ("%s: Schreibtest-Restdatei liess sich nicht loeschen (%s)"
                % (name, probe))
    if probe.exists():
        return "%s: Schreibtest-Restdatei blieb liegen (%s)" % (name, probe)
    return ""


def env_lage(hermes_home: Path) -> str:
    """Kann jedes Repo-Bot-Profil in die Repos schreiben? '' wenn gesund.

    Geprueft werden nur die Profile, die wirklich Repos bedienen: ihr `SOUL.md`
    nennt `Werkstatt`. Ein Profil ohne diesen Bezug braucht den Pfad nicht - es
    mitzuzaehlen erzeugt 27 Meldungen statt 17 und macht die Wache zum
    Dauer-Alarm, den niemand mehr liest. Dazu die Haupt-`.env`, die alle erben.

    Jedes Profil fuehrt `HERMES_WRITE_SAFE_ROOT` selbst. Fehlt der Werkstatt-Pfad,
    faellt die Sandbox auf den Standard zurueck (nur BrainFiles): der
    Schreibpruefer loest den Reparse-Punkt auf `O:\\` auf und lehnt JEDEN
    Schreibzugriff in die Repos ab - lesen geht, schreiben nicht."""
    if not hermes_home.is_dir():
        return "Hermes-Verzeichnis nicht gefunden (%s)" % hermes_home
    werkstatt = _normalisiert(VERWEISE.get("Werkstatt", r"O:\Werkstatt"))
    brainfiles = _normalisiert(str(WURZEL))

    zu_pruefen = []
    haupt = hermes_home / ".env"
    if haupt.is_file():
        zu_pruefen.append(haupt)
    for soul in sorted(hermes_home.glob("profiles/*/SOUL.md")):
        try:
            if "werkstatt" not in soul.read_text(encoding="utf-8",
                                                 errors="replace").lower():
                continue
        except OSError:
            continue
        env = soul.parent / ".env"
        if env.is_file():
            zu_pruefen.append(env)

    if not zu_pruefen:
        return "keine .env gefunden (%s)" % hermes_home

    fehlend = []
    for p in zu_pruefen:
        try:
            inhalt = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            fehlend.append("%s (nicht lesbar: %s)" % (p.relative_to(hermes_home), e))
            continue
        wert = ""
        for zeile in inhalt.splitlines():
            if zeile.startswith("HERMES_WRITE_SAFE_ROOT="):
                wert = zeile.split("=", 1)[1]
                break
        rel = p.relative_to(hermes_home)
        if not wert:
            fehlend.append("%s (kein Eintrag)" % rel)
            continue
        norm = _normalisiert(wert)
        fehlt = []
        if werkstatt not in norm:
            fehlt.append("Werkstatt")
        if brainfiles not in norm:
            fehlt.append("BrainFiles")
        if fehlt:
            fehlend.append("%s (ohne %s)" % (rel, ", ".join(fehlt)))
    if not fehlend:
        return ""
    return ("HERMES_WRITE_SAFE_ROOT unvollstaendig in %d von %d .env: %s - "
            "diese Repo-Bots koennen nicht in die Repos schreiben"
            % (len(fehlend), len(zu_pruefen), "; ".join(fehlend)))


# --- Zeuge 3: der Doktor ----------------------------------------------------

def doktor_kurz(doktor, wurzel) -> tuple:
    """(kritisch, meldung, fehler). `kritisch=None` heisst 'nicht ermittelbar'."""
    if not Path(doktor).exists():
        return None, "", "konfig-doktor.ps1 fehlt (%s)" % doktor
    try:
        aus = subprocess.run(
            [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(doktor), "-Kurz", "-OhneExtern"],
            capture_output=True, timeout=DOKTOR_FRIST_S, cwd=str(wurzel),
        )
    except subprocess.TimeoutExpired:
        return None, "", "konfig-doktor brauchte laenger als %d s" % int(DOKTOR_FRIST_S)
    except OSError as e:
        return None, "", "konfig-doktor nicht startbar (%s)" % e
    roh = (aus.stdout or b"").decode("utf-8", "replace").strip()
    fehler = (aus.stderr or b"").decode("utf-8", "replace").strip()
    code = aus.returncode
    if code == 2:
        return None, roh, "konfig-doktor selbst defekt: %s" % (roh or fehler)[:300]
    if "KRITISCH" not in roh:
        return None, roh, ("konfig-doktor lieferte keine lesbare Zeile "
                           "(Exit %s): %s" % (code, (roh or fehler)[:200]))
    teil = roh.split("KRITISCH", 1)[1]
    ziffern = ""
    for c in teil:
        if c.isdigit():
            ziffern += c
        elif ziffern:
            break
    if not ziffern:
        return None, roh, "konfig-doktor: Zahl hinter KRITISCH nicht lesbar"
    return int(ziffern), roh, ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--immer", action="store_true",
                    help="auch bei Gesundheit eine Zeile ausgeben")
    ap.add_argument("--json", action="store_true", help="Zustand als JSON")
    a = ap.parse_args(argv)

    befunde = []
    for name, ziel in VERWEISE.items():
        text = verweis_lage(WURZEL, name, ziel)
        if text:
            befunde.append(text)
            continue                   # kaputter Verweis: Ziel/Schreibtest sagen nichts
        text = ziel_lage(WURZEL, name, ziel)
        if text:
            befunde.append(text)
        if name in SCHREIBTEST:
            text = schreibtest(WURZEL, name, ziel)
            if text:
                befunde.append(text)

    text = env_lage(HERMES_HOME)
    if text:
        befunde.append(text)

    kritisch, kurz, doktor_fehler = doktor_kurz(DOKTOR, WURZEL)
    if doktor_fehler:
        befunde.append(doktor_fehler)
    elif kritisch:
        befunde.append("konfig-doktor meldet %d KRITISCH (%s)" % (kritisch, kurz))

    jetzt = time.time()
    merk = _merkdatei()
    gesendet = merk.get("gesendet") or {}
    neu, wiederholt = [], 0
    for b in befunde:
        k = _kennung(b)
        letzte = gesendet.get(k)
        if letzte and (jetzt - float(letzte)) < WIEDERHOLUNG_H * 3600:
            wiederholt += 1
            continue
        neu.append(b)
        gesendet[k] = jetzt
    _merken({"gesendet": gesendet, "stand": _jetzt(),
             "befunde": befunde, "kritisch_doktor": kritisch})

    if a.json:
        print(json.dumps({"befunde": befunde, "neu": neu,
                          "wiederholt": wiederholt,
                          "kritisch_doktor": kritisch,
                          "doktor_fehler": doktor_fehler,
                          "stand": _jetzt()}, ensure_ascii=False, indent=2))
        return 0

    if not befunde:
        if a.immer:
            print("konfig-doktor-wache: gesund (%d Verweis(e) ok, Doktor KRITISCH 0)"
                  % len(VERWEISE))
        return 0

    if not neu:
        if a.immer:
            print("konfig-doktor-wache: %d Befund(e), alle innerhalb der "
                  "Merkfrist schon gemeldet" % len(befunde))
        return 0

    zeilen = ["konfig-doktor-wache: %d Befund(e)" % len(neu)]
    for b in neu:
        zeilen.append("  - " + b)
    if wiederholt:
        zeilen.append("  (%d weitere innerhalb der Merkfrist schon gemeldet)"
                      % wiederholt)
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
