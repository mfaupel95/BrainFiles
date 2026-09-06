"""Task 13: der Orchestrator lauf.einmal().

Zwei Faelle:

* ohne Kerzen-Cache bricht einmal() hart ab und gibt None
* liefert die Suche keinen Kandidaten, entsteht trotzdem ein Ordner mit
  bericht.md, aber ohne commit.txt (kein-Vorschlag-Pfad)

Der zweite Fall haengt an echten wachen.json/konfig.json/spuren.json, ersetzt
aber die teuren Schritte (kerzen.laden, auswerter.befund, suche.suche,
digest.erzeuge) durch Fakes.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import lauf  # noqa: E402


class TestLaufAbbruch(unittest.TestCase):
    def test_kein_kerzencache_bricht_ab(self):
        alt = lauf.KERZEN_DIR
        try:
            with TemporaryDirectory() as d:
                lauf.KERZEN_DIR = Path(d) / "leer"
                r = lauf.einmal("spur1", kerzen_holen=False)
                self.assertIsNone(r)
        finally:
            lauf.KERZEN_DIR = alt


def _basis_wf():
    return {
        "gesamt": {"netto_gv_je_runde": -0.1, "n": 5, "max_drawdown": 1.0},
        "fenster": [],
    }


class TestLaufKeinVorschlag(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        self._berichte_alt = lauf.BERICHTE
        lauf.BERICHTE = Path(self._tmp.name)
        self.addCleanup(setattr, lauf, "BERICHTE", self._berichte_alt)

        p = mock.patch.object(
            lauf.kerzen, "laden",
            side_effect=lambda inst, cache_dir=None: ([[0, 1, 2, 3, 4, 5]], 1.0))
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.auswerter, "befund",
            side_effect=lambda spur, konfig, ordner: {"befunde": [],
                                                      "runden_gesamt": 5})
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.suche, "suche",
            side_effect=lambda *a, **k: {
                "kandidat": None,
                "basis_wf": _basis_wf(),
                "kandidat_wf": None,
                "auswertungen": 1,
                "grund": "nur 5 OOS-Runden (>= 20 noetig)",
                "aenderungen": {},
            })
        p.start(); self.addCleanup(p.stop)

        p = mock.patch.object(
            lauf.digest, "erzeuge",
            side_effect=lambda *a, **k: {"empfehlungen": "", "lehren": "",
                                        "uebersprungen": "LLM-Modus aus"})
        p.start(); self.addCleanup(p.stop)

    def test_zu_wenig_runden_gibt_kein_vorschlag(self):
        p = lauf.einmal("spur1", kerzen_holen=False)
        self.assertIsNotNone(p)
        self.assertTrue((p / "bericht.md").exists())
        self.assertFalse((p / "commit.txt").exists())


if __name__ == "__main__":
    unittest.main()
