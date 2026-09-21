"""Tests fuer die Trendwende-Spur (trendwende_btc).

Geprueft wird die REGEL, nicht ein Datenlauf:
  - ein Wechsel des SuperTrend von +1 auf -1 mit Schluss UNTER der EMA200
    ergibt 'short',
  - derselbe Wechsel UEBER der EMA200 ergibt nichts (Ruecksetzer im
    Aufwaertstrend),
  - ein gleichbleibender Trend ergibt nichts (nur der Wechsel zaehlt),
  - zu wenig Kerzen ergeben nichts (kein Signal aus dem Nichts).

Dazu der Modulwaechter: die reinen Funktionen duerfen nichts schreiben. Die
Spur ist neu (21.09.2026) und hat noch keinen Live-Zweig; ein Test, der im
echten Buch landet, waere hier besonders teuer.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402


def _kerzen(schlusskurse):
    """Kerzen aus Schlusskursen: [ts, open, high, low, close, vol]."""
    raus = []
    for i, c in enumerate(schlusskurse):
        raus.append([1_700_000_000_000 + i * 3_600_000,
                     c, c * 1.001, c * 0.999, c, 10.0])
    return raus


WACHEN = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))
W = dict(WACHEN, ema_filter_n=200, supertrend_n=10, supertrend_faktor=3.0)


class Signal(unittest.TestCase):
    @staticmethod
    def _serie(auf, s1, ab=0, s2=1.0, letzte=1.0):
        """Kerzenreihe aus Schrittfaktoren.

        Die Zahlen sind nicht geraten, sondern gesucht: die Faelle unten sind
        die Kombinationen, bei denen der SuperTrend GENAU auf der letzten Kerze
        dreht (FLIP = richtung[-2] +1, richtung[-1] -1) und die EMA-Bedingung
        einmal erfuellt ist und einmal nicht. So prueft der Test die Regel und
        nicht die Laune einer willkuerlichen Reihe.
        """
        kurs, raus = 100.0, []
        for _ in range(auf):
            kurs *= s1
            raus.append(kurs)
        for _ in range(ab):
            kurs *= s2
            raus.append(kurs)
        kurs *= letzte
        raus.append(kurs)
        return raus

    def test_wendepunkt_unter_der_ema_ergibt_short(self):
        # Seitenwaerts (260), dann drei Kerzen leicht und die letzte deutlich
        # nach unten: SuperTrend dreht, Schluss 98.70 < EMA 99.98.
        d = {"kerzen": _kerzen(self._serie(260, 1.0, 3, 0.999, 0.99))}
        self.assertEqual(h.signal(d, W), "short")

    def test_aufwaertstrend_ergibt_nichts(self):
        d = {"kerzen": _kerzen(self._serie(300, 1.003))}
        self.assertIsNone(h.signal(d, W))

    def test_zu_wenige_kerzen_ergeben_nichts(self):
        d = {"kerzen": _kerzen([100.0] * 50)}
        self.assertIsNone(h.signal(d, W))

    def test_leere_daten_ergeben_nichts(self):
        self.assertIsNone(h.signal({}, W))
        self.assertIsNone(h.signal({"kerzen": []}, W))

    def test_kurzer_ruecksetzer_im_aufwaertstrend_ergibt_nichts(self):
        # Aufstieg mit 1.0005 je Kerze, dann eine einzelne Kerze -3 %: der
        # SuperTrend dreht, der Schluss (110.46) liegt aber NOCH ueber der
        # EMA200 (108.62). Genau der Fall, den der Filter abfangen soll.
        d = {"kerzen": _kerzen(self._serie(260, 1.0005, 3, 1.0, 0.97))}
        self.assertIsNone(h.signal(d, W), "Ruecksetzer ist keine Wende")


class KeinSchreiben(unittest.TestCase):
    """quelle()/signal() sind reine Funktionen - sie duerfen nichts anlegen."""

    def test_reine_funktionen_beruehren_keine_dateien(self):
        vorher = {p.name for p in SPUR.iterdir()}
        h.signal({"kerzen": _kerzen([100.0] * 400)}, W)
        nachher = {p.name for p in SPUR.iterdir()}
        self.assertEqual(vorher, nachher)


class Wachen(unittest.TestCase):
    def test_kein_live_und_keine_freigabe(self):
        self.assertFalse(WACHEN["handel_erlaubt"])
        self.assertFalse(WACHEN["freigabe"]["erfuellt"])

    def test_ratschenbetrag_ist_das_buchrisiko(self):
        soll = (WACHEN["risiko_je_position_usd"]
                * WACHEN["max_offene_positionen"])
        self.assertEqual(WACHEN["drawdown_halbierung_usd"], soll)

    def test_stop_und_ziel_passen_zusammen(self):
        self.assertLessEqual(WACHEN["pflicht_stop_prozent_min"],
                             WACHEN["stop_prozent"])
        self.assertLessEqual(WACHEN["stop_prozent"],
                             WACHEN["pflicht_stop_prozent_max"])
        self.assertGreater(WACHEN["ziel_r_vielfaches"], 1.0)

    def test_zweitziel_zeigt_auf_q(self):
        self.assertTrue(WACHEN["journal_zweitziel"].startswith("Q:"))


if __name__ == "__main__":
    unittest.main()
