"""Tests: keine Zeitausstieg einer gefuellten eingelegten Position.

Bauplan-Abschnitt 6, Test 6 (Kern von Entscheidung A): eine gefuellte
eingelegte Position aelter als 48 h wird NICHT geschlossen, solange
stop/ziel/liq/Kill nicht getroffen sind (pruefe_ausstiege laesst sie stehen).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__


def _position(eroeffnet_zeit="2026-10-01T00:00:00+00:00"):
    return {"inst": "SOL-USD-um_xperp", "basis": "SOL", "seite": "long",
            "familie": "krypto", "einstieg": 128.50, "stop": 123.90,
            "ziel": 137.80, "liq": 100.0, "kontrakte": 1.0, "nominal": 128.5,
            "margin": 12.85, "hebel": 10.0, "modus": "live",
            "eroeffnet_zeit": eroeffnet_zeit, "funding_zuletzt": eroeffnet_zeit,
            "funding_summe": 0.0}


class KeinZeitausstieg(unittest.TestCase):
    def setUp(self):
        self.j = patch.object(h, "journal")
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_aelter_als_48h_wird_nicht_geschlossen(self):
        # Position ist ~12 Tage alt, Kurs zwischen Stop und Ziel.
        z = {"positionen": [_position()], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=("SOL-USD-um_xperp", 130.0)):
            h.pruefe_ausstiege(z, live=True, w={})
        self.assertEqual(len(z["positionen"]), 1,
                         "kein Zeitausstieg - Position bleibt stehen")

    def test_stop_trifft_weiterhin(self):
        z = {"positionen": [_position()], "letzte_stops": {}}
        with patch.object(h.okxf, "letzter_kurs_mit_fallback",
                          return_value=("SOL-USD-um_xperp", 120.0)), \
             patch.object(h.okxf, "markt_schliessen"):
            h.pruefe_ausstiege(z, live=True, w={})
        self.assertEqual(len(z["positionen"]), 0, "Stop schliesst weiterhin")


if __name__ == "__main__":
    unittest.main()
