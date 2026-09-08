import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import handeln

HIER = Path(__file__).resolve().parent


def _basis_wachen():
    w = json.loads((HIER.parent / "wachen.json").read_text("utf-8"))
    w["instrument_aktiv"] = "US30_USD"
    w["instrumente"]["US30_USD"] = {
        "oanda": "US30_USD", "eroeffnung": "15:30", "zone": "Europe/Berlin",
        "cash_close": "22:00", "spread_punkte": 2.0, "punkt_wert_eur": 1.0}
    return w


class TestPositionsgroesse(unittest.TestCase):
    def setUp(self):
        # Monkeypatches greifen in gemeinsam genutzten Modulzustand (oanda) -
        # ohne Restore leckt das in test_oanda_* (Muster aus test_handeln_ausstieg).
        self.addCleanup(setattr, handeln.oanda, "instrument_details",
                        handeln.oanda.instrument_details)
        self.addCleanup(setattr, handeln.oanda, "konto_marge_frei",
                        handeln.oanda.konto_marge_frei)
        self.w = _basis_wachen()
        self.w["risiko_pro_trade_eur"] = 20
        self.w["hebel_deckel"] = 20
        handeln.oanda.instrument_details = lambda inst, live=False: {
            "minimumTradeSize": 1.0, "displayPrecision": 1, "pipLocation": 0,
            "marginRate": 0.05}
        handeln.oanda.konto_marge_frei = lambda live=False: 100000.0

    def test_units_aus_risiko_durch_stopabstand(self):
        # Stopabstand 40 Punkte, punkt_wert 1 EUR -> units = 20 / (40*1) = 0.5 -> abgerundet
        units, hebel = handeln.positionsgroesse(40000.0, 39960.0, self.w)
        self.assertLessEqual(units * 40 * 1.0, 20.0 + 1e-9)   # Risiko nie ueber Budget
        self.assertGreaterEqual(units, 0.0)

    def test_hebel_wird_gedeckelt_nicht_gesetzt(self):
        # winziger Stopabstand -> grosse Position -> Hebel muss auf Deckel begrenzt sein
        handeln.oanda.konto_marge_frei = lambda live=False: 50.0
        units, hebel = handeln.positionsgroesse(40000.0, 39999.0, self.w)
        self.assertLessEqual(hebel, self.w["hebel_deckel"] + 1e-6)

    def test_reale_groesse_risiko_nah_am_budget_und_hebel_gedeckelt(self):
        # Groessere Zahlen, damit units > 0 ist und der Deckel wirklich greift -
        # die beiden Tests oben laufen mit den Fixture-Zahlen degeneriert auf 0.
        self.w["risiko_pro_trade_eur"] = 500
        self.w["hebel_deckel"] = 20

        # (a) reichlich Marge -> kein Deckel. Stopabstand 45, roh 11.11 -> 11 units.
        handeln.oanda.konto_marge_frei = lambda live=False: 200000.0
        units, hebel = handeln.positionsgroesse(40000.0, 39955.0, self.w)
        risiko = units * 45 * 1.0
        self.assertGreater(units, 0.0)                        # echte Position
        self.assertLessEqual(risiko, 500.0 + 1e-9)            # nie ueber Budget
        self.assertGreater(risiko, 500.0 - 45.0)             # hoechstens 1 mts drunter
        self.assertLessEqual(hebel, 20.0 + 1e-6)

        # (b) knappe Marge -> Rohhebel ~88 > Deckel. Position wird geschrumpft,
        #     nicht auf 0 gesetzt.
        handeln.oanda.konto_marge_frei = lambda live=False: 5000.0
        units_c, hebel_c = handeln.positionsgroesse(40000.0, 39955.0, self.w)
        self.assertGreater(units_c, 0.0)                      # nicht genullt
        self.assertLess(units_c, units)                       # geschrumpft
        self.assertLessEqual(hebel_c, 20.0 + 1e-6)

    def test_stopabstand_null_gibt_null(self):
        self.assertEqual(handeln.positionsgroesse(40000.0, 40000.0, self.w),
                         (0.0, 0.0))


class TestBreakout(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, handeln.oanda, "kerzen", handeln.oanda.kerzen)
        self.w = _basis_wachen()

    def _eine_kerze(self, close, complete=True, zeit=None):
        z = zeit or datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc)
        handeln.oanda.kerzen = lambda inst, **kw: [
            {"zeit": z, "o": 1, "h": 1, "l": 1, "c": close, "complete": complete}]

    def test_long_wenn_schluss_ueber_hoch(self):
        self._eine_kerze(40120.0)
        sig = handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0)
        self.assertEqual(sig, ("long", 40120.0))

    def test_short_wenn_schluss_unter_tief(self):
        self._eine_kerze(39980.0)
        sig = handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0)
        self.assertEqual(sig, ("short", 39980.0))

    def test_kein_signal_wenn_innerhalb_range(self):
        self._eine_kerze(40050.0)
        self.assertIsNone(handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0))

    def test_kein_signal_wenn_kerze_unvollstaendig(self):
        self._eine_kerze(40120.0, complete=False)
        self.assertIsNone(handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0))

    def test_kein_signal_nach_letztem_einstieg(self):
        # Kerze weit in der Zukunft -> hinter letzter_einstieg -> ausgefiltert.
        self._eine_kerze(40120.0, zeit=datetime(2099, 1, 1, tzinfo=timezone.utc))
        self.assertIsNone(handeln.breakout_signal(self.w, hoch=40100.0, tief=40000.0))


