#!/usr/bin/env python3
"""Cron-Huelle: Wache auf krakens Live-Buch.

Die Logik steht in `live_wache.py` (eine Fassung fuer alle Live-Buecher); hier
steht nur, WELCHE Spur gemeint ist. Der Hermes-Cron startet ausschliesslich
Skripte aus `Agenten/Hermes/scripts/`, deshalb diese Trennung.

Kraken ist seit dem 21.09.2026 08:43 live (Freigabefenster der Auto-Freigabe,
EUR-Guthaben ueber der Schwelle). 50 EUR je Position, Gebuehr 0 ueber das
Kraken-Pro-Abo. Die Wache meldet neue Live-Zeilen, Buchbereinigungen und den
Fensterwechsel - und schweigt, wenn nichts passiert.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_wache                                                  # noqa: E402

if __name__ == "__main__":
    sys.exit(live_wache.main("kraken"))