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
   Vorher wird ueber ``git apply --numstat`` erzwungen, dass der Patch
   **ausschliesslich** ``spur["bewertung_datei"]`` anfasst - sonst
   kaeme ein Hunk fuer ``wachen.json`` oder eine dritte Datei an der
   Denylist vorbei.
6. ``git add`` **genau** der zwei Zieldateien, dann ``git commit -F
   commit.txt``.
7. Vorschlagsordner nach ``verbesserer/berichte/erledigt/``.
8. Kurzen Commit-Hash zurueckgeben.

Ab dem ersten Schreibzugriff (Schritt 4) laeuft alles in einem
try/except: schlaegt ``git apply``/``add``/``commit`` fehl oder fasst der
Patch eine fremde Datei an, werden beide Zieldateien aus ``.bak``
wiederhergestellt, der Index geleert und ein ``{"ok": False}``-Dict
zurueckgegeben - ``anwenden`` wirft nie. Der Vorschlagsordner bleibt
liegen, ``.bak`` bleibt als Audit-Spur.

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


class _PatchFremd(Exception):
    """``bewertung.patch`` beruehrt eine andere Datei als die Bewertungsdatei.

    Wird innerhalb des Roll-back-Blocks von :func:`anwenden` geworfen und
    dort in eine ``{"ok": False}``-Antwort gewandelt.
    """


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


def _repo_wurzel(pfad):
    """Erster Vorfahre von ``pfad`` (inklusive), der ``.git`` enthaelt -
    Datei im Worktree oder Verzeichnis. ``None``, wenn keiner. Gleiche Logik
    wie ``vorschlag._repo_wurzel``."""
    pfad = Path(pfad)
    for anker in [pfad, *pfad.parents]:
        if (anker / ".git").exists():
            return anker
    return None


def _wurzel_relativ(pfad, repo):
    """``pfad`` relativ zur Repo-Wurzel als POSIX-String - so, wie ``git
    apply --numstat`` seine Pfade ausgibt. Faellt auf ``repo`` als Wurzel und
    zuletzt auf den blossen Dateinamen zurueck."""
    pfad = Path(pfad).resolve()
    wurzel = _repo_wurzel(pfad) or Path(repo)
    try:
        return pfad.relative_to(Path(wurzel).resolve()).as_posix()
    except ValueError:
        return pfad.name


def _patch_fremde_pfade(patch_datei, bewertung_pfad, repo):
    """Liste der von ``patch_datei`` beruehrten Pfade, die **nicht** der
    repo-relative Pfad von ``bewertung_pfad`` sind (leer = Patch fasst nur
    die Bewertungsdatei an). ``git apply --numstat`` parst den Patch, ohne
    ihn anzuwenden; ein unlesbarer Patch loest hier ``CalledProcessError``
    aus."""
    numstat = subprocess.run(
        ["git", "apply", "--numstat", str(patch_datei)],
        cwd=repo, capture_output=True, text=True, check=True)
    erlaubt = _wurzel_relativ(bewertung_pfad, repo)
    fremd = []
    for zeile in numstat.stdout.splitlines():
        spalten = zeile.split("\t")
        if len(spalten) < 3:
            continue
        pfad = spalten[2].strip()
        if pfad and pfad != erlaubt:
            fremd.append(pfad)
    return fremd


def _wiederherstellen(bak, wachen_pfad, bewertung_pfad, repo):
    """Beide Zieldateien aus ``bak`` zuruecckopieren und aus dem Index
    nehmen. Best effort - Fehler beim Aufraeumen werden geschluckt, damit
    :func:`anwenden` immer sein Dict zurueckgibt."""
    for pfad in (wachen_pfad, bewertung_pfad):
        quelle = bak / pfad.name
        if quelle.exists():
            try:
                shutil.copy2(quelle, pfad)
            except OSError:
                pass
    try:
        subprocess.run(
            ["git", "reset", "--", str(wachen_pfad), str(bewertung_pfad)],
            cwd=repo, capture_output=True, text=True, check=False)
    except OSError:
        pass


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

    # 2b. commit.txt frueh pruefen - vor jeder Aenderung am Arbeitsbaum.
    commit_datei = ordner / "commit.txt"
    if (not commit_datei.exists()
            or not commit_datei.read_text(encoding="utf-8").strip()):
        return {"ok": False, "grund": "commit.txt fehlt oder ist leer",
                "commit": None}

    # 3. .bak beider Zieldateien - ab hier bleibt die Sicherung als
    # Audit-Spur stehen, auch wenn spaeter zurueckgerollt wird.
    bak = WURZEL / "bak" / _zeitstempel()
    bak.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wachen_pfad, bak / wachen_pfad.name)
    shutil.copy2(bewertung_pfad, bak / bewertung_pfad.name)

    # 4.-7. Ab hier ist der Arbeitsbaum veraendert. Jeder Fehler - auch die
    # Pfad-Allowlist in Schritt 5 - stellt beide Zieldateien aus .bak wieder
    # her, nimmt Gestagtes zurueck und gibt ein ``{"ok": False}``-Dict
    # zurueck. ``anwenden`` wirft nie: dauerlauf/Task 12 verlassen sich auf
    # das Dict. Der Vorschlagsordner bleibt liegen (nicht nach erledigt/),
    # damit er neu versucht oder abgelehnt werden kann.
    try:
        # 4. wachen.json byteweise ersetzen (CRLF bleibt)
        if hat_wachen_neu:
            wachen_pfad.write_bytes(wachen_neu_datei.read_bytes())

        # 5. Gewichts-Patch - leere/nur-Whitespace-Datei ueberspringen.
        # Vor ``git apply``: erzwingen, dass der Patch NUR die Bewertungs-
        # datei anfasst. ``git apply`` selbst kennt keine Pfad-Schranke, die
        # Denylist sieht nur wachen.json - ein Hunk fuer wachen.json oder
        # eine dritte Datei kaeme sonst ungeprueft durch.
        patch_datei = ordner / "bewertung.patch"
        if (patch_datei.exists()
                and patch_datei.read_text(encoding="utf-8").strip()):
            fremd = _patch_fremde_pfade(patch_datei, bewertung_pfad, repo)
            if fremd:
                raise _PatchFremd(fremd[0])
            subprocess.run(["git", "apply", str(patch_datei)],
                           cwd=repo, check=True)

        # 6. genau die zwei Dateien stagen und committen
        subprocess.run(["git", "add", str(wachen_pfad), str(bewertung_pfad)],
                       cwd=repo, check=True)
        subprocess.run(["git", "commit", "-F", str(commit_datei)],
                       cwd=repo, check=True)
    except _PatchFremd as fehler:
        _wiederherstellen(bak, wachen_pfad, bewertung_pfad, repo)
        return {"ok": False,
                "grund": "Patch fasst fremde Datei an: %s" % fehler,
                "commit": None}
    except Exception as fehler:  # noqa: BLE001 - bewusst breit, siehe oben
        _wiederherstellen(bak, wachen_pfad, bewertung_pfad, repo)
        return {"ok": False,
                "grund": "Anwenden fehlgeschlagen, aus .bak wiederhergestellt: "
                         "%s" % fehler,
                "commit": None}

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
