"""Die Datenschicht der MoonDev-Spuren - ohne Netz.

Jede Attrappe ersetzt den Abruf; kein Test dieses Moduls darf ins Netz gehen.
Zwei Dinge werden hier besonders scharf geprueft, weil ein Fehler dort STILL
bleibt:

  * das sechste Kerzenfeld ist das QUOTE-Volumen (USD), nicht das
    Basisvolumen - mit dem falschen Feld waere die Schwelle um den Faktor Kurs
    verfehlt und die Movers-Spur haette nie gehandelt;
  * der Tages-Rang entsteht aus dem Volumen DIESES Tages, nicht aus einer
    einmal festgelegten Liste.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import historie_binance                                            # noqa: E402
import moondev_historie as mh                                      # noqa: E402


class Attrappe:
    """Ersetzt den Netzabruf. Kein Test dieses Moduls darf ins Netz."""

    def __init__(self, antworten):
        self.antworten = antworten
        self.aufrufe = []

    def __call__(self, url):
        self.aufrufe.append(url)
        for teil, antwort in self.antworten.items():
            if teil in url:
                return antwort
        raise AssertionError("unerwarteter Abruf: %s" % url)


TICKER = [{"symbol": "AAAUSDT", "quoteVolume": "900"},
          {"symbol": "BBBUSDT", "quoteVolume": "100"},
          {"symbol": "CCCUSDT", "quoteVolume": "500"},
          {"symbol": "DDDETH", "quoteVolume": "9999"}]

INFO = {"symbols": [
    {"symbol": "AAAUSDT", "status": "TRADING", "baseAsset": "AAA", "quoteAsset": "USDT"},
    {"symbol": "BBBUSDT", "status": "TRADING", "baseAsset": "BBB", "quoteAsset": "USDT"},
    {"symbol": "CCCUSDT", "status": "BREAK", "baseAsset": "CCC", "quoteAsset": "USDT"},
    {"symbol": "DDDETH", "status": "TRADING", "baseAsset": "DDD", "quoteAsset": "ETH"}]}

KERZEN = [[1609459200000, "100", "110", "90", "105", "7", 1609545599999, "735.5"],
          [1609545600000, "105", "120", "104", "118", "9", 1609631999999, "1006.25"]]


class DatenschichtTest(unittest.TestCase):
    """Basis: eigener Ablageordner, keine echten Abrufe."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.alt_ordner = mh.ORDNER
        mh.ORDNER = self.ordner.name
        self.alt_abruf = mh.abruf_json
        mh.abruf_json = Attrappe({"/ticker/24hr": TICKER, "/exchangeInfo": INFO})

    def tearDown(self):
        mh.ORDNER = self.alt_ordner
        mh.abruf_json = self.alt_abruf
        self.ordner.cleanup()


class UniversumTest(DatenschichtTest):
    def test_nur_handelbare_usdt_paare(self):
        """Ein Paar mit status BREAK oder Quote ETH gehoert nicht ins Universum."""
        self.assertEqual(["AAAUSDT", "BBBUSDT"], mh.universum(anzahl=10))

    def test_rang_nach_quote_volumen(self):
        self.assertEqual(["AAAUSDT", "BBBUSDT"], mh.universum(anzahl=2))

    def test_anzahl_wird_eingehalten(self):
        self.assertEqual(1, len(mh.universum(anzahl=1)))

    def test_leeres_universum_wird_gemeldet_statt_still_gelassen(self):
        """Eine leere Antwort darf nicht als 'keine Kandidaten' durchgehen."""
        mh.abruf_json = Attrappe({"/ticker/24hr": [], "/exchangeInfo": INFO})
        with self.assertRaises(RuntimeError):
            mh.universum(anzahl=10)

    def test_basis_kommt_aus_exchangeinfo_nicht_aus_dem_namen(self):
        """Der Basiswert steht in exchangeInfo - abgeschnitten waere geraten."""
        mh.abruf_json = Attrappe({"/ticker/24hr": TICKER, "/exchangeInfo": {
            "symbols": [{"symbol": "AAAUSDT", "status": "TRADING",
                         "baseAsset": "ANDERS", "quoteAsset": "USDT"}]}})
        mh.universum(anzahl=10)
        self.assertEqual("ANDERS", mh.basis_von("AAAUSDT"))

    def test_universum_wird_mit_herkunft_aufgezeichnet(self):
        """Ein Lauf ohne Beleg ist keiner - Rang und Herkunft gehoeren dazu."""
        mh.universum(anzahl=2)
        with open(os.path.join(mh.ORDNER, "_universum.json"), encoding="utf-8") as f:
            daten = json.load(f)
        self.assertEqual("binance", daten["herkunft"])
        self.assertEqual(["AAAUSDT", "BBBUSDT"],
                         [z["symbol"] for z in daten["symbole"]])
        self.assertEqual(900.0, daten["symbole"][0]["quote_volumen_usd"])


