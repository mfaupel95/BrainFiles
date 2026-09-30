"""pos_kennung: Kennung je Position und Journal-Kopf-Regeln."""

import io
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HANDEL)

import pos_kennung as pk  # noqa: E402

FORMAT = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{6}$")


class KennungTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, pk, "erzeuger", pk.erzeuger)
        pk.erzeuger = None
        pk._gemeldet.clear()

    def test_format_ohne_zeit(self):
        self.assertRegex(pk.neu(), FORMAT)

    def test_format_mit_iso_zeit(self):
        k = pk.neu("2026-09-30T15:30:12+00:00")
        self.assertRegex(k, FORMAT)
        self.assertTrue(k.startswith("20260930T153012-"))

    def test_nur_datum_gibt_kurzen_stempel(self):
        self.assertTrue(pk.neu("2026-09-30").startswith("20260930-"))

    def test_keine_doppelpunkte_im_namen(self):
        self.assertNotIn(":", pk.neu("2026-09-30T15:30:12+00:00"))

    def test_gleiche_sekunde_bleibt_eindeutig(self):
        zeit = "2026-09-30T15:30:12+00:00"
        self.assertEqual(len({pk.neu(zeit) for _ in range(500)}), 500)

    def test_test_naht(self):
        pk.erzeuger = lambda zeit=None: "test-1"
        self.assertEqual(pk.neu(), "test-1")


class JournalKopfTest(unittest.TestCase):
    NEU = ["zeit", "aktion", "pos_id"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pfad = os.path.join(self.tmp.name, "journal.csv")
        pk._gemeldet.clear()

    def _schreibe(self, text):
        with open(self.pfad, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def test_kopf_fehlt_oder_leer(self):
        self.assertIsNone(pk.kopf(self.pfad))
        self._schreibe("")
        self.assertIsNone(pk.kopf(self.pfad))

    def test_kopf_wird_gelesen(self):
        self._schreibe("zeit,aktion\n1,EINSTIEG\n")
        self.assertEqual(pk.kopf(self.pfad), ["zeit", "aktion"])

    def test_neue_datei_nimmt_neue_spalten(self):
        self.assertEqual(pk.spalten(self.pfad, self.NEU), self.NEU)

    def test_gleicher_kopf_bleibt(self):
        self._schreibe("zeit,aktion,pos_id\n")
        self.assertEqual(pk.spalten(self.pfad, self.NEU), self.NEU)

    def test_altjournal_behaelt_kopf_und_meldet_einmal(self):
        self._schreibe("zeit,aktion\n")
        err = io.StringIO()
        with redirect_stderr(err):
            a = pk.spalten(self.pfad, self.NEU)
            b = pk.spalten(self.pfad, self.NEU)
        self.assertEqual(a, ["zeit", "aktion"])
        self.assertEqual(b, ["zeit", "aktion"])
        self.assertEqual(err.getvalue().count("WARNUNG"), 1)

    def test_still_meldet_nicht(self):
        self._schreibe("zeit,aktion\n")
        err = io.StringIO()
        with redirect_stderr(err):
            pk.spalten(self.pfad, self.NEU, still=True)
        self.assertEqual(err.getvalue(), "")

    def test_zeile_kuerzt_auf_den_alten_kopf(self):
        # nie mehr Werte als der Kopf: sonst verschiebt DictReader alle Spalten
        self.assertEqual(pk.zeile(["a", "b", "c"], ["zeit", "aktion"]),
                         ["a", "b"])
        self.assertEqual(pk.zeile(["a", "b", "c"], None), ["a", "b", "c"])
        self.assertEqual(pk.zeile(["a", "b"], ["x", "y", "z"]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
