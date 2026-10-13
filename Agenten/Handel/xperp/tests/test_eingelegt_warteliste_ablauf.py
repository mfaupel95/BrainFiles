"""Tests: Ablauf einer WARTENDEN eingelegten Order (Entscheidung A).

Bauplan-Abschnitt 6, Test 3: Ein wartender Auftrag, dessen
gestellt+zeithorizont < jetzt, wird per okxf.order_stornieren storniert
(nur live/schutz), der Warteeintrag entfernt und als verwerfen/
auftrag_abgelaufen gebucht.
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


def _wartend(gestellt="2020-01-01T00:00:00+00:00", zeithorizont=48):
    return {"inst": "SOL-USD-um_xperp", "basis": "SOL", "seite": "long",
            "familie": "krypto", "einstieg": 128.50, "stop": 123.90,
            "ziel": 137.80, "liq": 100.0, "kontrakte": 1.0, "nominal": 128.5,
            "margin": 12.85, "hebel": 10.0, "gebuehr_taker": 0.0005,
            "ord_id": "12345", "gestellt": gestellt,
            "zeithorizont": zeithorizont}


class WartelisteAblauf(unittest.TestCase):
    def setUp(self):
        self.j = patch.object(h, "journal")
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_abgelaufene_wartende_order_wird_storniert(self):
        z = {"positionen": [], "wartende": [_wartend()]}
        with patch.object(h.okxf, "order_stornieren") as storno:
            n = h.wartende_auftraege(z, live=True, w={})
        self.assertEqual(n, 0)
        storno.assert_called_once()
        self.assertEqual(z["wartende"], [], "Warteeintrag entfernt")
        grund = [c.kwargs.get("grund") for c in h.journal.call_args_list]
        self.assertIn("auftrag_abgelaufen", grund)

    def test_papierlauf_storniert_nicht(self):
        z = {"positionen": [], "wartende": [_wartend()]}
        with patch.object(h.okxf, "order_stornieren") as storno:
            n = h.wartende_auftraege(z, live=False, w={})
        self.assertEqual(n, 0)
        storno.assert_not_called()
        self.assertEqual(z["wartende"], [], "Warteeintrag trotzdem entfernt")

    def test_noch_gueltige_wartende_order_bleibt(self):
        z = {"positionen": [], "wartende": [_wartend("2099-01-01T00:00:00+00:00")]}
        with patch.object(h.okxf, "order_stand",
                          return_value={"state": "live"}):
            n = h.wartende_auftraege(z, live=True, w={})
        self.assertEqual(n, 0)
        self.assertEqual(len(z["wartende"]), 1)


if __name__ == "__main__":
    unittest.main()
