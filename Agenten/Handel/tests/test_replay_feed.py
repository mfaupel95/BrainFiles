"""Der Adapter muss GENAU die Felder liefern, die die Spur entscheidet.

Ein Adapter mit falschen Feldern laesst die Spur still ohne Signal laufen und
erzeugt eine Zahl, die wie ein Messwert aussieht. Deshalb wird hier gegen den
QUELLTEXT der Spur geprueft, nicht gegen eine gepflegte Liste: wer die Spur
umbaut, soll hier einen roten Test bekommen statt einen stillen Nullauf.

Kein Test dieses Moduls geht ins Netz: alles laeuft ueber Attrappen-Kerzen.
"""

import inspect
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import moondev_historie as mh                                      # noqa: E402
import replay                                                      # noqa: E402

SPUREN = ("moondev_topmovers", "moondev_marktlage", "moondev_signalwelle")

# wachen-Werte, wie die Spuren sie fuehren
W = {"anzahl_coins": 250, "mindest_volumen_usd": 2e7,
     "btc_schwelle_pct": 2.0, "breite_oben": 0.60, "breite_unten": 0.40}


class BestandMixin:
    """Ein Bestand aus Attrappen-Kerzen, Ablage im Temp-Ordner."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        # Zwei Tage: Vortag flach, heute je Symbol eine andere Bewegung.
        # BTC +10 %, AAA -5 %, BBB +1 %, CCC +3 %  -> Breite 3/4 = 0.75
        for sym, vor, jetzt in (("BTCUSDT", 100.0, 110.0), ("AAAUSDT", 100.0, 95.0),
                                ("BBBUSDT", 100.0, 101.0), ("CCCUSDT", 100.0, 103.0)):
            mh.speichere_feed(sym, "1D", [[0, vor, vor, vor, vor, 1e7],
                                          [86400000, jetzt, jetzt, jetzt, jetzt, 2e7]])
        self.b = mh.Bestand()
        self.b.laden("1D")
        self.ts = 86400000

    def tearDown(self):
        mh.ORDNER = self.alt


class FeldTest(BestandMixin, unittest.TestCase):
    def test_adapter_liefert_was_die_entscheidung_liest(self):
        """Quelltext der Spur gegen die Felder des Adapters."""
        for spur in SPUREN:
            quelle = inspect.getsource(replay.spur_modul(spur).quelle)
            for feld in mh.FELDER[spur]:
                self.assertIn(feld, quelle,
                              "%s: Adapter liefert %r, die Spur liest es nicht"
                              % (spur, feld))

    def test_jede_feed_spur_hat_eine_quelle_und_eine_feldliste(self):
        self.assertEqual(sorted(SPUREN), sorted(mh.QUELLEN))
        self.assertEqual(sorted(SPUREN), sorted(mh.FELDER))


class TopmoversTest(BestandMixin, unittest.TestCase):
    def test_felder_werden_auf_die_namen_der_spur_uebersetzt(self):
        """Die Ablage heisst aenderung_pct/volumen_usd, die Spur liest
        aenderung_24h/volumen_24h. Ohne Uebersetzung sieht die Spur nichts."""
        daten, kurse, fehler = mh.quelle_topmovers(self.b, self.ts, W)
        self.assertEqual([], fehler)
        btc = daten["BTC"]
        self.assertAlmostEqual(10.0, btc["aenderung_24h"], places=6)
        self.assertAlmostEqual(2e7, btc["volumen_24h"], places=6)
        self.assertAlmostEqual(110.0, btc["kurs"], places=6)
        self.assertEqual("BTC", btc["name"])

    def test_kurse_tragen_ALLE_symbole_nicht_nur_die_kandidaten(self):
        """Eine offene Position ausserhalb der Kandidaten braucht ihren Kurs,
        sonst schliesst sie nie (spur_buch.pruefe_ausstiege)."""
        daten, kurse, _ = mh.quelle_topmovers(self.b, self.ts, dict(W, anzahl_coins=1))
        self.assertEqual(1, len(daten))
        self.assertEqual(["AAAUSDT", "BBBUSDT", "BTCUSDT", "CCCUSDT"],
                         sorted(self.b.symbole()))
        self.assertEqual(4, len(kurse))

    def test_erstes_kerzenpaar_ohne_vortag_liefert_None_statt_null(self):
        daten, _, _ = mh.quelle_topmovers(self.b, 0, W)
        self.assertIsNone(daten["BTC"]["aenderung_24h"])


class MarktlageTest(BestandMixin, unittest.TestCase):
    def test_breite_ist_ein_anteil_kein_prozentwert(self):
        """Die wachen liest 0.60/0.40 - 75 waere 7500 % und immer ueber der
        Schwelle, 0.75 ist richtig."""
        daten, _, fehler = mh.quelle_marktlage(self.b, self.ts, W)
        self.assertEqual([], fehler)
        self.assertAlmostEqual(0.75, daten["BTC"]["breite"], places=6)
        self.assertAlmostEqual(10.0, daten["BTC"]["btc_aenderung_24h"], places=6)

    def test_ohne_btc_kein_signal_statt_einer_erfundenen_zeile(self):
        mh.speichere_feed("ZZZUSDT", "1D", [[0, 1, 1, 1, 1, 1e7]])
        b = mh.Bestand()
        b.laden("1D")
        b._reihen.pop("BTCUSDT")
        daten, kurse, fehler = mh.quelle_marktlage(b, self.ts, W)
        self.assertEqual({}, daten)
        self.assertTrue(fehler)


class SignalwelleTest(unittest.TestCase):
    """Stundentakt: 26 Kerzen, damit 24h-Vorlauf da ist."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        for sym in ("AAAUSDT", "BBBUSDT"):
            mh.speichere_feed(sym, "1H", [
                [i * 3600000, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i, 10.0]
                for i in range(26)])
        self.b = mh.Bestand()
        self.b.laden("1H")
        self.ts = 25 * 3600000

    def tearDown(self):
        mh.ORDNER = self.alt

    def test_liefert_beide_aenderungen_und_das_volumen(self):
        daten, _, fehler = mh.quelle_signalwelle(self.b, self.ts, W)
        self.assertEqual([], fehler)
        z = daten["AAA"]
        self.assertAlmostEqual((125.0 / 124.0 - 1.0) * 100.0, z["aenderung_1h"], places=6)
        self.assertAlmostEqual((125.0 / 101.0 - 1.0) * 100.0, z["aenderung_24h"], places=6)
        self.assertAlmostEqual(240.0, z["volumen_24h"], places=6)
        self.assertAlmostEqual(125.0, z["kurs"], places=6)

    def test_ohne_24_kerzen_keine_kandidaten(self):
        daten, _, _ = mh.quelle_signalwelle(self.b, 5 * 3600000, W)
        self.assertEqual({}, daten)


