"""Der EMA-Cross gegen die Regel des Originals - nicht gegen Tageswerte.

Geprueft wird, was gelten soll:
  1. Die EMA rechnet so wie nautilus_trader sie rechnet: Seed ist der SMA
     der ersten n Werte, danach alpha = 2/(n+1). Eine andere Saat macht den
     Vergleich mit dem Original wertlos.
  2. Die Regel des Originals woertlich: fast >= slow heisst LONG, sonst
     SHORT. Beide Richtungen muessen vorkommen.
  3. Ohne Kreuz kein Auftrag - das ist der Punkt, an dem diese Spur vom
     Zeitgatter weg ist.
  4. Der Ausstieg dreht nur, wenn die Seite wirklich anders ist.
  5. Zu wenige Kerzen heissen: kein Signal, nicht "long geraten".
  6. Gegenprobe: eine Regel, die nur long liefert, faellt durch.
"""
import importlib.util
import math
import os
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(SPUR)
for p in (HANDEL, SPUR):
    if p not in sys.path:
        sys.path.append(p)

Pfad = os.path.join(SPUR, "handeln.py")
spec = importlib.util.spec_from_file_location("emacross", Pfad)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def kurzen(preise):
    """Kerzen in Hausform: [ts, o, h, l, c, vol]."""
    return [[i * 60, k, k, k, k, 1.0] for i, k in enumerate(preise)]


class EmaTest(unittest.TestCase):
    # 1 -------------------------------------------------------------
    def test_ema_seeds_als_sma_und_nicht_als_erster_wert(self):
        preise = [10.0] * 20
        # Ein reiner SMA-Seed ergibt bei konstanten Werten exakt diesen Wert.
        self.assertAlmostEqual(h.richte_ema(preise, 20), 10.0, places=9)
        # Ein Seed aus dem ERSTEN Wert ergaebe hier 100; der SMA der 20
        # Werte ergibt (100 + 19*1)/20 = 5,95. Genau der Unterschied.
        sprung = [100.0] + [1.0] * 19
        wert = h.richte_ema(sprung, 20)
        self.assertAlmostEqual(wert, 5.95, places=9,
                               msg="SMA der 20 Werte, nicht der erste Wert")

    # 2 -------------------------------------------------------------
    def test_alpha_ist_zwei_ueber_n_plus_eins(self):
        preise = [float(i) for i in range(40)]
        n = 10
        a = 2.0 / (n + 1.0)
        erwartet = sum(preise[:n]) / n
        for k in preise[n:]:
            erwartet = (k - erwartet) * a + erwartet
        self.assertAlmostEqual(h.richte_ema(preise, n), erwartet, places=9)

    # 3 -------------------------------------------------------------
    def test_regel_long_und_short_kommen_beide_vor(self):
        steigend = [float(100 + 3 * i) for i in range(60)]
        fallend = [float(100 + 3 * (59 - i)) for i in range(60)]
        self.assertEqual(h.richtung(kurzen(steigend)[0:], 10, 20), "long")
        self.assertEqual(h.richtung(kurzen(fallend)[0:], 10, 20), "short")

    # 4 -------------------------------------------------------------
    def test_ohne_kreuz_kein_auftrag(self):
        steigend = kurzen([float(100 + 3 * i) for i in range(60)])
        # lang bestaendigt "long": es MELDET die Seite, aber fuer einen
        # Auftrag braucht es einen Wechsel.
        self.assertIsNone(h.neue_richtung(steigend, 10, 20, "long"))
        self.assertEqual(h.neue_richtung(steigend, 10, 20, "short"), "long")

    # 5 -------------------------------------------------------------
    def test_zu_wenige_kerzen_ergeben_kein_signal(self):
        kurz = kurzen([100.0, 101.0, 102.0, 103.0])
        self.assertIsNone(h.richtung(kurz, 10, 20))
        self.assertIsNone(h.signal({"BTC-USDT-SWAP": {"kerzen": kurz}},
                                   {"symbol": "BTC-USDT-SWAP"}))
        self.assertFalse(h.kreuzwechsel(kurz, {"mindest_kerzen": 40}, {"seite": "long"}))

    # 6 -------------------------------------------------------------
    def test_ausstieg_dreht_nur_bei_seitenwechsel(self):
        fallend = kurzen([float(100 + 3 * (79 - i)) for i in range(80)])
        w = {"mindest_kerzen": 40, "ema_schnell": 10, "ema_langsam": 20}
        self.assertTrue(h.kreuzwechsel(fallend, w, {"seite": "long"}),
                        "long im fallenden Markt muss raus")
        self.assertFalse(h.kreuzwechsel(fallend, w, {"seite": "short"}),
                         "short im fallenden Markt bleibt")

    # 7 - die Gegenprobe: eine long-only-Regel darf hier nicht durch
    def test_gegenprobe_long_only_faellt_durch(self):
        fallend = kurzen([float(100 + 3 * (59 - i)) for i in range(60)])
        nur_long = "long"          # die Regel, die die drei Arme fahren
        self.assertNotEqual(nur_long, h.richtung(fallend, 10, 20),
                            "eine long-only-Regel erkennt keinen Short")

    # 8 -------------------------------------------------------------
    def test_schluesse_liest_hausform_und_liste(self):
        k = kurzen([1.0, 2.0, 3.0])
        self.assertEqual(h.schluesse(k), [1.0, 2.0, 3.0])
        self.assertEqual(h.schluesse([1.0, 2.0, 3.0]), [1.0, 2.0, 3.0])


if __name__ == "__main__":
    unittest.main()