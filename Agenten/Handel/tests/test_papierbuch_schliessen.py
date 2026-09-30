"""papierbuch_schliessen: Vorschau schreibt nichts, Anwenden nur bei ruhendem Buch.

Gebaut wird ein Miniatur-Handelsbaum (kraken/handeln.py als Attrappe mit
derselben Schnittstelle wie die Spur); gerufen wird die echte lauf()-Funktion
ueber ihren `wurzel`-Parameter.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import papierbuch_schliessen as ps  # noqa: E402

ATTRAPPE = '''
import json, os
HIER = os.path.dirname(os.path.abspath(__file__))
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "journal.txt")

def lade_zustand():
    with open(ZUSTAND, encoding="utf-8") as f:
        return json.load(f)

def schreibe_zustand(z):
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f)

def journal(*a, **k):
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(repr((a, k)) + "\\n")

def lade_wachen():
    return {}

def bueche_papier_altlasten_aus(z):
    papier = [p for p in z["positionen"] if p.get("modus") != "live"]
    for p in papier:
        journal("t", "papier", "AUSSTIEG", p["inst"], 1, 1, 1, 0, 0, "altlast")
    z["positionen"] = [p for p in z["positionen"] if p.get("modus") == "live"]
    return len(papier)
'''

POSITIONEN = [{"inst": "BTC", "modus": "papier"},
              {"inst": "ETH", "modus": "papier"},
              {"inst": "SOL", "modus": "live", "txid": "OABC"}]


class PapierbuchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = os.path.join(self.tmp.name, "kraken")
        os.makedirs(self.ordner)
        with open(os.path.join(self.ordner, "handeln.py"), "w",
                  encoding="utf-8") as f:
            f.write(ATTRAPPE)
        self.zustand = os.path.join(self.ordner, "zustand.json")
        self.journal = os.path.join(self.ordner, "journal.txt")
        with open(self.zustand, "w", encoding="utf-8") as f:
            json.dump({"positionen": POSITIONEN}, f)

    def _alt(self, sekunden):
        t = time.time() - sekunden
        os.utime(self.zustand, (t, t))

    def _lauf(self, anwenden):
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            erg = ps.lauf("kraken", anwenden=anwenden, wurzel=self.tmp.name)
        return erg, aus.getvalue()

    def _inst(self):
        with open(self.zustand, encoding="utf-8") as f:
            return [p["inst"] for p in json.load(f)["positionen"]]

    def test_vorschau_schreibt_nichts(self):
        self._alt(3600)
        vorher = open(self.zustand, encoding="utf-8").read()
        erg, text = self._lauf(anwenden=False)
        self.assertEqual(erg["gebucht"], 2)                  # "waeren dran"
        self.assertEqual(open(self.zustand, encoding="utf-8").read(), vorher)
        self.assertFalse(os.path.exists(self.journal))
        self.assertIn("wuerde buchen", text)

    def test_junger_zustand_wird_nicht_angefasst(self):
        self._alt(10)                                        # Zyklus laeuft
        erg, text = self._lauf(anwenden=True)
        self.assertTrue(erg.get("uebersprungen"))
        self.assertEqual(erg["gebucht"], 0)
        self.assertEqual(self._inst(), ["BTC", "ETH", "SOL"])
        self.assertIn("uebersprungen", text)

    def test_anwenden_bucht_papier_und_laesst_live_stehen(self):
        self._alt(3600)
        erg, _ = self._lauf(anwenden=True)
        self.assertEqual(erg["gebucht"], 2)
        self.assertEqual((erg["vorher"], erg["nachher"]), (3, 1))
        self.assertEqual(self._inst(), ["SOL"])              # live bleibt
        with open(self.journal, encoding="utf-8") as f:
            self.assertEqual(len(f.readlines()), 2)

    def test_ohne_papier_wird_nichts_gebucht(self):
        with open(self.zustand, "w", encoding="utf-8") as f:
            json.dump({"positionen": [POSITIONEN[2]]}, f)
        self._alt(3600)
        erg, _ = self._lauf(anwenden=True)
        self.assertEqual(erg["gebucht"], 0)
        self.assertEqual(self._inst(), ["SOL"])

    def test_grenze_ist_die_schonfrist(self):
        self._alt(ps.SCHONFRIST_S - 30)
        self.assertTrue(self._lauf(anwenden=True)[0].get("uebersprungen"))
        self._alt(ps.SCHONFRIST_S + 30)
        self.assertFalse(self._lauf(anwenden=True)[0].get("uebersprungen"))

    def test_alter_s(self):
        self.assertIsNone(ps._alter_s(os.path.join(self.tmp.name, "nein")))
        self._alt(120)
        self.assertAlmostEqual(ps._alter_s(self.zustand), 120, delta=5)


if __name__ == "__main__":
    unittest.main()
