"""Tests: Verfall eines eingelegten Auftrags (Entscheidung A).

Bauplan-Abschnitt 6, Test 2: Ein Auftrag mit gueltig_bis in der Vergangenheit
wird verworfen (Journal aktion=verwerfen, grund=auftrag_abgelaufen), es wird
KEINE Order gesendet.
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


def _auftrag(gueltig_bis="2020-01-01T00:00:00+00:00"):
    return {"instId": "SOL-USD-um_xperp", "seite": "long", "hebel": 10.0,
            "einstieg": 128.50, "stop": 123.90, "ziel": 137.80,
            "einsatz": 80.0, "zeithorizont": 48, "gueltig_bis": gueltig_bis,
            "gestellt": "2020-01-01T00:00:00+00:00"}


class Verfall(unittest.TestCase):
    def setUp(self):
        self.j = patch.object(h, "journal")
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_abgelaufener_auftrag_wird_verworfen(self):
        z = {"eingelegt": [_auftrag()]}
        n = h._pruefe_eingeleggte_vor_lauf(z, live=True, w={})
        self.assertEqual(n, 1)
        self.assertEqual(z["eingelegt"], [])
        grund = [c.kwargs.get("grund") for c in h.journal.call_args_list]
        self.assertIn("auftrag_abgelaufen", grund)

    def test_keine_order_bei_abgelaufenem_auftrag(self):
        # pruefe_einstiege bekommt nach dem Verfall keinen Kandidaten mehr.
        z = {"eingelegt": [_auftrag()], "positionen": [], "wartende": []}
        h._pruefe_eingeleggte_vor_lauf(z, live=True, w={})
        kand = h.kandidaten_aus_auftraegen(z, {})
        self.assertEqual(kand, [])

    def test_gueltiger_auftrag_bleibt(self):
        z = {"eingelegt": [_auftrag("2099-01-01T00:00:00+00:00")]}
        n = h._pruefe_eingeleggte_vor_lauf(z, live=True, w={})
        self.assertEqual(n, 0)
        self.assertEqual(len(z["eingelegt"]), 1)


if __name__ == "__main__":
    unittest.main()
