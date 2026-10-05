"""T-368: Die Worktree-Naht - ein Replay in einem Worktree sieht die leere Historie.

historie_binance.ORDNER = HIER/daten/historie ist RELATIV zur Modulposition.
Ein Worktree hat alle .py-Dateien, aber daten/ ist nicht versioniert. Eine
Modulkopie ohne daten/ laedt still 0 Kerzen -> '0 Runden' -> falsches
Messergebnis.

Die Naht: kerzen_fuer() prueft VOR dem Laden, ob der Ordner existiert.
Fehlt er, wird HistorieFehlt mit klarem Text geworfen - kein stiller Lauf.

Diese Tests schreiben NICHTS in echte Ordner - sie biegen ORDNER um.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import replay


class WorktreeNahtTest(unittest.TestCase):
    """Die Naht: fehlt der Ordner, ist jede Reihe leer."""

    def setUp(self):
        self.alt_ordner = replay.historie_binance.ORDNER
        self.addCleanup(self._zurueck)

    def _zurueck(self):
        replay.historie_binance.ORDNER = self.alt_ordner

    def test_ordner_da_ist_false(self):
        """Ordner existiert -> False."""
        self.assertFalse(replay.historie_ordner_fehlt())

    def test_ordner_fehlt_ist_true(self):
        """Ordner fehlt -> True."""
        replay.historie_binance.ORDNER = os.path.join(
            tempfile.gettempdir(), "gibts_nicht_12345")
        self.assertTrue(replay.historie_ordner_fehlt())

    def test_kerzen_fuer_wirft_historie_fehlt(self):
        """kerzen_fuer() wirft HistorieFehlt, wenn der Ordner fehlt."""
        replay.historie_binance.ORDNER = os.path.join(
            tempfile.gettempdir(), "gibts_nicht_12345")
        w = {"instrumente": ["BTC"], "kerzen_takt": "1H",
             "mindest_kerzen": 300}
        with self.assertRaises(replay.HistorieFehlt) as ctx:
            replay.kerzen_fuer("supertrend", w)
        text = str(ctx.exception)
        self.assertIn("nicht da", text)
        self.assertIn("auffuellen", text)

    def test_kerzen_fuer_laeuft_mit_ordner(self):
        """Gegenprobe: mit Ordner laeuft kerzen_fuer() normal."""
        w = {"instrumente": ["BTC"], "kerzen_takt": "1H",
             "mindest_kerzen": 300}
        # Muss keine HistorieFehlt werfen (Ordner ist da)
        try:
            replay.kerzen_fuer("supertrend", w)
        except replay.HistorieFehlt:
            self.fail("HistorieFehlt trotz vorhandenem Ordner")


if __name__ == "__main__":
    unittest.main()
