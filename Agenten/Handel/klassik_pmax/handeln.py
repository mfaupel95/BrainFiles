#!/usr/bin/env python3
"""PMax Explorer (Pine-Vorlage pmax-explorer.pine): Papierspur ueber Handel/klassik_regeln.py.

Regel: MAvg (EMA10 auf hl2) kreuzt ueber PMax = Long, darunter = Short; Ausstieg beim Gegenkreuz.

Aufruf: python handeln.py --vorschau | --papier | --wachen  (--live verweigert)
"""
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import klassik_regeln  # noqa: E402

if __name__ == "__main__":
    # Der Bus-Name steht WOERTLICH hier: die Bus-Suite prueft genau diese
    # Datei, die der Dauerlauf startet, auf ihren eigenen Namen (T-255). Der
    # Kern reicht ihn an spur_buch.zyklus weiter (dort entsteht ereignis.lauf).
    sys.exit(klassik_regeln.spur_main("klassik_pmax", HIER,
                                      bus_name="handel/klassik_pmax"))