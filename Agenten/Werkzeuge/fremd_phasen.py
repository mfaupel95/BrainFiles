"""Zeigt den Phasenstand der Fremd-Repos aus Agenten/FREMD-Phasen.json.

Aufruf:  python Agenten/Werkzeuge/fremd_phasen.py [--rolle handel] [--nur-offen]

Liest nur, ändert nichts. Exitcode 1, wenn die Datei kaputt ist oder ein
Eintrag gegen das Schema verstößt (Phase außerhalb 0-4, unbekannter Status,
blockiert ohne Grund).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
DATEI = WURZEL / "Agenten" / "FREMD-Phasen.json"
PHASEN = {0: "Inventur", 1: "Adapter", 2: "Hermes-Agent", 3: "UI-Start", 4: "Test+Betrieb"}
STATUS = ("offen", "in_arbeit", "fertig", "blockiert")


def pruefen(repos):
    fehler = []
    for r in repos:
        name = r.get("name", "?")
        if r.get("phase_aktuell") not in PHASEN:
            fehler.append(f"{name}: phase_aktuell {r.get('phase_aktuell')!r} ungültig")
        if r.get("status") not in STATUS:
            fehler.append(f"{name}: status {r.get('status')!r} ungültig")
        if r.get("status") == "blockiert" and not r.get("blockiert_weil"):
            fehler.append(f"{name}: blockiert ohne blockiert_weil")
    return fehler


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rolle", help="nur diese Rolle zeigen (handel, recherche, gedaechtnis, ui, referenz)")
    ap.add_argument("--nur-offen", action="store_true", help="nur Repos mit status offen oder blockiert")
    args = ap.parse_args()

    try:
        daten = json.loads(DATEI.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FEHLER: {DATEI} nicht lesbar: {e}")
        return 1

    repos = daten.get("repos", [])
    fehler = pruefen(repos)
    if fehler:
        print("SCHEMA-FEHLER:")
        for f in fehler:
            print(f"  - {f}")
        return 1

    auswahl = [r for r in repos
               if (not args.rolle or r["rolle"] == args.rolle)
               and (not args.nur_offen or r["status"] in ("offen", "blockiert"))]

    print(f"Fremd-Phasen, Stand {daten.get('stand', '?')} ({len(auswahl)} von {len(repos)} Repos)\n")
    for rolle in sorted({r["rolle"] for r in auswahl}):
        print(f"[{rolle}]")
        for r in (x for x in auswahl if x["rolle"] == rolle):
            phase = f"P{r['phase_aktuell']} {PHASEN[r['phase_aktuell']]}"
            zeile = f"  {r['name']:<38} {phase:<18} {r['status']:<10}"
            if r["status"] == "blockiert":
                zeile += f" -> {r['blockiert_weil']}"
            print(zeile.rstrip())
        print()

    zaehl = Counter(r["status"] for r in auswahl)
    print("Summe: " + ", ".join(f"{s} {zaehl.get(s, 0)}" for s in STATUS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
