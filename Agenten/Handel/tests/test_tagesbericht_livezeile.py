"""Die Zeile 'Live-Anbindung' im Tagesbericht.

WARUM: seit 21.09.2026 steht handel_erlaubt=true in jeder wachen.json - der
Bericht muss trennen, welche Spur einen Orderweg im Code hat (echter Geldpfad)
und welche nicht. Geprueft wird gegen eine GEFAELSCHTE Erhebung, damit der Test
ohne Netz und ohne echten Spurordner laeuft.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)

import tagesbericht as tb  # noqa: E402
import spuren_stand as ss  # noqa: E402


class LivezeileTest(unittest.TestCase):
    def setUp(self):
        self.alt = ss.sammle

    def tearDown(self):
        ss.sammle = self.alt

    def _setze(self, daten):
        ss.sammle = lambda nur=None: daten

    def test_trennt_haus_fremd_und_ohne_orderweg(self):
        self._setze([
            {"spur": "mosaic", "order": ["kraken_spot.py"], "art": "haus",
             "fenster": "offen bis 20:58"},
            {"spur": "nautilus", "order": ["grid_strategie.py"], "art": "fremd",
             "fenster": "-"},
            {"spur": "gitter", "order": [], "art": None, "fenster": "-"},
        ])
        z = tb.livezeile()
        self.assertIn("2 von 3", z)
        self.assertIn("haus: mosaic (F)", z)
        self.assertIn("fremd: nautilus", z)
        self.assertIn("1 ohne Orderweg", z)
        self.assertNotIn("gitter", z)

    def test_ohne_orderweg_keine_leere_aufzaehlung(self):
        self._setze([{"spur": "gitter", "order": [], "art": None, "fenster": "-"}])
        self.assertIn("keine Spur", tb.livezeile())

    def test_fehler_kippt_den_bericht_nicht(self):
        def kaputt(nur=None):
            raise RuntimeError("Log unlesbar")
        ss.sammle = kaputt
        self.assertIn("nicht geprueft", tb.livezeile())


if __name__ == "__main__":
    unittest.main()
