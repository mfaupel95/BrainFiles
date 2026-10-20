import json
import tempfile
import unittest
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import handeln
import wachen_orb as wp

INST = {"okx": "ETH-USDT-SWAP", "zone": "UTC", "eroeffnung": "00:00",
        "session_ende": "24:00", "spread_punkte": 0.1, "punkt_wert_usdt": 1.0}
W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USDT": 1.0},
     "max_range_punkte":     {"ETH_USDT": 40.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "ziel_punkte": {"ETH_USDT": 30},
     "instrument_aktiv": "ETH_USDT",
     "instrumente": {"ETH_USDT": INST}}


def _k(hh, mm, o, h, l, c):
    return {"zeit": datetime(2026, 9, 13, hh, mm, tzinfo=timezone.utc),
            "o": o, "h": h, "l": l, "c": c}


def _range_kerzen():
    # Range 00:00-00:30: hoch 100, tief 98
    return [_k(0, 0, 99, 100, 98, 99.5),
            _k(0, 15, 99.5, 100, 98, 99.8)]


class TestOpeningRange(unittest.TestCase):
    def test_hoch_tief_aus_ersten_zwei(self):
        hr = handeln.opening_range(_range_kerzen(), W, "ETH_USDT", date(2026, 9, 13))
        self.assertEqual(hr, (100.0, 98.0))

    def test_none_bei_einer_kerze(self):
        self.assertIsNone(handeln.opening_range(
            [_k(0, 0, 99, 100, 98, 99.5)], W, "ETH_USDT", date(2026, 9, 13)))


class TestBreakout(unittest.TestCase):
    def test_long_ueber_hoch(self):
        kerzen = _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertEqual(r, "long")
        self.assertEqual(kurs, 100.4)

    def test_short_unter_tief(self):
        kerzen = _range_kerzen() + [_k(0, 30, 97.8, 98.1, 97.5, 97.6)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertEqual(r, "short")
        self.assertEqual(kurs, 97.6)

    def test_kein_breakout(self):
        kerzen = _range_kerzen() + [_k(0, 30, 99.5, 99.9, 98.5, 99.6)]
        r, kurs = handeln.breakout_signal(kerzen[2:], 100.0, 98.0)
        self.assertIsNone(r)


class TestEinstieg(unittest.TestCase):
    def setUp(self):
        self.z = {"position": None, "letzter_lauf": None}
        handeln.kerzen_quelle = (
            lambda w, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])

    def tearDown(self):
        handeln.kerzen_quelle = None

    def test_kein_instrument_aktiv(self):
        w2 = dict(W, instrument_aktiv=None)
        m = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, w2, m)
        self.assertIsNone(e)
        self.assertIn("instrument_aktiv", meldung)

    def test_range_laeuft_noch(self):
        m = datetime(2026, 9, 13, 0, 15, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, W, m)
        self.assertIsNone(e)
        self.assertIn("Range laeuft", meldung)

    def test_long_einstieg(self):
        m = datetime(2026, 9, 13, 0, 45, tzinfo=timezone.utc)
        e, meldung = handeln.pruefe_einstieg(self.z, W, m)
        self.assertEqual(e, "papier")
        p = self.z["position"]
        self.assertEqual(p["richtung"], "long")
        self.assertEqual(p["stop"], 98.0)
        self.assertEqual(p["ziel"], 100.4 + 1.5 * 2.0)


