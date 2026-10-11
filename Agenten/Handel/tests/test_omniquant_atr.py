"""T-393 a (11.10.2026): der ATR-Stop der Omniquant-Spur.

Auftrag Max: omniquant soll Stop/Ziel wie xperp aus dem ATR rechnen
(stop_atr_faktor 1.5, ziel_atr_faktor 3.0, 4H-Kerzen n=14), statt die
5..12-%-Klammer aus dem Prognose-Bericht zu erben. Bei Hebel 6 kostete der
Median-Stop (11,3 %) rund 68 % des Einsatzes (Messung am Journal 11.10.2026).

Geprueft wird die REGEL, kein eingefrorener Stand:
  * gesetzter stop_atr_faktor -> Stop/Ziel aus dem ATR, nicht aus dem Bericht,
  * kein stop_atr_faktor -> Berichtswerte unveraendert (Rueckfall),
  * ATR nicht berechenbar -> Kandidat wird uebersprungen (nicht geraten),
  * die R:R bleibt 2:1 (3.0/1.5) - das ist der Sinn der Faktoren.

Kein Netz: okx.kerzen und letzter_kurs_quelle sind Attrappen.
"""
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
SPUR = os.path.join(HANDEL, "omniquant")
if SPUR not in sys.path:
    sys.path.insert(0, SPUR)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handeln as h                                              # noqa: E402
import okx as okx_mod                                            # noqa: E402


def _kerzen_steigend(close=10.0, anzahl=40):
    """Aufsteigende Kerzen [ts, o, h, l, c, v] - ATR traegt, R:R sauber."""
    out = []
    for i in range(anzahl):
        c = close + i * 0.01
        out.append([i * 3600 * 4, c - 0.02, c + 0.03, c - 0.03, c, 1000.0])
    return out


class AtrStopZielTest(unittest.TestCase):
    def setUp(self):
        self.echte_kerzen = okx_mod.kerzen
        self.echte_kurs = h.letzter_kurs_quelle
        h.letzter_kurs_quelle = lambda inst: 10.0
        h.bericht_quelle = None

    def tearDown(self):
        okx_mod.kerzen = self.echte_kerzen
        h.letzter_kurs_quelle = self.echte_kurs
        h.bericht_quelle = None

    def _w(self, **kw):
        w = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0}
        w.update(kw)
        return w

    def test_atr_faktoren_liefern_zweizu_eins(self):
        """Stop 1.5 x ATR, Ziel 3.0 x ATR -> Abstaende 2:1, abhaengig vom ATR."""
        okx_mod.kerzen = lambda inst, bar, anzahl: _kerzen_steigend()
        stop, ziel = h._atr_stop_ziel(self._w(), "SOL-USDT", "long",
                                      10.0, 9.0, 11.0)
        self.assertIsNotNone(stop)
        self.assertIsNotNone(ziel)
        abstand_stop = 10.0 - stop
        abstand_ziel = ziel - 10.0
        # Rundung/Ticks egal - der Quotient muss ~2 sein (3.0/1.5)
        self.assertAlmostEqual(abstand_ziel / abstand_stop, 2.0, places=3,
                               msg="R:R = ziel_atr_faktor / stop_atr_faktor")

    def test_atr_rechnet_enger_als_die_berichtsklammer(self):
        """Der Kern der Entscheidung: ATR-Stop ist enger als 5..12 %."""
        okx_mod.kerzen = lambda inst, bar, anzahl: _kerzen_steigend()
        stop, ziel = h._atr_stop_ziel(self._w(), "SOL-USDT", "long",
                                      10.0, 9.0, 11.0)
        breite = (10.0 - stop) / 10.0 * 100.0
        self.assertLess(breite, 5.0,
                        "ATR-Stop muss unter der Berichtsklammer (5 %) liegen, "
                        "sonst haette die Umstellung keinen Sinn")

    def test_ohne_faktor_bleiben_berichtswerte(self):
        """Rueckfall: kein stop_atr_faktor -> Bericht unveraendert."""
        okx_mod.kerzen = lambda inst, bar, anzahl: (_ for _ in ()).throw(
            AssertionError("ohne Faktor darf kein ATR geholt werden"))
        stop, ziel = h._atr_stop_ziel({}, "SOL-USDT", "long", 10.0, 9.0, 11.0)
        self.assertEqual(stop, 9.0)
        self.assertEqual(ziel, 11.0)

    def test_kaputte_kerzen_sind_kein_kandidat(self):
        """Keine Kerzen / kein ATR -> (None, None) -> Kandidat uebersprungen."""
        okx_mod.kerzen = lambda inst, bar, anzahl: []
        stop, ziel = h._atr_stop_ziel(self._w(), "SOL-USDT", "long",
                                      10.0, 9.0, 11.0)
        self.assertIsNone(stop)
        self.assertIsNone(ziel)

    def test_kandidaten_ueberschreibt_den_bericht(self):
        """kandidaten() reicht die ATR-Werte durch, der Bericht bleibt Preis."""
        okx_mod.kerzen = lambda inst, bar, anzahl: _kerzen_steigend()
        h.bericht_quelle = {
            "erzeugt": "2026-10-11T10:00:00+00:00",
            "treffer": [{"inst": "SOL-USDT", "richtung": "long",
                         "stop": 9.0, "ziel": 11.0,
                         "score": 60.0, "cr": 2.0}],
        }
        z = {"positionen": [], "erledigt": []}
        aus, fehler = h.kandidaten(z, self._w(), {})
        self.assertIsNone(fehler)
        self.assertEqual(len(aus), 1)
        self.assertNotEqual(aus[0]["stop"], 9.0,
                            "der Bericht-Stop ist ersetzt")
        self.assertNotEqual(aus[0]["ziel"], 11.0)
        abstand_stop = aus[0]["kurs"] - aus[0]["stop"]
        abstand_ziel = aus[0]["ziel"] - aus[0]["kurs"]
        self.assertAlmostEqual(abstand_ziel / abstand_stop, 2.0, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
