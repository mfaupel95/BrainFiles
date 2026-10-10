"""TP4, Teil 1: Einen Vorschlag anwenden - der einzige schreibende Pfad.

``anwenden.anwenden()`` ist die einzige Stelle im Projekt, die
``scanner/wachen.json`` und ``scanner/bewertung.py`` veraendert und einen
Commit erzeugt. Die Reihenfolge steht fest:

1. Arbeitsbaum pruefen - sauber fuer die zwei Zieldateien **und** nichts im
   Index.
2. Geaenderte oberste JSON-Schluessel pruefen - erst gegen die **fest
   verdrahtete** Denylist (gewinnt immer, egal was ``spuren.json`` als
   ``aenderbar`` deklariert), dann gegen die Whitelist mit Wertebereich aus
   ``spur["aenderbar"]["wachen.json"]``: jeder geaenderte Schluessel muss dort
   stehen und - wo ein ``[min, max]`` deklariert ist - hineinpassen. Fehlt die
   Whitelist, wird nur die Denylist geprueft.
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
7. Vorschlagsordner nach ``verbesserer/berichte/erledigt/`` (bei Namens-
   kollision mit Zeitstempel-Suffix, nie loeschend).
8. Kurzen Commit-Hash zurueckgeben.

``anwenden`` wirft nie - jeder Abschnitt ist abgesichert:

* Schritte 2 und 3 (lesen, JSON parsen, ``.bak`` anlegen) sind noch ohne
  Mutation; ein Fehler dort endet als ``{"ok": False, "grund":
  "Vorbereitung fehlgeschlagen: ..."}``.
* Ab dem ersten Schreibzugriff (Schritt 4) laeuft alles in einem
  try/except: schlaegt ``git apply``/``add``/``commit`` fehl oder fasst der
  Patch eine fremde Datei an, werden beide Zieldateien aus ``.bak``
  wiederhergestellt, der Index geleert und ein ``{"ok": False}``-Dict
  zurueckgegeben. Der Vorschlagsordner bleibt liegen, ``.bak`` bleibt als
  Audit-Spur.
* Schritte 7-8 laufen **nach** dem echten Commit: misslingt die Ablage oder
  der Hash-Abruf, bleibt es bei ``{"ok": True}`` (der Commit ist real), und
  ``grund`` vermerkt die misslungene Ablage.

Nur Standardbibliothek; Git wird als Kommando aufgerufen.
"""

import hashlib
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
_GESPERRTE_PRAEFIXE = (
    "freigabe", "drawdown", "kill_switch", "herzschlag",
    # Spur 2 (XPERP): Deckel, Hebel, Risiko, LLM-Filter, Papierfaktor,
    # Familien-Block, Grid und der Trailing-Hauptschalter sind nie Sache eines
    # Vorschlags - auch dann nicht, wenn jemand sie in spuren.json freigibt.
    "max_hebel", "max_margin", "max_offene_anlaeufe", "risiko_je_anlauf",
    "llm_", "papier_faktor", "familien", "grid_", "trailing_aktiv")


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
    """Die Zieldateien aus ``bak`` zuruecckopieren und aus dem Index
    nehmen. Best effort - Fehler beim Aufraeumen werden geschluckt, damit
    :func:`anwenden` immer sein Dict zurueckgibt."""
    ziele = [p for p in (wachen_pfad, bewertung_pfad) if p is not None]
    for pfad in ziele:
        quelle = bak / pfad.name
        if quelle.exists():
            try:
                shutil.copy2(quelle, pfad)
            except OSError:
                pass
    try:
        subprocess.run(
            ["git", "reset", "--", *[str(p) for p in ziele]],
            cwd=repo, capture_output=True, text=True, check=False)
    except OSError:
        pass


def _ablegen(ordner, unterordner):
    """``ordner`` nach ``WURZEL / "berichte" / unterordner / ordner.name``
    verschieben.

    Kollidiert der Name mit einem bereits abgelegten Ordner (zwei Vorschlaege
    fuer dieselbe Spur am selben Tag), wird an den Zielnamen ein Zeitstempel
    angehaengt - ein vorhandener Audit-Ordner wird nie geloescht."""
    ziel = WURZEL / "berichte" / unterordner / ordner.name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if ziel.exists():
        ziel = ziel.with_name(ziel.name + "-" + _zeitstempel())
    shutil.move(str(ordner), str(ziel))
    return ziel


