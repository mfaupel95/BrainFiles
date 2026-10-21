"""ORB auf OKX (Spur orb): Papierzyklus, Range, Breakout, Ausstiege.

Vorlage ist `orbk/tests/test_handeln_papier.py` (dieselbe Strategie auf Kraken).
Unterschiede dieser Spur: Datenquelle okxf statt kraken, Instrumente sind
OKX-Perpetuals (ETH_USDT/BTC_USDT), und das Ziel kommt aus ziel_modus/ziel_k
bzw. ziel_punkte der eigenen wachen.json.

Kein Netz: handeln.kerzen_quelle wird durch synthetische Kerzen ersetzt, das
Journal zeigt in einen Temp-Ordner (das echte Journal darf nie Testrunden
tragen - Befund 14.09.2026: 24 synthetische Zeilen im echten Buch).
"""
import json
import tempfile
import unittest
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import handeln
import wachen_orb as wp

INST = {"okx": "ETH-USDT-SWAP", "zone": "UTC", "eroeffnung": "00:00",
        "session_ende": "24:00", "spread_punkte": 0.1, "punkt_wert_usd": 1.0}
W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USDT": 1.0, "BTC_USDT": 150.0},
     "max_range_punkte":     {"ETH_USDT": 40.0, "BTC_USDT": 3000.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "ziel_punkte": {"ETH_USDT": 30},
     "instrumente_aktiv": ["ETH_USDT"],
     "max_offene_positionen": 2,
     "risiko_pro_trade_usdt": 10.0,
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
        self.z = {"positionen": [], "letzter_lauf": None}
        handeln.kerzen_quelle = (
            lambda w, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])

    def tearDown(self):
        handeln.kerzen_quelle = None

    def test_kein_instrument_aktiv(self):
        w2 = dict(W, instrumente_aktiv=[])
        m = datetime(2026, 9, 13, 1, 0, tzinfo=timezone.utc)
        e = handeln.pruefe_einstieg(self.z, w2, m)
        self.assertEqual(e, [])

    def test_range_laeuft_noch(self):
        # um 00:15 ist die Range (bis 00:30) noch offen -> kein Einstieg
        m = datetime(2026, 9, 13, 0, 15, tzinfo=timezone.utc)
        e = handeln.pruefe_einstieg(self.z, W, m)
        self.assertEqual(e, [])
        self.assertEqual(self.z["positionen"], [])

    def test_long_einstieg(self):
        m = datetime(2026, 9, 13, 0, 45, tzinfo=timezone.utc)
        e = handeln.pruefe_einstieg(self.z, W, m)
        self.assertEqual(len(e), 1)
        self.assertEqual(len(self.z["positionen"]), 1)
        p = self.z["positionen"][0]
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

    def _zusatz_p(self, kurs, tag=None):
        return {"inst": "ETH_USDT", "richtung": "long",
                "einstieg": 100.4, "stop": 98.0, "ziel": 103.4,
                "tag": tag or date(2026, 9, 13), "letzter_kurs": kurs}

    def test_stop_long(self):
        z = {"positionen": [self._zusatz_p(97.5)], "letzter_lauf": None}
        geschlossen = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertEqual(len(geschlossen), 1)
        p, grund = geschlossen[0]
        self.assertEqual(grund, "stop")
        self.assertEqual(p["ausgang"], "stop")
        self.assertEqual(z["positionen"], [])

    def test_ziel_long(self):
        z = {"positionen": [self._zusatz_p(103.5)], "letzter_lauf": None}
        geschlossen = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertEqual(len(geschlossen), 1)
        p, grund = geschlossen[0]
        self.assertEqual(grund, "ziel")

    def test_offen_bleibt(self):
        z = {"positionen": [self._zusatz_p(101.0)], "letzter_lauf": None}
        geschlossen = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertEqual(geschlossen, [])
        self.assertEqual(len(z["positionen"]), 1)

    def test_tag_als_iso_string_aus_zustand(self):
        # zustand.json speichert tag als ISO-String - pruefe_ausstiege muss
        # das parsen (der Fehler vom 13.09.2026: TypeError im Dauerlauf).
        z = {"positionen": [self._zusatz_p(101.0, tag="2026-09-13")],
             "letzter_lauf": None}
        geschlossen = handeln.pruefe_ausstiege(z, W, self.JETZT)
        self.assertEqual(geschlossen, [])
        self.assertEqual(len(z["positionen"]), 1)


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
            ztl = {"ETH_USDT": merkzeichen} if merkzeichen else {}
            zustand = {"positionen": [{"inst": "ETH_USDT", "richtung": "long",
                                       "einstieg": 100.4, "stop": 98.0,
                                       "ziel": 103.4, "tag": "2026-09-13",
                                       "letzter_kurs": 103.5}],
                       "zuletzt_gehandelt_tag": ztl}
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
        self.assertEqual(nachher.get("positionen") or [], [])
        einstiege = [m for m in meldungen if "EINSTIEG" in m]
        self.assertEqual(einstiege, [], meldungen)

    def test_gegenprobe_ohne_merkzeichen_stiegt_wieder_ein(self):
        """Ohne Merkzeichen reproduziert sich der Fehler - der Test kann
        also den Fix beweisen und nicht nur mitschwimmen."""
        meldungen, nachher, _ = self._lauf(None)
        self.assertEqual(len(nachher.get("positionen") or []), 1)
        einstiege = [m for m in meldungen if "EINSTIEG" in m]
        self.assertEqual(len(einstiege), 1, meldungen)


