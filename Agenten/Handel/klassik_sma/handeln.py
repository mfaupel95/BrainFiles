#!/usr/bin/env python3
"""SMA-Kreuz 20/50 (Pine-Vorlage sma-crossover): Papierspur ueber Handel/klassik_regeln.py.

Regel: Long beim Aufwaertskreuz SMA20 ueber SMA50, Short beim Abwaertskreuz; Ausstieg beim Gegenkreuz.

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
    sys.exit(klassik_regeln.spur_main("klassik_sma", HIER,
                                      bus_name="handel/klassik_sma"))
