"""Zwei Schreiber auf freigabe_fenster.json: Dauerlauf und Leitstand.

Geprueft: kein verlorener Eintrag bei parallelem Schreiben, belegte Sperre ->
TimeoutError ohne Schreiben, verwaiste Sperre wird entfernt, keine .tmp/.lock
bleibt liegen, os.replace wird bei PermissionError (Windows) wiederholt.
Gearbeitet wird in einem Temp-Ordner (DATEI wird umgebogen).

Direkt ausfuehrbar:  python tests/test_freigabefenster_sperre.py
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import freigabefenster as ff                                   # noqa: E402


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(ff, "DATEI",
                         os.path.join(self.tmp.name, "freigabe_fenster.json"))
        p.start()
        self.addCleanup(p.stop)

    def _inhalt(self):
        with open(ff.DATEI, encoding="utf-8") as f:
            return json.load(f)


class Sperre(Basis):
    def test_belegte_sperre_wirft_timeout_und_schreibt_nichts(self):
        ff.anfrage_stellen("xperp", 60)
        vorher = self._inhalt()
        open(ff.DATEI + ".lock", "w").close()
        with patch.object(ff, "SPERRE_WARTEN_S", 0.2):
            with self.assertRaises(TimeoutError):
                ff.schliessen("xperp", "Test")
        self.assertEqual(self._inhalt(), vorher)

    def test_verwaiste_sperre_wird_entfernt(self):
        sperre = ff.DATEI + ".lock"
        open(sperre, "w").close()
        alt = time.time() - 60
        os.utime(sperre, (alt, alt))
        ff.schliessen("xperp", "Test")
        self.assertFalse(os.path.exists(sperre))
        self.assertEqual(self._inhalt()["xperp"]["schliess_grund"], "Test")

    def test_parallele_schreiber_verlieren_nichts(self):
        def schreiber(praefix):
            for i in range(25):
                ff.anfrage_stellen("%s%d" % (praefix, i), 60)
        faeden = [threading.Thread(target=schreiber, args=(p,))
                  for p in ("a", "b")]
        for t in faeden:
            t.start()
        for t in faeden:
            t.join(30)
        self.assertEqual(len(self._inhalt()), 50)

    def test_keine_tmp_und_keine_sperre_bleibt_liegen(self):
        ff.anfrage_stellen("xperp", 60)
        ff.oeffnen("xperp", 2, wer="test")
        ff.alles_schliessen("Test")
        self.assertEqual(sorted(os.listdir(self.tmp.name)),
                         ["freigabe_fenster.json"])

    def test_replace_wiederholt_bei_permissionerror(self):
        echt = os.replace
        fehler = [PermissionError("belegt"), PermissionError("belegt")]

        def ersatz(a, b):
            if fehler:
                raise fehler.pop(0)
            return echt(a, b)

        with patch.object(ff.os, "replace", side_effect=ersatz):
            ff.anfrage_stellen("xperp", 60)
        self.assertIn("xperp", self._inhalt())
        self.assertEqual(fehler, [])


class Verhalten(Basis):
    def test_alles_schliessen_meldet_nur_offene(self):
        ff.anfrage_stellen("a", 60)
        ff.oeffnen("a", 1, wer="test")
        ff.anfrage_stellen("b", 60)
        self.assertEqual(ff.alles_schliessen("Test"), ["a"])
        d = self._inhalt()
        self.assertEqual(d["b"]["schliess_grund"], "Test")
        self.assertNotIn("anfrage_bis", d["b"])
        self.assertNotIn("offen_bis", d["a"])

    def test_alles_schliessen_haelt_kaputten_eintrag_aus(self):
        ff.anfrage_stellen("a", 60)
        ff.oeffnen("a", 1, wer="test")
        d = self._inhalt()
        d["kaputt"] = "kaputt"
        with open(ff.DATEI, "w", encoding="utf-8") as f:
            json.dump(d, f)
        self.assertEqual(ff.alles_schliessen("Test"), ["a"])
        d = self._inhalt()
        self.assertNotIn("offen_bis", d["a"])
        self.assertIsInstance(d["kaputt"], dict)
        self.assertEqual(d["kaputt"]["schliess_grund"], "Test")

    def test_alles_schliessen_ohne_datei_schreibt_nichts(self):
        self.assertEqual(ff.alles_schliessen("Test"), [])
        self.assertFalse(os.path.exists(ff.DATEI))

    def test_oeffnen_ohne_anfrage_bleibt_none(self):
        self.assertIsNone(ff.oeffnen("xperp", 2, wer="test"))


if __name__ == "__main__":
    unittest.main()
