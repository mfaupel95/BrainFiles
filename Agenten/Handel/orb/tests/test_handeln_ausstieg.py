import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


class TestAusstieg(unittest.TestCase):
    def setUp(self):
        self._orig_preis = handeln.oanda.preis
        self._orig_journal = handeln.journal
        self.addCleanup(setattr, handeln.oanda, "preis", self._orig_preis)
        self.addCleanup(setattr, handeln, "journal", self._orig_journal)
        self.w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
        # ein Instrument mit bekannten Werten forcieren
        self.key = "US30_USD"
        self.w["instrument_aktiv"] = self.key
        self.w["instrumente"][self.key] = {
            "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
            "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}
        self._preise = {}
        handeln.oanda.preis = lambda inst, live=False: {
            "bid": self._preise[inst], "ask": self._preise[inst] + 2.0,
            "spread_punkte": 2.0}
        self._journal = []
        handeln.journal = lambda *f: self._journal.append(f)

    def _pos(self, richtung, einstieg, stop, ziel, units=2.0):
        return {"inst": self.key, "richtung": richtung, "einstieg": einstieg,
                "stop": stop, "ziel": ziel, "units": units, "risiko_eur": 20.0,
                "eroeffnet": "2025-07-15", "order_id": None}

    def test_long_stop_schliesst_und_journalisiert(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 39940                     # unter Stop
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][2], "ausstieg")
        self.assertEqual(self._journal[-1][10], "stop")
        self.assertIn(self.key, z["letzte_stops"])

    def test_long_ziel_schliesst(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40120
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][10], "ziel")

    def test_short_stop_ist_oben(self):
        z = {"positionen": [self._pos("short", 40000, 40050, 39900)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40060
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][10], "stop")

    def test_offen_wenn_zwischen_stop_und_ziel(self):
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40010
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 1)