class TestOrbEigenheiten(unittest.TestCase):
    """Was orb von orbk unterscheidet: Ziel aus ziel_punkte, kein Live-Pfad."""

    def test_ziel_aus_punkten(self):
        w = dict(W, ziel_modus="punkte", ziel_punkte={"ETH_USDT": 30})
        ziel = handeln.ziel_kurs(w, "ETH_USDT", "long", 2000.0, 20.0)
        self.assertEqual(ziel, 2030.0)
        ziel = handeln.ziel_kurs(w, "ETH_USDT", "short", 2000.0, 20.0)
        self.assertEqual(ziel, 1970.0)

    def test_ziel_aus_r_vielfachem(self):
        w = dict(W, ziel_modus="r_vielfaches", ziel_k=1.5)
        self.assertEqual(handeln.ziel_kurs(w, "ETH_USDT", "long", 2000.0, 20.0),
                         2030.0)

    def test_live_pfad_gesperrt_ohne_handel_erlaubt(self):
        """Seit dem Live-Umbau gibt es einen echten Live-Pfad: live_sperren
        nennt handel_erlaubt=false als Sperrgrund. Der Dauerlauf fragt nur
        nach einer Freigabe, wenn GENAU EIN Grund fehlt - und der ist das
        Freigabefenster (siehe test_live.py)."""
        w = dict(W, handel_erlaubt=False, freigabe={"erfuellt": True},
                 journal_zweitziel="Q:/x")
        with patch.object(handeln, "zeitfenster_offen", lambda: True), \
                patch.object(handeln.okxf, "schluessel_vorhanden",
                             lambda: True):
            gruende = handeln.live_sperren(w)
        self.assertIn("handel_erlaubt=false", "; ".join(gruende))


