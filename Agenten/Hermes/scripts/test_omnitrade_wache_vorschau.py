"""Tests fuer den Vorschau-Modus der omnitrade-Wache (T-352).

Geprueft wird die REGEL, nicht ein Tageswert:

- Aufruf OHNE Argument (Vorschau) zeigt die berechneten Anker-Aenderungen
  und ruft NIE start.starte() - kein Rust-Prozess wird gestartet oder
  gestoppt, die Merkdatei bleibt unberuehrt.
- Erst --anwenden darf starte() aufrufen - je totem Lauf genau einmal.
- --trocken ist der Alias fuer die Vorschau.
- Der Cron-Wrapper omnitrade-wache-anwenden.py reicht --anwenden durch.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parents[1] / "Handel"

_spec = importlib.util.spec_from_file_location(
    "omnitrade_wache", HIER / "omnitrade-wache.py")
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)

# omnitrade_start ist dasselbe Modulobjekt, das der Kern verwendet - Patches
# darunter treffen auch dessen start.zustand()/statusdatei()/starte()-Aufrufe.
if str(HANDEL) not in sys.path:
    sys.path.insert(0, str(HANDEL))
import omnitrade_start as start  # noqa: E402

NAMEN = tuple(start.LAEUFE)


class Basis(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp(prefix="omnitrade-wache-vorschau-"))
        self._merk = wache.MERK
        wache.MERK = str(self.ordner / "merker.json")
        # Jeder benannte Lauf hat eine Statusdatei (er lief schon einmal).
        for n in NAMEN:
            (self.ordner / ("live_%s.json" % n)).write_text(
                json.dumps({"state": "running", "pid": 1}), encoding="utf-8")
        self._zustand = start.zustand
        self._statusdatei = start.statusdatei
        self._starte = start.starte
        self.gestartet: list[str] = []
        start.statusdatei = lambda n, symbol=None: str(
            self.ordner / ("live_%s.json" % n))
        start.starte = lambda n, trocken=False, symbol=None, intervall=None: (
            self.gestartet.append(n) or "%s: gestartet (test)" % n)

    def tearDown(self):
        wache.MERK = self._merk
        start.zustand = self._zustand
        start.statusdatei = self._statusdatei
        start.starte = self._starte
        shutil.rmtree(self.ordner, ignore_errors=True)

    def lauf(self, *argumente):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wache.main(list(argumente))
        return code, puffer.getvalue()

    def setze_zustand(self, laeuft_fuer, grund="PID tot, Datei auf running"):
        start.zustand = lambda n: (n in laeuft_fuer,
                                   "laeuft" if n in laeuft_fuer else grund)


class VorschauTest(Basis):

    def test_ohne_argument_vorschau_kein_start(self):
        """Kein Argument = Vorschau: zeigt die Aenderungen, startet nichts."""
        self.setze_zustand({"adx_macd_btc"})
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertIn("VORSCHAU", ausgabe)
        self.assertIn("NEU STARTEN", ausgabe)
        self.assertIn("adx_macd_eth", ausgabe)
        self.assertEqual(self.gestartet, [],
                         "die Vorschau darf keinen Rust-Prozess starten")

    def test_vorschau_zeigt_zaehlung(self):
        """Die Vorschau nennt laufend / wuerden neu gestartet / nicht angefasst."""
        self.setze_zustand({"adx_macd_btc", "adx_macd_eth", "rsi30_stop5_btc"})
        code, ausgabe = self.lauf()
        self.assertIn("3 laufen", ausgabe)
        self.assertIn("wuerden neu gestartet", ausgabe)
        self.assertIn("nicht angefasst", ausgabe)

    def test_alle_laufen_leere_vorschau(self):
        """Alles laeuft -> leere Ausgabe (Hausregel: nichts zu senden)."""
        self.setze_zustand(set(NAMEN))
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "")

    def test_vorschau_fasst_merkdatei_nicht_an(self):
        self.setze_zustand({"adx_macd_btc"})
        code, ausgabe = self.lauf()
        self.assertFalse((self.ordner / "merker.json").exists(),
                         "die Vorschau darf die Merkdatei nicht schreiben")

    def test_vorschau_flag_wie_ohne_argument(self):
        self.setze_zustand({"adx_macd_btc"})
        code, ausgabe = self.lauf("--vorschau")
        self.assertEqual(code, 0)
        self.assertIn("VORSCHAU", ausgabe)
        self.assertEqual(self.gestartet, [])

    def test_trocken_ist_alias_vorschau(self):
        self.setze_zustand({"adx_macd_btc"})
        code, ausgabe = self.lauf("--trocken")
        self.assertEqual(code, 0)
        self.assertIn("VORSCHAU", ausgabe)
        self.assertIn("NEU STARTEN", ausgabe)
        self.assertEqual(self.gestartet, [])


class AnwendenTest(Basis):

    def test_anwenden_startet_jeden_toten_lauf(self):
        """--anwenden startet tote Laeufe genau einmal (echte Rust-Prozesse)."""
        self.setze_zustand({"adx_macd_btc"})  # alles andere ist tot
        code, ausgabe = self.lauf("--anwenden")
        self.assertEqual(code, 0)
        erwartet = [n for n in NAMEN if n != "adx_macd_btc"]
        self.assertEqual(sorted(self.gestartet), sorted(erwartet))
        self.assertIn("neu gestartet", ausgabe)
        self.assertTrue((self.ordner / "merker.json").exists(),
                        "der Anwenden-Modus schreibt die Merkdatei")

    def test_anwenden_alle_laufen_nichts(self):
        self.setze_zustand(set(NAMEN))
        code, ausgabe = self.lauf("--anwenden")
        self.assertEqual(code, 0)
        self.assertEqual(self.gestartet, [])
        self.assertEqual(ausgabe.strip(), "")


class WrapperTest(unittest.TestCase):

    def test_wrapper_reicht_anwenden_durch(self):
        quelle = (HIER / "omnitrade-wache-anwenden.py").read_text(
            encoding="utf-8")
        self.assertIn("--anwenden", quelle)
        self.assertIn("main([\"--anwenden\"])", quelle)
        self.assertIn("omnitrade-wache.py", quelle)


if __name__ == "__main__":
    unittest.main(verbosity=2)
