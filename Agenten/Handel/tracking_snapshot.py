"""Tages-Snapshot fuer alle Handelsspuren.

Liest alle Spuren-Ordner, ermittelt offene Positionen aus zustand.json und
schreibt den Tagesstand in tracking.db (Tabelle spur_tagesstand).

Aufruf:
    cd Agenten\Handel
    python tracking_snapshot.py

Wann: taeglich, z. B. nach dem Handelslauf oder als Windows-Task.
"""
import json
import os
import sys
from pathlib import Path

HANDEL = Path(__file__).parent
if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))

import tracking


def _offene_positionen(spur_ordner: Path) -> int:
    """Offene Positionen aus zustand.json - risikostufenunabhaengig."""
    count = 0
    for datei in spur_ordner.glob("zustand*.json"):
        try:
            z = json.loads(datei.read_text(encoding="utf-8"))
            count += len(z.get("positionen", []))
        except Exception:
            pass
    return count


def main() -> None:
    fehler = 0
    ok_count = 0
    gesehen: set[str] = set()

    for journal in sorted(HANDEL.rglob("handelsjournal*.csv")):
        spur_ordner = journal.parent
        spur_name = spur_ordner.name
        if spur_name in gesehen:
            continue
        gesehen.add(spur_name)

        offene = _offene_positionen(spur_ordner)
        try:
            tracking.snapshot_sync(spur_name, offene_positionen_count=offene)
            print("OK   %s  (offene=%d)" % (spur_name, offene))
            ok_count += 1
        except Exception as e:
            print("FAIL %s  %s" % (spur_name, e))
            fehler += 1

    print("---")
    print("%d Spuren aktualisiert, %d Fehler." % (ok_count, fehler))
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
