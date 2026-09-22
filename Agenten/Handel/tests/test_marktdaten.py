"""Tests fuer Agenten/Werkzeuge/marktdaten.py - Parser ohne Netz.

Der Werkzeugpfad wird ueber den PFAD geladen (importlib), nicht ueber sys.path:
ein Eintrag auf Werkzeuge/ koennte gleichnamige Spurenmodule verdecken
(Hausregel aus Agenten/Handel/tests).
"""

import importlib.util
import os
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, "..", ".."))          # Agenten/
WERKZEUG = os.path.join(WURZEL, "Werkzeuge", "marktdaten.py")

spec = importlib.util.spec_from_file_location("marktdaten_werkzeug", WERKZEUG)
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)
assert md.__file__ == WERKZEUG, md.__file__


class KreisTest(unittest.TestCase):
    """Krypto oder nicht: am Symbol entscheiden, nicht raten."""

    def test_krypto_paare(self):
        for symbol in ("BTC-USDT", "eth-usdc", "SOL-USD"):
            self.assertTrue(md.ist_krypto(symbol), symbol)

    def test_aktien_indizes_etfs(self):
        for symbol in ("AAPL", "^GDAXI", "VUSA.DE", "XAU=F", "SAP.DE"):
            self.assertFalse(md.ist_krypto(symbol), symbol)


class OkxTest(unittest.TestCase):
    def test_kurszeile(self):
        zeile = md.okx_kurs("BTC-USDT", md.OKX_BEISPIEL)
        self.assertEqual("BTC-USDT", zeile["symbol"])
        self.assertEqual("OKX", zeile["quelle"])
        self.assertEqual("USDT", zeile["waehrung"])
        self.assertAlmostEqual(86258.6, zeile["kurs"], places=4)
        self.assertAlmostEqual(-0.3784, zeile["aenderung_pct"], places=2)
        self.assertEqual(1790107201, zeile["zeit"])

    def test_fehlerantwort_wirft(self):
        with self.assertRaises(ValueError):
            md.okx_kurs("BTC-USDT", '{"code":"51001","msg":"Instrument ID does not exist","data":[]}')


class YahooTest(unittest.TestCase):
    def test_kurszeile(self):
        zeile = md.yahoo_kurs("AAPL", md.YAHOO_BEISPIEL)
        self.assertEqual("AAPL", zeile["symbol"])
        self.assertEqual("Yahoo", zeile["quelle"])
        self.assertEqual("USD", zeile["waehrung"])
        self.assertAlmostEqual(339.75, zeile["kurs"], places=4)
        self.assertAlmostEqual(2.5381, zeile["aenderung_pct"], places=2)

    def test_kerzen(self):
        daten = md.yahoo_kerzen("AAPL", md.YAHOO_BEISPIEL)
        self.assertEqual(2, len(daten["kerzen"]))
        self.assertAlmostEqual(339.75, daten["kerzen"][1]["kurs"], places=4)
        self.assertAlmostEqual(340.0, daten["kerzen"][1]["hoch"], places=4)

    def test_leere_antwort_wirft(self):
        with self.assertRaises(ValueError):
            md.yahoo_kurs("NIX", '{"chart":{"result":[],"error":null}}')


class RssTest(unittest.TestCase):
    def test_titel_ohne_feednamen(self):
        titel = md.rss_titel(md.RSS_BEISPIEL, "Test", 8)
        self.assertEqual(["Erste Meldung", "Zweite Meldung"], [t["titel"] for t in titel])
        self.assertTrue(all(t["quelle"] == "Test" for t in titel))

    def test_grenze_wird_gehalten(self):
        self.assertEqual(1, len(md.rss_titel(md.RSS_BEISPIEL, "Test", 1)))

    def test_kaputtes_xml_wirft(self):
        with self.assertRaises(ValueError):
            md.rss_titel("<rss><channel>", "Test")


class TextTest(unittest.TestCase):
    """Die Ausgabezeile muss Quelle, Waehrung und Prozent tragen."""

    def test_krypto_zeile(self):
        zeile = md.kurs_text(md.okx_kurs("BTC-USDT", md.OKX_BEISPIEL))
        for marke in ("BTC-USDT", "OKX", "USDT", "-0.38%"):
            self.assertIn(marke, zeile, zeile)

    def test_aktien_zeile(self):
        zeile = md.kurs_text(md.yahoo_kurs("AAPL", md.YAHOO_BEISPIEL))
        for marke in ("AAPL", "Yahoo", "USD", "+2.54%"):
            self.assertIn(marke, zeile, zeile)


class BefehlswegTest(unittest.TestCase):
    """Der Selbsttest des Werkzeugs muss durchlaufen, und `news` darf ohne
    erreichbares Netz nicht abstuerzen (Fehler gehen nach stderr)."""

    def test_selbsttest_gruen(self):
        self.assertEqual(0, md.selbsttest())

    def test_hauptprogramm_kennt_die_drei_befehle(self):
        import io
        import contextlib
        for argv, erwartet in ((("selbsttest",), 0),):
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                code = md.main(list(argv))
            self.assertEqual(erwartet, code, puffer.getvalue())


if __name__ == "__main__":
    unittest.main()