"""Die Richtung in bewertung.bewerten().

richtung="long" ist der Standard und muss unveraendert bleiben - der
Marktscanner waehlt seine Kaeufe damit aus. richtung="short" spiegelt die
Chance-Bausteine auf ihr Gegenstueck (Preis unter den SMAs, Abwaertsrendite,
Erholung vom Tief); die Gewichte und der Rechenweg bleiben dieselben.

Kein Netz: reine Kursreihen.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent / "scanner"))

import bewertung  # noqa: E402


def _reihe(start, ende, tage=200, tief=None, hoch=None):
    """Glatte Reihe von ``start`` nach ``ende``, mit optionalem Extremwert."""
    k = []
    for i in range(tage):
        p = start + (ende - start) * i / (tage - 1)
        k.append([i * 86400000, p,
                  hoch if (hoch and i == tage - 10) else p + 0.5,
                  tief if tief else p - 0.5, p, 1000.0])
    return k


class RichtungTest(unittest.TestCase):

    def test_long_ist_der_standard(self):
        k = _reihe(100.0, 128.0)
        self.assertEqual(bewertung.bewerten(k),
                         bewertung.bewerten(k, richtung="long"))

    def test_fallende_reihe_ist_ein_short_fall(self):
        k = _reihe(156.0, 128.0, tief=118.0)
        self.assertGreater(
            bewertung.bewerten(k, richtung="short")["score"],
            bewertung.bewerten(k)["score"])

    def test_steigende_reihe_ist_ein_long_fall(self):
        k = _reihe(100.0, 128.0)
        self.assertGreater(
            bewertung.bewerten(k)["score"],
            bewertung.bewerten(k, richtung="short")["score"])

    def test_kennzahlen_tragen_beide_abstaende(self):
        k = _reihe(156.0, 128.0, tief=118.0)
        kn = bewertung.bewerten(k)["kennzahlen"]
        self.assertAlmostEqual(kn["abstand_60t_tief_pct"], 8.5, places=1)
        self.assertLess(kn["abstand_60t_hoch_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
