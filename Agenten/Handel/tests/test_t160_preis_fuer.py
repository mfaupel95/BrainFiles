"""Tests fuer T-160: Positionen behalten ihren Kurs ueber den Symbolwechsel.

Zwei Ebenen:
  * `moondev_daten.symbol_kurs` / `binance_symbol_kurs` - OFFLINE, der Abruf
    ist gepatcht. Geprueft wird die Reihenfolge (Binance zuerst, CoinGecko
    ueber ID-Cache bzw. /search, None wenn nichts hergibt) - nie ein Netz.
  * `spur_buch.zyklus(preis_fuer=...)` - die Verdrahtung: eine offene
    Position, deren Symbol aus dem Feed gefallen ist, bekommt ihren Kurs
    wieder und wird geschlossen, statt ewig offen zu bleiben.
"""

import csv
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for _p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import moondev_daten as daten  # noqa: E402
import spur_buch as buch  # noqa: E402

WACHEN = {
    "waehrung": "USD", "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0, "max_offene_positionen": 3,
    "max_pro_trade_usd": 100.0, "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 450.0, "stop_prozent": 8.0,
    "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 1.5, "drawdown_halbierung_usd": 15.0,
}


def _patche_hole_json(abruf):
    """hole_json gegen eine Tabelle tauschen: {url-Teil: Antwort}."""
    original = daten.hole_json

    def ersatz(url, zeitgrenze=daten.ZEITGRENZE):
        for teil, antwort in abruf.items():
            if teil in url:
                if isinstance(antwort, Exception):
                    raise antwort
                return antwort
        raise AssertionError("unerwarteter Abruf: %s" % url)

    daten.hole_json = ersatz
    return original


class SymbolKursTest(unittest.TestCase):
    """symbol_kurs / binance_symbol_kurs - ohne Netz."""

    def setUp(self):
        self.alt_hole_json = daten.hole_json
        self.alt_ids = dict(daten._SYMBOL_IDS)
        daten._SYMBOL_IDS.clear()

    def tearDown(self):
        daten.hole_json = self.alt_hole_json
        daten._SYMBOL_IDS.clear()
        daten._SYMBOL_IDS.update(self.alt_ids)

    def test_binance_liefert_und_spart_coingecko(self):
        original = _patche_hole_json({
            "ticker/price?symbol=BTCUSDT": {"symbol": "BTCUSDT",
                                             "price": "85000.10"},
        })
        try:
            self.assertAlmostEqual(daten.symbol_kurs("BTC"), 85000.10)
            self.assertEqual(daten._SYMBOL_IDS, {})   # kein Search noetig
        finally:
            daten.hole_json = original

    def test_coingecko_ueber_id_cache(self):
        # Coin gibt es auf Binance nicht (das Thema der Listingarb-Spur):
        # der Binance-Ticker meldet 404, dann greift CoinGecko.
        daten._SYMBOL_IDS["XYZ"] = "xyz-coin"
        original = _patche_hole_json({
            "ticker/price?symbol=XYZUSDT":
                __import__("urllib").error.HTTPError(
                    "url", 400, "Invalid symbol", {}, None),
            "simple/price": {"xyz-coin": {"usd": 1.2345}},
        })
        try:
            self.assertAlmostEqual(daten.symbol_kurs("XYZ"), 1.2345)
        finally:
            daten.hole_json = original

    def test_coingecko_ueber_search_rueckfall(self):
        original = _patche_hole_json({
            "ticker/price?symbol=ABCUSDT":
                __import__("urllib").error.HTTPError(
                    "url", 400, "Invalid symbol", {}, None),
            "/search?query=ABC": {"coins": [{"id": "abc-token",
                                             "symbol": "abc"}]},
            "simple/price": {"abc-token": {"usd": 9.0}},
        })
        try:
            self.assertAlmostEqual(daten.symbol_kurs("ABC"), 9.0)
            # zweite Abfrage laeuft dann aus dem Cache
            self.assertEqual(daten._SYMBOL_IDS.get("ABC"), "abc-token")
        finally:
            daten.hole_json = original

    def test_unbekanntes_symbol_gibt_none(self):
        original = _patche_hole_json({
            "ticker/price?symbol=NONEUSDT":
                __import__("urllib").error.HTTPError(
                    "url", 400, "Invalid symbol", {}, None),
            "/search?query=NONE": {"coins": []},
        })
        try:
            self.assertIsNone(daten.symbol_kurs("NONE"))
        finally:
            daten.hole_json = original

    def test_leerer_symbolname_gibt_none(self):
        self.assertIsNone(daten.symbol_kurs(""))
        self.assertIsNone(daten.symbol_kurs(None))

    def test_maerkte_fuellt_id_cache_nebenbei(self):
        original = _patche_hole_json({
            "/coins/markets": [{"id": "solana", "symbol": "sol"}],
        })
        try:
            daten.maerkte(anzahl=1)
            self.assertEqual(daten._SYMBOL_IDS.get("SOL"), "solana")
        finally:
            daten.hole_json = original


