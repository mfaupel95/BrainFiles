"""Tests fuer lesen.py - der Pump.fun-Leser, ohne Netz.

Geprueft werden die zwei Sicherheitsnetze (Schreibversuche werden verweigert,
bevor eine Verbindung aufgebaut wird), die Fehleruebersetzung (HTTP, kein
JSON) und die Normalisierung der Antworten (Feldnamen-Falle priceUSD vs
priceUsd, ISO-Zeit, Kettenfilter). Jeder Netzaufruf ist gemockt.

Aufruf:  python -m unittest discover -s tests   (im Ordner kopier/)
"""

import io
import json
import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
KOPIER = os.path.dirname(HIER)
if KOPIER not in sys.path:
    sys.path.insert(0, KOPIER)

import lesen                                                  # noqa: E402


def antwort(daten):
    """Ein urlopen-Ersatz, der JSON zurueckgibt."""
    class Antwort:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(daten).encode("utf-8")

    return Antwort()


class Waechter(unittest.TestCase):
    def test_methode_mit_schreibwort_wird_verweigert(self):
        with self.assertRaises(lesen.Schreibversuch):
            lesen.ruf("https://frontend-api-v3.pump.fun/pnl-leaderboard",
                      methode="swap")

    def test_unbekannter_host_wird_verweigert(self):
        with self.assertRaises(lesen.Schreibversuch):
            lesen.ruf("https://example.com/pnl-leaderboard")

    def test_pfad_ausserhalb_whitelist_wird_verweigert(self):
        for url in ("https://frontend-api-v3.pump.fun/order/123",
                    "https://frontend-api-v3.pump.fun/trades",
                    "https://swap-api.pump.fun/v1/transfer",
                    "https://frontend-api-v3.pump.fun/user-portfolio/../swap"):
            with self.assertRaises(lesen.Schreibversuch, msg=url):
                lesen.ruf(url)

    def test_post_nur_trades_batch(self):
        # POST auf einen anderen v1-Pfad ist kein Leseaufruf.
        with self.assertRaises(lesen.Schreibversuch):
            lesen.ruf("https://swap-api.pump.fun/v1/coins/X/market-activity",
                      methode="POST", daten={})

    def test_post_trades_batch_ist_erlaubt(self):
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort({"W": []})):
            d = lesen.trade_batch("MINT", ["W"])
        self.assertEqual(d, {"W": []})

    def test_lesen_weiss_wozu_schreibbefehl_da_ist(self):
        self.assertTrue(lesen.SCHREIBBEFEHLE)


class Fehler(unittest.TestCase):
    def test_http_fehler_wird_lesefehler(self):
        import urllib.error
        fehler = urllib.error.HTTPError("http://x", 404, "nf", {}, None)
        with patch.object(lesen.urllib.request, "urlopen",
                          side_effect=fehler):
            with self.assertRaises(lesen.Lesefehler) as ctx:
                lesen.ruf("https://frontend-api-v3.pump.fun/pnl-leaderboard")
        self.assertIn("404", str(ctx.exception))

    def test_kein_json_wird_lesefehler(self):
        class KeinJson:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"<html>kein json</html>"

        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=KeinJson()):
            with self.assertRaises(lesen.Lesefehler):
                lesen.ruf("https://frontend-api-v3.pump.fun/coins/X")


class Normalisierung(unittest.TestCase):
    def test_iso_ms_mit_z(self):
        from datetime import datetime, timezone
        erwartet = int(datetime(2026, 9, 14, 20, 24, 45,
                                tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(lesen._iso_ms("2026-09-14T20:24:45.000Z"), erwartet)
        self.assertEqual(lesen._iso_ms("2026-09-14T20:24:45Z"), erwartet)

    def test_iso_ms_kaputt_ist_none(self):
        self.assertIsNone(lesen._iso_ms("kein datum"))
        self.assertIsNone(lesen._iso_ms(""))

    def test_kette_aus_chainid(self):
        self.assertEqual(lesen._kette_aus_chainid(1399811149), "solana")
        self.assertIsNone(lesen._kette_aus_chainid(4663))

    def test_leaderboard_wird_entries(self):
        d = {"entries": [{"rank": 1, "walletAddress": "W1",
                          "username": "Trader", "pnlUsd": 100.0}]}
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort(d)):
            e = lesen.leaderboard(periode="daily", limit=1)
        self.assertEqual(e[0]["username"], "Trader")
        self.assertEqual(e[0]["pnlUsd"], 100.0)

    def test_portfolio_normalisiert_und_filtert(self):
        d = {"positions": [
            {"coinMint": "SOLTOKEN", "chainId": 1399811149,
             "tokenPriceUsd": 0.5,
             "coin": {"symbol": "X", "marketCapUsd": 100000.0},
             "valueUsd": 100.0, "isExited": False},
            {"coinMint": "EVMMINT", "chainId": 4663,
             "tokenPriceUsd": 1.0,
             "coin": {"symbol": "E", "marketCapUsd": 5000.0},
             "isExited": False},
        ]}
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort(d)):
            pf = lesen.portfolio("W")
        pos = pf["positions"]
        self.assertEqual(pos["SOLTOKEN"]["kette"], "solana")
        self.assertEqual(pos["SOLTOKEN"]["preis"], 0.5)
        self.assertEqual(pos["EVMMINT"]["kette"], None)

    def test_batch_feldnamen_priceUSD(self):
        d = {"W": [{"tx": "TX1", "type": "buy",
                    "timestamp": "2026-09-14T20:24:45.000Z",
                    "priceUSD": "0.0708",
                    "amountUSD": "1.04"}]}
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort(d)):
            kaeufe = lesen.letzter_kauf("MINT", ["W"])
        k = kaeufe["W"]
        self.assertEqual(k["typ"], "buy")
        self.assertEqual(k["preis"], 0.0708)
        self.assertEqual(k["zeit_ms"], 1789417485000)

    def test_v2_preise_liest_priceUsd(self):
        d = {"trades": [{"type": "sell", "timestamp": "2026-09-14T20:36:00Z",
                         "priceUsd": "0.071288984713167654"}]}
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort(d)):
            kurse = lesen.preise([("solana", "MINT")])
        self.assertAlmostEqual(kurse[("solana", "MINT")], 0.07128898471316)

    def test_risiko_stufen(self):
        # 'blockiert' statt 'gesperrt': das ist ein Filterwort des
        # Dauerlaufs und gehoert nicht in Ablehnungszeilen.
        for roh, erwartet in (({"is_banned": True}, "blockiert"),
                              ({"nsfw": True}, "blockiert"),
                              ({}, "ok")):
            with patch.object(lesen.urllib.request, "urlopen",
                              return_value=antwort(roh)):
                r = lesen.risiko("MINT")
            self.assertEqual(r["stufe"], erwartet, msg=str(roh))

    def test_letzter_kauf_nimmt_nur_buy(self):
        d = {"W": [{"tx": "T2", "type": "sell",
                    "timestamp": "2026-09-14T20:30:00.000Z",
                    "priceUSD": "0.09"},
                   {"tx": "T1", "type": "buy",
                    "timestamp": "2026-09-14T20:20:00.000Z",
                    "priceUSD": "0.07"}]}
        with patch.object(lesen.urllib.request, "urlopen",
                          return_value=antwort(d)):
            kaeufe = lesen.letzter_kauf("MINT", ["W"])
        self.assertEqual(kaeufe["W"]["tx"], "T1")


if __name__ == "__main__":
    unittest.main()