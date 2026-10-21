#!/usr/bin/env python3
"""Cron-Bruecke fuer die OKX-Demo-Positionswache (no_agent).

Der Cron-Befehl nimmt nur einen Dateinamen aus Agenten/Hermes/scripts/, nicht
einen Pfad mit Ordnern. Der Kern liegt deshalb bei der Spur selbst:
Agenten/Handel/omnitrade/demo_position_wache.py

Gemeldet wird nur: Schutz-Stop weg, Position geschlossen, Kurs nah am Stop,
Abfrage kaputt. Leere Ausgabe = nichts zu melden.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parent.parent          # Agenten/Hermes
WURZEL = HERMES.parent.parent                            # BrainFiles
KERN = WURZEL / "Agenten" / "Handel" / "omnitrade" / "demo_position_wache.py"


def main() -> int:
    if not KERN.is_file():
        # Ein fehlender Kern ist ein BEFUND, kein leeres Ergebnis.
        print("OKX-Demo-Wache: Kern fehlt: %s" % KERN)
        return 2
    spec = importlib.util.spec_from_file_location("demo_position_wache", KERN)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["demo_position_wache"] = modul
    spec.loader.exec_module(modul)
    return modul.main()


if __name__ == "__main__":
    raise SystemExit(main())
