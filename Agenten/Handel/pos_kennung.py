#!/usr/bin/env python3
"""Die Kennung EINER Position - eine Umsetzung fuer alle Spuren.

WARUM ES SIE GIBT (T-095, 30.09.2026)
-------------------------------------
Einstieg und Ausstieg wurden im Journal **je Instrument** gepaart
(`offen[inst]`). Zwei gleichzeitige Positionen im selben Instrument
ueberschreiben einander: der erste Ausstieg paart dann mit dem falschen
Einstieg, der ueberschriebene Einstieg faellt ganz weg. Gemessen am Backtest
ueber 5,7 Jahre (squeeze, 30.09.2026): 1092 Einstiege, 1088 Ausstiege - und nur
**759** gepaarte Runden, weil 330 Einstiege ueberschrieben und 329 Ausstiege
ohne Partner blieben. Trefferquote und `kosten_wendepunkt.f_max` standen damit
auf einer nicht zufaelligen Teilmenge (gleichzeitige Positionen im selben
Instrument sind eher gleichgerichtet).

Die Kennung wird beim EROEFFNEN erzeugt, in der Position mitgefuehrt und in
JEDER Zeile dieser Position geschrieben (Kauf UND Verkauf). Sie ist kurz und
lesbar:

    <JJJJMMTT>T<HHMMSS>-<6 Hex>       z.B. 20260930T153012-a1b2c3

Der Zufallsteil ist noetig, nicht bequem: zwei Positionen im selben Instrument
entstehen in derselben Sekunde, wenn ein Zyklus mehrere Instrumente auf einmal
eroeffnet - die Zeit allein waere kein eindeutiger Schluessel.

WAS SIE NICHT IST
-----------------
Keine Ordnernummer und kein Zeilenindex: sie muss einen Neustart, einen
Risikostufen-Lauf und einen Backtest ueberstehen. Deshalb steht sie in der
POSITION (zustand.json) und nicht in einer Zaehlervariablen.

ALT-JOURNALE
------------
Zeilen ohne Kennung bleiben lesbar - die Auswertung faellt dann auf die
Instrumentenpaarung zurueck. Eine bestehende Datei behaelt ihre Kopfzeile
(`spalten()`); eine Zeile mit mehr Feldern als der Kopf waere keine
Erweiterung, sondern eine Verschiebung ALLER Spalten (`csv.DictReader` legt
den Ueberhang unter `None` ab). Ein Journal ohne `pos_id` im Kopf schreibt
also weiter ohne Kennung - sichtbar, nicht still: `spalten()` meldet es.

Aufruf (Probe, ohne Argument = Trockenlauf):
    python pos_kennung.py
"""

from __future__ import annotations

import csv
import os
import sys
import uuid
from datetime import datetime, timezone

# Test-Naht: ein Test (oder eine Spur) darf die Erzeugung ersetzen.
#   pos_kennung.erzeuger = lambda zeit=None: "test-1"
erzeuger = None

# Wie viele Zeichen der Zufallsteil traegt. 6 Hex = 16,7 Mio Werte je Sekunde -
# mehr als genug fuer gleichzeitige Positionen, kurz genug fuer ein Journal.
HEX_ZEICHEN = 6

# Dateien, fuer die schon einmal gewarnt wurde (ein Zyklus schreibt mehrfach).
_gemeldet = set()


def _stempel(zeit=None) -> str:
    """Der Zeitstempel der Kennung - aus einem ISO-Zeitpunkt oder der Uhr."""
    if zeit:
        roh = str(zeit)
        # "2026-09-30T15:30:12+00:00" -> "20260930T153012"; alles andere wird
        # von den Ziffern befreit, damit die Kennung keine Doppelpunkte traegt
        # (ein Feld, das spaeter jemand als Pfadnamen benutzt, bricht daran).
        ziffern = "".join(c for c in roh if c.isdigit())
        if len(ziffern) >= 14:
            return ziffern[:8] + "T" + ziffern[8:14]
        return ziffern or "0"
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")


def neu(zeit=None) -> str:
    """Eine neue Positionskennung. `zeit` ist der Zeitpunkt des Einstiegs."""
    if erzeuger is not None:
        return erzeuger(zeit)
    return "%s-%s" % (_stempel(zeit), uuid.uuid4().hex[:HEX_ZEICHEN])


def kopf(pfad) -> list | None:
    """Die Kopfzeile eines vorhandenen Journals - None, wenn es keine gibt."""
    try:
        with open(pfad, encoding="utf-8", newline="") as f:
            erste = f.readline()
    except OSError:
        return None
    if not erste.strip():
        return None
    return next(csv.reader([erste]), [])


def spalten(pfad, neue, still=False) -> list:
    """Die Spalten, mit denen in DIESE Datei geschrieben wird (dict-Schreiber).

    Eine bestehende Datei behaelt ihre Kopfzeile. Fehlt darin `pos_id`, wird
    die Kennung NICHT geschrieben: die Zeile bleibt lesbar und die Auswertung
    nimmt die Instrumentenpaarung. Das ist ein Uebergangszustand, kein Fehler -
    aber er wird gemeldet, weil ein stiller Rueckfall wie ein Erfolg aussieht.
    Gemeldet wird EINMAL je Datei und Prozess: ein Zyklus schreibt mehrfach, und
    eine Warnung, die sich wiederholt, liest niemand mehr.
    """
    vorhanden = kopf(pfad)
    if not vorhanden:
        return list(neue)
    if list(vorhanden) == list(neue):
        return list(neue)
    if not still and "pos_id" in neue and "pos_id" not in vorhanden:
        if str(pfad) not in _gemeldet:
            _gemeldet.add(str(pfad))
            print("WARNUNG %s: Journal-Kopf ohne pos_id - Kennung wird nicht "
                  "geschrieben (Journal-pos-id-Werkzeug nachziehen)"
                  % os.path.basename(str(pfad)), file=sys.stderr)
    return list(vorhanden)


def zeile(felder, vorhandener_kopf) -> list:
    """Eine Zeile fuer einen SCHREIBER MIT FESTER SPALTENLISTE (scanner, kraken).

    `felder` steht in der Reihenfolge der NEUEN Spalten. Ist der Kopf der Datei
    kuerzer (Altjournal), wird hinten abgeschnitten - die neuen Felder stehen
    dort. So entsteht nie eine Zeile mit mehr Werten als der Kopf.
    """
    felder = list(felder)
    if not vorhandener_kopf:
        return felder
    return felder[:len(vorhandener_kopf)]


def main() -> int:
    print("Probe: %s" % neu())
    print("Probe mit Zeit: %s" % neu("2026-09-30T15:30:12+00:00"))
    a, b = neu(), neu()
    print("eindeutig: %s" % (a != b))
    return 0


if __name__ == "__main__":
    sys.exit(main())