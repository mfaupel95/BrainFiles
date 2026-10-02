"""Gegenbeweis zur Skalierungsregel (03.10.2026).

Nicht "die Zeile steht im Quelltext", sondern die drei Aussagen, die zaehlen:
1. Ein zweites Signal auf dieselbe Position vergroessert sie und legt KEINE
   zweite an - der Platzzaehler steigt nicht.
2. Einstieg wird der gewichtete Preis, Stop und Ziel entstehen daraus neu.
3. Die Auswertung rechnet die Runde mit dem KUMULATIVEN Einsatz, nicht mit
   dem ersten - sonst waeren Trefferquote und Ergebnis falsch.

Die Gegenprobe: mit zurueckgenommener Skalierung (Regel aus dem Spiel) muss
der dritte Test rot werden.
"""
import os
import sys
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import auswertung_alle  # noqa: E402
import skalieren        # noqa: E402


class SkalierenTest(unittest.TestCase):
    def basis(self):
        return {"inst": "BTC-USDT", "seite": "long", "einstieg": 100.0,
                "nominal": 500.0, "stop": 96.0, "ziel": 108.0,
                "stop_pct": 4.0, "pos_id": "P1"}

    def test_zweites_signal_vergroessert_statt_zu_doppeln(self):
        p = self.basis()
        positionen = [p]
        offen = skalieren.finde_offene(positionen, "BTC-USDT", "long")
        self.assertIsNotNone(offen)
        f = skalieren.skaliere(offen, 110.0, 500.0, 4.0, 2.0)
        self.assertIsNotNone(f)
        # Genau EINE Position, nicht zwei
        self.assertEqual(len(positionen), 1)
        self.assertEqual(p["nominal"], 1000.0)
        self.assertEqual(p["skalierungen"], 1)

    def test_einstieg_ist_gewichtet_stop_und_ziel_neu(self):
        p = self.basis()
        skalieren.skaliere(p, 110.0, 500.0, 4.0, 2.0)
        # gewichtet: (100*500 + 110*500)/1000 = 105
        self.assertAlmostEqual(p["einstieg"], 105.0, places=6)
        # Stop und Ziel aus dem NEUEN Einstieg, nicht aus dem alten Preis
        self.assertAlmostEqual(p["stop"], 105.0 * 0.96, places=6)
        self.assertAlmostEqual(p["ziel"], 105.0 * 1.08, places=6)

    def test_seitenwechsel_ist_kein_skalieren(self):
        p = self.basis()
        self.assertIsNone(skalieren.finde_offene([p], "BTC-USDT", "short"))
        # anderes Instrument auch nicht
        self.assertIsNone(skalieren.finde_offene([p], "ETH-USDT", "long"))


class RechenwegTest(unittest.TestCase):
    def test_runde_rechnet_mit_kumulativem_einsatz(self):
        zeilen = [
            {"zeit": "2026-10-01T10:00:00+00:00", "aktion": "kauf",
             "pos_id": "P1", "inst": "BTC", "einsatz_usd": "500.00"},
            {"zeit": "2026-10-01T11:00:00+00:00", "aktion": "kauf",
             "pos_id": "P1", "inst": "BTC", "einsatz_usd": "1000.00"},
            {"zeit": "2026-10-02T09:00:00+00:00", "aktion": "verkauf",
             "pos_id": "P1", "inst": "BTC", "einsatz_usd": "1200.00"},
        ]
        runden = auswertung_alle.runden_indikator(zeilen)
        self.assertEqual(len(runden), 1, "eine skalierte Position ist EINE Runde")
        # 1200 Erloes - 1000 kumulativer Einsatz = +200, nicht +700
        self.assertAlmostEqual(float(runden[0]["ergebnis"]), 200.0, places=2)

    def test_einfache_position_unveraendert(self):
        zeilen = [
            {"zeit": "2026-10-01T10:00:00+00:00", "aktion": "kauf",
             "pos_id": "P2", "inst": "BTC", "einsatz_usd": "500.00"},
            {"zeit": "2026-10-02T09:00:00+00:00", "aktion": "verkauf",
             "pos_id": "P2", "inst": "BTC", "einsatz_usd": "600.00"},
        ]
        runden = auswertung_alle.runden_indikator(zeilen)
        self.assertEqual(len(runden), 1)
        self.assertAlmostEqual(float(runden[0]["ergebnis"]), 100.0, places=2)

    def test_inkrementform_wuerde_die_runde_verfaelschen(self):
        """Gegenprobe: mit INKREMENT statt kumulativem Einsatz ginge die
        Rechnung in die Irre - deshalb schreibt die Regel kumulativ.

        Erloes 1200, Einsatz in der Summe 1000. Schriebe die zweite Zeile
        nur ihr eigenes Stueck (500), bliebe als Einsatz 500 stehen und die
        Runde meldete +700 statt +200 - eine Erfolgsquote, die keine ist.
        """
        inkrement = [
            {"zeit": "2026-10-01T10:00:00+00:00", "aktion": "kauf",
             "pos_id": "P3", "inst": "BTC", "einsatz_usd": "500.00"},
            {"zeit": "2026-10-01T11:00:00+00:00", "aktion": "kauf",
             "pos_id": "P3", "inst": "BTC", "einsatz_usd": "500.00"},
            {"zeit": "2026-10-02T09:00:00+00:00", "aktion": "verkauf",
             "pos_id": "P3", "inst": "BTC", "einsatz_usd": "1200.00"},
        ]
        runden = auswertung_alle.runden_indikator(inkrement)
        self.assertEqual(len(runden), 1)
        # Genau deshalb ist die Inkrementform falsch: sie zaehlt nur die
        # letzte Zeile und verliert die erste Haelfte des Einsatzes.
        self.assertAlmostEqual(float(runden[0]["ergebnis"]), 700.0, places=2)
        self.assertNotAlmostEqual(float(runden[0]["ergebnis"]), 200.0, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)