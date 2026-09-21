#!/usr/bin/env python3
"""Wache auf ein Live-Buch einer Handelsspur - eine Fassung fuer alle.

Warum eine gemeinsame Datei: die Wache ist bei jeder Spur dieselbe Rechnung
(neue Live-Zeile? Fensterwechsel? Buchbereinigung?) und unterscheidet sich nur
in Pfaden und Waehrung. Zwei Kopien waeren zwei Stellen, an denen dieselbe
Verbesserung nachgezogen werden muss.

Angeschlossen sind:
  - mosaic (Live seit 21.09.2026, 10 USDC je Position)
  - kraken (Live seit 21.09.2026 08:43, 50 EUR je Position, Gebuehr 0 via Pro)

Noch offen: `mosaic-live-wache.py` traegt seine eigene, aeltere Fassung
(dieselbe Rechnung, aber ein zweiter Ort fuer Verbesserungen). Es laeuft und
wird nicht angetastet, solange es laeuft - beim naechsten Anlass auf diese
Fassung umstellen.

Aufruf je Spur ueber eine duenne Huelle (der Hermes-Cron startet nur Skripte aus
`Agenten/Hermes/scripts/`):

    python kraken-live-wache.py
    python mosaic-live-wache.py

LEERE AUSGABE = nichts senden. Zustand je Spur in
`Agenten/Hermes/cache/<spur>-live-wache.json`.

WAS GEMELDET WIRD
  1. jede neue LIVE-Zeile im Journal (der erste echte Einstieg ist zugleich der
     Beweis, dass der Schluesselsatz ordern darf) - Fehlerzeilen als
     LIVE-FEHLER mit Grund,
  2. neue Zeilen mit Grund `buchbereinigung`: Papier-Ueberbleibsel im Live-Buch
     (sie belegen Plaetze und lassen den Live-Ausstieg ins Leere greifen),
  3. Fensterwechsel (live -> Papier, Papier -> live).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
STAND_ORDNER = Path(__file__).resolve().parents[1] / "cache"

# spur -> (Journal, Fenster-Schluessel, Waehrung, Mindestguthaben-Funktion)
SPUREN = {
    "mosaic": {"journal": HANDEL / "mosaic" / "handelsjournal.csv",
               "fenster": "mosaic", "waehrung": "USDC"},
    "kraken": {"journal": HANDEL / "kraken" / "handelsjournal.csv",
               "fenster": "kraken", "waehrung": "EUR"},
}


def _lies(pfad):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return {}


def _zeit(wert):
    if not wert:
        return None
    try:
        d = dt.datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def live_zeilen(journal):
    if not Path(journal).is_file():
        return []
    with Path(journal).open("r", newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("modus") or "").strip().lower() == "live"]


def fenster_lage(schluessel):
    d = _lies(HANDEL / "freigabe_fenster.json").get(schluessel) or {}
    bis = d.get("offen_bis")
    ende = _zeit(bis)
    if ende is None:
        return False, bis
    return ende > dt.datetime.now(dt.timezone.utc), bis


def _text(r):
    """Eine Live-Zeile als Meldung - Instrument und Betrag je Spuren-Schema."""
    aktion = (r.get("aktion") or "").strip()
    if aktion == "fehler":
        return "LIVE-FEHLER: %s %s  %s" % ((r.get("zeit") or "")[:16],
                                           r.get("inst") or r.get("paar") or "?",
                                           r.get("grund") or "")
    inst = r.get("inst") or r.get("paar") or r.get("symbol") or "?"
    betrag = r.get("einsatz_usd") or r.get("eur") or ""
    return "LIVE: %s %s %s @ %s  %s  (%s)" % (
        (r.get("zeit") or "")[:16], aktion, inst,
        r.get("preis") or r.get("einstieg") or "", betrag, r.get("grund") or "")


def wache(spur: str) -> int:
    cfg = SPUREN.get(spur)
    if not cfg:
        print("Unbekannte Spur: %s (bekannt: %s)" % (spur, ", ".join(SPUREN)))
        return 2
    journal = cfg["journal"]
    zeilen = live_zeilen(journal)
    offen, bis = fenster_lage(cfg["fenster"])
    stand_pfad = STAND_ORDNER / ("%s-live-wache.json" % spur)
    stand = _lies(stand_pfad)
    erstlauf = not stand

    meldungen = []
    vorher = int(stand.get("live_runden", 0))
    neu = zeilen[vorher:] if len(zeilen) > vorher else []
    for r in neu:
        meldungen.append(_text(r))
    bereinigt = [r for r in neu if (r.get("grund") or "") == "buchbereinigung"]
    if bereinigt:
        meldungen.append(
            "%s: %d Buchbereinigung(en) - Papier-Ueberbleibsel standen im "
            "Live-Buch und wurden ausgebucht." % (spur, len(bereinigt)))
    if erstlauf and zeilen:
        meldungen.append("%s hat %d Live-Zeile(n) im Journal - Beobachtung "
                         "laeuft ab jetzt." % (spur, len(zeilen)))

    war_offen = bool(stand.get("fenster_offen"))
    if not erstlauf and war_offen and not offen:
        meldungen.append("%s: Freigabefenster zu (war bis %s) - laeuft wieder "
                         "Papier, bis die Auto-Freigabe neu oeffnet." % (spur, bis))
    if not erstlauf and not war_offen and offen:
        meldungen.append("%s: Freigabefenster offen bis %s - live." % (spur, bis))

    STAND_ORDNER.mkdir(parents=True, exist_ok=True)
    stand_pfad.write_text(json.dumps({
        "live_runden": len(zeilen), "fenster_offen": offen, "offen_bis": bis,
        "geprueft": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in meldungen:
        print(m)
    return 0


def main(spur: str) -> int:
    return wache(spur)


if __name__ == "__main__":
    # Direktaufruf: --spur NAME (die Cron-Huellen rufen main() mit festem Namen)
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--spur", required=True, choices=sorted(SPUREN))
    sys.exit(wache(p.parse_args().spur))