class TestRundlauf(unittest.TestCase):
    """Ein voller Ein- und Ausstieg OHNE Kursbewegung kostet genau EINEN Spread
    je Runde - nicht 1,5 oder 2,0. Halber Spread als Aufschlag in der eur-Spalte
    des einstieg-Journals, halber Spread im _erloes_eur-Abzug beim Ausstieg,
    Ausstieg zu Mid. Deckungsgleich mit backtest.mit_kosten (Mid-zu-Mid, ein
    Spread). Der Suite fehlte bisher ein echter Einstieg->Ausstieg-Durchlauf."""

    def setUp(self):
        for attr in ("instrument_details", "konto_marge_frei", "kerzen", "preis"):
            self.addCleanup(setattr, handeln.oanda, attr, getattr(handeln.oanda, attr))
        self.addCleanup(setattr, handeln, "journal", handeln.journal)
        self.addCleanup(setattr, handeln.sess, "zwangsschluss", handeln.sess.zwangsschluss)
        self.S = 4.0
        self.pw = 1.0
        self.w = _basis_wachen()
        self.w["instrumente"]["US30_USD"]["spread_punkte"] = self.S
        self.w["instrumente"]["US30_USD"]["punkt_wert_eur"] = self.pw
        self.w["risiko_pro_trade_eur"] = 600
        self.w["hebel_deckel"] = 50
        handeln.oanda.instrument_details = lambda inst, live=False: {
            "minimumTradeSize": 1.0, "displayPrecision": 1, "pipLocation": 0,
            "marginRate": 0.05}
        handeln.oanda.konto_marge_frei = lambda live=False: 1e9
        self._rows = []
        handeln.journal = lambda *f: self._rows.append(tuple(f))

    def _feed(self, bruch_close):
        konf = self.w["instrumente"]["US30_USD"]
        heute = handeln.sess.handelstag(datetime.now(timezone.utc), konf["zone"])
        start, ende = handeln.sess.opening_range_fenster(konf, heute)
        r = {"zeit": start, "o": 40050, "h": 40100, "l": 40000, "c": 40050, "complete": True}
        brk = {"zeit": ende, "o": 40050, "h": max(bruch_close, 40100.0),
               "l": min(bruch_close, 40000.0), "c": bruch_close, "complete": True}
        handeln.oanda.kerzen = lambda inst, **kw: [dict(r), dict(r), brk]
        # Mid unveraendert = Bruch-Schlusskurs: keine Kursbewegung.
        handeln.oanda.preis = lambda inst, live=False: {
            "bid": bruch_close - self.S / 2, "ask": bruch_close + self.S / 2,
            "spread_punkte": self.S}

    def _runde_gv(self, bruch_close):
        self._feed(bruch_close)
        z = {"positionen": [], "letzte_stops": {}, "letzter_lauf": None, "modus": "papier"}
        handeln.pruefe_einstieg(z, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 1, "Einstieg hat nicht gefeuert")
        # ERST jetzt Zwangsschluss in die Vergangenheit ziehen - so feuert der
        # Ausstieg ohne Kursbewegung, ohne dabei sess.letzter_einstieg (das
        # zwangsschluss aufruft) waehrend des Einstiegs zu verbiegen.
        handeln.sess.zwangsschluss = lambda ik, tag: datetime(2000, 1, 1, tzinfo=timezone.utc)
        handeln.pruefe_ausstiege(z, self.w, live=False)
        self.assertEqual(z["positionen"], [], "Ausstieg hat nicht gefeuert")
        ein = next(r for r in self._rows if r[2] == "einstieg")
        aus = next(r for r in self._rows if r[2] == "ausstieg")
        einsatz, erloes, units = float(ein[6]), float(aus[6]), float(ein[7])
        return erloes - einsatz, units      # gv der Runde wie wachen_orb.runden_aus_journal

    def test_long_runde_kostet_genau_einen_spread(self):
        gv, units = self._runde_gv(40120.0)
        self.assertGreater(units, 0.0)
        self.assertAlmostEqual(gv, -self.S * self.pw * units, places=6)

    def test_short_runde_kostet_genau_einen_spread(self):
        gv, units = self._runde_gv(39880.0)
        self.assertGreater(units, 0.0)
        self.assertAlmostEqual(gv, -self.S * self.pw * units, places=6)


if __name__ == "__main__":
    unittest.main()
