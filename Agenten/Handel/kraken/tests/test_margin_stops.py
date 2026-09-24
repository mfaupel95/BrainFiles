"""Margin-Positionen absichern - die Regeln, ohne Netz und ohne Order.

Hintergrund (24.09.2026, Auftrag Max "Sui Zec und near auf kraken ebenfalls
absichern"): SUI, ZEC und NEAR liegen bei Kraken NICHT im Spot-Guthaben, sondern
als offene MARGIN-Positionen. Fuer die gelten andere Regeln als fuer eine
Spot-Position - und drei davon sind teuer, wenn sie fehlen:

1. Der Stop muss die Position SCHLIESSEN (close[ordertxid]) - ein nackter
   Verkaufsstop bliebe stehen und wuerde bei fehlender Position einen SHORT
   aufmachen.
2. Die Menge muss die der Position sein - nie mehr, sonst dreht der Rest short.
3. Ein Stop ueber dem Markt ist kein Schutz, sondern ein sofortiger Verkauf.
   Liegt der Einstieg so hoch, dass "Einstieg minus 7,5 %" ueber dem Markt
   liegt, wird die Position uebersprungen und gemeldet.
"""

import importlib.util
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
for p in (HANDEL, os.path.join(HANDEL, "scanner")):
    if p not in sys.path:
        sys.path.insert(0, p)


def _lade():
    pfad = os.path.join(SPUR, "margin_stops.py")
    spec = importlib.util.spec_from_file_location("margin_stops_test", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["margin_stops_test"] = m
    spec.loader.exec_module(m)
    return m


M = _lade()

PAARE = {
    "SUIEUR": {"ordermin": "5", "leverage_sell": [2, 3, 4, 5, 6, 7, 8, 9, 10]},
    "NEAREUR": {"ordermin": "4", "leverage_sell": [2, 3]},
    "XZECZUSD": {"ordermin": "0.01", "leverage_sell": [2, 3, 4, 5]},
}


def _pos(vol, cost, ordertxid="OAAA-BBBB-CCCC", paar="SUIEUR"):
    return {"pair": paar, "vol": str(vol), "cost": str(cost), "posstatus": "open",
            "ordertxid": ordertxid}


class Einstieg(unittest.TestCase):
    def test_aus_cost_und_vol(self):
        self.assertAlmostEqual(M.einstieg(_pos(192.14279, 161.3999436)),
                               0.8400000, places=6)

    def test_ohne_menge_kein_einstieg(self):
        self.assertIsNone(M.einstieg(_pos(0, 10)))


class StopPreis(unittest.TestCase):
    def test_sieben_komma_fuenf_prozent_unter_dem_einstieg(self):
        preis, grund = M.stop_preis(0.88, 0.8395)
        self.assertIsNone(grund)
        self.assertAlmostEqual(preis, 0.814, places=6)

    def test_stop_ueber_dem_markt_wird_verworfen(self):
        # Einstieg 1,00 - der Kurs ist aber schon auf 0,90 gefallen:
        # 0,925 waere ein sofortiger Verkauf, keine Absicherung.
        preis, grund = M.stop_preis(1.00, 0.90)
        self.assertIsNone(preis)
        self.assertIn("nicht unter dem Markt", grund)

    def test_ohne_kurs_kein_stop(self):
        preis, grund = M.stop_preis(1.0, None)
        self.assertIsNone(preis)
        self.assertIn("kein Einstieg", grund)


class StaubUndHebel(unittest.TestCase):
    def test_staubrest_wird_erkannt(self):
        self.assertTrue(M.ist_staub(_pos(2.3e-07, 0.0, paar="NEAREUR"),
                                    PAARE["NEAREUR"]))

    def test_echte_position_ist_kein_staub(self):
        self.assertFalse(M.ist_staub(_pos(31.190872, 120.01, paar="NEAREUR"),
                                     PAARE["NEAREUR"]))

    def test_hebel_ist_der_hoechste_erlaubte(self):
        self.assertEqual(M.hebel(PAARE["SUIEUR"]), 10)
        self.assertEqual(M.hebel(PAARE["NEAREUR"]), 3)
        self.assertEqual(M.hebel(PAARE["XZECZUSD"]), 5)

    def test_ohne_angabe_kein_hebel(self):
        self.assertIsNone(M.hebel({}))


class Plan(unittest.TestCase):
    def test_orderbare_position_traegt_die_ordertxid(self):
        pos = {"T2RKN7-F3YC2-3FVBCR": _pos(30.69447, 27.0111336,
                                          ordertxid="OQ2UFG-ZF3JX-JODBPO")}
        zeilen = M.plan(pos, {"SUIEUR": 0.8395}, PAARE)
        self.assertEqual(len(zeilen), 1)
        z = zeilen[0]
        self.assertIsNone(z["hinweis"])
        self.assertEqual(z["ordertxid"], "OQ2UFG-ZF3JX-JODBPO")
        self.assertEqual(z["hebel"], 10)
        self.assertLess(z["stop"], z["kurs"])

    def test_staub_und_zu_hoher_einstieg_bleiben_ohne_stop(self):
        pos = {"A": _pos(2.3e-07, 0.0, paar="NEAREUR"),
               "B": _pos(10.0, 12.0, ordertxid="OX")}
        zeilen = M.plan(pos, {"NEAREUR": 3.85, "SUIEUR": 0.8395}, PAARE)
        for z in zeilen:
            self.assertIsNone(z["stop"])
            self.assertTrue(z["hinweis"])


if __name__ == "__main__":
    unittest.main()
