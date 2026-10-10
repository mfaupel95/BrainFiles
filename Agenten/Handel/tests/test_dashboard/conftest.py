# tests/test_dashboard/conftest.py
# Hilfen fuer unittest (kein pytest im Dashboard-venv).
import json
import tempfile
import unittest
from pathlib import Path


class HandelVerzeichnis(unittest.TestCase):
    """Basisklasse: temporaeres Handel-Verzeichnis mit Minimal-Struktur."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.handel = Path(self._tmp.name)
        (self.handel / "dauerlauf.log").write_text("", encoding="utf-8")
        (self.handel / "freigabe_fenster.json").write_text("{}", encoding="utf-8")

    def spur_wachen(self, name, erlaubt=True, hs=45):
        d = self.handel / name
        d.mkdir(exist_ok=True)
        (d / "wachen.json").write_text(
            json.dumps({"handel_erlaubt": erlaubt, "herzschlag_max_minuten": hs,
                        "freigabe": {"erfuellt": False}}),
            encoding="utf-8")
        return d