class TestAusstiege(unittest.TestCase):
    # Feste Uhrzeit am Handelstag der Testposition: ohne jetzt-Parameter
    # greift seit dem 14.09.2026 00:00 UTC der Zwangsschluss des Vortags
    # und jeder Ausstiegs-Test faellt als 'zwangsschluss' statt des
    # geprüften Grundes.
    JETZT = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        # pruefe_ausstiege schreibt ueber _schliesse -> journal(). Ohne
        # Umleitung fuellte JEDER Suite-Lauf die echte handelsjournal.csv
        # mit synthetischen Testrunden (Befund 14.09.2026: 24 Zeilen mit
        # Einstieg 100.4 im echten Journal, gleiches Muster wie die
        # TEST-Q-Falle). Das Journal gehoert in den Temp-Ordner.
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_journal = handeln.JOURNAL
        handeln.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"

    def tearDown(self):
        handeln.JOURNAL = self.alt_journal
        self.tmp.cleanup()

    def test_stop_long(self):
        z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 97.5}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertTrue(veraendert)
        self.assertEqual(grund, "stop")
        self.assertEqual(z["position"]["ausgang"], "stop")

    def test_ziel_long(self):
        z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 103.5}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertEqual(grund, "ziel")

    def test_offen_bleibt(self):
        z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": date(2026, 9, 13), "letzter_kurs": 101.0}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertFalse(veraendert)
        self.assertIsNone(grund)

    def test_tag_als_iso_string_aus_zustand(self):
        # zustand.json speichert tag als ISO-String - pruefe_ausstiege muss
        # das parsen (der Fehler vom 13.09.2026: TypeError im Dauerlauf).
        z = {"position": {"inst": "ETH_USDT", "richtung": "long",
                          "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                          "tag": "2026-09-13", "letzter_kurs": 101.0}}
        veraendert, grund = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertFalse(veraendert)
        self.assertIsNone(grund)


class TestWiedereinstiegHemmt(unittest.TestCase):
    """Regression 13.09.2026: Ausstieg + Wiedereinstieg im Endloskreis.

    Der Ausstieg entfernt die Position; ohne Merkzeichen war "heute schon
    gehandelt" direkt wieder falsch und derselbe Breakout stieg im selben
    Zyklus erneut ein. Folge am echten Lauf: Journal voller identischer
    Ausstiegszeilen (51 an einem Tag), die Position "haengte" in
    zustand.json, und jede Viertelstunde ging eine AUSSTIEG-Meldung an
    Telegram.
    """

    def tearDown(self):
        handeln.kerzen_quelle = None

    def _lauf(self, merkzeichen):
        with tempfile.TemporaryDirectory() as w:
            zpfad = Path(w) / "zustand.json"
            jpfad = Path(w) / "handelsjournal.csv"
            zustand = {"position": {"inst": "ETH_USDT", "richtung": "long",
                                    "einstieg": 100.4, "stop": 98.0,
                                    "ziel": 103.4, "tag": "2026-09-13",
                                    "letzter_kurs": 103.5},
                       "zuletzt_gehandelt_tag": merkzeichen}
            zpfad.write_text(json.dumps(zustand, ensure_ascii=False),
                             encoding="utf-8")
            handeln.kerzen_quelle = (
                lambda w_, key: _range_kerzen()
                + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])
            try:
                with patch.object(handeln, "_wachen", lambda: W), \
                        patch.object(handeln, "ZUSTAND", zpfad), \
                        patch.object(handeln, "JOURNAL", jpfad), \
                        patch.object(handeln, "_letzter_kurs",
                                     lambda w_, key: 101.0), \
                        patch.object(handeln, "_jetzt", lambda: datetime(
                            2026, 9, 13, 1, 0, tzinfo=timezone.utc)):
                    meldungen = handeln.lauf()
            finally:
                handeln.kerzen_quelle = None
            nachher = json.loads(zpfad.read_text(encoding="utf-8"))
            zeilen = jpfad.read_text(encoding="utf-8").splitlines()
            return meldungen, nachher, zeilen

    def test_merkzeichen_verhindert_wiedereinstieg(self):
        meldungen, nachher, zeilen = self._lauf("2026-09-13")
        # Kopf + genau eine Ausstiegszeile, keine Einstiegszeile.
        self.assertEqual(len(zeilen), 2, zeilen)
        self.assertIsNone(nachher.get("position"))
        einstiege = [m for m in meldungen if "EINSTIEG" in m]
        self.assertEqual(einstiege, [], meldungen)

    def test_gegenprobe_ohne_merkzeichen_stiegt_wieder_ein(self):
        """Ohne Merkzeichen reproduziert sich der Fehler - der Test kann
        also den Fix beweisen und nicht nur mitschwimmen."""
        meldungen, nachher, _ = self._lauf(None)
        self.assertIsNotNone(nachher.get("position"))
        einstiege = [m for m in meldungen if "EINSTIEG" in m]
        self.assertEqual(len(einstiege), 1, meldungen)


if __name__ == "__main__":
    unittest.main()