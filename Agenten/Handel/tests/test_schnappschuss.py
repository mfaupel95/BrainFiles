"""Tests fuer den Tagesschnappschuss.

Schreibt ausschliesslich in einen Temp-Ordner. Der Schnappschuss ist kein
Buch - journal_zweitziel wird nirgends beruehrt, Bedingung 4 bleibt aussen vor.
"""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import schnappschuss                                     # noqa: E402


def _lage(name, positionen=(), sperren=(), runden=0, still=False):
    return {"schluessel": name, "name": name, "waehrung": "USD",
            "positionen": list(positionen), "sperren": list(sperren),
            "stillgelegt": still, "wachen": {"runden_gesamt": runden},
            "kennzahlen": None, "buchlage": "kein_buch", "buch_seit": None,
            "bilanz": None, "fehler": None, "roh": {}}


class SchreibenTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="stand_test_")
        self.addCleanup(shutil.rmtree, self.ordner, True)

    def test_schreibt_genau_eine_datei_mit_datumsnamen(self):
        stand = schnappschuss.baue([_lage("scanner", runden=5)])
        pfad = schnappschuss.schreibe(stand, ordner=self.ordner)
        self.assertEqual(os.listdir(self.ordner), [os.path.basename(pfad)])
        self.assertRegex(os.path.basename(pfad), r"^\d{4}-\d{2}-\d{2}\.json$")

    def test_traegt_nur_die_vier_felder(self):
        stand = schnappschuss.baue([_lage("scanner", runden=5)])
        felder = set(stand["spuren"]["scanner"])
        self.assertEqual(felder, {"positionen", "sperren", "runden",
                                  "stillgelegt"})

    def test_aufraeumen_loescht_nur_zu_alte(self):
        alt = (dt.date.today() - dt.timedelta(days=200)).isoformat()
        neu = dt.date.today().isoformat()
        for tag in (alt, neu):
            with open(os.path.join(self.ordner, tag + ".json"), "w",
                      encoding="utf-8") as f:
                json.dump({"datum": tag, "spuren": {}}, f)
        weg = schnappschuss.aufraeumen(ordner=self.ordner, tage=90)
        self.assertEqual(weg, 1)
        self.assertEqual(os.listdir(self.ordner), [neu + ".json"])

    def test_fremde_dateien_bleiben_liegen(self):
        with open(os.path.join(self.ordner, "notizen.txt"), "w",
                  encoding="utf-8") as f:
            f.write("nicht meins")
        schnappschuss.aufraeumen(ordner=self.ordner, tage=0)
        self.assertIn("notizen.txt", os.listdir(self.ordner))

    def test_abbruch_beim_schreiben_hinterlaesst_keine_datei(self):
        # Scheitert das Serialisieren (hier: ein Set, das json nicht kennt),
        # darf keine Datei unter dem Datumsnamen entstehen - weder leer noch
        # mit abgeschnittenem Inhalt. Die Nebendatei muss ebenfalls weg sein.
        heute = dt.date.today()
        stand = {"datum": heute.isoformat(), "gebaut": "x",
                 "spuren": {"kaputt": {1, 2}}}
        with self.assertRaises(TypeError):
            schnappschuss.schreibe(stand, ordner=self.ordner)
        self.assertEqual(os.listdir(self.ordner), [])


class VergleichTest(unittest.TestCase):
    def test_fehlender_vorgaenger_ist_kein_fehler(self):
        heute = schnappschuss.baue([_lage("scanner", runden=5)])
        self.assertEqual(schnappschuss.unterschiede(heute, None), {})

    def test_neue_sperre_wird_gemeldet(self):
        gestern = schnappschuss.baue([_lage("scanner", runden=5)])
        heute = schnappschuss.baue([_lage("scanner", runden=6,
                                          sperren=["KILL-SWITCH erreicht"])])
        d = schnappschuss.unterschiede(heute, gestern)
        self.assertIn("KILL-SWITCH erreicht", d["scanner"]["sperre_neu"])
        self.assertEqual(d["scanner"]["runden_mehr"], 1)


if __name__ == "__main__":
    unittest.main()
