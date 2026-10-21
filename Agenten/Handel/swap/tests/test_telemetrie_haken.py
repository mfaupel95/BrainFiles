"""Die Schliess-Haken von swap melden an telemetrie, schreiben aber nichts in die echte tracking.db.

Lauf (einzeln, die swap-Tests stoeren sich gegenseitig beim Import von handeln):
    python tests/test_telemetrie_haken.py
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

SWAP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SWAP not in sys.path:
    sys.path.insert(0, SWAP)

import handeln as h                               # noqa: E402


class SchliessHakenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(h, "JOURNAL", os.path.join(self.tmp.name, "handelsjournal.csv"))
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(h, "_kurs", lambda inst: 90.0)
        p.start()
        self.addCleanup(p.stop)

    def _zustand(self):
        er = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
        p = {"inst": "ABC-USD_UM_XPERP-1", "basis": "ABC", "seite": "long", "einstieg": 100.0,
             "nominal": 200.0, "margin": 40.0, "kontrakte": 2, "hebel": 5, "stop": 95.0,
             "ziel": 120.0, "eroeffnet_zeit": er}
        return {"positionen": [p], "letzte_stops": {}}, p

    def test_stop_ausstieg_meldet(self):
        z, p = self._zustand()
        with mock.patch.object(h.telemetrie, "geschlossen") as gemeldet:
            h.pruefe_ausstiege(z, False, {})
        gemeldet.assert_called_once()
        a = gemeldet.call_args.args
        self.assertEqual((a[1] is p, a[2], a[3], a[5]), (True, "papier", "stop", 90.0))
        self.assertAlmostEqual(a[4], -20.0 - 0.1, delta=0.01)       # -10 % von 200, minus Gebuehr
        self.assertAlmostEqual(a[6], 0.5, delta=0.01)               # 12 h = 0,5 Tage
        self.assertEqual(z["positionen"], [])

    def test_flach_stellen_meldet_mit_grund(self):
        z, p = self._zustand()
        with mock.patch.object(h.telemetrie, "geschlossen") as gemeldet:
            h.flach_stellen(z, False, "kill")
        self.assertEqual(gemeldet.call_args.args[3], "kill")

    def test_testjournal_schreibt_nichts_in_die_db(self):
        z, p = self._zustand()
        with mock.patch.object(h.telemetrie.tracking, "track_zyklus_abgeschlossen") as t:
            h.pruefe_ausstiege(z, False, {})
        t.assert_not_called()

    def test_haltedauer_ohne_zeit_ist_null(self):
        self.assertEqual(h._tage({}), 0)


if __name__ == "__main__":
    unittest.main()