class TestMehrInstrumente(unittest.TestCase):
    """Erweiterung 14.10.2026: BTC_USDT + ETH_USDT parallel.

    Zwei Instrumente koennen gleichzeitig Positionen halten (max je ein
    Trade pro Tag UND Instrument), und ob ein Instrument heute gehandelt
    wurde blockiert das ANDERE nicht.
    """

    W2 = dict(W, instrumente_aktiv=["BTC_USDT", "ETH_USDT"],
              instrumente={"ETH_USDT": INST,
                           "BTC_USDT": {"okx": "BTC-USDT-SWAP", "zone": "UTC",
                                        "eroeffnung": "00:00", "session_ende": "24:00",
                                        "spread_punkte": 1.5, "punkt_wert_usdt": 1.0}},
              max_offene_positionen=2,
              mindest_range_punkte={"ETH_USDT": 1.0, "BTC_USDT": 1.0},
              max_range_punkte={"ETH_USDT": 40.0, "BTC_USDT": 40.0})
    JETZT = datetime(2026, 9, 13, 0, 45, tzinfo=timezone.utc)

    def tearDown(self):
        handeln.kerzen_quelle = None

    def test_zwei_instrumente_parallel(self):
        z = {"positionen": [], "letzter_lauf": None}
        # beide Instrumente liefern denselben Long-Breakout
        handeln.kerzen_quelle = (
            lambda w, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])
        geoeffnet = handeln.pruefe_einstieg(z, self.W2, self.JETZT)
        self.assertEqual(len(geoeffnet), 2, geoeffnet)
        self.assertEqual(len(z["positionen"]), 2)
        insts = {p["inst"] for p in z["positionen"]}
        self.assertEqual(insts, {"BTC_USDT", "ETH_USDT"})

    def test_ein_trade_pro_tag_und_instrument(self):
        # ETH schon heute gehandelt (Merkzeichen), BTC nicht -> nur BTC oeffnet
        z = {"positionen": [], "letzter_lauf": None,
             "zuletzt_gehandelt_tag": {"ETH_USDT": "2026-09-13"}}
        handeln.kerzen_quelle = (
            lambda w, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])
        geoeffnet = handeln.pruefe_einstieg(z, self.W2, self.JETZT)
        self.assertEqual(len(geoeffnet), 1, geoeffnet)
        self.assertEqual(geoeffnet[0]["inst"], "BTC_USDT")

    def test_max_offene_positionen_deckelt(self):
        # bei max_offene_positionen=1 oeffnet nur das erste Instrument
        w = dict(self.W2, max_offene_positionen=1)
        z = {"positionen": [], "letzter_lauf": None}
        handeln.kerzen_quelle = (
            lambda w_, key: _range_kerzen() + [_k(0, 30, 100.2, 100.5, 100.1, 100.4)])
        geoeffnet = handeln.pruefe_einstieg(z, w, self.JETZT)
        self.assertEqual(len(geoeffnet), 1, geoeffnet)
        self.assertEqual(len(z["positionen"]), 1)


class AltstandZeichenketteTest(unittest.TestCase):
    """Zustand aus der Zeit VOR "ein Trade je Instrument" darf nicht werfen.

    Befund 21.10.2026: `zuletzt_gehandelt_tag` stand als EINE Zeichenkette in
    zustand.json (so schreibt orbk es heute noch). `ztl.get()` darauf warf
    AttributeError, der Einstiegsweg brach ab, orb endete 37 h lang in JEDEM
    Zyklus mit Rueckgabe 1 - und weil der Zustand erst am Ende geschrieben
    wird, blieb auch `letzter_lauf` stehen. Der Fehler sah im Leitstand wie
    eine blosse Pause aus.
    """

    def test_zeichenkette_heute_hemmt(self):
        z = {"positionen": [], "zuletzt_gehandelt_tag": "2026-09-13"}
        self.assertTrue(handeln._schon_gehandelt_heute(
            z, "ETH_USDT", date(2026, 9, 13)))

    def test_zeichenkette_gestern_hemmt_nicht(self):
        z = {"positionen": [], "zuletzt_gehandelt_tag": "2026-09-12"}
        self.assertFalse(handeln._schon_gehandelt_heute(
            z, "ETH_USDT", date(2026, 9, 13)))

    def test_lade_zustand_ersetzt_zeichenkette_durch_dict(self):
        with tempfile.TemporaryDirectory() as w:
            zpfad = Path(w) / "zustand.json"
            zpfad.write_text(json.dumps({"positionen": [],
                                         "zuletzt_gehandelt_tag": "2026-10-20"}),
                             encoding="utf-8")
            with patch.object(handeln, "ZUSTAND", zpfad):
                z = handeln.lade_zustand()
        self.assertEqual(z["zuletzt_gehandelt_tag"], {})


if __name__ == "__main__":
    unittest.main()