def _kandidat_hash(ordner):
    """Stabiler Identifikator des Kandidaten: sha256 ueber wachen.neu.json
    (die eigentliche Aenderung), sonst ueber bewertung.patch, sonst None."""
    for name in ("wachen.neu.json", "bewertung.patch"):
        datei = Path(ordner) / name
        if datei.exists():
            return hashlib.sha256(datei.read_bytes()).hexdigest()[:16]
    return None


def _anwendungslog(ordner, entscheidung, grund=""):
    """T-373: einen Eintrag an ``verbesserer/anwendungslog.json`` anhaengen
    (Append-JSON-Lines). Der Funnel ist nach dem Digest-Schritt blind -
    anwenden.py weiss, ob ein Vorschlag angewendet wurde, schreibt das aber
    nicht zurueck. Abwaertskompatibel: neue Datei, kein Umbau bestehender
    Logik. ``lauf_ts`` kommt aus dem Ordnernamen (``<datum>-<spur>``)."""
    name = Path(ordner).name
    # Ordnername ist "<datum>-<spur>", das Datum selbst hat Bindestriche
    # (2026-10-07-spur1). Die ersten 10 Zeichen sind das Datum.
    lauf_ts = name[:10] if len(name) >= 10 else name
    eintrag = {
        "lauf_ts": lauf_ts,
        "anwendung_ts": datetime.now(timezone.utc).isoformat(),
        "kandidat_hash": _kandidat_hash(ordner),
        "entscheidung": entscheidung,
        "grund_optional": grund or "",
    }
    ziel = WURZEL / "anwendungslog.json"
    with open(ziel, "a", encoding="utf-8") as f:
        f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    return eintrag


