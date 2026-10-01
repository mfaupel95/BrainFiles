#!/usr/bin/env python3
"""Donchian-Ausbruch 20/10 (Pine-Vorlage donchian-breakout): Papierspur ueber Handel/klassik_regeln.py.

Regel: Long, wenn der Schluss ueber dem Hoch der 20 Kerzen DAVOR schliesst, Short unter dem Tief; Ausstieg am 10er-Gegenkanal. (Die Pine-Vorlage rechnet den Kanal inklusive der laufenden Kerze und kann nie ausloesen.)

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
    sys.exit(klassik_regeln.spur_main("klassik_donchian", HIER,
                                      bus_name="handel/klassik_donchian"))
