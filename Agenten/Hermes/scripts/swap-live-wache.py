#!/usr/bin/env python3
"""Cron-Huelle: Wache auf swaps Live-Buch.

Die Logik steht in `live_wache.py` (eine Fassung fuer alle Live-Buecher); hier
steht nur, WELCHE Spur gemeint ist. Der Hermes-Cron startet ausschliesslich
Skripte aus `Agenten/Hermes/scripts/`, deshalb diese Trennung.

ANLASS (Befund 24.09.2026): swap ist live (handel_erlaubt=true,
freigabe.erfuellt=true, echter Orderweg in swap/handeln.py, live seit 21.09.
11:11) und war die einzige live handelnde Spur OHNE eigene Wache - ein
stummer Ausfall waere nur im Tagesbericht aufgefallen.

Die Wache meldet neue Live-Zeilen (Einstieg, Ausstieg, Fehler), Buchbereinigungen
und den Fensterwechsel - und schweigt, wenn nichts passiert.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_wache                                                  # noqa: E402

if __name__ == "__main__":
    sys.exit(live_wache.main("swap"))