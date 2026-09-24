"""Bedingung 4 gilt an JEDEM Ausgang des Zyklus, nicht nur am Ende.

BEFUND (24.09.2026, gemessen mit spiegelstand.py): der Schattenarm
omniquant_weit stellte in seinem ersten Dauerlauf-Zyklus sechs Papierpositionen
als 'herzschlag' flach - der Herzschlag-Ausstieg kehrt frueh zurueck, VOR der
Spiegelung am Zyklusende. Q:\\Handel_Journal\\omniquant_weit blieb auf dem Stand
des vorigen Zyklus stehen, und spiegelstand meldete ueber mehrere Zyklen
'ABWEICHUNG'. Genau dieselbe Luecke hatte der scanner (21.09.2026) und
moondev_marktlage (22.09.2026).

Der Test liest die QUELLE: eine Spiegelung muss vor dem ersten vorzeitigen
Ausgang stehen. Das prueft die Regel, nicht einen Zustand - und geht darum
auch dann nicht kaputt, wenn Zahlen oder Texte sich aendern.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(SPUR))

QUELLE = (SPUR / "handeln.py").read_text(encoding="utf-8")


class SpiegelungJederAusgang(unittest.TestCase):

    def test_herzschlag_ausgang_spiegelt_vor_dem_return(self):
        """Der einzige fruehe Ausgang, der SCHREIBT, muss auch kopieren."""
        anfang = QUELLE.find("if herzschlag_alt(")
        self.assertGreater(anfang, 0, "Herzschlag-Ausgang nicht gefunden")
        ende = QUELLE.find("# Kill-Switch", anfang)
        block = QUELLE[anfang:ende]
        self.assertIn("schreibe_zustand(z)", block)
        self.assertIn("_spiegeln(w, z)", block,
                      "der Herzschlag-Ausgang schreibt den Zustand, kopiert aber nicht")
        self.assertLess(block.find("schreibe_zustand(z)"), block.find("_spiegeln(w, z)"),
                        "erst schreiben, dann kopieren")

    def test_vorschau_schreibt_und_spiegelt_nicht(self):
        """Eine Vorschau darf nirgends kopieren - sonst ist sie ein Schreibzugriff."""
        anfang = QUELLE.find('if modus == "vorschau":')
        self.assertGreater(anfang, 0)
        block = QUELLE[anfang:QUELLE.find("letzter_lauf", anfang)]
        self.assertNotIn("_spiegeln(", block)

    def test_helfer_spiegelt_journal_und_zustand_an_das_zweitziel(self):
        rumpf = QUELLE[QUELLE.find("def _spiegeln("):]
        rumpf = rumpf[:rumpf.find("\ndef ", 1)]
        self.assertIn("journal_zweitziel", rumpf)
        self.assertIn("[JOURNAL, ZUSTAND]", rumpf)
        self.assertIn("vermerke_spiegelung", rumpf)

    def test_der_arm_erbt_die_spiegelung(self):
        """omniquant_weit ruft denselben Kern - also gilt die Regel dort mit."""
        arm = (SPUR / "omniquant_weit.py").read_text(encoding="utf-8")
        self.assertIn("_main", arm,
                      "der Arm muss handeln._main() rufen, sonst fehlt ihm die "
                      "ganze Ausstiegs- und Spiegelungslogik")

    def test_auch_am_ende_wird_gespiegelt(self):
        """Zwei Kopierwege: der Helfer am Anfang und der Block am Zyklusende."""
        self.assertGreaterEqual(
            len(re.findall(r"spiegele_journal\(", QUELLE)), 2,
            "am Anfang UND am Zyklusende muss kopiert werden")


if __name__ == "__main__":
    unittest.main()