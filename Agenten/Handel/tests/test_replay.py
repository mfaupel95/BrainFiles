"""Schreibschutz, Backtest-Ordner und Gegenprobe des Replay-Kerns.

Der wichtigste Test dieser Datei ist `NichtsAusserhalbTest`: er vergleicht
Dateiliste und Groessen des ECHTEN Spurenordners und der Q:-Spiegelung vor und
nach einem Replay-Lauf. Ein Test, der in ein echtes Ziel schreibt, hat hier
nichts zu suchen (Lehre vom 14.09.2026, TEST-Q:-FALLE).

`replay.verzeichnis` zeigt in JEDEM Test auf einen Temp-Ordner - auch der
Backtest-Bereich selbst wird nicht angefasst.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import replay                                                     # noqa: E402

# Kurze Reihe = schneller Lauf. Die Spuren rechnen ihre Indikatoren je Schritt
# ueber die ganze Reihe; die volle Historie dauerte Stunden.
KERZEN = 1200


def _inventar(ordner):
    """{pfad: groesse} eines Ordners, ohne __pycache__."""
    aus = {}
    for wurzel, _, dateien in os.walk(ordner):
        if "__pycache__" in wurzel:
            continue
        for d in dateien:
            p = os.path.join(wurzel, d)
            try:
                aus[p] = os.path.getsize(p)
            except OSError:
                aus[p] = -1
    return aus


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = replay.verzeichnis
        replay.verzeichnis = lambda: self.tmp.name

    def tearDown(self):
        replay.verzeichnis = self.alt
        self.tmp.cleanup()


class NichtsAusserhalbTest(ReplayTest):
    def test_replay_ruehrt_den_echten_spurenordner_nicht_an(self):
        spur = os.path.join(HANDEL, "supertrend")
        vorher = _inventar(spur)
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        self.assertEqual(vorher, _inventar(spur))

    def test_replay_ruehrt_die_auss_er_haus_kopie_nicht_an(self):
        ziel = "Q:\\Handel_Journal\\supertrend"
        if not os.path.isdir(ziel):
            self.skipTest("Q: nicht angeschlossen")
        vorher = _inventar(ziel)
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        self.assertEqual(vorher, _inventar(ziel))

    def test_replay_schreibt_in_den_backtest_ordner(self):
        runden, offen = replay.lauf_a("supertrend", gebuehr_pct=0.1,
                                      lauf="test", max_kerzen=KERZEN)
        ordner = replay.buch_ordner("supertrend", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        self.assertTrue(ordner.startswith(self.tmp.name))
        self.assertGreater(len(runden), 0)

    def test_das_journal_ist_lesbar_und_liefert_runden(self):
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        k = replay.kennzahlen(os.path.join(replay.buch_ordner("supertrend", "test"),
                                           "handelsjournal.csv"))
        # Der eigentliche Punkt: das Journal hat EIN-/AUSSTIEGSZEILEN, sonst
        # gaebe es nichts zu paaren und die Runden waeren 0.
        self.assertGreater(k["runden"], 0)
        self.assertIn("f_max", k)


class BuchOrdnerTest(ReplayTest):
    def test_wachen_kopie_zeigt_nach_innen(self):
        ordner = replay.buch_ordner("supertrend", "a")
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertNotIn("Q:", str(w.get("journal_zweitziel")))
        self.assertEqual(ordner, w["journal_zweitziel"])
        self.assertFalse(w["handel_erlaubt"])
        self.assertTrue(ordner.startswith(self.tmp.name))

    def test_spur_ohne_handeln_wird_benannt(self):
        with self.assertRaises(FileNotFoundError):
            replay.spur_modul("gibtesnicht")


class FensterTest(ReplayTest):
    """Das rollierende Fenster: schnell, treu und plausibel.

    Im Betrieb sieht eine Spur nie die ganze Geschichte, sondern ihre feste
    `kerzen_anzahl`. Das Fenster bildet das nach - und macht den Lauf ueber
    Jahre erst bezahlbar (ohne Fenster ist jeder Schritt O(n), der Lauf O(n^2)).
    """

    def test_fenster_liefert_runden_und_keine_unmoeglichen_werte(self):
        runden, offen = replay.lauf_a("supertrend", 0.1, "fenster",
                                      max_kerzen=3000, fenster=400)
        self.assertGreater(len(runden), 10)
        for r in runden:
            # Stop 5 %, Ziel 10 % - mehr als 50 % Bewegung ist bei diesen
            # Regeln unmoeglich und waere das Zeichen eines Instrumenten-
            # Durcheinanders (Kerzen des einen, Position des anderen).
            self.assertLess(abs(r["ausstieg"] / r["einstieg"] - 1.0), 0.5)
            self.assertIn(r["inst"], ("BTC-USDC", "ETH-USDC", "SOL-USDC"))

    def test_fenster_ist_schneller_als_das_praefix(self):
        import time
        t0 = time.time()
        replay.lauf_a("supertrend", 0.1, "schnell", max_kerzen=2000, fenster=400)
        mit = time.time() - t0
        t0 = time.time()
        replay.lauf_a("supertrend", 0.1, "langsam", max_kerzen=2000)
        ohne = time.time() - t0
        self.assertLess(mit, ohne)


class FamilieBTest(ReplayTest):
    """Familie B laeuft ueber `spur_buch.zyklus` - und darf nichts nach aussen.

    Drei Dinge muessen nach dem Lauf unveraendert sein: der Bus (kein Eintrag),
    die Zeituhr von `spur_buch` und das echte Q:-Ziel.
    """

    def test_lauf_b_bucht_in_den_backtest_ordner(self):
        k, zeilen = replay.lauf_b("trendwende_btc", gebuehr_pct=0.05,
                                  lauf="test", max_kerzen=1500, fenster=400)
        ordner = replay.buch_ordner("trendwende_btc", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        self.assertTrue(ordner.startswith(self.tmp.name))
        self.assertIn("runden", k)

    def test_lauf_b_oeffnet_keine_bus_meldung(self):
        # spur_buch zuerst: es legt den Bus-Ordner in sys.path (ereignis.py).
        import spur_buch
        import ereignis
        gerufen = []
        alt_bus, alt_spiegel = ereignis.lauf, spur_buch.spiegeln
        ereignis.lauf = lambda name: gerufen.append(name)
        try:
            replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test2",
                          max_kerzen=900, fenster=400)
        finally:
            ereignis.lauf, spur_buch.spiegeln = alt_bus, alt_spiegel
        self.assertEqual([], gerufen)

    def test_lauf_b_stellt_die_zeituhr_wieder_her(self):
        import spur_buch
        vorher = spur_buch.zeit_quelle
        replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test3",
                      max_kerzen=900, fenster=400)
        self.assertIs(vorher, spur_buch.zeit_quelle)

    def test_die_uhr_laeuft_mit_den_kerzen_nicht_mit_der_wanduhr(self):
        """Beweis, dass die Zeituhr gesetzt wird: die Journalzeiten spannen
        den historischen Zeitraum ab, nicht die Minuten des Laufs."""
        import csv
        replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test4",
                      max_kerzen=1500, fenster=400)
        pfad = os.path.join(replay.buch_ordner("trendwende_btc", "test4"),
                            "handelsjournal.csv")
        with open(pfad, encoding="utf-8", newline="") as f:
            zeiten = sorted(r["zeit"] for r in csv.DictReader(f) if r.get("zeit"))
        self.assertGreater(len(zeiten), 0)
        import datetime as dt
        erste = dt.datetime.fromisoformat(zeiten[0])
        letzte = dt.datetime.fromisoformat(zeiten[-1])
        self.assertGreater((letzte - erste).days, 20)

    def test_nicht_nachrechenbare_spur_wird_verweigert_statt_geraten(self):
        with self.assertRaises(RuntimeError) as ctx:
            replay.lauf_b("moondev_whale", gebuehr_pct=0.05, lauf="test5")
        self.assertIn("nicht nachrechenbar", str(ctx.exception))
        self.assertIn("50030", str(ctx.exception))


class GebuehrTest(unittest.TestCase):
    """Die Gebuehr ist der teuerste Fehler eines Backtests - sie muss stimmen."""

    def test_wachen_wert_hat_vorrang(self):
        self.assertEqual(0.6, replay.gebuehr_fuer("kraken", {"gebuehr_taker": 0.006}))
        self.assertEqual(0.05, replay.gebuehr_fuer("xperp", {"gebuehr_taker": 0.0005}))

    def test_fehlender_wert_faellt_auf_den_boersensatz_der_spur(self):
        self.assertEqual(0.1, replay.gebuehr_fuer("squeeze", {}))
        self.assertEqual(0.05, replay.gebuehr_fuer("liq_wand", {}))
        self.assertEqual(0.6, replay.gebuehr_fuer("orbk", {}))

    def test_kein_pauschalwert_und_keine_stille_null(self):
        for spur in replay.SPUREN_TEIL_A:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)

    def test_unbekannte_spur_wird_gemeldet_statt_geraten(self):
        with self.assertRaises(KeyError):
            replay.gebuehr_fuer("diegibtesnicht", {})


class GegenprobeTest(ReplayTest):
    """Der neue Kern muss dasselbe rechnen wie der alte - sonst luegt er."""

    def test_squeeze_stimmt_mit_backtest_prognose_ueberein(self):
        e = replay.gegenprobe("squeeze", gebuehr_pct=0.1, max_kerzen=KERZEN)
        self.assertTrue(e["gleich"], "Abweichungen: %s" % e["abweichungen"][:3])
        self.assertGreater(e["runden"], 0)
        self.assertEqual(e["runden"], e["runden_alt"])


if __name__ == "__main__":
    unittest.main()
