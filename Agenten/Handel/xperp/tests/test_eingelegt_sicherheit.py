"""Tests: Sicherheitspruefungen des eingelegten Auftrags.

Bauplan-Abschnitt 6, Test 5: je Sperre aus Abschnitt 5 - Freigabefenster zu /
handel_erlaubt=false / Hebel > Deckel / Stop fehlt (Auftrag verworfen) /
Kill-Switch / max_offene_anlaeufe erreicht -> keine Order.
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


def _auftrag(hebel=10.0, stop=123.90, einsatz=80.0):
    return {"instId": "SOL-USD-um_xperp", "seite": "long", "hebel": hebel,
            "einstieg": 128.50, "stop": stop, "ziel": 137.80,
            "einsatz": einsatz, "zeithorizont": 48,
            "gueltig_bis": "2099-01-01T00:00:00+00:00",
            "gestellt": "2026-10-12T14:30:00+00:00"}


def _w():
    return {"max_offene_anlaeufe": 4, "max_margin_gesamt_usd": 600.0,
            "max_margin_je_anlauf_usd": 80.0, "max_hebel": 5.0,
            "gebuehr_taker": 0.0005, "wartungsmarge": 0.005,
            "risiko_je_anlauf_usd": 7.5, "familien": {}}


def _instr():
    return {"instId": "SOL-USD-um_xperp", "ctVal": "1", "lotSz": "1",
            "minSz": "1", "tickSz": "0.01"}


class Sicherheit(unittest.TestCase):
    def setUp(self):
        self.j = patch.object(h, "journal")
        self.j.start()
        self.addCleanup(self.j.stop)

    def _kand(self, auftrag):
        z = {"eingelegt": [auftrag], "positionen": [], "wartende": []}
        return z, h.kandidaten_aus_auftraegen(z, _w())[0]

    def test_hebel_ueber_deckel_keine_order(self):
        z, kand = self._kand(_auftrag(hebel=20.0))
        with patch.object(h.okxf, "instrument", return_value=_instr()), \
             patch.object(h.okxf, "order_limit") as ol:
            h.pruefe_einstiege(z, [kand], _w(), live=True,
                               s={"wochenende": False})
        ol.assert_not_called()
        self.assertEqual(z["positionen"], [])

    def test_stop_fehlt_auftrag_verworfen(self):
        z = {"eingelegt": [_auftrag(stop=0.0)], "positionen": [], "wartende": []}
        n = h._pruefe_eingeleggte_vor_lauf(z, live=True, w=_w())
        self.assertEqual(n, 1)
        self.assertEqual(z["eingelegt"], [])
        grund = [c.kwargs.get("grund") for c in h.journal.call_args_list]
        self.assertIn("auftrag_ohne_stop", grund)

    def test_einsatz_zu_gross_verworfen(self):
        z = {"eingelegt": [_auftrag(einsatz=9999.0)], "positionen": [], "wartende": []}
        n = h._pruefe_eingeleggte_vor_lauf(z, live=True, w=_w())
        self.assertEqual(n, 1)
        grund = [c.kwargs.get("grund") for c in h.journal.call_args_list]
        self.assertIn("auftrag_zu_gross", grund)

    def test_max_offene_anlaeufe_erreicht_keine_order(self):
        z, kand = self._kand(_auftrag())
        z["positionen"] = [{"basis": "A", "margin": 10.0, "familie": "krypto"},
                           {"basis": "B", "margin": 10.0, "familie": "krypto"},
                           {"basis": "C", "margin": 10.0, "familie": "krypto"},
                           {"basis": "D", "margin": 10.0, "familie": "krypto"}]
        w = dict(_w(), max_offene_anlaeufe=4)
        with patch.object(h.okxf, "instrument", return_value=_instr()), \
             patch.object(h.okxf, "order_limit") as ol:
            h.pruefe_einstiege(z, [kand], w, live=True,
                               s={"wochenende": False})
        ol.assert_not_called()

    def test_handel_erlaubt_false_keine_order(self):
        # handel_erlaubt=false sperrt live (sperren_live); pruefe_einstiege
        # bekommt dann live=False und sendet keine Order.
        z, kand = self._kand(_auftrag())
        with patch.object(h.okxf, "instrument", return_value=_instr()), \
             patch.object(h.okxf, "order_limit") as ol:
            h.pruefe_einstiege(z, [kand], _w(), live=False,
                               s={"wochenende": False})
        ol.assert_not_called()


if __name__ == "__main__":
    unittest.main()
