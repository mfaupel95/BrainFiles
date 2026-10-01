"""Die Hand meldet VERFALLENE Belege genau einmal (Befund T-283).

Warum es diesen Test gibt
-------------------------
Ein verfallener Beleg ist kein Schaden - er kauft nicht. Er ist aber
UNSICHTBAR: `freigabebeleg.offene()` laesst ihn weg, und der Handler sah bis
zum 01.10.2026 nur nach den gueltigen. Im Zyklus 11:25:51 der kraken-Spur
entstanden neun Belege, acht davon starben an der Frist von damals 180 s,
waehrend der Ausfuehrer `beleg-hand` im 5-Minuten-Takt lief - beschlossene
Orders, die nie ausgefuehrt wurden, ohne eine einzige Meldung. Der Handler
meldet sie jetzt (Zeile + Journalzeile) und merkt sie (`merke_verfallen`),
damit dieselbe Feststellung nicht bei jedem Cron-Lauf wiederkehrt.

Ohne Netz, ohne Boerse, ohne echte Datei: das Beleg-Modul ist ein Stub, die
kraken-Spur ein Recorder.

Ausfuehrbar (aus dem Handel-Ordner): python -m unittest tests.test_beleg_hand_verfallen
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HIER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HIER))

import beleg_hand as bh                                              # noqa: E402

assert Path(bh.__file__).resolve().parent == HIER


class BelegStub:
    """Steht fuer freigabebeleg: liefert die verfallenen und merkt sie."""

    def __init__(self, verfallene):
        self._verfallene = list(verfallene)
        self.gemerkt = []

    def offene(self):
        return []

    def verfallene(self):
        return list(self._verfallene)

    def merke_verfallen(self, spur, grund=""):
        self.gemerkt.append((spur, grund))
        # Wie im echten Modul: nach dem Merken faellt der Beleg aus verfallene().
        self._verfallene = [d for d in self._verfallene if d.get("spur") != spur]
        return True


class JournalRecorder:
    def __init__(self):
        self.zeilen = []

    def journal(self, *felder):
        self.zeilen.append(felder)


def _beleg(spur="kraken", paar="ALGOEUR", kennung="K-1"):
    return {"spur": spur, "kennung": kennung, "seite": "buy", "paar": paar,
            "menge": 445.0, "preis_max": 0.1287531,
            "erstellt": "2026-10-01T11:25:51+00:00",
            "gueltig_bis": "2026-10-01T11:35:51+00:00",
            "grund": "Einstieg %s" % paar}


class VerfalleneTest(unittest.TestCase):
    def setUp(self):
        self.stub = BelegStub([_beleg()])
        self.rec = JournalRecorder()
        self.echt_beleg = bh.beleg
        self.echt_weg = bh._kraken_weg
        bh.beleg = self.stub
        bh._kraken_weg = lambda: self.rec
        self.addCleanup(setattr, bh, "beleg", self.echt_beleg)
        self.addCleanup(setattr, bh, "_kraken_weg", self.echt_weg)

    def _lauf(self):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            berichte = bh.lauf(anwenden=True)
        return berichte, puffer.getvalue()

    def test_verfallener_beleg_wird_gemeldet_und_gemerkt(self):
        berichte, ausgabe = self._lauf()
        self.assertEqual(berichte, [], "ein verfallener Beleg fuehrt nichts aus")
        self.assertIn("VERFALLEN", ausgabe)
        self.assertIn("ALGOEUR", ausgabe)
        self.assertIn("K-1", ausgabe)
        self.assertEqual(self.stub.gemerkt, [("kraken", "Frist abgelaufen")])
        self.assertEqual(len(self.rec.zeilen), 1, "genau EINE Journalzeile")
        felder = self.rec.zeilen[0]
        self.assertIn("beleg_verfallen", felder)
        self.assertIn("ALGOEUR", felder)
        self.assertTrue(any("K-1" in str(f) for f in felder),
                        "die Kennung muss in der Journalzeile stehen: %s" % (felder,))

    def test_dieselbe_feststellung_kommt_nicht_wieder(self):
        """Der Cron laeuft alle 5 Minuten - eine Meldung, nicht zwoelf."""
        _, erste = self._lauf()
        _, zweite = self._lauf()
        self.assertIn("VERFALLEN", erste)
        self.assertNotIn("VERFALLEN", zweite, "zweite Runde darf nichts wiederholen")
        self.assertEqual(len(self.rec.zeilen), 1)
        self.assertIn("keine offenen Belege", zweite)

    def test_fremde_spur_wird_gemeldet_aber_nicht_gebucht(self):
        """Fuer eine Spur ohne Weg gibt es keine Journalzeile - nur die Meldung."""
        self.stub._verfallene = [_beleg(spur="mosaic", paar="XXBTZEUR")]
        _, ausgabe = self._lauf()
        self.assertIn("VERFALLEN", ausgabe)
        self.assertIn("mosaic", ausgabe)
        self.assertEqual(self.rec.zeilen, [], "kein kraken-Weg fuer eine fremde Spur")
        self.assertEqual(self.stub.gemerkt, [("mosaic", "Frist abgelaufen")])

    def test_journalfehler_kippt_die_meldung_nicht(self):
        class Kaputt:
            def journal(self, *felder):
                raise RuntimeError("Journal nicht beschreibbar")

        bh._kraken_weg = lambda: Kaputt()
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            berichte = bh.lauf(anwenden=True)
        self.assertEqual(berichte, [])
        self.assertEqual(self.stub.gemerkt, [("kraken", "Frist abgelaufen")],
                         "gemerkt wird auch ohne Journalzeile - sonst wiederholt es sich ewig")


if __name__ == "__main__":
    unittest.main()