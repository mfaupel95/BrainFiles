"""Fenster, Urteil und Waechter des Optimierers - ohne Netz, ohne echten Lauf."""

import hashlib
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import optimieren                                                 # noqa: E402
import replay                                                     # noqa: E402


class FensterTest(unittest.TestCase):
    def test_fenster_sind_lueckenlos_und_ueberlappungsfrei(self):
        f = optimieren.fenster(4000, 4)
        self.assertEqual(4, len(f))
        self.assertEqual(0, f[0][0][0])
        self.assertEqual(4000, f[-1][1][1])
        for such, pruef in f:
            self.assertLess(such[0], such[1])
            self.assertEqual(such[1], pruef[0])       # lueckenlos
            self.assertLessEqual(such[1], pruef[1])

    def test_zu_kurze_reihe_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            optimieren.fenster(100, 4)

    def test_ein_fenster_ist_erlaubt(self):
        self.assertEqual(1, len(optimieren.fenster(2000, 1)))


class UrteilTest(unittest.TestCase):
    def test_kandidat_ohne_prueffenster_vorteil_ist_kein_hebel(self):
        gleich = {"runden": 20, "netto_pct_mittel": 0.5}
        u = optimieren.urteil_aus([gleich], dict(gleich), [])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("kein Hebel", u["grund"])

    def test_zu_wenige_runden_sind_ein_befund_keine_messung(self):
        u = optimieren.urteil_aus([{"runden": 4, "netto_pct_mittel": 3.0}],
                                  {"runden": 4, "netto_pct_mittel": 3.0}, [])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("Befund", u["grund"])

    def test_hausform_ohne_netto_pct_mittel_wird_verstanden(self):
        """`kosten_wendepunkt.wendepunkt()` liefert kein netto_pct_mittel.

        Genau daran ist der erste Optimierer-Lauf abgestuerzt (KeyError). Das
        Vergleichsmass ist dann ergebnis_summe / runden.
        """
        def haus(runden, summe):
            return {"runden": runden, "ergebnis_summe": summe,
                    "R": 5.0, "C": 10.0, "p": 0.5, "f_max": 2.5}
        self.assertAlmostEqual(0.2, optimieren.je_runde(haus(10, 2.0)))
        u = optimieren.urteil_aus([haus(10, 1.0)], haus(10, 3.0), [haus(10, 2.5)])
        self.assertTrue(u["ueberlebt"])

    def test_besser_im_prueffenster_und_im_mittel_ueberlebt(self):
        u = optimieren.urteil_aus([{"runden": 20, "netto_pct_mittel": 0.1}],
                                  {"runden": 20, "netto_pct_mittel": 1.0},
                                  [{"runden": 20, "netto_pct_mittel": 0.8}])
        self.assertTrue(u["ueberlebt"])

    def test_positiv_im_prueffenster_aber_negatives_mittel_faellt_durch(self):
        u = optimieren.urteil_aus([{"runden": 20, "netto_pct_mittel": 0.1}],
                                  {"runden": 20, "netto_pct_mittel": 0.3},
                                  [{"runden": 20, "netto_pct_mittel": -2.0}])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("rollierendes Mittel", u["grund"])


class SchluesselTest(unittest.TestCase):
    """Der Waechter, der die stille Nullnummer verhindert."""

    def test_fehlender_suchschluessel_bricht_ab_und_nennt_den_namen(self):
        t = {"schluessel": ["gibtsnicht", "pflicht_stop_prozent_min"],
             "raster": {"gibtsnicht": [1], "pflicht_stop_prozent_min": [1]}}
        w = {"pflicht_stop_prozent_min": 5.0, "ziel_r_vielfaches": 2.0}
        with self.assertRaises(RuntimeError) as ctx:
            optimieren.pruefe_schluessel("squeeze", t, w)
        self.assertIn("gibtsnicht", str(ctx.exception))

    def test_vorhandene_schluessel_gehen_durch(self):
        t = {"schluessel": ["ziel_r_vielfaches"], "raster": {"ziel_r_vielfaches": [2]}}
        self.assertTrue(optimieren.pruefe_schluessel("squeeze", t, {"ziel_r_vielfaches": 2.0}))

    def test_unbekannte_spur_wird_gemeldet(self):
        with self.assertRaises(KeyError) as ctx:
            optimieren.suchtabelle("diegibtesnicht")
        self.assertIn("squeeze", str(ctx.exception))

    def test_jede_tabelle_nennt_schluessel_und_raster_zusammen(self):
        for spur in ("squeeze", "wavetrend", "macd_mtf", "supertrend",
                     "trendwende_btc"):
            t = optimieren.suchtabelle(spur)
            self.assertEqual(sorted(t["schluessel"]), sorted(t["raster"]))
            for name, werte in t["raster"].items():
                self.assertGreaterEqual(len(werte), 2, name)


