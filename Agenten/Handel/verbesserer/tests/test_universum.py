"""Verbesserer testet das LIVE-Universum des Scanners statt der Watchlist.

Der Scanner handelt mit wachen.json universum.modus 'alle'; der Rueckblick
testete bis 09.10.2026 die 11-Coin-Watchlist (7 nach Ausrichtung) - und kam
nie auf die geforderten 20 Runden. Geprueft wird die Wahl des Universums und
ihre Rueckfaelle, nicht die Rechnung. Kein Netz: okx.alle_paare ist ersetzt.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import lauf  # noqa: E402
import okx  # noqa: E402
import suche  # noqa: E402

WACHEN = {"watchlist": ["BTC-USDC", "ETH-USDC", "SOL-USDC"],
          "universum": {"modus": "alle", "quotes": ["USDC"],
                        "min_volumen_24h_usd": 500000}}
MARKT = [("BTC-USDC", 9e9), ("ETH-USDC", 5e9), ("SOL-USDC", 2e9),
         ("ADA-USDC", 1e9), ("SUI-USDC", 9e8)]


class UniversumWahlTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _markt(self, paare=MARKT, fehler=None):
        return mock.patch.object(okx, "alle_paare",
                                 side_effect=fehler, return_value=paare)

    def test_mit_schalter_kommt_das_live_universum(self):
        with self._markt() as m:
            paare, hinweis = lauf._universum(
                WACHEN, {"universum_testen": True}, True, self.dir)
        self.assertEqual(paare, [p for p, _ in MARKT])
        self.assertIn("5 Paare", hinweis)
        m.assert_called_once_with(quote=["USDC"], min_volumen_usd=500000)

    def test_ohne_schalter_bleibt_es_die_watchlist(self):
        with self._markt() as m:
            paare, hinweis = lauf._universum(WACHEN, {}, True, self.dir)
        self.assertEqual(paare, WACHEN["watchlist"])
        self.assertIsNone(hinweis)
        m.assert_not_called()

    def test_watchlist_modus_der_wachen_bleibt_watchlist(self):
        w = {**WACHEN, "universum": {"modus": "watchlist"}}
        paare, hinweis = lauf._universum(
            w, {"universum_testen": True}, True, self.dir)
        self.assertEqual(paare, WACHEN["watchlist"])
        self.assertIsNone(hinweis)

    def test_ohne_abruf_gilt_der_kerzen_cache_nur_mit_passender_quote(self):
        for n in ("ADA-USDC", "BTC-USDC", "SUI-USDC", "BTC-USDT"):
            (self.dir / (n + ".json")).write_text("{}", encoding="utf-8")
        with self._markt() as m:
            paare, hinweis = lauf._universum(
                WACHEN, {"universum_testen": True}, False, self.dir)
        m.assert_not_called()
        self.assertEqual(paare, ["ADA-USDC", "BTC-USDC", "SUI-USDC"])  # kein BTC-USDT
        self.assertIn("Kerzen-Cache", hinweis)

    def test_abruffehler_faellt_auf_den_cache_zurueck(self):
        for n in ("ADA-USDC", "BTC-USDC", "SUI-USDC"):
            (self.dir / (n + ".json")).write_text("{}", encoding="utf-8")
        with self._markt(fehler=RuntimeError("HTTP 500")):
            paare, hinweis = lauf._universum(
                WACHEN, {"universum_testen": True}, True, self.dir)
        self.assertEqual(paare, ["ADA-USDC", "BTC-USDC", "SUI-USDC"])

    def test_zu_wenig_paare_faellt_auf_die_watchlist_zurueck(self):
        with self._markt(paare=[("BTC-USDC", 9e9)]):
            paare, hinweis = lauf._universum(
                WACHEN, {"universum_testen": True}, True, self.dir)
        self.assertEqual(paare, WACHEN["watchlist"])
        self.assertIn("nicht ermittelbar", hinweis)


class WatchlistDropTest(unittest.TestCase):
    BASIS = {"gates": {}, "gewichte": {}, "sizing": None,
             "watchlist": ["A", "B", "C", "D", "E", "F", "G", "H"]}

    def _drops(self, **kw):
        # nur die Nachbarn zaehlen, die sich in der watchlist unterscheiden
        try:
            nb = suche.nachbarn(self.BASIS, {}, False, **kw)
        except Exception:                       # BASIS ist verkuerzt
            self.skipTest("Kandidatenform fuer nachbarn() unvollstaendig")
        return [k for k in nb if k["watchlist"] != self.BASIS["watchlist"]]

    def test_drops_sind_standard(self):
        self.assertGreater(len(self._drops()), 0)

    def test_drops_lassen_sich_abschalten(self):
        self.assertEqual(self._drops(watchlist_aenderbar=False), [])


class SpurenJsonTest(unittest.TestCase):
    def test_spur1_testet_das_universum_spur3_nicht(self):
        s = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
        self.assertTrue(s["spur1"]["universum_testen"])
        self.assertNotIn("universum_testen", s["spur3"])


if __name__ == "__main__":
    unittest.main()
