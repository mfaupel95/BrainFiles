#!/usr/bin/env python3
"""NEU: Connors RSI(2)-Ruecksetzer im Trend: Papierspur ueber Handel/klassik_regeln.py.

Regel: Long, wenn RSI(2) unter 10 faellt UND der Schluss ueber der SMA200 liegt; Short spiegelbildlich (RSI(2) ueber 90, unter SMA200). Ausstieg: Schluss ueber (long) bzw. unter (short) die SMA5.

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
    sys.exit(klassik_regeln.spur_main("klassik_rsi2", HIER,
                                      bus_name="handel/klassik_rsi2"))
