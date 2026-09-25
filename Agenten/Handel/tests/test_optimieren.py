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
        gleich = {"runden": 40, "netto_pct_mittel": 0.5}
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
        u = optimieren.urteil_aus([haus(50, 5.0)], haus(50, 15.0), [haus(50, 12.5)])
        self.assertTrue(u["ueberlebt"])

    def test_besser_im_prueffenster_und_im_mittel_ueberlebt(self):
        u = optimieren.urteil_aus([{"runden": 40, "netto_pct_mittel": 0.1}],
                                  {"runden": 40, "netto_pct_mittel": 1.0},
                                  [{"runden": 40, "netto_pct_mittel": 0.8}])
        self.assertTrue(u["ueberlebt"])

    def test_positiv_im_prueffenster_aber_negatives_mittel_faellt_durch(self):
        u = optimieren.urteil_aus([{"runden": 40, "netto_pct_mittel": 0.1}],
                                  {"runden": 40, "netto_pct_mittel": 0.3},
                                  [{"runden": 40, "netto_pct_mittel": -2.0}])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("rollierendes Mittel", u["grund"])

    def test_unter_der_mindestrundenzahl_zaehlt_nichts(self):
        """8 Runden waren im ersten Entwurf genug - und liessen 18 von 18 durch."""
        u = optimieren.urteil_aus([{"runden": 12, "netto_pct_mittel": 5.0}],
                                  {"runden": 12, "netto_pct_mittel": 9.0}, [])
        self.assertFalse(u["ueberlebt"])
        self.assertIn("Befund", u["grund"])

    def test_gegen_die_heutige_einstellung_zaehlt_der_vorsprung(self):
        """Positiv, aber nicht besser als der Status quo -> kein Hebel."""
        kand = {"runden": 50, "ergebnis_summe": 50.0}        # 1,0 % je Runde
        basis = {"runden": 50, "ergebnis_summe": 55.0}       # 1,1 % je Runde
        u = optimieren.urteil_aus([kand], kand, [], grundlinie=basis,
                                  gebuehr_pct=0.1)
        self.assertFalse(u["ueberlebt"])
        self.assertIn("heutigen Einstellung", u["grund"])

    def test_klarer_vorsprung_gegen_die_heutige_einstellung_ueberlebt(self):
        kand = {"runden": 50, "ergebnis_summe": 150.0}       # 3,0 % je Runde
        basis = {"runden": 50, "ergebnis_summe": 25.0}       # 0,5 % je Runde
        u = optimieren.urteil_aus([kand], kand, [], grundlinie=basis,
                                  gebuehr_pct=0.1)
        self.assertTrue(u["ueberlebt"])
        self.assertIn("besser als heute", u["grund"])

    def test_gebuehr_wird_abgezogen(self):
        """Brutto 0,15 % je Runde sind netto -0,05 % - kein Hebel."""
        k = {"runden": 50, "ergebnis_summe": 7.5}            # 0,15 % brutto
        self.assertAlmostEqual(0.15, optimieren.je_runde(k), places=6)
        self.assertAlmostEqual(-0.05, optimieren.je_runde(k, 0.1), places=6)
        u = optimieren.urteil_aus([k], k, [], grundlinie={"runden": 50,
                                                          "ergebnis_summe": 0.0},
                                  gebuehr_pct=0.1)
        self.assertFalse(u["ueberlebt"])


