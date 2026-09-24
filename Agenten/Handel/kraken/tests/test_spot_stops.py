"""Spot-Stops ab Mindestwert - die Regeln, ohne Netz und ohne Order.

Auftrag Max 24.09.2026 (T-051): "alle ab 50 EUR". Geprueft wird hier die reine
Rechnung; dass die Orders an der Boerse landen, belegt der Lauf selbst
(OpenOrders).
"""
import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)                     # Agenten/Handel/kraken
sys.path.insert(0, HIER)


def _lade(name, pfad):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


s = _lade("spot_stops", os.path.join(SPUR, "spot_stops.py"))
assert s.__file__.startswith(SPUR), s.__file__

PAARE = {
    "ALGOEUR": {"base": "ALGO", "quote": "ZEUR", "lot_decimals": 8,
                "ordermin": "0.1"},
    "SOLEUR": {"base": "SOL", "quote": "ZEUR", "lot_decimals": 8,
               "ordermin": "0.02"},
    "ETHEUR": {"base": "XETH", "quote": "ZEUR", "lot_decimals": 8,
               "ordermin": "0.002"},
    "XETHZEUR": {"base": "XETH", "quote": "ZEUR", "lot_decimals": 8,
                 "ordermin": "0.002"},
    "ADAUSD": {"base": "ADA", "quote": "ZUSD", "lot_decimals": 8,
               "ordermin": "5"},
    "PEPEUSD": {"base": "PEPE", "quote": "ZUSD", "lot_decimals": 0,
                "ordermin": "50000"},
}


class NameTest(unittest.TestCase):
    def test_kraken_praefixe(self):
        for roh, erwartet in (("XXBT", "BTC"), ("XBT", "BTC"), ("XETH", "ETH"),
                              ("ZEUR", "EUR"), ("ZUSD", "USD"), ("SOL", "SOL"),
                              ("KAS", "KAS")):
            self.assertEqual(s.norm(roh), erwartet, roh)

    def test_sonderformen_und_paarschreibweise(self):
        self.assertEqual(s.norm("ADA.S"), "ADA")
        self.assertEqual(s.norm("HYPE.B"), "HYPE")
        self.assertEqual(s.norm("SOL/EUR"), "SOL")
        self.assertEqual(s.norm(""), "")

    def test_muenze_aus_paar_ueber_die_tabelle(self):
        self.assertEqual(s.muenze_aus_paar("ETHEUR", PAARE), "ETH")
        self.assertEqual(s.muenze_aus_paar("XETHZEUR", PAARE), "ETH")

    def test_muenze_aus_paar_ohne_tabelle(self):
        # Kraken nennt lange und kurze Form; beide muessen auf die Muenzmenge
        # zurueckfallen, sonst gilt ETH als ungeschuetzt, obwohl ein Stop liegt.
        self.assertEqual(s.muenze_aus_paar("XXBTZUSD", {}), "BTC")
        self.assertEqual(s.muenze_aus_paar("SOL/EUR", {}), "SOL")
        self.assertEqual(s.muenze_aus_paar("ALGOEUR", {}), "ALGO")
        self.assertEqual(s.muenze_aus_paar("FOO", {}), "FOO")


class PaarWahlTest(unittest.TestCase):
    def test_eur_vor_usd(self):
        paare = dict(PAARE)
        paare["SOLUSD"] = {"base": "SOL", "quote": "ZUSD", "lot_decimals": 8,
                           "ordermin": "0.02"}
        self.assertEqual(s.paar_waehlen("SOL", paare), "SOLEUR")

    def test_nur_usd_geht_auch(self):
        self.assertEqual(s.paar_waehlen("ADA", PAARE), "ADAUSD")

    def test_kein_paar(self):
        self.assertIsNone(s.paar_waehlen("FOO", PAARE))


