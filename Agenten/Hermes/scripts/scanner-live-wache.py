#!/usr/bin/env python3
"""Cron-Huelle: Wache auf das Live-Buch des scanner (OKX-Spot).

Die Logik steht in `live_wache.py` - eine Fassung fuer alle Live-Buecher.
Diese Datei ist nur der Einhaengepunkt fuer den Hermes-Cron, der ausschliesslich
Skripte aus `Agenten/Hermes/scripts/` startet.

Warum gerade der scanner: er ist das aktivste Live-Buch (7 Tage 118 Runden,
+2.090 USD, Treffer 90 %) und hatte am 21.09.2026 den Fehler, dass Papier-
Positionen im Live-Buch standen - jede Position ohne `kauf_ord_id` liess sich
nicht verkaufen. Die Wache meldet jede neue Live-Zeile (auch die Buchbereinigung),
Fehlerzeilen als LIVE-FEHLER und den Fensterwechsel. Leere Ausgabe = nichts senden.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import live_wache                                                  # noqa: E402

if __name__ == "__main__":
    sys.exit(live_wache.main("scanner"))