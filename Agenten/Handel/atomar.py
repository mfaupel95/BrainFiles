"""Zustandsdateien atomar schreiben und laut lesen.

WARUM ES DAS GIBT (30.09.2026)
------------------------------
Die Spuren schrieben ihren Bestand (zustand.json = die offenen Positionen) mit
`open(pfad, "w")` bzw. `write_text`. Das kuerzt die Datei zuerst auf 0 Byte und
schreibt dann. Bricht der Prozess dazwischen ab (Absturz, Neustart des Rechners,
vom Dauerlauf beendet), bleibt eine leere oder halbe Datei.

Schlimmer war das Lesen: die meisten Spuren fingen `(OSError, ValueError)` und
lieferten dann einen LEEREN Bestand. Der naechste Schreibvorgang ueberschrieb
die Datei damit - die offenen Positionen waren weg, im Live-Modus also echte
Positionen ohne Stop-Verwaltung. Unter Windows genuegt dafuer schon ein
Lesezugriff, der kurz mit einem Virenscanner oder der Handelszentrale
kollidiert (PermissionError ist ein OSError).

WAS HIER GILT
-------------
Schreiben: in eine Nebendatei im selben Ordner, `fsync`, dann `os.replace`
(atomar, auch unter Windows). Der letzte vollstaendige Stand bleibt als
`<datei>.bak` liegen. `os.replace` scheitert unter Windows mit PermissionError,
solange ein Leser die Zieldatei offen hat - deshalb wenige kurze Wiederholungen.

Lesen: Datei fehlt -> Vorgabe (erster Lauf). Datei unlesbar -> wenige
Wiederholungen. Datei defekt -> die `.bak` versuchen (Warnung auf stderr), sonst
`ZustandDefekt`: die Spur bricht den Zyklus laut ab, statt mit leerem Bestand
weiterzumachen. Ein ausgefallener Zyklus ist billiger als verlorene Positionen.

Diese Datei hat keine Abhaengigkeiten ausser der Standardbibliothek. Die Spuren
laden sie per Dateipfad (wie risikostufe.py), nicht ueber sys.path.
"""

from __future__ import annotations

import json
import os
import sys
import time

WIEDERHOLUNGEN = 6
PAUSE_S = 0.05


class ZustandDefekt(Exception):
    """Zustandsdatei und Sicherung sind nicht lesbar - der Bestand ist unklar."""


def _wiederholt(aktion, fehler=PermissionError):
    """Aktion ausfuehren; bei `fehler` kurz warten und neu versuchen."""
    for versuch in range(WIEDERHOLUNGEN):
        try:
            return aktion()
        except fehler:
            if versuch == WIEDERHOLUNGEN - 1:
                raise
            time.sleep(PAUSE_S * (versuch + 1))


def schreibe_text(pfad, text, newline=None):
    """`text` atomar nach `pfad` schreiben; der Vorstand wird zu `pfad + ".bak"`.

    `newline` wie bei open(): None = Plattformstandard (wie bisher `write_text`
    und `open(..., "w")`), "\\n" = immer LF.
    """
    pfad = os.fspath(pfad)
    neben = "%s.tmp-%d" % (pfad, os.getpid())
    try:
        with open(neben, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        _sichere_vorstand(pfad)
        _wiederholt(lambda: os.replace(neben, pfad))
    except BaseException:
        try:
            os.remove(neben)
        except OSError:
            pass
        raise


def _sichere_vorstand(pfad):
    """Den bisherigen Stand als .bak aufheben - aber nur, wenn er heil ist.

    Eine defekte Datei darf die gute Sicherung nicht verdraengen.
    """
    try:
        with open(pfad, encoding="utf-8") as f:
            alt = f.read()
        json.loads(alt)
    except (OSError, ValueError):
        return
    bak = pfad + ".bak"
    neben = "%s.tmp-%d" % (bak, os.getpid())
    try:
        with open(neben, "w", encoding="utf-8", newline="") as f:
            f.write(alt)
        _wiederholt(lambda: os.replace(neben, bak))
    except OSError:
        try:
            os.remove(neben)
        except OSError:
            pass                # Sicherung ist Zugabe, kein Grund abzubrechen


def schreibe_json(pfad, daten, indent=2, ensure_ascii=False, ende="\n",
                  newline=None):
    """`daten` als JSON atomar schreiben (Format wie bisher: indent 2, UTF-8)."""
    schreibe_text(pfad, json.dumps(daten, indent=indent,
                                   ensure_ascii=ensure_ascii) + ende,
                  newline=newline)


def _lese(pfad):
    def einmal():
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    return _wiederholt(einmal)


def lade_json(pfad, vorgabe):
    """JSON lesen. `vorgabe` ist eine Funktion (frisches Dict je Aufruf).

    Fehlt die Datei: `vorgabe()`. Ist sie defekt: die Sicherung, sonst
    `ZustandDefekt`. Andere Lesefehler (gesperrt) kommen nach den
    Wiederholungen als Ausnahme durch - NICHT als leerer Bestand.
    """
    pfad = os.fspath(pfad)
    try:
        return _lese(pfad)
    except FileNotFoundError:
        return vorgabe()
    except ValueError as e:
        try:
            z = _lese(pfad + ".bak")
        except (OSError, ValueError):
            raise ZustandDefekt(
                "%s ist defekt (%s) und hat keine lesbare Sicherung (.bak) - "
                "Bestand unklar, Zyklus abgebrochen. Datei pruefen, nicht "
                "loeschen." % (pfad, e)) from e
        print("WARNUNG: %s defekt (%s) - Stand aus der Sicherung .bak gelesen."
              % (pfad, e), file=sys.stderr)
        return z
