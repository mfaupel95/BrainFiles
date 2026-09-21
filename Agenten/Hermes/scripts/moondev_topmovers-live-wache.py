#!/usr/bin/env python3
"""Cron-Huelle: Wache auf das Live-Buch der Spur moondev_topmovers.

Die Logik steht in `live_wache.py` (eine Fassung fuer alle Live-Buecher);
hier steht nur, WELCHE Spur gemeint ist. Zusaetzlich zu Live-Zeilen und
Fensterwechseln meldet sie bei dieser Spur den Grund des Risiko-Vorfilters,
wenn er den Einstieg zurueckhaelt - denn ein offenes Freigabefenster allein
bedeutet hier noch keinen Kauf.

Leere Ausgabe = nichts senden.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_wache import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main("moondev_topmovers"))
