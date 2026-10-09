"""Tests fuer Agenten/Handel/fib.py - reine Rechnung, ohne Netz.

fib.py wird ueber den PFAD geladen (Hausregel aus tests/): ein sys.path-Eintrag
auf Handel/ koennte gleichnamige Spurenmodule verdecken.
"""

import importlib.util
import os
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
PFAD = os.path.join(HIER, "..", "fib.py")
spec = importlib.util.spec_from_file_location("fib_modul", PFAD)
fib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fib)


def kerzen(punkte, spanne=0.1):
    """Eine Kerze je Preispunkt: High = p+spanne, Low = p-spanne."""
    return [[i, p, p + spanne, p - spanne, p, 1.0] for i, p in enumerate(punkte)]


# Tief 100 (Index 3), Hoch 120 (Index 9), dann Ruecksetzer auf 110.
LONG = [112, 108, 104, 100, 104, 108, 112, 116, 118, 120, 117, 113, 110]
# Spiegelbild: Hoch 120, Tief 100, Ruecksetzer nach oben auf 110.
SHORT = [108, 112, 116, 120, 116, 112, 108, 104, 102, 100, 103, 107, 110]


class PivotTest(unittest.TestCase):
    def test_abwechselnd_und_bestaetigt(self):
        pv = fib.pivots(kerzen(LONG), 2, 2)
        self.assertEqual([t for _, _, t in pv], ["L", "H"])
        self.assertAlmostEqual(pv[0][1], 99.9)
        self.assertAlmostEqual(pv[1][1], 120.1)

    def test_unbestaetigter_pivot_zaehlt_nicht(self):
        # Hoch bei Index 9 hat nur eine Kerze danach -> bei rechts=2 kein Pivot.
        self.assertEqual([t for _, _, t in fib.pivots(kerzen(LONG[:11]), 2, 2)], ["L"])

    def test_gleichstand_ist_kein_pivot(self):
        k = kerzen([10, 10, 10, 10, 10])
        self.assertEqual(fib.pivots(k, 2, 2), [])

    def test_gleiche_art_behaelt_extremeres(self):
        # zwei Tiefs hintereinander ohne Hoch dazwischen -> das tiefere bleibt
        k = kerzen([110, 105, 100, 102, 101, 98, 103, 104, 106, 108])
        pv = fib.pivots(k, 2, 2)
        tiefs = [p for p in pv if p[2] == "L"]
        self.assertEqual(len(tiefs), 1)
        self.assertAlmostEqual(tiefs[0][1], 97.9)


class SwingTest(unittest.TestCase):
    def test_long_bein(self):
        sw = fib.swing(kerzen(LONG), "long", 2, 2, min_hub_pct=1.0)
        self.assertAlmostEqual(sw["tief"], 99.9)
        self.assertAlmostEqual(sw["hoch"], 120.1)

    def test_falsche_seite_gibt_none(self):
        self.assertIsNone(fib.swing(kerzen(LONG), "short", 2, 2))

    def test_short_bein(self):
        sw = fib.swing(kerzen(SHORT), "short", 2, 2)
        self.assertAlmostEqual(sw["hoch"], 120.1)
        self.assertAlmostEqual(sw["tief"], 99.9)

    def test_ursprung_unterschritten_kein_bein(self):
        k = kerzen(LONG + [99, 98])
        self.assertIsNone(fib.swing(k, "long", 2, 2))

    def test_zu_kleiner_hub(self):
        self.assertIsNone(fib.swing(kerzen(LONG), "long", 2, 2, min_hub_pct=50.0))

    def test_ende_wandert_mit_dem_trend(self):
        sw = fib.swing(kerzen(LONG + [122]), "long", 2, 2)
        self.assertAlmostEqual(sw["hoch"], 122.1)

    def test_ungueltige_seite(self):
        with self.assertRaises(ValueError):
            fib.swing(kerzen(LONG), "quer")