class PreisFuerVerdrahtungTest(unittest.TestCase):
    """Die zyklus-Verdrahtung: Position ohne Feed-Symbol bekommt den Kurs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wachen_pfad, zustand_pfad, journal_pfad = buch.pfade(self.tmp.name)
        with open(wachen_pfad, "w", encoding="utf-8") as f:
            json.dump(WACHEN, f)
        z = buch.lade_zustand(zustand_pfad)
        z["positionen"] = [{
            "inst": "XYZ", "seite": "long", "einstieg": 100.0,
            "stop": 92.0, "ziel": 115.0, "stop_pct": 8.0,
            "nominal": 50.0, "modus": "papier", "pos_id": "t160",
            "eroeffnet_zeit": "2026-10-07T00:00:00+00:00",
        }]
        buch.schreibe_zustand(zustand_pfad, z)
        self.addCleanup(self.tmp.cleanup)

    def _journal_zeilen(self):
        _, _, journal_pfad = buch.pfade(self.tmp.name)
        with open(journal_pfad, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_position_ohne_feed_symbol_wird_geschlossen(self):
        # Der Feed liefert nur noch AAA - XYZ ist gefallen. preis_fuer rettet
        # den Kurs (unter dem Stop), der Zyklus schliesst die Position.
        alt = buch.zeit_quelle
        buch.zeit_quelle = lambda: "2026-10-07T12:00:00+00:00"
        self.addCleanup(setattr, buch, "zeit_quelle", alt)
        code = buch.zyklus(
            self.tmp.name,
            lambda w: ({"AAA": {}}, {}, []),
            lambda d, w: None, "papier", "test",
            preis_fuer=lambda inst: 90.0 if inst == "XYZ" else None)
        self.assertEqual(code, 0)
        zeilen = self._journal_zeilen()
        verkauf = [z for z in zeilen if z["aktion"] == "verkauf"
                   and z["inst"] == "XYZ"]
        self.assertEqual(len(verkauf), 1, "Position wurde nicht geschlossen")
        self.assertEqual(verkauf[0]["grund"], "stop")
        self.assertEqual(verkauf[0]["pos_id"], "t160")
        _, zustand_pfad, _ = buch.pfade(self.tmp.name)
        self.assertEqual(buch.lade_zustand(zustand_pfad)["positionen"], [])

    def test_ohne_preis_fuer_bleibt_position_offen_mit_meldung(self):
        # Gegenprobe: ohne preis_fuer bleibt die Position offen (der alte
        # T-160-Zustand) - nur die Gegenprobe beweist, dass der Test den Fix
        # misst und nicht den Zufall.
        alt = buch.zeit_quelle
        buch.zeit_quelle = lambda: "2026-10-07T12:00:00+00:00"
        self.addCleanup(setattr, buch, "zeit_quelle", alt)
        buch.zyklus(self.tmp.name,
                    lambda w: ({"AAA": {}}, {}, []),
                    lambda d, w: None, "papier", "test")
        _, zustand_pfad, _ = buch.pfade(self.tmp.name)
        rest = buch.lade_zustand(zustand_pfad)["positionen"]
        self.assertEqual(len(rest), 1)
        self.assertEqual(rest[0]["inst"], "XYZ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