def anwenden(ordner, spur, repo):
    """Vorschlag aus ``ordner`` anwenden. Rueckgabe
    ``{"ok": bool, "grund": str, "commit": str | None}``.
    """
    ordner = Path(ordner)
    repo = Path(repo)
    wachen_pfad = Path(spur["wachen"]).resolve()
    # Spur 2 (XPERP) hat keine Bewertungsdatei: nur wachen.json wird angefasst.
    bewertung_pfad = (Path(spur["bewertung_datei"]).resolve()
                      if spur.get("bewertung_datei") else None)
    ziele = [p for p in (wachen_pfad, bewertung_pfad) if p is not None]
    pfade = [str(p) for p in ziele]

    # 1. Arbeitsbaum
    ok, grund = baum_sauber(pfade, repo)
    if not ok:
        return {"ok": False, "grund": "Arbeitsbaum nicht sauber: " + grund,
                "commit": None}

    # 2. Denylist + Bereichs-/Whitelist-Pruefung - nur wenn es ueberhaupt
    #    einen wachen.json-Diff gibt. Alles hier ist noch lesend; ein Fehler
    #    (kaputtes JSON, verschwundene Datei) endet als "Vorbereitung
    #    fehlgeschlagen" ohne jede Aenderung am Arbeitsbaum.
    wachen_neu_datei = ordner / "wachen.neu.json"
    hat_wachen_neu = wachen_neu_datei.exists()
    if hat_wachen_neu:
        try:
            alt = wachen_pfad.read_text(encoding="utf-8")
            neu = wachen_neu_datei.read_text(encoding="utf-8")
            schluessel = geaenderte_schluessel(alt, neu)
        except Exception as fehler:  # noqa: BLE001
            return {"ok": False,
                    "grund": "Vorbereitung fehlgeschlagen: %s" % fehler,
                    "commit": None}

        # 2a. Fest verdrahtete Denylist - gewinnt immer.
        frei, name = denylist_ok(schluessel)
        if not frei:
            return {"ok": False, "grund": "Denylist: " + name, "commit": None}

        # 2b. Bereichs-/Whitelist-Pruefung (Spec TP4, Schritt 2): jeder
        #     geaenderte Schluessel muss in spuren.json unter
        #     spur["aenderbar"]["wachen.json"] stehen und - wo dort ein
        #     [min, max] deklariert ist - innerhalb dieser Grenzen liegen.
        #     Fehlt die Whitelist ganz, wird der Check uebersprungen
        #     (Rueckwaertskompatibilitaet); "liste" (watchlist) hat keinen
        #     Bereich.
        wl = spur.get("aenderbar", {}).get("wachen.json")
        if wl is not None:
            try:
                neu_obj = json.loads(neu)
            except Exception as fehler:  # noqa: BLE001
                return {"ok": False,
                        "grund": "Vorbereitung fehlgeschlagen: %s" % fehler,
                        "commit": None}
            for key in sorted(schluessel):
                if key not in wl:
                    return {"ok": False,
                            "grund": "nicht auf der Whitelist: %s" % key,
                            "commit": None}
                bereich = wl[key]
                if (isinstance(bereich, list) and len(bereich) == 2
                        and all(isinstance(g, (int, float))
                                and not isinstance(g, bool) for g in bereich)):
                    lo, hi = bereich
                    try:
                        wert = float(neu_obj[key])
                    except (KeyError, TypeError, ValueError):
                        return {"ok": False,
                                "grund": ("kein numerischer Wert fuer "
                                          "Bereichsschluessel: %s" % key),
                                "commit": None}
                    if wert < lo or wert > hi:
                        return {"ok": False,
                                "grund": ("ausserhalb des erlaubten Bereichs: "
                                          "%s=%s nicht in [%s, %s]"
                                          % (key, neu_obj[key], lo, hi)),
                                "commit": None}

    # 2b2. Basis-Pruefsumme (Spur 2): hat sich wachen.json seit dem Lauf
    #      geaendert - auch an einem Whitelist-Schluessel, den der Vorschlag
    #      gar nicht anfasst -, wuerde das byteweise Ueberschreiben diese
    #      Aenderung still zuruecksetzen. Vorschlaege ohne Pruefsumme (Spur 1,
    #      Spur 3) bleiben unveraendert.
    basis_datei = ordner / "basis.sha256"
    if hat_wachen_neu and basis_datei.exists():
        soll = basis_datei.read_text(encoding="utf-8").strip()
        ist = hashlib.sha256(wachen_pfad.read_bytes()).hexdigest()
        if ist != soll:
            return {"ok": False,
                    "grund": ("wachen.json hat sich seit dem Lauf geaendert "
                              "(Basis-Pruefsumme) - /nein und neuen Lauf "
                              "abwarten"),
                    "commit": None}

    # 2c. commit.txt frueh pruefen - vor jeder Aenderung am Arbeitsbaum.
    commit_datei = ordner / "commit.txt"
    if (not commit_datei.exists()
            or not commit_datei.read_text(encoding="utf-8").strip()):
        return {"ok": False, "grund": "commit.txt fehlt oder ist leer",
                "commit": None}

    # 3. .bak beider Zieldateien - ab hier bleibt die Sicherung als
    # Audit-Spur stehen, auch wenn spaeter zurueckgerollt wird. Noch keine
    # Mutation - ein Fehler beim Sichern endet als "Vorbereitung
    # fehlgeschlagen" ohne Rollback-Bedarf.
    try:
        bak = WURZEL / "bak" / _zeitstempel()
        bak.mkdir(parents=True, exist_ok=True)
        for ziel in ziele:
            shutil.copy2(ziel, bak / ziel.name)
    except Exception as fehler:  # noqa: BLE001
        return {"ok": False,
                "grund": "Vorbereitung fehlgeschlagen: %s" % fehler,
                "commit": None}

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
            if bewertung_pfad is None:
                raise _PatchFremd(patch_datei.name)
            fremd = _patch_fremde_pfade(patch_datei, bewertung_pfad, repo)
            if fremd:
                raise _PatchFremd(fremd[0])
            subprocess.run(["git", "apply", str(patch_datei)],
                           cwd=repo, check=True)

        # 6. genau die zwei Dateien stagen und committen
        subprocess.run(["git", "add", *pfade], cwd=repo, check=True)
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

    # 7.-8. Der Commit steht. Ablage nach erledigt/ und Hash-Abruf duerfen den
    # Erfolg nicht mehr kippen: schlaegt eines fehl, bleibt es bei
    # ``{"ok": True}`` mit dem echten Hash (soweit ermittelbar) - nur der
    # Grund vermerkt die misslungene Ablage.
    try:
        _anwendungslog(ordner, "angewendet")
        _ablegen(ordner, "erledigt")
        kurz = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo, capture_output=True, text=True, check=True)
        return {"ok": True, "grund": "angewandt",
                "commit": kurz.stdout.strip()}
    except Exception as fehler:  # noqa: BLE001
        kurz = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo, capture_output=True, text=True, check=False)
        hash_kurz = kurz.stdout.strip() if kurz.returncode == 0 else None
        return {"ok": True,
                "grund": "angewandt (Ablage nach erledigt/ misslang: %s)"
                         % fehler,
                "commit": hash_kurz or None}


def ablehnen(ordner, grund):
    """``grund`` in ``ordner/ABGELEHNT.txt`` schreiben, dann ``ordner`` nach
    ``verbesserer/berichte/abgelehnt/`` verschieben."""
    ordner = Path(ordner)
    (ordner / "ABGELEHNT.txt").write_text(grund, encoding="utf-8")
    _ablegen(ordner, "abgelehnt")