class LevelTest(unittest.TestCase):
    def setUp(self):
        self.l = {"seite": "long", "tief": 100.0, "hoch": 120.0}
        self.s = {"seite": "short", "tief": 100.0, "hoch": 120.0}

    def test_retracement_long_und_short(self):
        self.assertAlmostEqual(fib.retracement_preis(self.l, 0.5), 110.0)
        self.assertAlmostEqual(fib.retracement_preis(self.l, 0.618), 120 - 0.618 * 20)
        self.assertAlmostEqual(fib.retracement_preis(self.s, 0.5), 110.0)
        self.assertAlmostEqual(fib.retracement_preis(self.s, 0.618), 100 + 0.618 * 20)

    def test_tiefe(self):
        self.assertAlmostEqual(fib.tiefe(self.l, 110.0), 0.5)
        self.assertAlmostEqual(fib.tiefe(self.s, 110.0), 0.5)
        self.assertAlmostEqual(fib.tiefe(self.l, 120.0), 0.0)

    def test_ziele(self):
        self.assertAlmostEqual(fib.ziel_preis(self.l, 1.0), 120.0)
        self.assertAlmostEqual(fib.ziel_preis(self.l, 1.272), 100 + 1.272 * 20)
        self.assertAlmostEqual(fib.ziel_preis(self.s, 1.0), 100.0)
        self.assertAlmostEqual(fib.ziel_preis(self.s, 1.272), 120 - 1.272 * 20)


class PlanTest(unittest.TestCase):
    def test_long_plan(self):
        p = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=0.5,
                     stop_puffer_pct=0.0)
        self.assertTrue(p["ok"], p["grund"])
        self.assertAlmostEqual(p["stop"], 99.9)
        self.assertTrue(p["in_zone"])
        self.assertLess(p["stop"], 110.0)
        self.assertTrue(all(z["preis"] > 110.0 for z in p["ziele"]))
        self.assertEqual([z["erweiterung"] for z in p["ziele"]], [1.0, 1.272, 1.618])

    def test_short_plan_gespiegelt(self):
        p = fib.plan(kerzen(SHORT), "short", 110.0, links=2, rechts=2, min_r=0.5,
                     stop_puffer_pct=0.0)
        self.assertTrue(p["ok"], p["grund"])
        self.assertAlmostEqual(p["stop"], 120.1)
        self.assertTrue(all(z["preis"] < 110.0 for z in p["ziele"]))

    def test_stop_786_enger_als_ursprung(self):
        a = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=0.5)
        b = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=0.5,
                     stop_art="786")
        self.assertGreater(b["stop"], a["stop"])

    def test_rahmen_lehnt_ab_statt_zu_klemmen(self):
        p = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=0.5,
                     stop_min_pct=2.0, stop_max_pct=4.0)
        self.assertFalse(p["ok"])
        self.assertIn("ueber Rahmen", p["grund"])
        self.assertGreater(p["stop_pct"], 4.0)        # ungeklemmter Wert bleibt sichtbar

    def test_stop_unter_rahmen(self):
        p = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=0.5,
                     stop_min_pct=50.0)
        self.assertFalse(p["ok"])
        self.assertIn("unter Rahmen", p["grund"])

    def test_zone_pflicht(self):
        k = kerzen(LONG)
        # Tiefe bei 117 ~ 0,15 -> ausserhalb 0,5..0,618
        a = fib.plan(k, "long", 117.0, links=2, rechts=2, min_r=0.1)
        b = fib.plan(k, "long", 117.0, links=2, rechts=2, min_r=0.1, zone_pflicht=True)
        self.assertTrue(a["ok"])
        self.assertFalse(a["in_zone"])
        self.assertFalse(b["ok"])

    def test_min_r_lehnt_ab(self):
        p = fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, min_r=1.5)
        self.assertFalse(p["ok"])
        self.assertIn("min", p["grund"])

    def test_kurs_unter_ursprung(self):
        p = fib.plan(kerzen(LONG), "long", 95.0, links=2, rechts=2)
        self.assertFalse(p["ok"])

    def test_ohne_bein(self):
        p = fib.plan(kerzen([10, 10, 10, 10, 10, 10]), "long", 10.0, links=2, rechts=2)
        self.assertFalse(p["ok"])
        self.assertEqual(p["grund"], "kein Bein")

    def test_ungueltige_stop_art(self):
        with self.assertRaises(ValueError):
            fib.plan(kerzen(LONG), "long", 110.0, links=2, rechts=2, stop_art="x")

    def test_kein_blick_nach_vorn(self):
        # Plan auf k[:n] darf sich nicht aendern, wenn spaeter Kerzen folgen,
        # die den Pivot nicht betreffen (Pivot-Bestaetigung nur aus Vergangenheit).
        k = kerzen(LONG)
        a = fib.plan(k, "long", 110.0, links=2, rechts=2, min_r=0.5)
        b = fib.plan(k[:], "long", 110.0, links=2, rechts=2, min_r=0.5)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
