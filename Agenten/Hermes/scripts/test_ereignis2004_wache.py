#!/usr/bin/env python3
"""Tests fuer ereignis2004-wache.py - Regeln statt Tageswerte.

Die Wache ruft Get-WinEvent auf; die Tests pruefen die reine Meldelogik
`berichte()` mit festen Fixtures:
  * Erstlauf ohne Merkdatei meldet
  * zweiter Lauf (Merkdatei gesetzt) schweigt bei alter Gruppe
  * neue Gruppe meldet
  * Rueckgang (0 Ereignisse) meldet genau einmal
"""

import importlib.util
import os
import unittest
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
WACHE = os.path.join(HIER, "ereignis2004-wache.py")
WACHE = os.path.normpath(WACHE)

spec = importlib.util.spec_from_file_location("wache2004", WACHE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def lade():
    s = importlib.util.spec_from_file_location("wache2004", WACHE)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def ereignis(iso):
    return {"TimeCreated": iso, "Msg": "virtueller Speicher"}


class MeldelogikTest(unittest.TestCase):
    def test_erstlauf_meldet(self):
        m = lade()
        jetzt = datetime(2026, 10, 8, 1, 0)
        meldungen, z = m.berichte(
            [ereignis("2026-10-07T01:32:54+02:00")] * 4, {}, jetzt
        )
        self.assertEqual(len(meldungen), 1)
        self.assertIn("4 in 24 h", meldungen[0])
        self.assertIn("2026-10-07T01:32:54+02:00", meldungen[0])

    def test_zweiter_lauf_schweigt(self):
        m = lade()
        jetzt = datetime(2026, 10, 8, 1, 0)
        _, z = m.berichte(
            [ereignis("2026-10-07T01:32:54+02:00")] * 4, {}, jetzt
        )
        # gleiche Ereignisse, Merkdatei gesetzt -> keine neue Gruppe
        meldungen2, _ = m.berichte(
            [ereignis("2026-10-07T01:32:54+02:00")] * 4, z, jetzt
        )
        self.assertEqual(meldungen2, [], "alte Gruppe darf nicht erneut melden")

    def test_neue_gruppe_meldet(self):
        m = lade()
        jetzt = datetime(2026, 10, 8, 1, 0)
        _, z = m.berichte([ereignis("2026-10-07T01:32:54+02:00")], {}, jetzt)
        # neue Gruppe NACH der Merkzeit -> meldet
        meldungen, _ = m.berichte(
            [ereignis("2026-10-08T02:00:00+02:00")], z, jetzt
        )
        self.assertEqual(len(meldungen), 1)
        self.assertIn("1 in 24 h", meldungen[0])

    def test_rueckgang_meldet_einmal(self):
        m = lade()
        jetzt = datetime(2026, 10, 8, 1, 0)
        meldungen, z = m.berichte([], {}, jetzt)
        self.assertEqual(len(meldungen), 1)
        self.assertIn("Rueckgang", meldungen[0])
        # zweiter Lauf ohne Ereignisse -> schweigt (rueckgang_gemeldet=True)
        meldungen2, _ = m.berichte([], z, jetzt)
        self.assertEqual(meldungen2, [])


if __name__ == "__main__":
    unittest.main()