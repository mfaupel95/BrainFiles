#!/usr/bin/env python3
"""Wache auf mosaics Live-Buch: meldet jede neue Live-Zeile, sonst nichts.

Auftrag Max 21.09.2026: "Einsatz erstmal so lassen und beobachten."

Die Spur handelt seit dem 21.09.2026 live (10 USDC je Position, Freigabefenster
bis 18:58, dann fragt die Auto-Freigabe erneut). Zwei Dinge sind zu beobachten,
die man sonst erst Tage spaeter merkt:

  1. Kommt ueberhaupt eine Order durch? Der OKX-Schluesselsatz ist fuer das
     LESEN belegt (Kurs, Guthaben), fuer das ORDERN nicht. Scheitert eine
     Order, steht das im Journal NICHT - aber eine Live-Zeile bleibt aus.
  2. Faellt die Spur still auf Papier zurueck? Nach Ablauf des Fensters (12 h)
     laeuft sie wieder Papier, bis die Auto-Freigabe neu oeffnet. Ohne Meldung
     sieht das aus wie "mosaic tut nichts".

Aufruf (Hermes-Cron, no_agent, alle 10 Minuten):
    python mosaic-live-wache.py

LEERE AUSGABE = nichts senden. Zustand liegt in
Agenten/Hermes/cache/mosaic-live-wache.json (Laufzeitstand, nicht versioniert).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
MOSAIC = HANDEL / "mosaic"
JOURNAL = MOSAIC / "handelsjournal.csv"
FENSTER = HANDEL / "freigabe_fenster.json"
ZUSTAND = MOSAIC / "zustand.json"
STAND = Path(__file__).resolve().parents[1] / "cache" / "mosaic-live-wache.json"


def _lies(pfad):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return {}


def live_zeilen():
    if not JOURNAL.is_file():
        return []
    with JOURNAL.open("r", newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if (r.get("modus") or "") == "live"]


def fenster_lage():
    d = _lies(FENSTER).get("mosaic") or {}
    bis = d.get("offen_bis")
    if not bis:
        return False, None
    try:
        ende = datetime.fromisoformat(bis)
    except ValueError:
        return False, bis
    if ende.tzinfo is None:
        ende = ende.replace(tzinfo=timezone.utc)
    return ende > datetime.now(timezone.utc), bis


def main() -> int:
    zeilen = live_zeilen()
    offen, bis = fenster_lage()
    stand = _lies(STAND)
    erstlauf = not stand

    meldungen = []
    vorher = int(stand.get("live_runden", 0))
    if len(zeilen) > vorher:
        for r in zeilen[vorher:]:
            if (r.get("aktion") or "") == "fehler":
                meldungen.append("LIVE-FEHLER: %s %s  %s" % (
                    r.get("zeit", "")[:16], r.get("inst", ""),
                    r.get("grund", "")))
                continue
            meldungen.append("LIVE: %s %s %s @ %s  %s USD  (%s)" % (
                r.get("zeit", "")[:16], r.get("aktion", ""), r.get("inst", ""),
                r.get("preis", ""), r.get("einsatz_usd", ""), r.get("grund", "")))
    if erstlauf and zeilen:
        meldungen.append("mosaic hat %d Live-Zeile(n) im Journal - Beobachtung "
                         "laeuft ab jetzt." % len(zeilen))

    # Fensterwechsel melden: von live auf papier (oder zurueck)
    war_offen = bool(stand.get("fenster_offen"))
    if not erstlauf and war_offen and not offen:
        meldungen.append("mosaic: Freigabefenster zu (war bis %s) - laeuft "
                         "wieder Papier, bis die Auto-Freigabe neu oeffnet." % bis)
    if not erstlauf and not war_offen and offen:
        meldungen.append("mosaic: Freigabefenster offen bis %s - live." % bis)

    STAND.parent.mkdir(parents=True, exist_ok=True)
    STAND.write_text(json.dumps({
        "live_runden": len(zeilen),
        "fenster_offen": offen,
        "offen_bis": bis,
        "geprueft": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in meldungen:
        print(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())