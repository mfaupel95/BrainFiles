#!/usr/bin/env python3
"""EMA-Kreuz 12/26 (Pine-Vorlage ema-crossover): Papierspur ueber Handel/klassik_regeln.py.

Regel: Long beim Kreuz EMA12 ueber EMA26, Short beim Gegenkreuz; Ausstieg beim Gegenkreuz.

Aufruf: python handeln.py --vorschau | --papier | --wachen  (--live verweigert)
"""
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import klassik_regeln  # noqa: E402

if __name__ == "__main__":
    sys.exit(klassik_regeln.spur_main("klassik_ema", HIER))
