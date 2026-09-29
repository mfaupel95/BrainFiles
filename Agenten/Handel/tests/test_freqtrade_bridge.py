"""Tests fuer `freqtrade_bridge` - die Bruecke zum lokalen FreqTrade-Bot.

Drei Teile:
  * KEIN Netz: `urlopen` wird durch Doubles ersetzt (Adresse, Anmeldung,
    Fehlerfaelle, Kurzlage offline).
  * Quelltext per AST: nur GET, kein Handels-Endpunkt freigegeben.
  * Live gegen 127.0.0.1:8080 - wird uebersprungen, wenn der Bot nicht laeuft.

Aufruf aus `Agenten/Handel/tests`:
    ..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_freqtrade_bridge
"""

import ast
import base64
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import freqtrade_bridge as ft  # noqa: E402

ZUGANG = ("http://127.0.0.1:8080", "max", "geheim")


class Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def antwort(daten):
    return Antwort(json.dumps(daten).encode("utf-8"))


class HoleTest(unittest.TestCase):

    def test_adresse_methode_und_anmeldung(self):
        gesehen = []

        def urlopen(anfrage, timeout):
            gesehen.append(anfrage)
            return antwort({"status": "pong"})

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            self.assertEqual(ft.hole("trades", ZUGANG, limit=5), {"status": "pong"})
        anfrage = gesehen[0]
        self.assertEqual(anfrage.full_url, "http://127.0.0.1:8080/api/v1/trades?limit=5")
        self.assertEqual(anfrage.get_method(), "GET")
        erwartet = "Basic " + base64.b64encode(b"max:geheim").decode()
        self.assertEqual(anfrage.get_header("Authorization"), erwartet)

    def test_unbekannter_endpunkt_wird_abgelehnt(self):
        for name in ("forceenter", "forceexit", "start", "stop", "../status"):
            with self.assertRaises(ValueError):
                ft.hole(name, ZUGANG)

    def test_http_fehler_wird_freqtradefehler(self):
        def urlopen(anfrage, timeout):
            raise urllib.error.HTTPError(anfrage.full_url, 401, "Unauthorized", {}, None)

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            with self.assertRaisesRegex(ft.FreqtradeFehler, "401"):
                ft.hole("status", ZUGANG)

    def test_verbindungsabbruch_wird_freqtradefehler(self):
        def urlopen(anfrage, timeout):
            raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            with self.assertRaisesRegex(ft.FreqtradeFehler, "nicht erreichbar"):
                ft.hole("ping", ZUGANG)


class ZugangTest(unittest.TestCase):

    def test_aus_bot_konfiguration(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "config.json")
            with open(pfad, "w", encoding="utf-8") as f:
                json.dump({"api_server": {"username": "u", "password": "p"}}, f)
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(ft.zugang(pfad), ("http://127.0.0.1:8080", "u", "p"))

    def test_umgebung_geht_vor(self):
        umgebung = {"FREQTRADE_URL": "http://h:1/", "FREQTRADE_USER": "a",
                    "FREQTRADE_PASSWORD": "b"}
        with mock.patch.dict(os.environ, umgebung, clear=True):
            self.assertEqual(ft.zugang(os.devnull + "_fehlt"), ("http://h:1", "a", "b"))


class LageTest(unittest.TestCase):

    def test_offline_wirft_nicht(self):
        def urlopen(anfrage, timeout):
            raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            lage = ft.lage(ZUGANG)
        self.assertFalse(lage["erreichbar"])
        self.assertIn("nicht erreichbar", lage["fehler"])

    def test_verdichtet_die_antworten(self):
        daten = {
            "show_config": {"dry_run": True, "state": "running", "exchange": "binance",
                            "strategy": "SampleStrategy", "timeframe": "5m",
                            "stake_currency": "USDT"},
            "profit": {"trade_count": 4, "profit_closed_coin": 12.5, "profit_all_coin": 10.0},
            "balance": {"stake": "USDT", "total": 10010.0},
            "status": [{"trade_id": 1}, {"trade_id": 2}],
        }

        def urlopen(anfrage, timeout):
            endpunkt = anfrage.full_url.split("/api/v1/")[1].split("?")[0]
            return antwort(daten[endpunkt])

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            lage = ft.lage(ZUGANG)
        self.assertEqual(lage["offene_trades"], 2)
        self.assertEqual(lage["trades_gesamt"], 4)
        self.assertEqual(lage["guthaben"], 10010.0)
        self.assertTrue(lage["dry_run"])
        self.assertEqual(lage["strategie"], "SampleStrategy")


class NurLesendTest(unittest.TestCase):
    """Am Quelltext: keine Handels-Endpunkte, keine andere Methode als GET."""

    def setUp(self):
        with open(ft.__file__, encoding="utf-8") as f:
            self.baum = ast.parse(f.read())

    def test_keine_handelsendpunkte_freigegeben(self):
        verboten = {"forceenter", "forcebuy", "forceexit", "forcesell", "start",
                    "stop", "stopbuy", "stopentry", "reload_config", "blacklist",
                    "delete_trade", "cancel_open_order"}
        self.assertFalse(verboten & ft.ERLAUBT)

    def test_nur_get(self):
        methoden = [kw.value.value for knoten in ast.walk(self.baum)
                    if isinstance(knoten, ast.Call)
                    for kw in knoten.keywords
                    if kw.arg == "method" and isinstance(kw.value, ast.Constant)]
        self.assertEqual(methoden, ["GET"])

    def test_kein_schreibzugriff_auf_dateien(self):
        for knoten in ast.walk(self.baum):
            if (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                    and knoten.func.id == "open" and len(knoten.args) > 1):
                modus = knoten.args[1]
                if isinstance(modus, ast.Constant):
                    self.assertEqual(modus.value, "r")


def _bot_laeuft():
    try:
        ft.hole("ping", zeitgrenze=2)
        return True
    except (ft.FreqtradeFehler, OSError):
        return False


@unittest.skipUnless(_bot_laeuft(), "FreqTrade-Bot auf 127.0.0.1:8080 laeuft nicht")
class LiveTest(unittest.TestCase):

    def test_lage_vom_echten_bot(self):
        lage = ft.lage()
        self.assertTrue(lage["erreichbar"], lage)
        self.assertTrue(lage["dry_run"], "Bot laeuft NICHT im Probebetrieb")
        self.assertEqual(lage["zustand"], "running")


if __name__ == "__main__":
    unittest.main()
