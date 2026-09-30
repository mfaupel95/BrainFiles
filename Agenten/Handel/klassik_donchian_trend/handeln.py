#!/usr/bin/env python3
"""NEU: Donchian-Ausbruch mit EMA200-Trendfilter: Papierspur ueber Handel/klassik_regeln.py.

Regel: Donchian-20-Ausbruch, aber nur in Richtung der EMA200-Steigung (Long: Schluss ueber steigender EMA200, Short: unter fallender). Ausstieg am 10er-Gegenkanal.

Aufruf: python handeln.py --vorschau | --papier | --wachen  (--live verweigert)
"""
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import klassik_regeln  # noqa: E402

if __name__ == "__main__":
    sys.exit(klassik_regeln.spur_main("klassik_donchian_trend", HIER))
