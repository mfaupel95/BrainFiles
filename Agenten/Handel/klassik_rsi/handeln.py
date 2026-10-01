#!/usr/bin/env python3
"""RSI-Rueckkehr (Pine-Vorlage rsi-mean-reversion): Papierspur ueber Handel/klassik_regeln.py.

Regel: Long, wenn RSI(14) von unten ueber 30 kreuzt, Short, wenn er von oben unter 70 kreuzt; Ausstieg Long bei RSI 55, Short bei 45.

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
    sys.exit(klassik_regeln.spur_main("klassik_rsi", HIER,
                                      bus_name="handel/klassik_rsi"))
