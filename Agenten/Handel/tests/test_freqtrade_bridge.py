"""Tests fuer `freqtrade_bridge` - die Bruecke zum lokalen FreqTrade-Bot.

Drei Teile:
  * KEIN Netz: `urlopen` wird durch Doubles ersetzt (Adresse, Anmeldung,
    Fehlerfaelle, Kurzlage offline, Bot-Liste, Uebersicht).
  * Quelltext per AST: nur GET, kein Handels-Endpunkt freigegeben.
  * Live gegen die Bot-Liste aus `freqtrade/bots.json` - wird uebersprungen,
    wenn kein Bot aus dieser Liste antwortet. Die fruehere Fassung pruefte
    nur die feste Adresse 8080 und uebersprang auch dann, wenn drei Bots
    auf 8081-8083 liefen.

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


class BotsTest(unittest.TestCase):
    """Die Bot-Liste kommt aus freqtrade/bots.json - einer Wahrheit mit bots.py."""

    def test_echte_datei_zeigt_die_Bots_aus_bots_json(self):
        """Was die Bruecke nennt, ist genau der Inhalt von bots.json - keine zweite Liste.

        Die Zahl der Bots ist keine Eigenschaft (sie wachst mit jedem neuen
        Aufsatz), die Uebereinstimmung MIT der Datei ist die Regel.
        """
        with open(ft.BOTS_KONFIG, encoding="utf-8") as f:
            inhalt = json.load(f)
        erwartet = [(b["name"], int(b["port"])) for b in inhalt.get("bots") or []]
        self.assertTrue(erwartet, "bots.json nennt keine Bots")
        self.assertEqual([(b["name"], b["port"]) for b in ft.bots()], erwartet)

    def test_porte_sind_verschieden(self):
        # Zwei Bots auf einem Port koennten nicht beide antworten: die Liste
        # waere dann kaputt, nicht die Boerse.
        liste = ft.bots()
        self.assertEqual(len(liste), len({b["port"] for b in liste}))

    def test_fehlende_datei_ist_leere_liste(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ft.bots(os.path.join(os.sep, "gibt", "es", "nicht.json")),
                             [])

    def test_kaputter_eintrag_wird_ausgelassen(self):
        """Ohne Port kein Bot - erfunden wird keine Adresse."""
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "bots.json")
            with open(pfad, "w", encoding="utf-8") as f:
                json.dump({"bots": [{"name": "ohne-port"},
                                    {"port": 9091},
                                    {"name": "gut", "port": "9092",
                                     "strategie": "S", "zeitrahmen": "1h"}]}, f)
            self.assertEqual(ft.bots(pfad),
                             [{"name": "gut", "port": 9092, "strategie": "S",
                               "zeitrahmen": "1h", "container": "",
                               "max_open_trades": None, "hausspur": ""}])

    def test_json_muell_ist_leere_liste(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "bots.json")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write("{nicht json")
            self.assertEqual(ft.bots(pfad), [])


class ZugangFuerTest(unittest.TestCase):
    """Port vom Bot, Anmeldung vom AUFSATZ, sonst von der Basis-config.

    Die Aufsatz-Dateien config.<name>.json tragen eigene Zufallspasswoerter,
    die die Container seit dem Umbau akzeptieren (gemessen 02.10.2026:
    show_config 200 mit dem Aufsatz-Passwort, 401 mit dem Basis-Passwort auf
    8081-8083). Fehlt der Aufsatz, gilt die Basis-config.json - der Test
    deckt genau diesen Rueckfall ab.
    """

    def test_port_wird_ersetzt_anmeldung_behalten(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = os.path.join(ordner, "config.json")
            with open(pfad, "w", encoding="utf-8") as f:
                json.dump({"api_server": {"listen_port": 8080,
                                          "username": "max", "password": "basis"}}, f)
            with mock.patch.dict(os.environ, {}, clear=True):
                url, benutzer, passwort = ft.zugang_fuer(8082, pfad)
        self.assertEqual(url, "http://127.0.0.1:8082")
        self.assertEqual((benutzer, passwort), ("max", "basis"))

    def test_umgebung_url_behaelt_ihren_Rechner(self):
        with mock.patch.dict(os.environ,
                             {"FREQTRADE_URL": "http://127.0.0.1:9999/",
                              "FREQTRADE_USER": "a", "FREQTRADE_PASSWORD": "b"},
                             clear=True):
            url, benutzer, passwort = ft.zugang_fuer(8083)
        self.assertEqual(url, "http://127.0.0.1:8083")
        self.assertEqual((benutzer, passwort), ("a", "b"))


class UebersichtTest(unittest.TestCase):
    """Eine Zeile je Bot, auch fuer den nicht erreichbaren - und nie eine exception."""

    LISTE = [{"name": "laufend", "port": 8081, "strategie": "S1",
              "zeitrahmen": "1h", "max_open_trades": 3},
             {"name": "tot", "port": 8082, "strategie": "S2",
              "zeitrahmen": "1h", "max_open_trades": 1}]

    def _antworten(self, endpunkt):
        antworten = {"show_config": {"dry_run": True, "state": "running"},
                     "count": {"current": 2, "max": 3},
                     "profit": {"trade_count": 12, "profit_closed_coin": -3.5}}
        if endpunkt in antworten:
            return antworten[endpunkt]
        raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))

    def test_pro_bot_eine_zeile(self):
        def urlopen(anfrage, timeout):
            # http://127.0.0.1:8081/api/v1/show_config -> (8081, show_config)
            nach_adresse = anfrage.full_url.split("/api/v1/", 1)
            host = nach_adresse[0].split("//", 1)[1].split("/", 1)[0]
            endpunkt = nach_adresse[1].split("?", 1)[0]
            if int(host.rsplit(":", 1)[1]) != 8081:
                raise urllib.error.URLError(ConnectionRefusedError(10061, "refused"))
            return antwort(self._antworten(endpunkt))

        with mock.patch.object(ft.urllib.request, "urlopen", urlopen):
            zeilen = ft.uebersicht(bot_liste=self.LISTE)
        self.assertEqual([z["name"] for z in zeilen], ["laufend", "tot"])
        a, b = zeilen
        self.assertTrue(a["erreichbar"])
        self.assertEqual((a["offen"], a["trades"], a["gewinn"]), (2, 12, -3.5))
        self.assertEqual(a["zustand"], "running")
        self.assertFalse(b["erreichbar"])
        self.assertIn("refused", b["fehler"])

    def test_leere_Liste_ist_leere_Uebersicht(self):
        with mock.patch.object(ft.urllib.request, "urlopen") as offen:
            self.assertEqual(ft.uebersicht(bot_liste=[]), [])
        offen.assert_not_called()          # kein Grund, ein Netz zu beruehren


def _bot_laeuft():
    """Live-Test nur, wenn WIRKLICH ein Bot aus der Liste antwortet.

    Bis 30.09.2026 pruefte das hier die feste Adresse 8080. Die war tot, die
    drei Bot-Container auf 8081-8083 liefen - der LiveTest wurde uebersprungen
    und sagte "Bot laeuft nicht", obwohl drei liefen.
    """
    return any(z["erreichbar"]
               for z in ft.uebersicht(zeitgrenze=2, bot_liste=ft.bots())) \
        or bool(ft.lage().get("erreichbar"))


@unittest.skipUnless(_bot_laeuft(), "kein FreqTrade-Bot aus freqtrade/bots.json laeuft")
class LiveTest(unittest.TestCase):

    def test_lage_vom_echten_bot(self):
        bots = ft.bots()
        bot = bots[0] if bots else None
        lage = ft.lage_fuer(bot) if bot else ft.lage()
        self.assertTrue(lage["erreichbar"], lage)
        self.assertTrue(lage["dry_run"], "Bot laeuft NICHT im Probebetrieb")
        self.assertEqual(lage["zustand"], "running")

    def test_bots_json_und_wirklichkeit_die_gleiche_Porten_sind(self):
        """Jeder Bot aus der Liste hat eine Antwort oder einen genannten Grund."""
        for zeile in ft.uebersicht(zeitgrenze=3, bot_liste=ft.bots()):
            if not zeile["erreichbar"]:
                self.assertTrue(zeile["fehler"], zeile)
            else:
                self.assertIn(zeile["zustand"], ("running", "stopped"))


if __name__ == "__main__":
    unittest.main()
