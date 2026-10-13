"""Tests: eingelegter Auftrag statt Rangliste.

Bauplan-Abschnitt 6, Test 4: Bei nicht-leerem eingelegt.json liefert
lauf()/pruefe_einstiege Kandidaten aus den Auftraegen, NICHT aus der
Rangliste (range/auswahl gemockt).
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


def _auftrag(inst="SOL-USD-um_xperp", seite="long"):
    return {"instId": inst, "seite": seite, "hebel": 10.0,
            "einstieg": 128.50, "stop": 123.90, "ziel": 137.80,
            "einsatz": 80.0, "zeithorizont": 48,
            "gueltig_bis": "2099-01-01T00:00:00+00:00",
            "gestellt": "2026-10-12T14:30:00+00:00"}


class StattRangliste(unittest.TestCase):
    def test_kandidaten_kommen_aus_den_auftraegen(self):
        z = {"eingelegt": [_auftrag()]}
        kand = h.kandidaten_aus_auftraegen(z, {})
        self.assertEqual(len(kand), 1)
        self.assertEqual(kand[0]["basis"], "SOL")
        self.assertEqual(kand[0]["seite"], "long")
        self.assertEqual(kand[0]["instId"], "SOL-USD-um_xperp")
        self.assertIn("auftrag", kand[0])

    def test_anlauf_wird_fuer_eingelegt_nicht_gerufen(self):
        # pruefe_einstiege verarbeitet den eingelegten Kandidaten ueber
        # _anlauf_aus_auftrag, nicht ueber anlauf() (der die Rangliste kennt).
        z = {"eingelegt": [_auftrag()], "positionen": [], "wartende": []}
        kand = h.kandidaten_aus_auftraegen(z, {})
        w = {"max_offene_anlaeufe": 4, "max_margin_gesamt_usd": 600.0,
             "max_margin_je_anlauf_usd": 80.0, "max_hebel": 5.0,
             "gebuehr_taker": 0.0005, "wartungsmarge": 0.005,
             "risiko_je_anlauf_usd": 7.5, "familien": {}}
        s = {"wochenende": False}
        with patch.object(h, "anlauf") as anlauf, \
             patch.object(h.okxf, "instrument",
                          return_value={"instId": "SOL-USD-um_xperp",
                                        "ctVal": "1", "lotSz": "1",
                                        "minSz": "1", "tickSz": "0.01"}):
            h.pruefe_einstiege(z, kand, w, live=False, s=s)
        anlauf.assert_not_called()

    def test_leer_faellt_auf_rangliste_zurueck(self):
        z = {"eingelegt": []}
        self.assertEqual(h.kandidaten_aus_auftraegen(z, {}), [])


if __name__ == "__main__":
    unittest.main()
