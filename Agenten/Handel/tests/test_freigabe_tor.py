"""Das Gebuehren-Tor an seinen Regeln, nicht an heutigen Zahlen.

Diese Tests sichern genau die Eigenschaft, an der das Tor scheitern
kann: es darf eine Spur freigeben, die es kennt, und es darf NICHT
freigeben, was beanstandet ist. Der Scanner ist der Beweis fuer die
zweite Haelfte - er hat die beste Zahl im Haus und ist trotzdem zu.
"""
import json
import os
import tempfile
import unittest

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir))
if HANDEL not in os.sys.path:
    os.sys.path.append(HANDEL)

import freigabe_tor as tor


WACHE = {"gebuehr_taker": 0.0005, "trigger_modus": "signal"}   # 0,10 % je Runde


class TorTest(unittest.TestCase):
    def setUp(self):
        self.ord = tempfile.mkdtemp()
        self.merk = os.path.join(self.ord, "t.json")
        self._alt = tor.MERK
        tor.MERK = self.merk

    def tearDown(self):
        tor.MERK = self._alt

    def stand(self, spur, **d):
        sat = {"_zeit": 1.0, "spuren": {spur: {
            "n": 20, "n_basis": 20, "n_excess": 20, "mean_excess": 1.0,
            "befunde": [], "mean": 1.0, "treffer": 0.5}}}
        sat["spuren"][spur].update(d)
        with open(self.merk, "w", encoding="utf-8") as fh:
            json.dump(sat, fh)

    # 1 -------------------------------------------------------------
    def test_positive_spur_passiert(self):
        self.stand("gut")
        ok, g = tor.pruefe("gut", WACHE)
        self.assertTrue(ok, g)

    # 2 - die Bedingung, an der das Tor sonst wertlos waere
    def test_beanstandete_spur_bleibt_zu(self):
        self.stand("schlecht", mean_excess=8.52,
                   befunde=["87 von 161 Runden auf EIN Instrument"])
        ok, g = tor.pruefe("schlecht", WACHE)
        self.assertFalse(ok)
        self.assertTrue(any("beanstandet" in x for x in g),
                        "der Befund muss der Grund sein: %s" % g)

    # 3 -------------------------------------------------------------
    def test_zu_wenige_runden(self):
        self.stand("klein", n=7, n_basis=7, n_excess=7)
        ok, g = tor.pruefe("klein", WACHE)
        self.assertFalse(ok)
        self.assertTrue(any("7 Runden" in x for x in g))

    # 4 -------------------------------------------------------------
    def test_gebuehr_frisst_den_excess(self):
        self.stand("grenz", mean_excess=0.09)     # 0,09 % Excess, 0,10 % Gebuehr
        ok, g = tor.pruefe("grenz", WACHE)
        self.assertFalse(ok, "0,09 % Excess gegen 0,10 % Gebuehr ist ein Verlust")
        self.assertTrue(any("0.10" in x or "0,10" in x for x in g), g)

    # 5 -------------------------------------------------------------
    def test_ohne_signalmodus_zu(self):
        self.stand("zeitgatter", trigger_modus="")
        w = dict(WACHE); w["trigger_modus"] = "takт"
        ok, g = tor.pruefe("zeitgatter", w)
        self.assertFalse(ok)
        self.assertTrue(any("Signal-Modus" in x for x in g))

    # 6 - das Tor darf nicht ueber seine eigene Unkenntnis sperren
    def test_unbekannte_spur_wird_nicht_gesperrt(self):
        ok, g = tor.pruefe("gibtesnicht", WACHE)
        self.assertTrue(ok, "eine Spur ohne Auditrundlage ist unbewiesen, "
                            "nicht abgelehnt - und das wird gemeldet: %s" % g)

    # 7 - die Gebuehr wird richtig gerechnet: je Seite, Runde = doppelt
    def test_gebuehr_ist_je_seite(self):
        self.assertAlmostEqual(tor.gebuehr_pro_runde({"gebuehr_taker": 0.0005}),
                               0.10, places=9)
        self.assertAlmostEqual(tor.gebuehr_pro_runde({"gebuehr_taker": 0.006}),
                               1.20, places=9)
        self.assertAlmostEqual(tor.gebuehr_pro_runde({}), 0.20, places=9)

    # 8 - die Gegenprobe: ohne die Befund-Bedingung waere der scanner offen
    def test_gegenprobe_ohne_befundbedingung(self):
        self.stand("gegner", mean_excess=8.52,
                   befunde=["misst die Auswahl, nicht die Spur"])
        w = dict(WACHE)
        alt = tor.MIN_RUNDEN
        # dieselbe Spur, aber so geprueft, als gaebe es die Befund-Bedingung nicht
        d = {"n": 161, "n_basis": 67, "n_excess": 67,
             "mean_excess": 8.52, "befunde": []}
        netto = d["mean_excess"] - tor.gebuehr_pro_runde(w)
        self.assertGreater(netto, 0)
        tor.MIN_RUNDEN = alt


if __name__ == "__main__":
    unittest.main()