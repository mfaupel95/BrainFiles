"""Tests fuer itb_bruecke: ITB-Export -> Journal -> Tor -> Papierbuch.

Geprueft wird die REGEL: ein Signal wird hoechstens einmal eroeffnet, auch
wenn ITB dieselbe Kerze mehrfach exportiert; ein altes Signal kommt nicht
durch. Die Ende-zu-Ende-Pruefung laeuft ueber das echte Papierbuch und die
echte wachen.json, nur das Journal ist in einem temporaeren Ordner.
"""
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(HIER, "..", "..", "Bus")))

import fremd_papier as fp                                            # noqa: E402
import fremd_tor as ft                                               # noqa: E402
import itb_bruecke as ib                                             # noqa: E402
import journal                                                       # noqa: E402

WACHE = os.path.join(os.path.dirname(HIER), "fremd_signale", "wachen.json")
JETZT = 1_800_000_000


def export(tmp, zeilen):
    pfad = os.path.join(tmp, "itb_signale.csv")
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write("instrument,ts_utc,buy,sell\n" + "".join(zeilen))
    return pfad


class BrueckeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = self.tmp.name
        with open(WACHE, encoding="utf-8") as f:
            self.wache = json.load(f)

    def tearDown(self):
        self.tmp.cleanup()

    def test_vorschau_schreibt_nichts(self):
        pfad = export(self.tmp.name, ["BTC-USDT,%d,True,False\n" % JETZT])
        neu = ib.bruecke(pfad, wurzel=self.wurzel, schreiben=False)
        self.assertEqual(len(neu), 1)
        self.assertEqual(journal.lesen(wurzel=self.wurzel), [])

    def test_gleiche_kerze_zweimal_wird_nur_einmal_angehaengt(self):
        pfad = export(self.tmp.name, ["BTC-USDT,%d,True,False\n" % JETZT])
        ib.bruecke(pfad, wurzel=self.wurzel, schreiben=True)
        zweiter = ib.bruecke(pfad, wurzel=self.wurzel, schreiben=True)
        self.assertEqual(zweiter, [])
        self.assertEqual(len(journal.lesen(wurzel=self.wurzel)), 1)

    def test_signal_wird_im_papierbuch_eroeffnet(self):
        pfad = export(self.tmp.name, ["BTC-USDT,%d,True,False\n" % JETZT])
        ib.bruecke(pfad, wurzel=self.wurzel, schreiben=True)
        zeilen = journal.lesen(wurzel=self.wurzel)
        z = fp.leer()
        ergebnis = fp.verarbeite(z, zeilen, lambda inst: 100.0, self.wache, JETZT)
        self.assertEqual(len(ergebnis), 1)
        self.assertTrue(ergebnis[0][1], ergebnis[0][2])
        self.assertIn("BTC-USDT", z["offen"])
        # 5 USD Risiko bei 4 % Stop = 125 USD Position
        self.assertAlmostEqual(z["offen"]["BTC-USDT"]["menge_usd"], 125.0)

    def test_altes_signal_kommt_nicht_durch(self):
        pfad = export(self.tmp.name, ["BTC-USDT,%d,True,False\n" % (JETZT - 3600)])
        ib.bruecke(pfad, wurzel=self.wurzel, schreiben=True)
        zeilen = journal.lesen(wurzel=self.wurzel)
        z = fp.leer()
        ergebnis = fp.verarbeite(z, zeilen, lambda inst: 100.0, self.wache, JETZT)
        self.assertFalse(ergebnis[0][1])
        self.assertNotIn("BTC-USDT", z["offen"])

    def test_ohne_freigabe_kein_signal_im_tor(self):
        pfad = export(self.tmp.name, ["ETH-USDT,%d,True,False\n" % JETZT])
        ib.bruecke(pfad, wurzel=self.wurzel, schreiben=True)
        zeilen = journal.lesen(wurzel=self.wurzel)
        z = fp.leer()
        ergebnis = fp.verarbeite(z, zeilen, lambda inst: 100.0, self.wache, JETZT)
        self.assertFalse(ergebnis[0][1])
        self.assertEqual(z["offen"], {})


if __name__ == "__main__":
    unittest.main()
