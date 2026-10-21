"""Der Schliess-Haken von omniquant meldet an telemetrie, schreibt aber nichts in die echte tracking.db.

Lauf: python -m unittest discover -s tests -p "test_telemetrie_haken.py"
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HIER)
sys.path.insert(0, HANDEL)

import handeln as h                               # noqa: E402


class SchliessHakenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(h, "JOURNAL", os.path.join(self.tmp.name, "handelsjournal.csv"))
        p.start()
        self.addCleanup(p.stop)

    def _position(self):
        return {"inst": "BTC-USDC", "seite": "long", "einstieg": 100.0, "nominal": 50.0,
                "stop": 95.0, "ziel": 110.0, "eroeffnet": "2026-10-01"}

    def test_ausstieg_meldet_gv_kurs_und_grund(self):
        z = {"positionen": []}
        p = self._position()
        z["positionen"].append(p)
        with mock.patch.object(h.telemetrie, "geschlossen") as gemeldet:
            h.schliesse(z, p, "ziel", 110.0, {})
        gemeldet.assert_called_once()
        args = gemeldet.call_args.args
        self.assertEqual((args[1] is p, args[2], args[3], args[5]), (True, "papier", "ziel", 110.0))
        self.assertAlmostEqual(args[4], 4.5, delta=0.6)            # ~+10 % von 50, minus Kosten

    def test_vorschau_meldet_nichts(self):
        z = {"positionen": []}
        p = self._position()
        z["positionen"].append(p)
        with mock.patch.object(h, "SCHREIBEN", False), \
                mock.patch.object(h.telemetrie, "geschlossen") as gemeldet:
            h.schliesse(z, p, "ziel", 110.0, {})
        gemeldet.assert_not_called()

    def test_journal_im_testordner_ist_fremd_und_schreibt_nichts(self):
        z = {"positionen": []}
        p = self._position()
        z["positionen"].append(p)
        with mock.patch.object(h.telemetrie.tracking, "track_zyklus_abgeschlossen") as t:
            h.schliesse(z, p, "stop", 94.0, {})
        t.assert_not_called()


if __name__ == "__main__":
    unittest.main()
