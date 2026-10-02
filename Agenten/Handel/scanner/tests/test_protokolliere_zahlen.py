"""protokolliere() nimmt die Messwerte an, die ihre Aufrufer uebergeben.

Anlass (02.10.2026, 23:26): der Scanner brach 17 Zyklen lang zwischen 02:23
und 06:26 mit

    TypeError: protokolliere() got an unexpected keyword argument 'betrag'

ab. Der Aufrufer in `pruefe_einstiege` reicht `betrag=` und `noetig=` an die
Guthaben-Ablehnung, die Hilfsfunktion nahm aber nur `(grund, anzahl)`. Ein
Zyklus, der in eine Sperre laeuft, ist damit genau der Zyklus, der nicht
zurueckkommt - das Tor hat den Handel verhindert und die Buchhaltung
abgerissen.

Die Gegenprobe steckt im Test: mit der alten Signatur (nur `anzahl`) muss
er rot werden - das beweist, dass der Test den Fehler ueberhaupt findet.
"""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(SPUR)
for _p in (SPUR, HANDEL):          # die Spur ZULETZT einsortieren (PY-TEST-
    if _p not in sys.path:         # FALLE: sonst laedt der Test
        sys.path.insert(0, _p)     # scanner/handeln.py statt des eigenen)
import handeln as h
assert h.__file__.startswith(SPUR), h.__file__


class ProtokolliereZahlenTest(unittest.TestCase):
    """Die Erweiterung der Hilfsfunktion, gemessen an der Datei, die sie schreibt."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scanprot_")
        self.alt_ablehnungen = h.ABLEHNUNGEN
        # Path, nicht str: journal_ablehnung ruft ABLEHNUNGEN.exists()
        h.ABLEHNUNGEN = Path(self.tmp) / "ablehnungen.csv"

    def tearDown(self):
        h.ABLEHNUNGEN = self.alt_ablehnungen
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _zeilen(self):
        with open(h.ABLEHNUNGEN, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_nimmt_die_messwerte_der_guthaben_ablehnung(self):
        # GENAU der Aufruf, der 17 Zyklen abbrach.
        h.protokolliere("zu wenig USDC frei", betrag=1.76, noetig=120.0)
        z = self._zeilen()
        self.assertEqual(len(z), 1, z)
        self.assertIn("betrag=1.76", z[0]["grund"])
        self.assertIn("noetig=120.0", z[0]["grund"])
        self.assertEqual(z[0]["art"], "zyklus")

    def test_die_alte_signatur_wuerde_diesen_aufruf_reissen(self):
        """Gegenprobe: die Kapazitaets-Zeile traegt den Fehler, nicht der Test."""
        def alt(grund, anzahl=1):          # die Signatur von vor dem Fix
            if anzahl:
                h.journal_ablehnung(zeit=h._jetzt(), art="zyklus",
                                    grund=grund, anzahl=anzahl)
        with self.assertRaises(TypeError):
            alt("zu wenig USDC frei", betrag=1.76, noetig=120.0)

    def test_anzahl_null_ohne_zahlen_schreibt_nichts(self):
        h.protokolliere("Buch voll", 0)
        self.assertFalse(os.path.exists(h.ABLEHNUNGEN))

    def test_ohne_messwerte_unveraendert(self):
        h.protokolliere("Buch voll")
        z = self._zeilen()
        self.assertEqual(len(z), 1)
        self.assertEqual(z[0]["grund"], "Buch voll")
        self.assertEqual(z[0]["anzahl"], "1")


if __name__ == "__main__":
    unittest.main()