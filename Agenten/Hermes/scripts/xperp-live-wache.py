#!/usr/bin/env python3
"""Cron-Huelle: Wache auf das Live-Buch von xperp (XPERP-Kontrakte, OKX).

Die Logik steht in `live_wache.py` - eine Fassung fuer alle Live-Buecher.
Diese Datei ist nur der Einhaengepunkt fuer den Hermes-Cron, der ausschliesslich
Skripte aus `Agenten/Hermes/scripts/` startet.

xperp ist die aelteste Live-Spur (seit 17.09.2026, vier Kontrakte, USD-marginiert
und damit in USDC besichert). Die Wache meldet neue Kaeufe und Verkaeufe, etwaige
Fehlerzeilen und den Fensterwechsel; die `funding`-Zeilen alle 8 Stunden sind kein
Handel und werden uebersprungen. Leere Ausgabe = nichts senden.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_wache                                                  # noqa: E402

if __name__ == "__main__":
    sys.exit(live_wache.main("xperp"))