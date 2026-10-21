#!/usr/bin/env python3
"""Wache: omnitrade2 PR #1 (OKX-SWAP) Statusueberblick - nur Aenderungen melden.

Laeuft als Hermes-Cron OHNE Modell (no_agent): **leere Ausgabe heisst alles
wie erwartet** und es wird nichts gesendet (Watchdog-Muster).

WARUM ES DIESEN WARCHTER GIBT
-----------------------------
Der OKX-SWAP-Adapter (Handover 20.10.2026, T-419) liegt als Draft-PR #1 auf
mfaupel95/omnitrade2. Naechster Schritt ist die Demo-Verifikation (Keys im
Container, Order 0.0001 BTC, PR dann ready for review). Damit diese Arbeit
nicht still liegen bleibt, meldet die Wache NUR Statuswechsel des PR:

  * Draft -> ready_for_review  (die Demo-Verifikation ist durchgelaufen)
  * open -> merged / closed    (der Stand ist entschieden)
  * Staleness: PR bleibt laenger als STALE_TAGE Tage Draft - dann erinnert
    sie einmal pro Woche an die ausstehende Demo-Verifikation.

Der PR-Status kommt aus der oeffentlichen GitHub-REST-API (kein Token noetig,
Repo ist public). Merkdatei gegen Wiederholung - eine Meldung pro Aenderung
bzw. pro Woche bei Staleness.

Aufruf:
    python omnitrade2-demo-wache.py             # echter Waechter
    python omnitrade2-demo-wache.py --alle      # auch aktuellen Stand zeigen
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
MERK = HIER.parent / "cache" / "omnitrade2-demo-wache.json"

PR_URL = "https://api.github.com/repos/mfaupel95/omnitrade2/pulls/1"
STALE_TAGE = 14.0        # nach 14 Tagen Draft erinnern
WIEDERHOLUNG_STUNDEN = 24 * 7  # Staleness-Erinnerung 1x/Woche


def pr_status():
    """(state, is_draft, updated_at_iso, title) vom PR - oder Fehler."""
    req = urllib.request.Request(PR_URL, headers={"User-Agent": "omnitrade2-demo-wache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    return {
        "state": d.get("state"),
        "draft": bool(d.get("draft")),
        "updated": d.get("updated_at"),
        "title": d.get("title"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alle", action="store_true")
    args = ap.parse_args()

    try:
        p = pr_status()
    except Exception as e:
        # Ein Fehler der Pruefung selbst ist NIE leeres Ergebnis.
        print("FEHLER: PR-Status nicht abrufbar: {}".format(e))
        return 1

    now = datetime.now(timezone.utc)
    stand = {}
    if MERK.exists():
        try:
            stand = json.loads(MERK.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            stand = {}

    zustand = "draft" if p["draft"] else ("ready" if p["state"] == "open" else p["state"])
    if args.alle:
        print("PR #1: {} (state={}) - {}\nUpdated: {}".format(
            zustand, p["state"], p["title"], p["updated"]))

    meldung = None
    vorher = stand.get("zustand")

    if zustand != vorher:
        if vorher is None:
            meldung = "omnitrade2 PR #1 ist {} (erster Blick): {}".format(zustand, p["title"])
        else:
            meldung = "omnitrade2 PR #1: {} -> {} ({})".format(vorher, zustand, p["title"])
    elif zustand == "draft":
        # Staleness pruefen: letzter merkwuerdiger Zeitpunkt
        letzter_merk = stand.get("zeit", now.isoformat())
        try:
            dt_alt = datetime.fromisoformat(letzter_merk.replace("Z", "+00:00"))
            alter = (now - dt_alt).days
        except Exception:
            alter = 0
        if alter >= STALE_TAGE:
            letzte_meldung = stand.get("letzte_stale", 0.0)
            if now.timestamp() - letzte_meldung >= WIEDERHOLUNG_STUNDEN * 3600:
                meldung = ("omnitrade2 PR #1 ist seit {} Tagen Draft - Demo-"
                           "Verifikation ausstehend (T-419, Keys im Container)").format(int(alter))
                stand["letzte_stale"] = now.timestamp()

    if meldung:
        print(meldung)

    stand["zustand"] = zustand
    stand["zeit"] = p["updated"] or now.isoformat()
    if not args.alle:
        MERK.write_text(json.dumps(stand, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())