"""Nur die Basis uebernimmt Fremdpositionen (Auftrag Max 12.10.2026).

BEFUND aus den drei Journalen (standard/mittel/hoch): Der Abgleich laeuft in
jeder Risikostufe, die Stufen fragen aber dasselbe Boersenkonto. Jede holte die
Handpositionen in ihr eigenes Buch (`fremdposition_uebernommen`) und buchte sie
spaeter als `buchbereinigung_geist` aus - dieselben Ereignisse bis zu dreimal.
Eine Stufe ist Papiergeld (`risikostufe.live_erlaubt` = nur Basis), sie braucht
keine Boersenpositionen im Buch.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import test_abgleich_papier as tp                                    # noqa: E402
from test_abgleich_papier import Umgebung, WACHEN, _boerse, _pos     # noqa: E402

h = tp.h
setUpModule, tearDownModule = tp.setUpModule, tp.tearDownModule


class StufenTest(unittest.TestCase):
    def test_basis_uebernimmt_die_fremdposition(self):
        z = {"positionen": [], "wartende": []}
        with Umgebung([_boerse(tp.NEU, 5)]) as u, \
                patch.object(h.risikostufe, "ist_basis", return_value=True):
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["fremde"], 1)
        self.assertEqual([p["inst"] for p in z["positionen"]], [tp.NEU])
        self.assertEqual([j["grund"] for j in u.journal], ["fremdposition_uebernommen"])

    def test_stufe_uebernimmt_nichts(self):
        z = {"positionen": [], "wartende": []}
        with Umgebung([_boerse(tp.NEU, 5)]) as u, \
                patch.object(h.risikostufe, "ist_basis", return_value=False):
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["fremde"], 0)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(u.journal, [])
        self.assertEqual(u.gestellte_stops, [])

    def test_stufe_raeumt_altbestand_weiter_ab(self):
        """Eine schon uebernommene, an der Boerse weggefallene Live-Position
        wird auch in einer Stufe noch ausgebucht (Altbestand drainiert)."""
        z = {"positionen": [_pos(tp.XRP, kontrakte=704.0)], "wartende": []}
        with Umgebung([]) as u, \
                patch.object(h.risikostufe, "ist_basis", return_value=False):
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["geister"], 1)
        self.assertEqual(z["positionen"], [])
        self.assertEqual([j["grund"] for j in u.journal], ["buchbereinigung_geist"])


if __name__ == "__main__":
    unittest.main()
