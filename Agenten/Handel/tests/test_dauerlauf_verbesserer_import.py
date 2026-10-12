"""Ein kaputter verbesserer/-Import darf den Dauerlauf nicht aufhalten, aber
auch nicht lautlos bleiben (Review 09.10.2026)."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HANDEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HANDEL))

import dauerlauf                                                 # noqa: E402


class VerbessererImport(unittest.TestCase):
    def test_intakter_import_meldet_nichts(self):
        with patch.object(dauerlauf, "VERB_IMPORT_FEHLER", None), \
             patch.object(dauerlauf.ereignis, "hinweis") as h:
            self.assertFalse(dauerlauf.verbesserer_import_melden())
        h.assert_not_called()

    def test_importfehler_wird_gemeldet(self):
        with patch.object(dauerlauf, "VERB_IMPORT_FEHLER",
                          "ModuleNotFoundError: anfrage"), \
             patch.object(dauerlauf.ereignis, "hinweis") as h, \
             patch("sys.stderr"):
            self.assertTrue(dauerlauf.verbesserer_import_melden())
        h.assert_called_once()
        self.assertIn("ModuleNotFoundError", h.call_args[0][1])

    def test_toter_bus_wirft_nicht(self):
        with patch.object(dauerlauf, "VERB_IMPORT_FEHLER", "X: y"), \
             patch.object(dauerlauf.ereignis, "hinweis",
                          side_effect=RuntimeError("Bus tot")), \
             patch("sys.stderr"):
            self.assertTrue(dauerlauf.verbesserer_import_melden())

    def test_attribut_existiert_im_echten_modul(self):
        self.assertTrue(hasattr(dauerlauf, "VERB_IMPORT_FEHLER"))


if __name__ == "__main__":
    unittest.main()
