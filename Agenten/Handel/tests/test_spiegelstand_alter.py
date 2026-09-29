"""Test fuer das Herzschlag-Alter im Spiegelstand (Fehlalarm vom 29.09.2026).

Eine Spur, die nur live laeuft, schreibt `zustand.live.json`; ihr
`zustand.json` friert ein. Wer nur den Papierstand liest, meldet fuer sie
jeden Tag "Herzschlag alt (> 2 h) - laeuft die Spur ueberhaupt?" (gemessen:
moondev_marktlage stand auf 204 min, waehrend der Live-Zweig alle 15 min lief).
`frisches_alter()` nimmt deshalb den FRISCHESTEN der beiden Staende.

Was hier belegt wird:
  1. Nur Papierstand: dessen Alter zaehlt (unveraendert wie vorher).
  2. Papier alt, live frisch: das frische Alter zaehlt (der Fix).
  3. Nur Live-Stand: sein Alter zaehlt.
  4. Weder noch (oder unlesbarer Zeitstempel): None, kein Absturz.
  5. Risikostufe: der Suffix wird in BEIDE Namen gebogen.
  6. Gegenprobe: die alte Rechnung (nur zustand.json) liefert fuer Fall 2
     wieder den alten Wert - sonst prueft der Test nicht, was er soll.

Nachsehen statt glauben:
    .venv/Scripts/python.exe -m unittest tests.test_spiegelstand_alter
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import risikostufe                                          # noqa: E402
import spiegelstand                                        # noqa: E402

STUNDEN_ALT = 4


def _zeit(vor_stunden):
    return (datetime.now(timezone.utc)
            - timedelta(hours=vor_stunden)).isoformat()


class FrischesAlter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="spiegel-alter-")
        self.ohne = lambda n: n                              # noqa: E731

    def schreibe(self, name, letzter_lauf):
        with open(os.path.join(self.tmp, name), "w", encoding="utf-8") as f:
            json.dump({"letzter_lauf": letzter_lauf}, f)

    def test_1_nur_papierstand(self):
        self.schreibe("zustand.json", _zeit(STUNDEN_ALT))
        a = spiegelstand.frisches_alter(self.tmp, self.ohne)
        self.assertAlmostEqual(a, STUNDEN_ALT * 60, delta=5)

    def test_2_papier_alt_live_frisch(self):
        self.schreibe("zustand.json", _zeit(STUNDEN_ALT))
        self.schreibe("zustand.live.json", _zeit(0.1))
        a = spiegelstand.frisches_alter(self.tmp, self.ohne)
        self.assertLess(a, 30, "der frische Live-Stand muss gewinnen")

    def test_2gegenprobe_alte_rechnung_war_der_fehlalarm(self):
        """Ohne den Fix kommt genau der gemeldete Wert heraus."""
        self.schreibe("zustand.json", _zeit(STUNDEN_ALT))
        self.schreibe("zustand.live.json", _zeit(0.1))
        with open(os.path.join(self.tmp, "zustand.json"), encoding="utf-8") as f:
            alt = spiegelstand.alter_minuten(json.load(f)["letzter_lauf"])
        self.assertAlmostEqual(alt, STUNDEN_ALT * 60, delta=5)

    def test_3_nur_livestand(self):
        self.schreibe("zustand.live.json", _zeit(0.5))
        a = spiegelstand.frisches_alter(self.tmp, self.ohne)
        self.assertLess(a, 90)

    def test_4_kein_stand_und_kaputter_stempel(self):
        self.assertIsNone(spiegelstand.frisches_alter(self.tmp, self.ohne))
        self.schreibe("zustand.json", "kein Datum")
        self.schreibe("zustand.live.json", "")
        self.assertIsNone(spiegelstand.frisches_alter(self.tmp, self.ohne))

    def test_5_risikostufe_biegt_beide_namen(self):
        benenne = lambda n: risikostufe.datei_fuer(n, "mittel")   # noqa: E731
        papier, live = benenne("zustand.json"), benenne("zustand.live.json")
        self.assertNotEqual(papier, live)
        # Nur die Stufendateien sind da - der flache Name darf nicht treffen.
        self.schreibe(live, _zeit(0.2))
        a = spiegelstand.frisches_alter(self.tmp, benenne)
        self.assertIsNotNone(a, "%s wurde nicht gefunden" % live)
        self.assertLess(a, 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
