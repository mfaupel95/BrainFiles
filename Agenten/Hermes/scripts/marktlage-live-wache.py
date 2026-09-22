#!/usr/bin/env python3
"""Wache auf das Live-Buch von moondev_marktlage: meldet Neues, sonst nichts.

Auftrag Max 22.09.2026: die zweite Kraken-Spur soll das liegende EUR-Guthaben
arbeiten lassen ("weitere nach auswertung bereite Spur an kraken anschliessen").
Sie ordert XXBTZEUR mit 60-150 EUR und Kraken-Stop.

Drei Dinge, die man sonst erst Tage spaeter merkt:

  1. Kommt ueberhaupt eine Order durch? Der Kraken-Orderweg dieses Zweigs war
     fuer Lesen belegt; ein gescheiterter Kauf steht als Zeile `fehler` im
     Journal - gemeldet wird sie hier.
  2. Der DATENWEG kann still sein: die Signalquelle ist CoinGecko oeffentlich,
     und HTTP 429 kam schon vor. "Keine Daten" heisst kein Handel - das ist
     kein Fehler, aber es sieht aus wie "die Spur tut nichts".
  3. Fensterwechsel: nach 12 h laeuft sie wieder Papier, bis die Auto-Freigabe
     neu oeffnet.

Aufruf (Hermes-Cron, no_agent, alle 10 Minuten):
    python marktlage-live-wache.py

LEERE AUSGABE = nichts senden. Zustand in
Agenten/Hermes/cache/marktlage-live-wache.json (Laufzeitstand, nicht versioniert).
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
SPUR = HANDEL / "moondev_marktlage"
JOURNAL = SPUR / "handelsjournal.live.csv"
FENSTER = HANDEL / "freigabe_fenster.json"
STAND = Path(__file__).resolve().parents[1] / "cache" / "marktlage-live-wache.json"
NAME = "moondev_marktlage"


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
    d = _lies(FENSTER).get(NAME) or {}
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


def _zeile_text(r):
    if (r.get("aktion") or "") == "fehler":
        return "LIVE-FEHLER: %s %s  %s" % (r.get("zeit", "")[:16],
                                           r.get("pair", ""), r.get("grund", ""))
    return "LIVE: %s %s %s  %s EUR  Menge %s  Stop %s  (%s)" % (
        r.get("zeit", "")[:16], r.get("aktion", ""), r.get("pair", ""),
        r.get("eur", ""), r.get("menge", ""), r.get("stop", ""), r.get("grund", ""))


def main() -> int:
    zeilen = live_zeilen()
    offen, bis = fenster_lage()
    stand = _lies(STAND)
    erstlauf = not stand

    meldungen = []
    vorher = int(stand.get("live_zeilen", 0))
    if erstlauf and zeilen:
        meldungen.append("%s hat %d Live-Zeile(n) im Buch - Beobachtung laeuft "
                         "ab jetzt." % (NAME, len(zeilen)))
    elif len(zeilen) > vorher:
        for r in zeilen[vorher:]:
            meldungen.append(_zeile_text(r))

    war_offen = bool(stand.get("fenster_offen"))
    if not erstlauf and war_offen and not offen:
        meldungen.append("%s: Freigabefenster zu (war bis %s) - laeuft wieder "
                         "Papier, bis die Auto-Freigabe neu oeffnet." % (NAME, bis))
    if not erstlauf and not offen and zeilen and not stand.get("ohne_fenster_gemeldet"):
        meldungen.append("%s: Freigabefenster ist ZU, es liegen aber Live-Zeilen "
                         "im Buch - bitte pruefen." % NAME)

    STAND.parent.mkdir(parents=True, exist_ok=True)
    STAND.write_text(json.dumps({
        "live_zeilen": len(zeilen),
        "fenster_offen": offen,
        "offen_bis": bis,
        "ohne_fenster_gemeldet": (not offen and bool(zeilen)),
        "geprueft": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in meldungen:
        print(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