class KerzenformTest(DatenschichtTest):
    def test_sechstes_feld_ist_das_quote_volumen(self):
        """735.5 (Feld 7, USD) - NICHT 7 (Feld 5, Basis).

        Die Movers-Spur prueft gegen `mindest_volumen_usd` (20 Mio USD). Mit
        Basisvolumen waere die Schwelle um den Faktor Kurs verfehlt und die
        Spur haette nie gehandelt.
        """
        r = mh.normalisiere_feed(KERZEN)
        self.assertEqual([1609459200000, 100.0, 110.0, 90.0, 105.0, 735.5], r[0])
        self.assertEqual(1006.25, r[1][5])
        self.assertEqual(int, type(r[0][0]))
        self.assertEqual(float, type(r[0][5]))

    def test_speichern_haengt_an_und_entdoppelt(self):
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        self.assertEqual(2, len(mh.lade_feed("AAAUSDT", "1D")))

    def test_kuerzere_antwort_ersetzt_die_historie_nicht(self):
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed(KERZEN))
        mh.speichere_feed("AAAUSDT", "1D", mh.normalisiere_feed([KERZEN[0]]))
        self.assertEqual(2, len(mh.lade_feed("AAAUSDT", "1D")))

    def test_unbekannter_takt_wird_gemeldet(self):
        with self.assertRaises(KeyError):
            mh.datei("AAAUSDT", "7M")

    def test_hole_feed_paginiert_und_schneidet_auf_den_zeitraum(self):
        """Zwei Seiten, dann Stillstand - Abbruch ueber gleiche Zeitstempel."""
        seiten = [KERZEN]
        rufe = {"n": 0}

        def abruf(url):
            rufe["n"] += 1
            return seiten[0] if rufe["n"] == 1 else []

        mh.abruf_json = abruf
        reihen = mh.hole_feed("AAAUSDT", "1D", 1609459200000, 1900000000000, pause=0)
        self.assertEqual(2, len(reihen))
        self.assertEqual(1609459200000, reihen[0][0])


class AblageTest(unittest.TestCase):
    """Ohne Umbiegung: hier wird der Ablageort des Moduls selbst geprueft.

    Die uebrigen Klassen biegen `mh.ORDNER` auf ein Temp-Verzeichnis um - dort
    waere die Regel unsichtbar. Der scharfe Teil ist, dass beide Ablagen auf
    VERSCHIEDENE Ordner zeigen: sonst liest eine Feed-Kerze spaeter das
    Basisvolumen der gewoehnlichen Kerze.
    """

    def test_eigener_ordner_und_eigenes_namensschema(self):
        self.assertEqual(os.path.join(mh.HIER, "daten", "historie", "feed"), mh.ORDNER)
        self.assertEqual(os.path.join(mh.ORDNER, "AAAUSDT_1D.json"),
                         mh.datei("AAAUSDT", "1D"))
        self.assertNotEqual(
            os.path.dirname(historie_binance.datei("BTC-USDC", "1D")),
            os.path.dirname(mh.datei("BTCUSDT", "1D")),
            "Feed und gewoehnliche Kerzen muessen in getrennten Ordnern liegen")

    def test_feed_kerzen_tragen_das_quote_volumen_der_gewoehnliche_nicht(self):
        """Der Unterschied, der zaehlt: Feld 6 ist USD, nicht Basis."""
        roh = [[1609459200000, "100", "110", "90", "105", "7", 0, "735.5"]]
        feed = mh.normalisiere_feed(roh)[0]
        gewoehnlich = historie_binance.reihen_normalisieren(roh)[0]
        self.assertEqual(735.5, feed[5])
        self.assertEqual(7.0, gewoehnlich[5])


class PaareTest(unittest.TestCase):
    def test_bare_namen_der_funding_spur(self):
        """Ohne diese Namen faellt die Funding-Spur auf einen KeyError."""
        for inst, sym in (("BTC", "BTCUSDT"), ("ETH", "ETHUSDT"), ("SOL", "SOLUSDT")):
            self.assertEqual(sym, historie_binance.symbol(inst))

    def test_bestehende_namen_bleiben(self):
        self.assertEqual("BTCUSDT", historie_binance.symbol("BTC-USDC"))
        self.assertEqual("HYPEUSDT", historie_binance.symbol("HYPE"))


if __name__ == "__main__":
    unittest.main()
