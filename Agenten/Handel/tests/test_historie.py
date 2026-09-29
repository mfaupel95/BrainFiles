"""Naht-Tests fuer historie_binance.py - kein Netz, kein echter Zielpfad."""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

import historie_binance                                                   # noqa: E402


class MappingTest(unittest.TestCase):
    def test_okx_und_kraken_namen_landen_auf_demselben_symbol(self):
        for name in ("BTC-USDC", "BTC-USDT", "BTC-USDT-SWAP", "XBT/USD"):
            self.assertEqual("BTCUSDT", historie_binance.symbol(name))

    def test_unbekanntes_paar_wirft_mit_liste(self):
        with self.assertRaises(KeyError) as ctx:
            historie_binance.symbol("WUNDERKERZE-USDT")
        self.assertIn("BTC-USDC", str(ctx.exception))

    def test_symbol_ist_gross_klein_unabhaengig(self):
        self.assertEqual("BTCUSDT", historie_binance.symbol("btc-usdc"))


class SpeicherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = historie_binance.ORDNER
        historie_binance.ORDNER = self.tmp.name

    def tearDown(self):
        historie_binance.ORDNER = self.alt
        self.tmp.cleanup()

    @staticmethod
    def reihe(ts, kurs):
        return [ts, kurs, kurs + 1.0, kurs - 1.0, kurs + 0.5, 12.0]

    def test_normalisieren_macht_int_und_float(self):
        roh = [["1502942400000", "4261.48", "4313.62", "4261.32", "4308.83",
                "47.18100900"]]
        r = historie_binance.reihen_normalisieren(roh)
        self.assertEqual([int, float, float, float, float, float],
                         [type(x) for x in r[0]])
        self.assertEqual(1502942400000, r[0][0])

    def test_speichere_haengt_an_und_entdoppelt(self):
        a = [self.reihe(1000, 10.0), self.reihe(2000, 11.0)]
        b = [self.reihe(2000, 11.0), self.reihe(3000, 12.0)]
        self.assertEqual(2, historie_binance.speichere("BTC-USDC", "1H", a))
        self.assertEqual(3, historie_binance.speichere("BTC-USDC", "1H", b))
        reihen = historie_binance.lade("BTC-USDC", "1H")
        self.assertEqual([1000, 2000, 3000], [r[0] for r in reihen])

    def test_lade_sortiert_aufsteigend_auch_bei_wirrem_bestand(self):
        historie_binance.speichere("ETH-USDC", "1H",
                           [self.reihe(3000, 12.0), self.reihe(1000, 10.0)])
        self.assertEqual([1000, 3000],
                         [r[0] for r in historie_binance.lade("ETH-USDC", "1H")])

    def test_lade_ohne_datei_ist_leer_und_wirft_nicht(self):
        self.assertEqual([], historie_binance.lade("SOL-USDC", "1H"))

    def test_unbekannter_takt_wird_abgelehnt(self):
        with self.assertRaises(KeyError):
            historie_binance.datei("BTC-USDC", "7M")


class AbrufTest(unittest.TestCase):
    """Der Abruf wird ueber die Naht `abruf_json` gefaelscht - kein Netz."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_o, self.alt_a = historie_binance.ORDNER, historie_binance.abruf_json
        historie_binance.ORDNER = self.tmp.name
        self.aufrufe = []

        def fake(url):
            self.aufrufe.append(url)
            if "/klines" in url and "startTime=1000" in url:
                return [["1000", "10", "11", "9", "10.5", "5"],
                        ["2000", "10.5", "12", "10", "11.5", "6"]]
            if "/klines" in url:
                return [["3000", "11.5", "13", "11", "12.5", "7"]]
            return [{"fundingTime": 1000, "fundingRate": "0.0003"},
                    {"fundingTime": 2000, "fundingRate": "-0.0001"}]
        historie_binance.abruf_json = fake

    def tearDown(self):
        historie_binance.ORDNER, historie_binance.abruf_json = self.alt_o, self.alt_a
        self.tmp.cleanup()

    def test_von_binance_blaettert_und_normalisiert(self):
        r = historie_binance.von_binance("BTC-USDC", "1H", 1000, 4000)
        self.assertEqual([1000, 2000, 3000], [x[0] for x in r])
        self.assertEqual(float, type(r[0][4]))
        self.assertEqual(3, len(self.aufrufe))

    def test_von_binance_haelt_von_und_bis_ein(self):
        r = historie_binance.von_binance("BTC-USDC", "1H", 1000, 2500)
        self.assertEqual([1000, 2000], [x[0] for x in r])

    def test_funding_liefert_paare_aus_zeit_und_satz(self):
        f = historie_binance.funding("BTC-USDC", 0, 5000)
        self.assertEqual([(1000, 0.0003), (2000, -0.0001)], f)

    def test_auffuellen_schreibt_und_stand_zaehlt(self):
        bericht = historie_binance.auffuellen(["BTC-USDC"], ["1H"], von_ms=1000, bis_ms=4000)
        self.assertEqual(3, bericht["BTC-USDC"]["1H"]["kerzen"])
        self.assertEqual(3, historie_binance.stand()["reihen"]["BTCUSDT_1H"]["kerzen"])


if __name__ == "__main__":
    unittest.main()
