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


if __name__ == "__main__":
    unittest.main()
