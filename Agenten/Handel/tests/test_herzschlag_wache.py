"""Herzschlag-Wache: meldet nur Wechsel und nur echte Stille."""

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir))
if HANDEL not in os.sys.path:
    os.sys.path.append(HANDEL)

import herzschlag_wache as hw

JETZT = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def iso(minuten_her):
    return (JETZT - timedelta(minutes=minuten_her)).isoformat()


class Wache(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        with open(os.path.join(self.d, "dauerlauf.py"), "w", encoding="utf-8") as fh:
            fh.write('SPUREN = {\n  "a": {"ordner": "a"},\n  "b": {"ordner": "bb"},\n'
                     '  "c": {"ordner": "c"},\n}\n')
        self.merk = os.path.join(self.d, "cache", "m.json")

    def spur(self, ordner, minuten_her, grenze=None):
        os.makedirs(os.path.join(self.d, ordner), exist_ok=True)
        with open(os.path.join(self.d, ordner, "zustand.json"), "w") as fh:
            json.dump({"letzter_lauf": None if minuten_her is None
                       else iso(minuten_her)}, fh)
        if grenze is not None:
            with open(os.path.join(self.d, ordner, "wachen.json"), "w") as fh:
                json.dump({"herzschlag_max_minuten": grenze}, fh)

    def test_spurliste_liest_ordner(self):
        self.assertEqual(hw.spurliste(self.d), [("a", "a"), ("b", "bb"), ("c", "c")])

    def test_stille_wird_gefunden_frische_nicht(self):
        self.spur("a", 10)                  # frisch (Vorgabe 180)
        self.spur("bb", 500)                # still
        self.spur("c", None)                # nie gelaufen -> zaehlt nicht
        s = hw.stille_spuren(self.d, JETZT)
        self.assertEqual(list(s), ["b"])

    def test_eigene_grenze_aus_wachen_json(self):
        self.spur("a", 40, grenze=30)       # xperp-artig: 30 min
        self.assertIn("a", hw.stille_spuren(self.d, JETZT))

    def test_wechsel_nur_bei_aenderung(self):
        self.assertEqual(hw.wechsel({"b": 5}, {}), (["b"], []))
        self.assertEqual(hw.wechsel({"b": 5}, {"still": ["b"]}), ([], []))
        self.assertEqual(hw.wechsel({}, {"still": ["b"]}), ([], ["b"]))

    def test_lauf_schreibt_merkdatei_und_meldet_einmal(self):
        self.spur("bb", 500)
        s1, neu1, _ = hw.lauf(self.d, JETZT, True, self.merk)
        s2, neu2, _ = hw.lauf(self.d, JETZT, True, self.merk)
        self.assertEqual(neu1, ["b"])
        self.assertEqual(neu2, [])          # zweiter Lauf: kein neuer Wechsel

    def test_stand_modus_schreibt_nichts(self):
        self.spur("bb", 500)
        hw.lauf(self.d, JETZT, False, self.merk)
        self.assertFalse(os.path.exists(self.merk))


if __name__ == "__main__":
    unittest.main()