class WachenUnberuehrtTest(unittest.TestCase):
    def test_wachen_patch_schreibt_nicht_in_die_echte_wachen(self):
        def _hash(pfad):
            with open(pfad, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()

        echt = os.path.join(HANDEL, "supertrend", "wachen.json")
        vorher = _hash(echt)
        replay.verzeichnis = lambda: tempfile.mkdtemp()
        replay.lauf_a("supertrend", 0.1, "patchprobe", max_kerzen=900,
                      fenster=400, wachen_patch={"pflicht_stop_prozent_min": 1.0,
                                                 "ziel_r_vielfaches": 1.5})
        self.assertEqual(vorher, _hash(echt))


class ZeitraumTest(unittest.TestCase):
    """Ein zu kurzer Zeitraum wird angehoben und GEMELDET, nicht still gerechnet."""

    def test_zu_kurzer_zeitraum_im_4h_takt_wird_angehoben(self):
        # 6 Monate im 4H-Takt sind 1092 Kerzen - fuer 2 Fenster zu wenig (1200).
        # Vorher stuerzte genau das mit ValueError ab.
        aus = optimieren.suche("supertrend", 0.1, n_fenster=2, monate=6,
                               trocken=True)
        self.assertGreaterEqual(aus["plan"]["kerzen"], 1200)

    def test_kerzen_je_monat_kennt_die_takte(self):
        self.assertGreater(optimieren.kerzen_je_monat("1H"),
                           optimieren.kerzen_je_monat("4H"))
        self.assertGreater(optimieren.kerzen_je_monat("4H"),
                           optimieren.kerzen_je_monat("1D"))


class KerzenuhrTest(unittest.TestCase):
    """Familie A muss DIESELBE Uhr-Naht benutzen wie Familie B.

    Ohne sie schreibt das Backtest-Journal die Wanduhr des Laufs statt der
    Kerzenzeit - gemessen 2026-09-25: alle 48 Zeilen eines 6-Monats-Laufs
    trugen die Uhrzeit des Laufs, und jede Fensterteilung darauf war falsch
    (alle 18 Kandidaten meldeten "0 Runden").
    """

    def test_journalzeit_ist_die_kerzenzeit(self):
        import csv
        import datetime as dt
        import tempfile
        import replay as rp
        tmp = tempfile.mkdtemp()
        alt = rp.verzeichnis
        rp.verzeichnis = lambda: tmp
        try:
            rp.lauf_a("squeeze", 0.1, "uhr", max_kerzen=900, fenster=400)
            pfad = os.path.join(rp.buch_ordner("squeeze", "uhr"),
                                "handelsjournal.csv")
        finally:
            rp.verzeichnis = alt
        with open(pfad, encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
        self.assertGreater(len(zeilen), 0)
        for z in zeilen:
            self.assertTrue(z.get("_kerzen_ts"), "Kerzenstempel fehlt")
            aus_stempel = dt.datetime.fromtimestamp(
                float(z["_kerzen_ts"]) / 1000.0, dt.timezone.utc).isoformat(
                    timespec="seconds")
            self.assertEqual(aus_stempel, z["zeit"])


class TrockenTest(unittest.TestCase):
    def test_trockenlauf_rechnet_nicht_und_schreibt_nicht(self):
        import replay as rp
        tmp = tempfile.mkdtemp()
        alt = rp.verzeichnis
        rp.verzeichnis = lambda: tmp
        try:
            aus = optimieren.suche("squeeze", 0.1, n_fenster=2, monate=6,
                                   trocken=True)
        finally:
            rp.verzeichnis = alt
        self.assertEqual([], aus["kandidaten"])
        self.assertEqual(18, aus["plan"]["kandidaten"])
        self.assertGreater(aus["plan"]["geschaetzte_sekunden"], 0)
        self.assertEqual([], os.listdir(tmp))


if __name__ == "__main__":
    unittest.main()
