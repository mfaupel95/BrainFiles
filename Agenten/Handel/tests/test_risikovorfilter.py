"""Tests fuer den Risiko-Vorfilter (`Handel/risikovorfilter.py`) - ohne Netz.

Der Vorfilter setzt die Zahlen des Moon-Dev `risk_agent` um (12-Stunden-Fenster,
+/-5 % beziehungsweise +/-25 USD) und laeuft VOR dem Einstieg. Geprueft wird
hier:

  * die Paarung Kauf/Verkauf aus dem Journal (ohne Paarung kein Ergebnis),
  * das Zeitfenster (aeltere Runden zaehlen nicht),
  * Verlustgrenze, Gewinnziel, Prozent- und Buchrisiko-Grenze,
  * dass der Vorfilter AUS ist, solange die Wache ihn nicht einschaltet,
  * der Einbau im Buch: bei gerissener Grenze entsteht keine Position.
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner")):
    if p not in sys.path:
        sys.path.insert(0, p)

import risikovorfilter as vf  # noqa: E402
import spur_buch as buch  # noqa: E402

JETZT = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
WACHEN = {
    "risikovorfilter": True,
    "risiko_fenster_stunden": 12.0,
    "risiko_verlust_max_usd": 25.0,
    "risiko_verlust_max_pct": 5.0,
    "risiko_gewinn_ziel_usd": 25.0,
    "risiko_gewinn_ziel_pct": 5.0,
    "max_gesamt_usd": 300.0,
    "risiko_buchdeckel_usd": None,
}

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis", "einsatz_usd",
           "stop", "ziel", "stop_pct", "grund"]


def journal(runden, tmp, jetzt=None):
    """Journal mit Paaren schreiben: runden = [(alter_stunden, kauf, verkauf)].

    jetzt ist der Bezugspunkt der Alterangaben. Die reinen Funktionstests
    uebergeben ihr festes JETZT; der Einbautest geht durch buch.einstieg() und
    damit durch risikovorfilter, das datetime.now() liest - dort MUSS der
    Bezugspunkt die echte Uhr sein, sonst liegt das synthetische Journal
    ausserhalb des 12-Stunden-Fensters und der Test faellt (Befund 21.09.2026:
    JETZT stand fest auf dem 17.09., der Test war nur an seinem eigenen Tag
    gruen).
    """
    jetzt = jetzt or datetime.now(timezone.utc)
    p = os.path.join(tmp, "handelsjournal.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        w.writeheader()
        for i, (alter, kauf, verkauf) in enumerate(runden):
            t = (jetzt - timedelta(hours=alter)).isoformat(timespec="seconds")
            w.writerow({"zeit": t, "modus": "papier", "aktion": "kauf",
                        "inst": "TEST%d" % i, "seite": "long", "preis": "100",
                        "einsatz_usd": "%.2f" % kauf,
                        "grund": "test"})
            w.writerow({"zeit": t, "modus": "papier", "aktion": "verkauf",
                        "inst": "TEST%d" % i, "seite": "long", "preis": "100",
                        "einsatz_usd": "%.2f" % verkauf,
                        "grund": "test"})
    return p


class FensterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_paarung_und_ergebnis(self):
        p = journal([(1, 100.0, 110.0)], self.tmp.name, jetzt=JETZT)
        ergebnis, einsatz, n = vf.fenster_pnl(p, WACHEN, JETZT)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(ergebnis, 10.0)
        self.assertAlmostEqual(einsatz, 100.0)

    def test_alte_runden_zaehlen_nicht(self):
        p = journal([(20, 100.0, 50.0)], self.tmp.name, jetzt=JETZT)
        ergebnis, einsatz, n = vf.fenster_pnl(p, WACHEN, JETZT)
        self.assertEqual(n, 0)
        self.assertAlmostEqual(ergebnis, 0.0)

    def test_verkauf_ohne_kauf_zaehlt_nicht(self):
        p = os.path.join(self.tmp.name, "j.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN)
            w.writeheader()
            w.writerow({"zeit": JETZT.isoformat(), "aktion": "verkauf",
                        "inst": "X", "einsatz_usd": "100"})
        self.assertEqual(vf.fenster_pnl(p, WACHEN, JETZT)[2], 0)


class GrenzenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.z = {"positionen": []}

    def tearDown(self):
        self.tmp.cleanup()

    def test_verlustgrenze_stoppt(self):
        p = journal([(1, 100.0, 70.0)], self.tmp.name, jetzt=JETZT)     # -30 USD
        ok, warum = vf.pruefe(WACHEN, p, self.z, 5.0, JETZT)
        self.assertFalse(ok)
        self.assertIn("Tagesverlust", warum)

    def test_gewinnziel_stoppt(self):
        p = journal([(1, 100.0, 130.0)], self.tmp.name, jetzt=JETZT)    # +30 USD
        ok, warum = vf.pruefe(WACHEN, p, self.z, 5.0, JETZT)
        self.assertFalse(ok)
        self.assertIn("Gewinn", warum)

    def test_prozentgrenze_stoppt_frueher_als_die_betragsgrenze(self):
        # -6 USD auf 20 USD Einsatz sind -30 %, aber noch unter 25 USD.
        p = journal([(1, 20.0, 14.0)], self.tmp.name, jetzt=JETZT)
        ok, warum = vf.pruefe(WACHEN, p, self.z, 5.0, JETZT)
        self.assertFalse(ok)
        self.assertIn("%", warum)

    def test_ruhiges_fenster_laesst_durch(self):
        p = journal([(1, 100.0, 101.0)], self.tmp.name, jetzt=JETZT)
        ok, warum = vf.pruefe(WACHEN, p, self.z, 5.0, JETZT)
        self.assertTrue(ok, warum)

    def test_buchdeckel_greift(self):
        z = {"positionen": [{"nominal": 299.0, "stop_pct": 100.0}]}
        p = journal([], self.tmp.name, jetzt=JETZT)
        ok, warum = vf.pruefe(WACHEN, p, z, 5.0, JETZT)
        self.assertFalse(ok)
        self.assertIn("Deckel", warum)

    def test_ohne_schalter_ist_der_vorfilter_aus(self):
        w = dict(WACHEN)
        w["risikovorfilter"] = False
        p = journal([(1, 100.0, 10.0)], self.tmp.name, jetzt=JETZT)     # -90 USD
        ok, warum = vf.pruefe(w, p, self.z, 5.0, JETZT)
        self.assertTrue(ok)
        self.assertIn("aus", warum)

    def test_lage_zeigt_das_fenster(self):
        p = journal([(1, 100.0, 95.0)], self.tmp.name, jetzt=JETZT)
        lage = vf.lage(WACHEN, p, self.z, JETZT)
        self.assertTrue(lage["aktiv"])
        self.assertEqual(lage["runden"], 1)
        self.assertAlmostEqual(lage["ergebnis_usd"], -5.0)


class EinbauTest(unittest.TestCase):
    """Der Vorfilter greift im Buch - VOR dem Einstieg, nicht danach."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (buch.SCHREIBEN,)
        buch.SCHREIBEN = True
        w = dict(WACHEN)
        w.update({"risiko_je_position_usd": 5.0, "max_pro_trade_usd": 100.0,
                  "stop_prozent": 5.0, "pflicht_stop_prozent_min": 3.0,
                  "pflicht_stop_prozent_max": 12.0, "ziel_r_vielfaches": 1.5,
                  "max_offene_positionen": 3, "drawdown_halbierung_usd": 15.0})
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)

    def tearDown(self):
        buch.SCHREIBEN = self.alt[0]
        self.tmp.cleanup()

    def test_bei_gerissener_grenze_entsteht_keine_position(self):
        journal([(1, 100.0, 60.0)], self.tmp.name)          # -40 USD
        z = {"positionen": []}
        p = buch.einstieg(z, "BTC", "long", 100.0,
                          {"risiko_je_position_usd": 5.0, "max_pro_trade_usd": 100.0,
                           "stop_prozent": 5.0, "pflicht_stop_prozent_min": 3.0,
                           "pflicht_stop_prozent_max": 12.0, "ziel_r_vielfaches": 1.5,
                           "risikovorfilter": True, "max_gesamt_usd": 300.0},
                          1.0, "test",
                          journal_pfad=os.path.join(self.tmp.name,
                                                    "handelsjournal.csv"))
        self.assertIsNone(p)
        self.assertEqual(z["positionen"], [])

    def test_ohne_vorfilter_wird_gebucht(self):
        journal([(1, 100.0, 60.0)], self.tmp.name)
        z = {"positionen": []}
        p = buch.einstieg(z, "BTC", "long", 100.0,
                          {"risiko_je_position_usd": 5.0, "max_pro_trade_usd": 100.0,
                           "stop_prozent": 5.0, "pflicht_stop_prozent_min": 3.0,
                           "pflicht_stop_prozent_max": 12.0, "ziel_r_vielfaches": 1.5,
                           "max_gesamt_usd": 300.0},
                          1.0, "test",
                          journal_pfad=os.path.join(self.tmp.name,
                                                    "handelsjournal.csv"))
        self.assertIsNotNone(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
