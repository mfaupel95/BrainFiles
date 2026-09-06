"""TP4, Teil 1: Einen Vorschlag anwenden - der einzige schreibende Pfad.

``anwenden.anwenden()`` ist die einzige Stelle im Projekt, die
``scanner/wachen.json`` und ``scanner/bewertung.py`` veraendert und einen
Commit erzeugt. Die Reihenfolge steht fest:

1. Arbeitsbaum pruefen - sauber fuer die zwei Zieldateien **und** nichts im
   Index.
2. Geaenderte oberste JSON-Schluessel gegen eine **fest verdrahtete** Denylist
   pruefen. Diese Liste gewinnt immer - egal, was ``spuren.json`` als
   ``aenderbar`` deklariert.
3. Zeitgestempeltes ``.bak`` beider Zieldateien nach
   ``verbesserer/bak/<zeit>/``.
4. ``wachen.neu.json`` **byteweise** nach ``spur["wachen"]`` schreiben - kein
   Reserialisieren, damit CRLF und Formatierung erhalten bleiben.
5. ``bewertung.patch`` per ``git apply`` - nur, wenn er nicht leer ist
   (Task 10 liefert bei reiner Gate-/Sizing-Aenderung eine leere Datei).
6. ``git add`` **genau** der zwei Zieldateien, dann ``git commit -F
   commit.txt``.
7. Vorschlagsordner nach ``verbesserer/berichte/erledigt/``.
8. Kurzen Commit-Hash zurueckgeben.

Nur Standardbibliothek; Git wird als Kommando aufgerufen.
"""

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import suche  # liegt neben diesem Modul; nur ``DENYLIST`` wird gebraucht

WURZEL = Path(__file__).resolve().parent

# Zusaetzlich zur festen ``suche.DENYLIST`` gesperrt: jeder Schluessel, der mit
# einem dieser Praefixe beginnt, ist ein harter Sicherheitsschalter und darf
# nie von einem Vorschlag angefasst werden.
_GESPERRTE_PRAEFIXE = ("freigabe", "drawdown", "kill_switch", "herzschlag")


def geaenderte_schluessel(alt_text, neu_text):
    """Menge der obersten JSON-Schluessel, deren Wert sich zwischen ``alt_text``
    und ``neu_text`` unterscheidet.

    Beide Texte werden als JSON geparst. Ungueltiges JSON oder ein Nicht-Objekt
    an oberster Ebene -> ``ValueError``.
    """
    try:
        alt = json.loads(alt_text)
        neu = json.loads(neu_text)
    except json.JSONDecodeError as fehler:
        raise ValueError("kein gueltiges JSON: %s" % fehler) from fehler
    if not isinstance(alt, dict) or not isinstance(neu, dict):
        raise ValueError("JSON-Objekt an oberster Ebene erwartet")
    fehlt = object()
    return {s for s in set(alt) | set(neu)
            if alt.get(s, fehlt) != neu.get(s, fehlt)}


def denylist_ok(schluessel):
    """``(True, "")`` wenn keiner der Schluessel gesperrt ist.

    ``(False, name)`` beim ersten Schluessel (alphabetisch), der in
    ``suche.DENYLIST`` liegt oder mit einem der ``_GESPERRTE_PRAEFIXE``
    beginnt.
    """
    for name in sorted(schluessel):
        if name in suche.DENYLIST or name.startswith(_GESPERRTE_PRAEFIXE):
            return False, name
    return True, ""


def baum_sauber(pfade, repo):
    """``git status --porcelain`` fuer ``pfade`` leer **und** nichts im Index.

    Rueckgabe ``(True, "")`` wenn beide Bedingungen halten, sonst
    ``(False, grund)``.
    """
    repo = Path(repo)
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", *[str(p) for p in pfade]],
        cwd=repo, capture_output=True, text=True)
    if status.returncode != 0:
        return False, "Baum: git status fehlgeschlagen: " + status.stderr.strip()
    if status.stdout.strip():
        return False, "Baum traegt Aenderung an Zieldatei: " + \
            status.stdout.strip()
    index = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo, capture_output=True, text=True)
    if index.returncode != 0:
        return False, "Baum: git diff --cached fehlgeschlagen: " + \
            index.stderr.strip()
    if index.stdout.strip():
        return False, "Baum hat Eintrag im Index: " + index.stdout.strip()
    return True, ""


