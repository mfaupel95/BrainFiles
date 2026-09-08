import json
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


class TestAusstieg(unittest.TestCase):
    def setUp(self):
        # Alle drei Monkeypatches greifen in gemeinsam genutzten Modulzustand
        # (oanda, handeln.sess) - ohne Restore leckt das in test_oanda_* und
        # test_session.
        self.addCleanup(setattr, handeln.oanda, "preis", handeln.oanda.preis)
        self.addCleanup(setattr, handeln, "journal", handeln.journal)
        self.addCleanup(setattr, handeln.sess, "zwangsschluss",
                        handeln.sess.zwangsschluss)
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

    def _pos(self, richtung, einstieg, stop, ziel, units=2.0, eroeffnet=None):
        return {"inst": self.key, "richtung": richtung, "einstieg": einstieg,
                "stop": stop, "ziel": ziel, "units": units, "risiko_eur": 20.0,
                "eroeffnet": eroeffnet or date.today().isoformat(),
                "order_id": None}

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
        # Zwangsschluss neutralisieren: hier steht NUR "Kurs echt zwischen Stop
        # und Ziel -> Position bleibt offen" unter Test, keine Uhrzeit-Logik.
        fern = datetime(2999, 1, 1, tzinfo=timezone.utc)
        handeln.sess.zwangsschluss = lambda ik, tag: fern
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40010
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 1)

    def test_stale_position_wird_zwangsgeschlossen(self):
        # Gestern eroeffnet, gestriger Cash-Close laengst vorbei -> sofort zu,
        # egal ob Kurs zwischen Stop und Ziel liegt.
        alt = "2025-07-15"
        z = {"positionen": [self._pos("long", 40000, 39950, 40100, eroeffnet=alt)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40010                     # zwischen Stop und Ziel
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self._journal[-1][10], "zwangsschluss")

    def test_journal_eur_betrag_long_und_short_ziel(self):
        # half-spread = 0.5 * spread_punkte(2) * punkt_wert(1) * units(2) = 2.0
        # eur-Feld = risiko_eur(20) + (wert_eur - half-spread)
        fern = datetime(2999, 1, 1, tzinfo=timezone.utc)
        handeln.sess.zwangsschluss = lambda ik, tag: fern

        # long liest bid. bid = 40100 = Ziel, wert_eur = (40100-40000)*1*2 = 200
        # -> eur = 20 + (200 - 2) = 218.00
        z = {"positionen": [self._pos("long", 40000, 39950, 40100)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 40100
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(self._journal[-1][10], "ziel")
        self.assertAlmostEqual(float(self._journal[-1][6]), 218.00, places=2)

        # short ziel: liest ask = bid + 2. bid = 39898 -> ask = 39900 = Ziel
        # wert_eur = (40000-39900)*1*2 = 200 -> eur = 20 + (200 - 2) = 218.00
        z = {"positionen": [self._pos("short", 40000, 40050, 39900)],
             "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        self._preise[self.key] = 39898
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(self._journal[-1][10], "ziel")
        self.assertAlmostEqual(float(self._journal[-1][6]), 218.00, places=2)
