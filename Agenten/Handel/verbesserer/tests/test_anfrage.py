import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
import anfrage  # noqa: E402


class TestAnfrage(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.b = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _mach(self, name):
        o = self.b / name
        o.mkdir(parents=True)
        (o / "commit.txt").write_text(
            "verbesserer: Scanner/OKX Parameter angepasst\n\n"
            "Geaenderte Schluessel: mindest_score\n", "utf-8")
        return o

    def test_offener_vorschlag_findet_neuen(self):
        o = self._mach("2026-09-13-spur1")
        self.assertEqual(anfrage.offener_vorschlag(self.b), o)

    def test_angefragt_wird_uebersprungen(self):
        o = self._mach("2026-09-13-spur1")
        anfrage.markiere_angefragt(o)
        self.assertIsNone(anfrage.offener_vorschlag(self.b))
        self.assertEqual(anfrage.wartet(self.b), o)

    def test_erledigt_wird_ignoriert(self):
        o = self._mach("erledigt/2026-09-01-spur1")
        self.assertIsNone(anfrage.offener_vorschlag(self.b))

    def test_text_nennt_schluessel(self):
        o = self._mach("2026-09-13-spur1")
        self.assertIn("mindest_score", anfrage.text(o))
        self.assertIn("/ja", anfrage.text(o))
