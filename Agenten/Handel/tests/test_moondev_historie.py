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

# Ein echtes Paar mit chinesischem Namen: Binance fuehrt solche Symbole
# (29.09.2026 gemessen: 币安人生USDT, 牛来USDT). So eines ist nicht abrufbar.
CHINESISCH = "币安人生USDT"

INFO = {"symbols": [
    {"symbol": CHINESISCH, "status": "TRADING", "baseAsset": "币安人生",
     "quoteAsset": "USDT"},
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

    def test_paare_mit_nicht_abrufbarem_namen_fliegen_raus(self):
        """Ein einziges solches Paar reisst sonst den GANZEN Abruf mit.

        Binance fuehrt Paare mit chinesischen Namen; urllib kann die Adresse
        nicht kodieren ("'ascii' codec can't encode characters in position
        26-27"), und der Fehler trifft dann ein voellig anderes Symbol.
        """
        mh.abruf_json = Attrappe({"/ticker/24hr": TICKER,
                                  "/exchangeInfo": INFO})
        sym = mh.universum(anzahl=10)
        self.assertNotIn(CHINESISCH, sym)
        self.assertNotIn(CHINESISCH, mh._basis)
        self.assertEqual([CHINESISCH], mh._verworfen)

    def test_das_uebersprungene_paar_steht_im_stand(self):
        """Nicht still weglassen: der Stand nennt es."""
        mh.abruf_json = Attrappe({"/ticker/24hr": TICKER,
                                  "/exchangeInfo": INFO})
        mh.universum(anzahl=10)
        self.assertEqual([CHINESISCH], mh.stand()["verworfen"])

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


class BestandTest(DatenschichtTest):
    """Der Marktquerschnitt je Tag - die Grundlage jeder Feed-Entscheidung.

    Drei Reihen mit Absicht: AAA steigt, BBB faellt, CCC hat nur EINEN Tag.
    Damit laesst sich alles pruefen, was still schiefgehen kann - der Rang,
    das Fehlen einer Kerze und die Breite.
    """

    def setUp(self):
        super().setUp()
        mh.speichere_feed("AAAUSDT", "1D", [
            [0, 10, 10, 10, 10, 50], [86400000, 10, 12, 10, 12, 50],
            [172800000, 12, 14, 12, 14, 50]])
        mh.speichere_feed("BBBUSDT", "1D", [
            [0, 10, 10, 10, 5, 300], [86400000, 5, 5, 4, 4, 300],
            [172800000, 4, 4, 4, 2, 300]])
        mh.speichere_feed("CCCUSDT", "1D", [[172800000, 900, 900, 900, 900, 900]])
        self.b = mh.Bestand()
        self.b.laden("1D")

    def test_rang_entsteht_je_tag_aus_dem_volumen_dieses_tages(self):
        """Nicht aus einer einmal festgelegten Liste - sonst waere der
        Marktquerschnitt von heute der von gestern."""
        self.assertEqual(["CCCUSDT", "BBBUSDT", "AAAUSDT"], self.b.rang(172800000))
        self.assertEqual(["BBBUSDT", "AAAUSDT"], self.b.rang(86400000))

    def test_tafel_enthaelt_nur_symbole_mit_kerze_an_diesem_zeitpunkt(self):
        self.assertEqual(["AAAUSDT", "BBBUSDT"], sorted(self.b.tafel(86400000)))

    def test_tafel_traegt_die_aenderung_zum_vortag(self):
        t = self.b.tafel(86400000)
        self.assertAlmostEqual(20.0, t["AAAUSDT"]["aenderung_pct"], 6)
        self.assertAlmostEqual(-20.0, t["BBBUSDT"]["aenderung_pct"], 6)

    def test_erster_tag_einer_reihe_hat_keine_aenderung(self):
        """None, nicht 0: eine fehlende Vorzeile ist keine Nullbewegung."""
        t = self.b.tafel(0)
        self.assertIsNone(t["AAAUSDT"]["aenderung_pct"])
        self.assertIsNone(t["AAAUSDT"]["aenderung_pct_7d"])

    def test_kurse_umfassen_ALLE_geladenen_symbole(self):
        """`pruefe_ausstiege` liest `kurse`.

        Fehlt dort ein Symbol, schliesst diese Position NIE und der Lauf meldet
        weniger Runden, als es tatsaechlich gab - ein stiller Fehler, deshalb
        steht er hier als eigener Test.
        """
        k = self.b.kurse(259200000)
        self.assertEqual(["AAAUSDT", "BBBUSDT", "CCCUSDT"], sorted(k))
        self.assertEqual(2.0, k["BBBUSDT"])

    def test_fehlt_das_symbol_ganz_ist_der_kurs_None_statt_geraten(self):
        self.assertIsNone(self.b.kurs("DDDUSDT", 259200000))

    def test_quantil_sortiert_selbst(self):
        self.assertAlmostEqual(5.0, mh.quantil([10, 1, 5, 3], 0.5), 6)
        self.assertAlmostEqual(1.0, mh.quantil([10, 1, 5, 3], 0.0), 6)
        self.assertAlmostEqual(10.0, mh.quantil([10, 1, 5, 3], 1.0), 6)

    def test_quantil_einer_leeren_reihe_ist_None(self):
        self.assertIsNone(mh.quantil([], 0.5))

    def test_breite_ist_der_anteil_positiver_aenderungen(self):
        """Ein Tag: AAA +20 %, BBB -20 % -> 0.5. CCC hat keine Kerze und
        zaehlt NICHT mit - sonst waere die Breite von der Datenlage abhaengig.
        """
        b = self.b.breite(86400000)
        self.assertAlmostEqual(0.5, b["anteil"], 6)
        self.assertEqual(2, b["gemessen"])
        # CCC hat an diesem Tag noch keine Kerze - es steht gar nicht in der
        # Tafel, ist also auch keine unbemessene Zeile.
        self.assertEqual(0, b["ohne_kerze"])

    def test_ohne_vortag_zaehlt_das_symbol_als_unbemessen(self):
        """Am ersten Tag steht das Symbol in der Tafel, hat aber keine Vorzeile.

        Dann ist die Breite KEINE Aussage (None) - 0 % waere 'keiner steigt'.
        """
        b = self.b.breite(0)
        self.assertIsNone(b["anteil"])
        self.assertEqual(0, b["gemessen"])
        self.assertEqual(2, b["ohne_kerze"])

    def test_breite_ohne_daten_ist_kein_anteil_sondern_None(self):
        """0.0 waere eine Aussage ('keiner steigt') - es ist keine.

        Ein Zeitpunkt in der Zukunft ist NICHT der Fall 'keine Daten': dort
        laeuft die letzte bekannte Kerze weiter, und das ist Absicht.
        """
        for name in os.listdir(mh.ORDNER):
            os.remove(os.path.join(mh.ORDNER, name))
        leer = mh.Bestand()
        self.assertEqual([], leer.laden("1D"))
        self.assertIsNone(leer.breite(0)["anteil"])
        self.assertIsNone(leer.kurs("AAAUSDT", 0))

    def test_tafel_begrenzt_auf_die_top_n(self):
        t = self.b.tafel(172800000, top=2)
        self.assertEqual(["BBBUSDT", "CCCUSDT"], sorted(t))

    def test_tafel_ohne_top_nimmt_alle(self):
        self.assertEqual(3, len(self.b.tafel(172800000)))

    def test_kurs_bleibt_die_letzte_kerze_wenn_der_zeitpunkt_danach_liegt(self):
        """Im Nachlauf ist das die LAUFENDE Kerze, nicht die naechste."""
        self.assertEqual(14.0, self.b.kurs("AAAUSDT", 999999999999))


class StundentafelTest(DatenschichtTest):
    """Der Stundenquerschnitt fuer die Signalwelle.

    26 Kerzen, Kurs steigt je Stunde um 1: damit ist jede Aenderung
    nachrechenbar und keine Zahl stammt aus dem Code selbst.
    """

    def setUp(self):
        super().setUp()
        k = [[i * 3600000, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i, 10.0]
             for i in range(26)]
        mh.speichere_feed("AAAUSDT", "1H", k)
        mh.speichere_feed("BBBUSDT", "1H", k)
        self.b = mh.Bestand()
        self.b.laden("1H")

    def test_aenderung_1h_ist_schluss_gegen_vorstunde(self):
        z = [x for x in self.b.tafel_stunde(25 * 3600000)
             if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual((125.0 / 124.0 - 1.0) * 100.0,
                               z["aenderung_1h"], places=6)

    def test_aenderung_24h_geht_24_kerzen_zurueck(self):
        z = [x for x in self.b.tafel_stunde(25 * 3600000)
             if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual((125.0 / 101.0 - 1.0) * 100.0,
                               z["aenderung_24h"], places=6)

    def test_ohne_24_kerzen_vorlauf_kein_eintrag(self):
        """Ein Wert aus drei Kerzen waere keine 24h-Aenderung - die Zeile
        fehlt dann ganz, statt eine 3h-Zahl als 24h auszugeben."""
        self.assertEqual([], self.b.tafel_stunde(5 * 3600000))

    def test_volumen_24h_ist_die_summe_der_letzten_24_kerzen(self):
        z = [x for x in self.b.tafel_stunde(25 * 3600000)
             if x["symbol"] == "AAAUSDT"][0]
        self.assertAlmostEqual(240.0, z["volumen_24h"], places=6)

    def test_rang_beginnt_bei_eins(self):
        self.assertEqual([1, 2], [z["rang"] for z in self.b.tafel_stunde(25 * 3600000)])

    def test_top_begrenzt_die_liste(self):
        self.assertEqual(1, len(self.b.tafel_stunde(25 * 3600000, top=1)))


class FundingTest(DatenschichtTest):
    def test_funding_zu_nimmt_den_letzten_satz_vor_dem_zeitpunkt(self):
        """Nie den naechsten: das waere ein Blick in die Zukunft."""
        reihe = [[0, 0.0001], [28800000, 0.0002], [57600000, 0.0003]]
        self.assertEqual(0.0002, mh.funding_zu(reihe, 40000000))

    def test_der_satz_gilt_ab_seinem_zeitstempel(self):
        reihe = [[0, 0.0001], [28800000, 0.0002]]
        self.assertEqual(0.0002, mh.funding_zu(reihe, 28800000))

    def test_vor_dem_ersten_satz_gibt_es_keinen_wert(self):
        self.assertIsNone(mh.funding_zu([[28800000, 0.0002]], 1000))

    def test_funding_wird_entdoppelt_gespeichert(self):
        mh.speichere_funding("BTC", [[0, 0.0001]])
        mh.speichere_funding("BTC", [[0, 0.0001], [28800000, 0.0002]])
        self.assertEqual(2, len(mh.lade_funding("BTC")))

    def test_funding_steht_unter_dem_symbol_nicht_unter_dem_instrument(self):
        """Eine Reihe je Symbol - sonst suchte die Funding-Spur im Leeren."""
        self.assertTrue(mh.funding_datei("BTC").endswith("funding_BTCUSDT.json"))

    def test_mark_preis_kommt_aus_der_stundenkerze(self):
        mh.speichere_feed("BTCUSDT", "1H", [[0, 1, 1, 1, 50000.0, 10]])
        self.assertEqual(50000.0, mh.mark_preis("BTCUSDT", 0))

    def test_mark_preis_vor_der_ersten_kerze_ist_None(self):
        mh.speichere_feed("BTCUSDT", "1H", [[7200000, 1, 1, 1, 50000.0, 10]])
        self.assertIsNone(mh.mark_preis("BTCUSDT", 0))

    def test_funding_dict_hat_genau_die_form_der_spur(self):
        mh.speichere_funding("BTC", [[0, 0.0003]])
        mh.speichere_feed("BTCUSDT", "1H", [[0, 1, 1, 1, 50000.0, 10]])
        self.assertEqual({"funding_rate": 0.0003, "mark_price": 50000.0},
                         mh.funding_dict("BTC", 0))

    def test_funding_dict_ohne_satz_ist_None_statt_einer_leeren_form(self):
        mh.speichere_feed("BTCUSDT", "1H", [[0, 1, 1, 1, 50000.0, 10]])
        self.assertIsNone(mh.funding_dict("BTC", 0))

    def test_funding_stand_zaehlt_die_saetze(self):
        mh.speichere_funding("BTC", [[0, 0.0001], [28800000, 0.0002]])
        self.assertEqual(2, mh.funding_stand()["BTCUSDT"]["saetze"])


class NachlaufTest(DatenschichtTest):
    """Nachladen: am Stand fortsetzen, nicht jedes Mal alles."""

    def test_setzt_am_letzten_stand_fort(self):
        mh.speichere_feed("AAAUSDT", "1D", [[0, 1, 1, 1, 1, 10],
                                            [86400000, 1, 1, 1, 1, 10],
                                            [172800000, 1, 1, 1, 1, 10]])
        self.assertEqual(172800001, mh._startpunkt("AAAUSDT", "1D", 0))

    def test_holt_von_vorn_wenn_die_reihe_spaet_anfaengt(self):
        """Ein spaeter gelistetes Paar bekommt sein ganzes Fenster - sonst
        bliebe die Luecke fuer immer."""
        mh.speichere_feed("AAAUSDT", "1D", [[864000000, 1, 1, 1, 1, 10]])
        self.assertEqual(0, mh._startpunkt("AAAUSDT", "1D", 0))

    def test_ohne_gespeicherte_reihe_von_vorn(self):
        self.assertEqual(12345, mh._startpunkt("NEUUSDT", "1D", 12345))

    def test_stundenreihe_setzt_stundenweise_fort(self):
        """Die Toleranz haengt am Takt: zwei STUNDEN, nicht zwei Tage."""
        mh.speichere_feed("AAAUSDT", "1H", [[3600000, 1, 1, 1, 1, 10]])
        self.assertEqual(3600001, mh._startpunkt("AAAUSDT", "1H", 0))
        mh.speichere_feed("BBBUSDT", "1H", [[86400000, 1, 1, 1, 1, 10]])
        self.assertEqual(0, mh._startpunkt("BBBUSDT", "1H", 0))

    def test_mehrere_faeden_liefern_dasselbe_ergebnis(self):
        """Faeden sind Mittel zum Zweck - sie duerfen nichts veraendern."""
        def abruf(url):
            start = int(url.split("startTime=")[1])
            if start > 1609459200000:
                return []
            sym = url.split("symbol=")[1].split("&")[0]
            return [[1609459200000, "1", "2", "0.5", "1.5", "1", 0,
                     str(100 + len(sym))]]

        mh.abruf_json = abruf
        syms = ["AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT", "EEEUSDT"]
        b1 = mh.auffuellen(syms, "1D", 1609459200000, 1609459200000,
                           pause=0, faeden=1)
        for s in syms:
            os.remove(mh.datei(s, "1D"))
        b2 = mh.auffuellen(syms, "1D", 1609459200000, 1609459200000,
                           pause=0, faeden=4)
        self.assertEqual(sorted(b1), sorted(b2))
        for s in syms:
            self.assertEqual(b1[s]["kerzen"], b2[s]["kerzen"])
            self.assertEqual(1, b2[s]["kerzen"])
            self.assertEqual(100 + len(s), mh.lade_feed(s, "1D")[0][5])


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
