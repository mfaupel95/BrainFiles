"""Tests fuer demo_position_wache.beurteilen (reine Funktion, kein Netz)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR = HIER.parent
_spec = importlib.util.spec_from_file_location("demo_position_wache", SPUR / "demo_position_wache.py")
w = importlib.util.module_from_spec(_spec)
sys.modules["demo_position_wache"] = w
_spec.loader.exec_module(w)

JETZT = 1_800_000_000.0


def lage(pos=2.1, stops=1, trigger=61000.0, kurs=67768.9, fehler=None, upl=2.43, geschuetzt=None):
    if geschuetzt is None:
        geschuetzt = pos if stops else 0.0
    return {"position": pos, "upl": upl, "stops": stops, "trigger": trigger,
            "kurs": kurs, "fehler": fehler, "geschuetzt": geschuetzt}


class RegelTest(unittest.TestCase):
    def test_gesund_keine_meldung(self):
        self.assertEqual(w.beurteilen(lage(), {}, JETZT), [])

    def test_schutz_weg_wird_gemeldet(self):
        m = w.beurteilen(lage(stops=0), {"position_war_da": True}, JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("KEIN Schutz-Stop", m[0])

    def test_schutz_weg_wiederholt_sich_nicht_staendig(self):
        alt = {"position_war_da": True, "letzte_schutzmeldung": JETZT - 60}
        self.assertEqual(w.beurteilen(lage(stops=0), alt, JETZT), [])
        alt_alt = {"position_war_da": True, "letzte_schutzmeldung": JETZT - w.WIEDERHOLUNG_S - 1}
        self.assertEqual(len(w.beurteilen(lage(stops=0), alt_alt, JETZT)), 1)

    def test_geschlossen_wird_genau_einmal_gemeldet(self):
        m = w.beurteilen(lage(pos=0.0, stops=0), {"position_war_da": True}, JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("flach", m[0])
        # zweiter Lauf: alt traegt position_war_da=False -> keine zweite Meldung
        self.assertEqual(w.beurteilen(lage(pos=0.0, stops=0), {"position_war_da": False}, JETZT), [])

    def test_nah_am_stop_einmal(self):
        m = w.beurteilen(lage(kurs=61500.0), {}, JETZT)   # 0,82 % ueber 61000
        self.assertEqual(len(m), 1)
        self.assertIn("ueber dem Stop", m[0])
        # schon gemeldet -> nicht nochmal
        self.assertEqual(w.beurteilen(lage(kurs=61500.0), {"nahe_gemeldet": True}, JETZT), [])

    def test_fern_vom_stop_keine_meldung(self):
        self.assertEqual(w.beurteilen(lage(kurs=65000.0), {}, JETZT), [])

    def test_fehler_gegenprobe(self):
        m = w.beurteilen(lage(fehler="Positionen: HTTP502"), {}, JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("nicht abfragbar", m[0])
        # innerhalb der Wiederholungssperre still
        self.assertEqual(w.beurteilen(lage(fehler="x"), {"letzter_fehler": JETZT - 60}, JETZT), [])

    def test_ohne_trigger_keine_abstandsmeldung(self):
        self.assertEqual(w.beurteilen(lage(trigger=None), {}, JETZT), [])

    def test_teilgedeckter_stop_wird_gemeldet(self):
        # Ein Stop mit 2,1 deckt eine Position von 2,2 NICHT - genau der Fall
        # vom 21.10.2026, nachdem eine zweite Order 0,1 Kontrakte dazukamen.
        jetzt = lage(pos=2.2, stops=1, geschuetzt=2.1)
        m = w.beurteilen(jetzt, {}, JETZT)
        self.assertEqual(len(m), 1)
        self.assertIn("deckt nur", m[0])
        # voll gedeckt -> keine Meldung
        self.assertEqual(w.beurteilen(lage(pos=2.2, stops=1, geschuetzt=2.2), {}, JETZT), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
