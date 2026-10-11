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
            "n": 40, "n_basis": 40, "n_excess": 40, "mean_excess": 1.0,
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

    # 9 - Konfidenz: positives Mittel, aber Streuung zu gross
    def test_streuung_frisst_die_konfidenz(self):
        self.stand("laut", mean_excess=1.0, std_excess=10.0)   # SE = 1.58 %
        ok, g = tor.pruefe("laut", WACHE)
        self.assertFalse(ok)
        self.assertTrue(any("Konfidenzgrenze" in x for x in g), g)

    # 10 - enge Streuung passiert
    def test_enge_streuung_passiert(self):
        self.stand("ruhig", mean_excess=1.0, std_excess=1.0)
        ok, g = tor.pruefe("ruhig", WACHE)
        self.assertTrue(ok, g)

    # 11 - Bonferroni: mehr geprueftes Spuren verschaerfen z
    def test_mehr_spuren_verschaerfen_die_grenze(self):
        # SE = 0.15 -> z-Grenze 0.9/0.15 = 6: bei 1 Spur (z~1.64) offen,
        # bei 40 Spuren (z~3.23) offen, bei 400 Spuren (z~3.72) auch -
        # also einen Grenzfall waehlen: netto 0.9, SE 0.3 -> z-Grenze 3.0
        self.stand("grenzfall", mean_excess=1.0, std_excess=0.3 * 40 ** 0.5)
        ok1, _ = tor.pruefe("grenzfall", WACHE)
        self.assertTrue(ok1)                      # z(1 Spur) = 1.64 < 3.0
        with open(self.merk, encoding="utf-8") as fh:
            sat = json.load(fh)
        for i in range(60):
            sat["spuren"]["x%d" % i] = dict(sat["spuren"]["grenzfall"])
        with open(self.merk, "w", encoding="utf-8") as fh:
            json.dump(sat, fh)
        ok2, g = tor.pruefe("grenzfall", WACHE)
        self.assertFalse(ok2)                     # z(61 Spuren) = 3.34 > 3.0
        self.assertTrue(any("Konfidenzgrenze" in x for x in g), g)

    # 13 - Out-of-Sample: Edge nur in einer Haelfte
    def test_edge_nur_in_einer_haelfte_bleibt_zu(self):
        self.stand("regime", mean_excess=1.0, n_frueh=20, n_spaet=20,
                   mean_excess_frueh=2.0, mean_excess_spaet=0.0)
        ok, g = tor.pruefe("regime", WACHE)
        self.assertFalse(ok)
        self.assertTrue(any("Haelften" in x for x in g), g)

    # 14 - beide Haelften positiv
    def test_edge_in_beiden_haelften_passiert(self):
        self.stand("stabil", mean_excess=1.0, n_frueh=20, n_spaet=20,
                   mean_excess_frueh=1.1, mean_excess_spaet=0.9)
        ok, g = tor.pruefe("stabil", WACHE)
        self.assertTrue(ok, g)

    # 15 - zu kleine Haelfte: keine Pruefung
    def test_zu_kleine_haelfte_entfaellt(self):
        self.stand("klein2", mean_excess=1.0, n_frueh=5, n_spaet=5,
                   mean_excess_frueh=2.0, mean_excess_spaet=-1.0)
        ok, g = tor.pruefe("klein2", WACHE)
        self.assertTrue(ok, g)

    # 12 - aelterer Auditstand ohne std: Bedingung entfaellt
    def test_ohne_std_keine_konfidenzbedingung(self):
        self.stand("alt")
        ok, g = tor.pruefe("alt", WACHE)
        self.assertTrue(ok, g)


class HalbierungTest(unittest.TestCase):
    def test_halbierung_teilt_in_journalreihenfolge(self):
        import spur_audit
        h = spur_audit.halbierung([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual((h["n_frueh"], h["n_spaet"]), (2, 3))
        self.assertAlmostEqual(h["mean_excess_frueh"], 1.5)
        self.assertAlmostEqual(h["mean_excess_spaet"], 4.0)

    def test_halbierung_bei_zu_wenig_werten_leer(self):
        import spur_audit
        h = spur_audit.halbierung([1.0])
        self.assertIsNone(h["mean_excess_frueh"])
        self.assertEqual(h["n_frueh"], 0)


if __name__ == "__main__":
    unittest.main()