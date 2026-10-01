"""Der Lagerbestand: was festliegt und WARUM (T-280).

Zwei Ursachen, die man am Betrag nicht unterscheidet:
  * **unter_ordermin** - Kraken verlangt je Paar eine Mindestmenge; sammeln
    hilft, die Order waere abgelehnt worden.
  * **kein_paar** - Sonderformen (`.S` gestakt, `.B`/`.EQ` Kontencodes) haben
    KEINEN Markt. Gemessen: `AssetPairs` fuehrt keine Basis mit einem Punkt.
    Eine Order ist dort kein Weg - nur Unstaking oder Wandeln.

Die Fixtures sind die am 01.10.2026 gemessenen Zahlen (PEPE 409.009,94 gegen
ordermin 1.500.000; ONDO 10,74331 gegen 15; ADA.S/ATOM21.S/HYPE.B/XPEV.EQ ohne
Paar). Kein Netz: Staende und Paare kommen als Attrappe.

Ausfuehrbar (aus dem kraken-Ordner): python -m unittest tests.test_lagerbestand
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import lagerbestand as lb                                            # noqa: E402

assert Path(lb.__file__).resolve().parent == HIER.parent

STAENDE = {
    "ADA.S": "50.63776095", "ADA": "0.00339265", "AVAX": "0.0000000000",
    "EURC": "0.000000", "ONDO": "10.74331", "PEPE": "409009.94",
    "USDC": "99.05099779", "XXLM": "511.14312861", "YFI": "0.00000",
}

PAARE = {
    "PEPEEUR": {"base": "PEPE", "quote": "ZEUR", "ordermin": "1500000",
                "costmin": "0.45", "status": "online"},
    "PEPEUSD": {"base": "PEPE", "quote": "ZUSD", "ordermin": "1500000",
                "costmin": "0.5", "status": "online"},
    "ONDOEUR": {"base": "ONDO", "quote": "ZEUR", "ordermin": "15",
                "costmin": "0.45", "status": "online"},
    "ADAEUR": {"base": "ADA", "quote": "ZEUR", "ordermin": "20",
               "costmin": "0.45", "status": "online"},
    "XXLMZEUR": {"base": "XXLM", "quote": "ZEUR", "ordermin": "30",
                 "costmin": "0.45", "status": "online"},
    # Ein Posten, dessen ERSTES Paar alphabetisch vor dem USDC-Paar liegt -
    # die Quote muss trotzdem nach QUOTEN gewaehlt werden.
    "YFIUSDC": {"base": "YFI", "quote": "USDC", "ordermin": "0.0001",
                "costmin": "0.5", "status": "online"},
    "YFIAUD": {"base": "YFI", "quote": "ZAUD", "ordermin": "0.0001",
               "costmin": "1", "status": "online"},
}


class LageTest(unittest.TestCase):
    def setUp(self):
        self.zeilen = {z["code"]: z for z in lb.lage(STAENDE, PAARE)}

    def test_pepe_liegt_unter_dem_ordermin(self):
        z = self.zeilen["PEPE"]
        self.assertEqual(z["lage"], lb.UNTER_ORDERMIN)
        self.assertEqual(z["paar"], "PEPEEUR")
        self.assertEqual(z["ordermin"], 1500000.0)
        self.assertAlmostEqual(z["fehlt"], 1090990.06, places=6)
        self.assertIn("sammeln", z["grund"])

    def test_ondo_liegt_unter_dem_ordermin(self):
        z = self.zeilen["ONDO"]
        self.assertEqual(z["lage"], lb.UNTER_ORDERMIN)
        self.assertAlmostEqual(z["fehlt"], 15.0 - 10.74331, places=8)

    def test_sonderform_hat_kein_paar(self):
        z = self.zeilen["ADA.S"]
        self.assertEqual(z["lage"], lb.KEIN_PAAR)
        self.assertIsNone(z["paar"])
        self.assertIn("Sonderform", z["grund"])
        self.assertNotIn("ORDNE", z["grund"])       # kein Vorschlag, der nicht geht

    def test_kleine_bestaende_ueber_dem_ordermin_sind_handelbar(self):
        self.assertEqual(self.zeilen["XXLM"]["lage"], lb.STAND)
        self.assertEqual(self.zeilen["XXLM"]["paar"], "XXLMZEUR")

    def test_barmittel_ist_keine_sonderform(self):
        """USDC ist eine Quotewaehrung, kein gestakter Posten.

        Ohne diese Unterscheidung erklaerte das Werkzeug Barmittel mit
        "gestakt oder tokenisiert" - eine FALSCHE Ursache, und die Ursache ist
        genau das, was hier gesucht wird. Nach diesem Befund steht USDC nicht
        mehr in der Liste der festliegenden Posten.
        """
        z = self.zeilen["USDC"]
        self.assertEqual(z["lage"], lb.BARMITTEL)
        self.assertIn("Barmittel", z["grund"])
        self.assertNotIn("gestakt", z["grund"])
        self.assertNotIn(z["lage"], lb.FEST)

    def test_nullstaende_sind_kein_befund(self):
        """Ein Kontostand von 0 ist kein festliegender Posten - sonst waere die
        Liste voller Staub und der eine echte Befund unsichtbar."""
        self.assertNotIn("AVAX", self.zeilen)
        self.assertNotIn("EURC", self.zeilen)

    def test_quote_wird_nach_der_reihenfolge_gewaehlt(self):
        """YFI hat ein AUD- und ein USDC-Paar: genommen wird USDC, nicht das
        alphabetisch erste."""
        zeilen = {z["code"]: z for z in lb.lage({"YFI": "1.0"}, PAARE)}
        z = zeilen["YFI"]
        self.assertEqual(z["paar"], "YFIUSDC")
        self.assertEqual(z["quote"], "USDC")

    def test_paare_lesen_packt_die_result_huelle_aus(self):
        self.assertEqual(lb.paare_lesen({"result": PAARE})["PEPEEUR"]["base"], "PEPE")
        self.assertEqual(lb.paare_lesen(PAARE)["ONDOEUR"]["ordermin"], "15")
        # Eine kaputte/leere Antwort ist eine leere Tabelle, kein Absturz -
        # und NICHT der echte Abruf (der liegt in paare_lesen() ohne Argument).
        self.assertEqual(lb.paare_lesen({}), {})
        self.assertEqual(lb.paare_lesen({"result": None}), {})
        self.assertEqual(lb.paare_lesen({"result": {"X": "kein dict"}}), {})


class WertTest(unittest.TestCase):
    def test_wert_rechnet_menge_mal_kurs(self):
        zeilen = lb.lage({"XXLM": "511.14312861"}, PAARE)
        lb.werte_ergaenzen(zeilen, kurs_fn=lambda paar: 0.2)
        self.assertAlmostEqual(zeilen[0]["wert_quote"], 102.2286, places=4)

    def test_ein_kaputter_kurs_kippt_den_lauf_nicht(self):
        zeilen = lb.lage({"XXLM": "511.0", "ONDO": "10.0"}, PAARE)

        def kurs(paar):
            raise RuntimeError("kein Kurs")

        lb.werte_ergaenzen(zeilen, kurs_fn=kurs)
        self.assertTrue(all(z["wert_quote"] is None for z in zeilen),
                        "ohne Kurs bleibt der Wert leer, nicht 0")

    def test_posten_ohne_paar_werden_nicht_bewertet(self):
        zeilen = lb.lage({"ADA.S": "50.63776095"}, PAARE)
        lb.werte_ergaenzen(zeilen, kurs_fn=lambda paar: 1.0)
        self.assertIsNone(zeilen[0]["wert_quote"])


class AusgabeTest(unittest.TestCase):
    def test_tabelle_nennt_alle_spalten(self):
        text = lb._tabelle(lb.lage(STAENDE, PAARE))
        for spalte in ("CODE", "MENGE", "LAGE", "PAAR", "ORDERMIN",
                       "FEHLT BIS ORDERMIN", "WERT"):
            self.assertIn(spalte, text)

    def test_main_zeigt_nur_die_festliegenden(self):
        """Gegenprobe am Aufruf: jeder festliegende Posten steht da, sonst keiner."""
        import contextlib
        import io
        import unittest.mock as mock
        puffer = io.StringIO()
        with mock.patch.object(lb.k, "kontostaende", return_value=STAENDE), \
             mock.patch.object(lb, "paare_lesen", return_value=PAARE), \
             mock.patch.object(sys, "argv", ["lagerbestand.py", "--ohne-kurse"]), \
             contextlib.redirect_stdout(puffer):
            code = lb.main()
        text = puffer.getvalue()
        self.assertEqual(code, 0)
        for code_ in ("PEPE", "ONDO", "ADA.S"):
            self.assertIn(code_, text)
        self.assertIn("4 von 6", text,
                      "vier festliegende von sechs Posten: %s" % text)
        self.assertNotIn("XXLM", text, "handelbare Posten gehoeren nicht in die Kurzliste")
        self.assertNotIn("USDC", text, "Barmittel ist kein festliegender Posten")


if __name__ == "__main__":
    unittest.main()