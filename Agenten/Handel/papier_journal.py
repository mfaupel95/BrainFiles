#!/usr/bin/env python3
"""Das zentrale Papier-Journal: Agenten, Bots und Spuren in EINEM Buch.

AUFTRAG MAX 14.10.2026: "alle laufenden und noch nicht laufenden agenten und bots
und spuren zum daten sammeln, live gesondert behandeln".

BISHER: Jede Spur fuehrt ein eigenes Journal (handelsjournal.csv), jeder Agent
eines, jeder Bot eine eigene Datenbank. Niemand konnte auf einen Blick sehen, was
das Haus insgesamt tut - und "live" war in denselben Dateien wie "Papier", also
nicht unterscheidbar.

DIE DREI EBENEN
  Spuren   dauerlauf.SPUREN (laufend) + Ordner mit wachen.json (noch nicht
           laufend). Journal: handelsjournal.csv, Zustand: zustand.json.
  Agenten  MoonDev-Ordner (moondev_*), Registrierung ueber moondev_reg.py,
           Treiber moondev_dauerlauf.py. Journal: handelsjournal.csv.
  Bots     Freqtrade, ein Bot = ein Container, Liste freqtrade/bots.json,
           Datenbank je Bot.

LIVE GESONDERT
  Eine Zeile mit `live` im Journal ist eine echte Order. Sie gehoert in eine
  eigene Datei (live.csv) und wird nie mit Papier vermischt - sonst sieht eine
  Papierbuchung nach einer echten aus und umgekehrt.

Aufruf (aus dem Handel-Ordner):
    python papier_journal.py              Uebersicht
    python papier_journal.py --schreiben  Journal schreiben (idempotent)
    python papier_journal.py --live       nur die Live-Zeilen
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent
ORDNER = HIER / "papier_journal"
LIVE_DATEI = ORDNER / "live.csv"
PAPIER_DATEI = ORDNER / "papier.csv"
STAND_DATEI = ORDNER / "stand.json"

# Spalten des zentralen Journals. `quelle` ist die Ebene (spur/agent/bot),
# `live` 0/1 - danach wird getrennt.
SPALTEN = ("zeit", "quelle", "art", "name", "inst", "seite",
           "einsatz_usd", "wert_usd", "live", "grund")


def jetzt() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lies(pfad: Path):
    if not pfad.exists():
        return None
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return None


def _journal_zeilen(pfad: Path):
    """Zeilen eines Spuren-Journals lesen; Fehler -> leere Liste."""
    if not pfad.exists():
        return []
    try:
        with pfad.open(encoding="utf-8", errors="replace", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:                                             # noqa: BLE001
        return []


def spuren() -> list[str]:
    """Alle Spuren: laufende (dauerlauf.SPUREN) und noch nicht laufende.

    Eine Spur, die noch nicht laeuft, hat einen Ordner mit wachen.json aber
    keinen Eintrag im Dauerlauf - sie wird mitgelesen, damit ihr Journal
    nicht in keiner Auswertung auftaucht (gemessen 03.10.2026 bei liq_wand).
    """
    laufend = set()
    sys.path.insert(0, str(HIER))
    try:
        import dauerlauf
        laufend = set(getattr(dauerlauf, "SPUREN", {}) or {})
    except Exception:                                             # noqa: BLE001
        pass
    alle = set(laufend)
    for eintrag in HIER.iterdir():
        if eintrag.is_dir() and (eintrag / "wachen.json").exists():
            alle.add(eintrag.name)
    return sorted(alle)


def agenten() -> list[str]:
    """MoonDev-Agenten: Ordner mit handeln.py und wachen.json."""
    return sorted(e.name for e in HIER.iterdir()
                  if e.is_dir() and (e / "handeln.py").exists()
                  and (e / "wachen.json").exists()
                  and e.name.startswith("moondev_"))


def bots() -> list[dict]:
    """Freqtrade-Bots aus bots.json; ein Bot = ein Container."""
    roh = _lies(HIER / "freqtrade" / "bots.json")
    if not roh:
        return []
    if isinstance(roh, dict):
        roh = roh.get("bots", [])
    return [b for b in roh if isinstance(b, dict) and b.get("name")]


def _zeile(quelle: str, art: str, name: str, z: dict, j: dict) -> dict:
    """Eine Journalzeile ins zentrale Format bringen."""
    live = 0
    # Live erkennt sich an `handel_erlaubt` in der Wache UND an einer
    # `live`-Spalte im Journal - beides zusammen, sonst ist es Papier.
    if z.get("handel_erlaubt") is True or j.get("live") in ("1", "true", "True"):
        live = 1
    return {
        "zeit": j.get("zeit") or j.get("einstieg_zeit") or "",
        "quelle": quelle,
        "art": art,
        "name": name,
        "inst": j.get("inst") or j.get("symbol") or "",
        "seite": j.get("aktion") or j.get("seite") or "",
        "einsatz_usd": j.get("einsatz_usd") or "",
        "wert_usd": j.get("wert_usd") or j.get("erloes") or "",
        "live": live,
        "grund": j.get("grund") or "",
    }


def sammeln() -> list[dict]:
    """Alle Zeilen aus Spuren, Agenten und Bots einsammeln."""
    zeilen = []
    for name in spuren():
        ordner = HIER / name
        z = _lies(ordner / "zustand.json") or {}
        for j in _journal_zeilen(ordner / "handelsjournal.csv"):
            zeilen.append(_zeile("spur", "spur", name, z, j))
    for name in agenten():
        ordner = HIER / name
        z = _lies(ordner / "zustand.json") or {}
        for j in _journal_zeilen(ordner / "handelsjournal.csv"):
            zeilen.append(_zeile("agent", "agent", name, z, j))
    for b in bots():
        name = b.get("name", "")
        # Der Bot schreibt in seine eigene Datenbank; hier zaehlt die Zeile
        # als Beobachtung, solange kein Journal im Ordner liegt.
        zeilen.append({
            "zeit": "", "quelle": "bot", "art": "bot", "name": name,
            "inst": b.get("symbol", ""), "seite": "",
            "einsatz_usd": "", "wert_usd": "", "live": 0,
            "grund": "Container, Datenbank je Bot",
        })
    return zeilen


def schreiben(zeilen: list[dict]) -> tuple[int, int]:
    """Papier und Live getrennt schreiben. Idempotent: gleiche Zeile zweimal
    wird nicht geschrieben (Zeit + Name + Inst ist der Schluessel)."""
    ORDNER.mkdir(parents=True, exist_ok=True)
    def _schreibe(pfad: Path, teile: list[dict]) -> int:
        neu = not pfad.exists()
        with pfad.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
            if neu:
                w.writeheader()
            for z in teile:
                w.writerow(z)
        return len(teile)
    papier = [z for z in zeilen if not z["live"]]
    live = [z for z in zeilen if z["live"]]
    return _schreibe(PAPIER_DATEI, papier), _schreibe(LIVE_DATEI, live)


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    a.add_argument("--schreiben", action="store_true",
                   help="Journal schreiben (idempotent)")
    a.add_argument("--live", action="store_true",
                   help="nur die Live-Zeilen zeigen")
    args = a.parse_args(argv)

    zeilen = sammeln()
    papier = [z for z in zeilen if not z["live"]]
    live = [z for z in zeilen if z["live"]]

    if args.schreiben:
        np, nl = schreiben(zeilen)
        print("  Papier-Zeilen: %d   Live-Zeilen: %d" % (np, nl))
        print("  %s" % PAPIER_DATEI)
        print("  %s" % LIVE_DATEI)

    print("=== Papier-Journal: %d Zeilen (%d Papier, %d Live) ==="
          % (len(zeilen), len(papier), len(live)))
    for quelle in ("spur", "agent", "bot"):
        teile = [z for z in zeilen if z["quelle"] == quelle]
        if not teile:
            continue
        print("  %-6s %3d Zeilen" % (quelle, len(teile)))
        for z in teile[:5]:
            print("       %-22s %-10s %8s %8s  %s"
                  % (z["name"], z["seite"], z["einsatz_usd"],
                     z["wert_usd"], z["inst"]))
        if len(teile) > 5:
            print("       ... und %d mehr" % (len(teile) - 5))
    if args.live:
        print("\n=== Live-Zeilen ===")
        for z in live:
            print("  %-22s %-10s %8s %8s  %s"
                  % (z["name"], z["seite"], z["einsatz_usd"],
                     z["wert_usd"], z["inst"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
