"""Zwei Regeln aus dem Handgriff "Kraken-Stops auf 7,5 % stellen" (24.09.2026).

Beide haben sich an echtem Geld gezeigt und sind teuer, wenn sie fehlen:

1. Ein Stop-Loss darf NIE mehr Menge haben als die Brieftasche hergibt. Kraken
   reserviert die Menge eines Stop-Loss; die Brieftasche fuehrt aber den
   NETTO-Zufluss (Gebuehr abgezogen). Das Buch fuehrte 0.00066027 BTC, verfuegbar
   waren 0.0006527067 - der erste Versuch scheiterte mit "EOrder:Insufficient
   funds", und in der Zwischenzeit stand die Position OHNE Stop da.
2. Kraken schreibt DASSELBE Paar zweimal verschieden: "XXBTZEUR"/"XETHZEUR" in
   der Order-Anfrage, "XBTEUR"/"ETHEUR" in der offenen Order. Ein Vergleich der
   rohen Zeichenketten haelt ein geschuetztes Paar fuer ungeschuetzt.

Kein Netz, keine Order - beide Funktionen sind reine Rechnung.
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
    pfad = os.path.join(SPUR, "kraken_stops_7_5.py")
    spec = importlib.util.spec_from_file_location("kraken_stops_7_5_test", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["kraken_stops_7_5_test"] = m
    spec.loader.exec_module(m)
    return m


S = _lade()


class StopMenge(unittest.TestCase):
    def test_nie_mehr_als_verfuegbar(self):
        # Der echte Fall: Buch 0.00066027, verfuegbar 0.0006527067
        self.assertEqual(S.stop_menge(0.00066027, 0.0006527067), 0.0006527)

    def test_position_gewinnt_wenn_kleiner(self):
        # Max haelt mehr SOL als die Spur: der Stop deckt nur die Position.
        self.assertEqual(S.stop_menge(0.48058439, 1.4617934558), 0.48058439)

    def test_abgerundet_auf_die_lotstellen(self):
        self.assertEqual(S.stop_menge(0.04072038, 0.0407176319), 0.04071763)

    def test_nie_aufgerundet(self):
        # Aufrunden wuerde die Order wieder scheitern lassen.
        self.assertLessEqual(S.stop_menge(0.0006527067, 0.0006527067),
                             0.0006527067)


class Paarschreibweisen(unittest.TestCase):
    def test_btc_zwei_schreibweisen_treffen_sich(self):
        self.assertEqual(S.normal("XXBTZEUR"), S.normal("XBTEUR"))
        self.assertEqual(S.normal("XXBTZEUR"), ("BTC", "EUR"))

    def test_eth_und_sol(self):
        self.assertEqual(S.normal("XETHZEUR"), S.normal("ETHEUR"))
        self.assertEqual(S.normal("XETHZEUR"), ("ETH", "EUR"))
        self.assertEqual(S.normal("SOLEUR"), ("SOL", "EUR"))

    def test_dollar_paare(self):
        self.assertEqual(S.normal("XBTUSD"), S.normal("XXBTZUSD"))

    def test_unbekanntes_paar_bleibt_vergleichbar(self):
        self.assertEqual(S.normal("ABCXYZ"), S.normal("abcxyz"))


if __name__ == "__main__":
    unittest.main()