def _zeitstempel():
    """UTC-Zeitstempel, dateisystemtauglich und je Aufruf eindeutig."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _ablegen(ordner, unterordner):
    """``ordner`` nach ``WURZEL / "berichte" / unterordner / ordner.name``
    verschieben; ein bereits vorhandenes Ziel wird ersetzt."""
    ziel = WURZEL / "berichte" / unterordner / ordner.name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if ziel.exists():
        shutil.rmtree(ziel)
    shutil.move(str(ordner), str(ziel))
    return ziel


def anwenden(ordner, spur, repo):
    """Vorschlag aus ``ordner`` anwenden. Rueckgabe
    ``{"ok": bool, "grund": str, "commit": str | None}``.
    """
    ordner = Path(ordner)
    repo = Path(repo)
    wachen_pfad = Path(spur["wachen"]).resolve()
    bewertung_pfad = Path(spur["bewertung_datei"]).resolve()
    pfade = [str(wachen_pfad), str(bewertung_pfad)]

    # 1. Arbeitsbaum
    ok, grund = baum_sauber(pfade, repo)
    if not ok:
        return {"ok": False, "grund": "Arbeitsbaum nicht sauber: " + grund,
                "commit": None}

    # 2. Denylist - nur wenn es ueberhaupt einen wachen.json-Diff gibt.
    wachen_neu_datei = ordner / "wachen.neu.json"
    hat_wachen_neu = wachen_neu_datei.exists()
    if hat_wachen_neu:
        alt = wachen_pfad.read_text(encoding="utf-8")
        neu = wachen_neu_datei.read_text(encoding="utf-8")
        schluessel = geaenderte_schluessel(alt, neu)
        frei, name = denylist_ok(schluessel)
        if not frei:
            return {"ok": False, "grund": "Denylist: " + name, "commit": None}

    # 3. .bak beider Zieldateien
    bak = WURZEL / "bak" / _zeitstempel()
    bak.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wachen_pfad, bak / wachen_pfad.name)
    shutil.copy2(bewertung_pfad, bak / bewertung_pfad.name)

    # 4. wachen.json byteweise ersetzen (CRLF bleibt)
    if hat_wachen_neu:
        wachen_pfad.write_bytes(wachen_neu_datei.read_bytes())

    # 5. Gewichts-Patch - leere/nur-Whitespace-Datei ueberspringen
    patch_datei = ordner / "bewertung.patch"
    if patch_datei.exists() and patch_datei.read_text(encoding="utf-8").strip():
        subprocess.run(["git", "apply", str(patch_datei)],
                       cwd=repo, check=True)

    # 6. genau die zwei Dateien stagen und committen
    subprocess.run(["git", "add", str(wachen_pfad), str(bewertung_pfad)],
                   cwd=repo, check=True)
    subprocess.run(["git", "commit", "-F", str(ordner / "commit.txt")],
                   cwd=repo, check=True)

    # 7. Ordner nach berichte/erledigt/
    _ablegen(ordner, "erledigt")

    # 8. kurzer Commit-Hash
    kurz = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          cwd=repo, capture_output=True, text=True, check=True)
    return {"ok": True, "grund": "angewandt", "commit": kurz.stdout.strip()}


def ablehnen(ordner, grund):
    """``grund`` in ``ordner/ABGELEHNT.txt`` schreiben, dann ``ordner`` nach
    ``verbesserer/berichte/abgelehnt/`` verschieben."""
    ordner = Path(ordner)
    (ordner / "ABGELEHNT.txt").write_text(grund, encoding="utf-8")
    _ablegen(ordner, "abgelehnt")
