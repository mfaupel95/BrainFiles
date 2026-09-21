"""Tests fuer spiegelfrist-wache.py - die Alarmrichtung, nicht der Zufall.

Warum ueberhaupt: der Waechter ist die Wache fuer Bedingung 4 geworden, und
seine Aussage ist die Abwesenheit einer Meldung ("leer = alles gut"). Genau
diese Richtung muss man pruefen koennen, ohne Q: anzufassen - ein Waechter,
der nichts meldet und nichts geprueft hat, sieht aus wie Ruhe.

Geprueft wird gegen einen TEMP-Baum eigener Bauart (nie gegen echte Spuren):
  1. eine alte Abweichung wird gemeldet
  2. dieselbe Feststellung wird nicht wiederholt (Merkdatei)
  3. eine frische Abweichung schweigt (Test-/Laufrauschen)
  4. Kopien gleich -> keine Meldung
  5. unerreichbares Ziel (Q: abgezogen) wird gemeldet, aber nur einmal

Aufruf:  python -m unittest discover -s Agenten/Hermes/scripts -t Agenten/Hermes/scripts
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE = HIER / "spiegelfrist-wache.py"


def lade_wache():
    spec = importlib.util.spec_from_file_location("spiegelfrist_wache", str(WACHE))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class AlarmrichtungTest(unittest.TestCase):

    def setUp(self):
        self.w = lade_wache()
        self.sp = self.w.lade_spiegelstand()
        self.assertIsNotNone(self.sp, "spiegelstand.py nicht ladbar")
        self.tmp = Path(tempfile.mkdtemp(prefix="spiegelfrist-"))
        self.handel = self.tmp / "Handel"
        self.ziel = self.tmp / "Q" / "testspur"
        self.spur = self.handel / "testspur"
        self.ziel.mkdir(parents=True)
        self.spur.mkdir(parents=True)
        (self.spur / "wachen.json").write_text(json.dumps({
            "journal_zweitziel": str(self.ziel)}), encoding="utf-8")
        (self.spur / "zustand.json").write_text("{}", encoding="utf-8")
        self.journal = self.spur / "handelsjournal.csv"
        self.journal.write_text("zeit,aktion\n", encoding="utf-8")
        # Der Waechter fragt spiegelstand, welche Spuren laufen - hier eine.
        # Gepatcht wird SPIEGELSTAND, denn von dort kommt die Dateiliste.
        self.sp.spuren_im_lauf = lambda handel=None: {"testspur"}
        self.sp.spuren_ordner = lambda handel=None: {"testspur": "testspur"}
        # Merkdatei ins Temp lenken (nie in den echten cache-Ordner).
        self.w.MERKDATEI = self.tmp / "merker.json"

    def _befund(self, frist=20.0):
        return self.w.befund_je_spur(self.sp, handel=str(self.handel),
                                     frist=frist)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _gleich_machen(self):
        shutil.copy2(self.journal, self.ziel / self.journal.name)

    def test_1_alte_abweichung_wird_gemeldet(self):
        os.utime(self.journal, (time.time() - 3600, time.time() - 3600))
        zeilen, geprueft, _ = self._befund()
        self.assertEqual(geprueft, 1)
        self.assertEqual(len(zeilen), 1)
        self.assertIn("handelsjournal.csv", zeilen[0])
        self.assertIn("testspur", zeilen[0])

    def test_2_keine_wiederholung_derselben_feststellung(self):
        os.utime(self.journal, (time.time() - 3600, time.time() - 3600))
        zeilen, _, _ = self._befund()
        zu1, merker = self.w.entdopple(zeilen, {})
        self.assertEqual(len(zu1), 1)
        zu2, _ = self.w.entdopple(zeilen, merker)
        self.assertEqual(zu2, [], "dieselbe Feststellung wurde wiederholt")

    def test_3_frische_abweichung_schweigt(self):
        # Genau der Fall "Tests haben in eine echte Spur geschrieben": die
        # Datei ist eben erst entstanden, der naechste Zyklus zieht nach.
        zeilen, _, _ = self._befund()
        self.assertEqual(zeilen, [])

    def test_4_gleiche_kopien_schweigen(self):
        self._gleich_machen()
        os.utime(self.journal, (time.time() - 3600, time.time() - 3600))
        zeilen, _, abweichend = self._befund()
        self.assertEqual(zeilen, [])
        self.assertEqual(abweichend, 0)

    def test_5_unerreichbares_ziel_wird_gemeldet_und_entdoppelt(self):
        shutil.rmtree(self.ziel)
        zeilen, _, _ = self._befund()
        self.assertEqual(len(zeilen), 1)
        self.assertIn("NICHT ERREICHBAR", zeilen[0])
        zu1, merker = self.w.entdopple(zeilen, {})
        zu2, _ = self.w.entdopple(zeilen, merker)
        self.assertEqual(len(zu1), 1)
        self.assertEqual(zu2, [])

    def test_6_meldung_nicht_doppelt_bei_wachsendem_rueckstand(self):
        # Der Rueckstand waechst minuetlich; die Feststellung bleibt dieselbe.
        os.utime(self.journal, (time.time() - 3600, time.time() - 3600))
        z1, _, _ = self._befund()
        os.utime(self.journal, (time.time() - 7200, time.time() - 7200))
        z2, _, _ = self._befund()
        zu1, merker = self.w.entdopple(z1, {})
        zu2, _ = self.w.entdopple(z2, merker)
        self.assertEqual(len(zu1), 1)
        self.assertEqual(zu2, [], "wachsender Rueckstand erzeugte eine neue Meldung")


if __name__ == "__main__":
    unittest.main()