class WalkForwardTest(unittest.TestCase):
    """Jedes Fenster zaehlt, nicht "erstes gegen letztes"."""

    @staticmethod
    def f(runden, je_runde):
        return {"runden": runden, "ergebnis_summe": runden * je_runde}

    def test_gewinnt_alle_fenster_und_ist_positiv_im_mittel(self):
        kand = [self.f(50, 1.0), self.f(50, 0.8), self.f(50, 1.2)]
        basis = [self.f(50, 0.2), self.f(50, 0.3), self.f(50, 0.1)]
        u = optimieren.urteil_walkforward(kand, basis, gebuehr_pct=0.1)
        self.assertTrue(u["ueberlebt"])
        self.assertEqual(3, u["fenster_gewonnen"])

    def test_ein_verlorenes_fenster_kippt_das_urteil(self):
        kand = [self.f(50, 1.0), self.f(50, 0.05), self.f(50, 1.2)]
        basis = [self.f(50, 0.2), self.f(50, 0.3), self.f(50, 0.1)]
        u = optimieren.urteil_walkforward(kand, basis, gebuehr_pct=0.1)
        self.assertFalse(u["ueberlebt"])
        self.assertIn("verliert in 1 von 3", u["grund"])

    def test_alle_gewonnen_aber_im_mittel_negativ_faellt_durch(self):
        kand = [self.f(50, 0.05), self.f(50, 0.05)]
        basis = [self.f(50, -0.9), self.f(50, -0.9)]     # noch schlechter
        u = optimieren.urteil_walkforward(kand, basis, gebuehr_pct=0.1)
        self.assertFalse(u["ueberlebt"])
        self.assertIn("negativ", u["grund"])

    def test_zu_wenige_auswertbare_fenster_ist_ein_befund(self):
        kand = [self.f(5, 9.0), self.f(50, 1.0), self.f(4, 8.0)]
        basis = [self.f(5, 0.1), self.f(50, 0.2), self.f(4, 0.1)]
        u = optimieren.urteil_walkforward(kand, basis, gebuehr_pct=0.1)
        self.assertFalse(u["ueberlebt"])
        self.assertIn("Befund", u["grund"])
        self.assertEqual(2, u["fenster_zu_wenig"])

    def test_fenstermittel_wird_berichtet(self):
        kand = [self.f(50, 1.0), self.f(50, 2.0)]
        basis = [self.f(50, 0.1), self.f(50, 0.1)]
        u = optimieren.urteil_walkforward(kand, basis, gebuehr_pct=0.1)
        self.assertAlmostEqual(1.3, u["netto_mittel"], places=3)


class TotesFeldTest(unittest.TestCase):
    """Ein Rasterfeld, das nichts unterscheidet, gehoert in den Bericht."""

    def test_feld_ohne_wirkung_wird_erkannt(self):
        ergebnisse = [
            {"werte": {"stop_max": 8.0, "stop_min": 3.0},
             "je_fenster": [{}, {"runden": 50, "ergebnis_summe": 100.0}]},
            {"werte": {"stop_max": 12.0, "stop_min": 3.0},
             "je_fenster": [{}, {"runden": 50, "ergebnis_summe": 100.0}]},
            {"werte": {"stop_max": 8.0, "stop_min": 7.0},
             "je_fenster": [{}, {"runden": 50, "ergebnis_summe": 20.0}]},
        ]
        self.assertEqual(["stop_max"], optimieren.felder_ohne_wirkung(ergebnisse))

    def test_ohne_gleiche_ergebnisse_ist_nichts_tot(self):
        ergebnisse = [
            {"werte": {"a": 1}, "je_fenster": [{}, {"runden": 50,
                                                    "ergebnis_summe": 10.0}]},
            {"werte": {"a": 2}, "je_fenster": [{}, {"runden": 50,
                                                    "ergebnis_summe": 20.0}]},
        ]
        self.assertEqual([], optimieren.felder_ohne_wirkung(ergebnisse))


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
        # 3 x 3 Rasterfelder. Vorher 18 (3 x 2 x 3) - das tote Feld
        # `pflicht_stop_prozent_max` ist entfernt, siehe spur_opt.json.
        self.assertEqual(9, aus["plan"]["kandidaten"])
        self.assertGreater(aus["plan"]["geschaetzte_sekunden"], 0)
        self.assertEqual([], os.listdir(tmp))


if __name__ == "__main__":
    unittest.main()