class GebuehrTest(unittest.TestCase):
    def test_jede_spur_hat_einen_boersensatz(self):
        """Ohne Satz waere die Kostenrechnung still null."""
        for spur in replay.SPUREN_TEIL_A + replay.SPUREN_TEIL_C:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)

    def test_funding_ist_eigene_familie_und_nicht_teil_a(self):
        self.assertIn("moondev_funding", replay.SPUREN_TEIL_C)
        self.assertNotIn("moondev_funding", replay.SPUREN_TEIL_A)

    def test_schrittweite_ist_der_funding_takt(self):
        """Acht Stunden - der Takt, in dem sich ein Funding-Satz aendert."""
        self.assertEqual(8, replay.FUNDING_STUNDEN)


class LaufFeedTest(BestandMixin, unittest.TestCase):
    def test_adapter_sieht_den_stand_des_schritts_nicht_den_letzten(self):
        """Zwei Zeitpunkte muessen zwei verschiedene Tafeln ergeben.

        Waere der Zeitpunkt fest verdrahtet, saehe jeder Schritt denselben
        Markt - und der Lauf saehe wie eine Messung aus.
        """
        daten, _, _ = mh.QUELLEN["moondev_topmovers"](self.b, 86400000, W)
        self.assertAlmostEqual(10.0, daten["BTC"]["aenderung_24h"], places=6)
        self.assertAlmostEqual(-5.0, daten["AAA"]["aenderung_24h"], places=6)

    def test_ohne_vortag_keine_kandidaten_am_ersten_schritt(self):
        """Der erste Tag hat keine 24h-Aenderung - er zaehlt nicht als Signal."""
        daten, _, _ = mh.QUELLEN["moondev_topmovers"](self.b, 0, W)
        self.assertTrue(all(v["aenderung_24h"] is None for v in daten.values()))

    def test_unbekannte_spur_wird_gemeldet(self):
        with self.assertRaises(KeyError):
            replay.lauf_feed("diegibtesnicht", 0.05, "t")

    def test_verweigerte_spur_wird_nicht_geraten(self):
        with self.assertRaises(RuntimeError):
            replay.lauf_feed("moondev_sniper", 0.05, "t")

    def test_verweigerte_spuren_nennen_einen_grund(self):
        for spur in ("moondev_sniper", "moondev_listingarb"):
            self.assertIn(spur, replay.NICHT_NACHRECHENBAR)
            self.assertGreater(len(replay.NICHT_NACHRECHENBAR[spur]), 20)


