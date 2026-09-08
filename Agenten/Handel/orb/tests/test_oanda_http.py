import json
import unittest
import urllib.error
import io

import oanda


def _http_error(code, body=b"{}"):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(body))


class TestZugang(unittest.TestCase):
    def setUp(self):
        self._alt_token = oanda.token
        self._alt_konto_id = oanda.konto_id

    def tearDown(self):
        oanda.token = self._alt_token
        oanda.konto_id = self._alt_konto_id

    def test_zugang_fehlt_ohne_variablen(self):
        oanda.token = lambda: None
        oanda.konto_id = lambda: None
        self.assertFalse(oanda.zugang_vorhanden())

    def test_host_wechselt_mit_live(self):
        self.assertIn("fxpractice", oanda.host(live=False))
        self.assertIn("fxtrade", oanda.host(live=True))


class Test401(unittest.TestCase):
    def setUp(self):
        self._alt_oeffne = oanda._oeffne
        self._alt_token = oanda.token
        self._alt_konto_id = oanda.konto_id
        oanda.token = lambda: "tok"
        oanda.konto_id = lambda: "kid"

    def tearDown(self):
        oanda._oeffne = self._alt_oeffne
        oanda.token = self._alt_token
        oanda.konto_id = self._alt_konto_id

    def test_401_gegen_practice_meldet_token_abgelaufen(self):
        oanda._oeffne = lambda req, timeout: (_ for _ in ()).throw(_http_error(401))
        with self.assertRaises(oanda.OandaAuthFehler) as ctx:
            oanda._roh_json("https://api-fxpractice.oanda.com/v3/x")
        self.assertIn("abgelaufen", str(ctx.exception).lower())

    def test_401_gegen_live_host_nennt_practice_token_verdacht(self):
        oanda._oeffne = lambda req, timeout: (_ for _ in ()).throw(_http_error(401))
        with self.assertRaises(oanda.OandaAuthFehler) as ctx:
            oanda._roh_json("https://api-fxtrade.oanda.com/v3/x")
        self.assertIn("practice", str(ctx.exception).lower())


class TestRohJson(unittest.TestCase):
    def setUp(self):
        self._alt_oeffne = oanda._oeffne
        self._alt_token = oanda.token

    def tearDown(self):
        oanda._oeffne = self._alt_oeffne
        oanda.token = self._alt_token

    def test_erfolg_gibt_dict(self):
        oanda.token = lambda: "tok"
        oanda._oeffne = lambda req, timeout: io.BytesIO(json.dumps({"ok": 1}).encode())
        self.assertEqual(oanda._roh_json("https://api-fxpractice.oanda.com/v3/x"),
                         {"ok": 1})