class PlanTest(unittest.TestCase):
    def test_stop_liegt_prozent_unter_dem_kurs(self):
        zeilen = s.plan({"ALGO": 513.98}, {}, PAARE, {"ALGOEUR": 0.10})
        z = zeilen[0]
        self.assertEqual(z["status"], "ok")
        self.assertAlmostEqual(z["stop"], 0.0925, places=6)
        self.assertLess(z["stop"], z["kurs"])

    def test_stop_nie_ueber_dem_markt(self):
        # prozent=0 ist der Grenzfall: dann ist der Stop genau der Kurs und darf
        # NICHT als Order rausgehen (das waere ein sofortiger Verkauf).
        zeilen = s.plan({"ALGO": 513.98}, {}, PAARE, {"ALGOEUR": 0.10}, prozent=0)
        self.assertEqual(zeilen[0]["status"], "hinweis")
        self.assertIn("nicht unter dem Markt", zeilen[0]["grund"])

    def test_unter_mindestwert_mit_zahl_im_grund(self):
        zeilen = s.plan({"KAS": 400.0}, {}, {"KASEUR": {"base": "KAS",
                                                       "quote": "ZEUR"}},
                        {"KASEUR": 0.10}, ab_eur=50.0)
        self.assertEqual(zeilen[0]["status"], "hinweis")
        self.assertIn("40.00", zeilen[0]["grund"])

    def test_vollstaendig_reserviert_wird_nicht_geordert(self):
        # BTC/ETH sind durch die mosaic-Stops vollstaendig belegt (hold_trade).
        zeilen = s.plan({"XETH": 0.0407164940}, {"XETH": 0.0407176300}, PAARE,
                        {"ETHEUR": 2358.85})
        self.assertEqual(zeilen[0]["status"], "hinweis")
        self.assertIn("reserviert", zeilen[0]["grund"])
        self.assertEqual(zeilen[0]["menge"], 0.0)

    def test_freier_rest_bekommt_trotzdem_einen_stop(self):
        # SOL: 1,46 gesamt, 0,48 haelt schon ein Stop -> der Rest wird geschuetzt
        # und der Vermerk nennt den bestehenden Stop.
        offene = [{"vol": "0.48058439",
                   "descr": {"pair": "SOLEUR", "ordertype": "stop-loss",
                             "price": "96.24"}}]
        zeilen = s.plan({"SOL": 1.4617934558}, {"SOL": 0.4805843900}, PAARE,
                        {"SOLEUR": 102.15}, offene=offene)
        z = zeilen[0]
        self.assertEqual(z["status"], "ok")
        self.assertAlmostEqual(z["menge"], 0.9812090658, places=8)
        self.assertIn("traegt schon einen Stop", z["schon"])

    def test_quote_und_staking_werden_uebersprungen(self):
        zeilen = s.plan({"ZEUR": 500.0, "ETH2": 1.0, "USDC": 100.0}, {}, PAARE, {})
        self.assertEqual([z["status"] for z in zeilen], ["hinweis"] * 3)

    def test_ohne_schliesst_aus(self):
        zeilen = s.plan({"SOL": 1.0}, {}, PAARE, {"SOLEUR": 102.15},
                        ohne={"SOL"})
        self.assertEqual(zeilen[0]["status"], "hinweis")
        self.assertIn("--ohne", zeilen[0]["grund"])

    def test_ohne_paar_kein_stop(self):
        zeilen = s.plan({"ATOM21": 5.0}, {}, PAARE, {})
        self.assertEqual(zeilen[0]["status"], "hinweis")
        self.assertIn("kein EUR/USD-Handelspaar", zeilen[0]["grund"])

    def test_bestehender_stop_ueber_die_ganze_menge_wird_erkannt(self):
        offene = [{"vol": "513.98026315",
                   "descr": {"pair": "ALGOEUR", "ordertype": "stop-loss",
                             "price": "0.09033"}}]
        schon = s.geschuetzte(offene, PAARE)
        self.assertIn("ALGO", schon)
        self.assertEqual(schon["ALGO"][0], "ALGOEUR")

    def test_marktorder_zaehlt_nicht_als_schutz(self):
        offene = [{"vol": "5.0", "descr": {"pair": "ALGOEUR",
                                           "ordertype": "market",
                                           "price": "0"}}]
        self.assertEqual(s.geschuetzte(offene, PAARE), {})


class MengerundungTest(unittest.TestCase):
    def test_menge_wird_abgerundet_und_gegen_ordermin_geprueft(self):
        z = {"paar": "PEPEUSD", "menge": 123456.789}
        menge, fehler = s._betrag_gerundet(z, PAARE)
        self.assertEqual(menge, 123456.0)          # lot_decimals 0 -> abrunden
        self.assertEqual(fehler, "")

    def test_unter_ordermin_wird_gemeldet(self):
        z = {"paar": "PEPEUSD", "menge": 100.0}
        menge, fehler = s._betrag_gerundet(z, PAARE)
        self.assertIn("ordermin", fehler)


if __name__ == "__main__":
    unittest.main()