class LaufFeedEchtTest(unittest.TestCase):
    """Ein echter Durchlauf ueber Attrappen-Kerzen, Ablage im Temp-Ordner.

    Beweist die Verdrahtung: Adapter -> spur_buch.zyklus -> Journal im
    BACKTEST-Ordner. Ohne diesen Test waere ein Adapter denkbar, der die Spur
    still ohne Signal laufen laesst.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        # Alle drei Symbole springen an Tag 20 von 100 auf 112 (+12 %): das ist
        # ein Top-Mover-Signal (+8..40 %) bei Volumen ueber 2e7 USD.
        for sym in ("AAAUSDT", "BBBUSDT", "CCCUSDT"):
            mh.speichere_feed(sym, "1D", [
                [i * 86400000, *(100.0 if i < 20 else 112.0,) * 4, 2e7]
                for i in range(40)])
        self.bt = tempfile.mkdtemp(prefix="bt_")
        self.alt_v = replay.verzeichnis
        replay.verzeichnis = lambda: self.bt

    def tearDown(self):
        mh.ORDNER = self.alt
        replay.verzeichnis = self.alt_v

    def test_durchlauf_schreibt_ein_journal_und_zaehlt_die_schritte(self):
        k, _ = replay.lauf_feed("moondev_topmovers", 0.1, "takt",
                                mindest_symbole=2)
        self.assertGreater(k["schritte"], 30)
        self.assertEqual(3, k["universum"])
        self.assertEqual("1D", k["takt"])
        self.assertAlmostEqual(0.1, k["gebuehr_pct"], places=9)
        journal = os.path.join(self.bt, "moondev_topmovers", "takt",
                               "handelsjournal.csv")
        self.assertTrue(os.path.isfile(journal), "kein Journal geschrieben")
        with open(journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertGreater(len(zeilen), 1, "Journal ohne eine einzige Buchung")

    def test_ein_tag_mit_zu_wenig_reihen_ist_kein_schritt(self):
        """Drei Reihen sind keine Marktbreite."""
        b = mh.Bestand()
        b.laden("1D")
        self.assertGreaterEqual(len(b.schritte(mindest_symbole=3)), 30)
        self.assertEqual([], b.schritte(mindest_symbole=4))

    def test_zu_wenig_reihen_wird_gemeldet_statt_gerechnet(self):
        with self.assertRaises(RuntimeError):
            replay.lauf_feed("moondev_topmovers", 0.1, "takt",
                             mindest_symbole=99)


class LaufCTest(unittest.TestCase):
    def test_ohne_funding_reihen_wird_der_befehl_genannt(self):
        tmp = tempfile.mkdtemp(prefix="feed_")
        alt = mh.ORDNER
        mh.ORDNER = tmp
        bt = tempfile.mkdtemp(prefix="bt_")
        alt_v = replay.verzeichnis
        replay.verzeichnis = lambda: bt
        try:
            with self.assertRaises(RuntimeError) as c:
                replay.lauf_c("moondev_funding", 0.04, "takt")
            self.assertIn("--funding", str(c.exception))
        finally:
            mh.ORDNER = alt
            replay.verzeichnis = alt_v


if __name__ == "__main__":
    unittest.main()
