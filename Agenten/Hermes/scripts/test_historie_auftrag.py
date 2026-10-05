"""Tests des Nachlade-Auftrags: die drei Wege, die unterscheiden muss.

  1. alles frisch  -> STILLE, kein Kindprozess
  2. Historie alt  -> Nachlade-Auftrag, Ausgabe sichtbar
  3. Wache kaputt  -> LAUT, NICHT "alles frisch"

Der dritte Fall ist der Grund fuer dieses Skript ueberhaupt. Die erste
Fassung hatte `WACHE = HIER / "historie-wache.py"` - `HIER` ist die DATEI,
also zeigte der Pfad auf `historie-auftrag.py/historie-wache.py`. `subprocess`
meldet einen fehlenden Pfad NICHT als Fehler, sondern mit leerer Ausgabe, und
die Regel "leer heisst alles frisch" machte daraus "alles in Ordnung". Ein
still gebliebener Wecker ist die teuerste Form von gruen - der Befund vom
05.10.2026 haette sich jeden Tag wiederholt und niemand haette es gemerkt.

HINWEIS (05.10.2026): Diese Datei verschwand zweimal Minuten nach dem
Schreiben (T-100, Dateischwund). Deshalb wird sie SOFORT gestaged und
committet, nicht am Ende einer laengeren Arbeit.
"""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]
if not (WURZEL / "Agenten" / "Handel" / "moondev_historie.py").is_file():
    WURZEL = HIER.parents[3]
SCRIPT = HIER / "historie-auftrag.py"


def _lade():
    spec = importlib.util.spec_from_file_location("historie_auftrag", SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Attrappe(unittest.TestCase):
    """Alle drei Zustaende, ohne einen echten Abruf."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="auftrag-"))
        self.merk = self.tmp / "merk.json"
        self.gelaufene = []                 # Kommandozeilen je Aufruf
        self.alt_run = None
        self.addCleanup(self.aufraeumen)

    def aufraeumen(self):
        if self.alt_run is not None:
            import subprocess as sp
            sp.run = self.alt_run
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.assertFalse(self.tmp.exists())

    def _binden(self, befund, returncode=0):
        """Ein Auftrag, der `befund` sieht und `returncode` kriegt."""
        import subprocess as sp
        w = _lade()
        w.MERKFILEI = self.merk
        w._zu_tun = lambda: befund

        # Die Liste wird als Parameter uebergeben, nicht ueber `self`:
        # `self` hier ist die GEFAELSCHT-Instanz, nicht der Test (der eigene
        # Erstlauf: AttributeError in jedem Nachlade-Test). Die Liste gehoert
        # dem Test, nicht dem Attrappen-Objekt.
        class Gefaelscht:
            stdout = "Nachgeladen: 27 Reihen"
            stderr = ""

            def __init__(self, kommando):
                self.returncode = returncode
                protokoll.append(kommando)

        protokoll = self.gelaufene
        self.alt_run = sp.run
        sp.run = lambda kommando, **kw: Gefaelscht(kommando)
        return w


class FrischTest(Attrappe):
    def test_leere_wache_ist_stille(self):
        w = self._binden("")
        code = w.main()
        self.assertEqual(0, code)
        self.assertEqual([], self.gelaufene,
                         "alles frisch heisst: KEIN Nachladeprozess")

    def test_frischer_lauf_wird_gemerkt_ohne_fehlversuch(self):
        w = self._binden("")
        w.main()
        with open(self.merk, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(0, m["fehlversuche"])
        self.assertEqual("alles frisch", m["bemerkung"])


class NachladenTest(Attrappe):
    def test_befund_ausloest_den_auftrag(self):
        w = self._binden("1D: 3 von 3 Reihen aelter als 5 Tage")
        code = w.main()
        self.assertEqual(0, code)
        self.assertEqual(1, len(self.gelaufene), "es muss genau einmal laufen")
        kommando = self.gelaufene[0]
        self.assertIn("--anwenden", kommando,
                      "der Cron-Auftrag traegt --anwenden - das Werkzeug "
                      "selbst bleibt bei der Vorschau")
        self.assertIn("30", kommando, "Ziel 30 = Vorgabe des Backtests")

    def test_erfolg_setzt_den_fehlversuchzaehler_zurueck(self):
        with open(self.merk, "w", encoding="utf-8") as f:
            json.dump({"fehlversuche": 2, "letzter_fehlversuch": 0}, f)
        w = self._binden("1D: zu alt", returncode=0)
        w.main()
        with open(self.merk, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(0, m["fehlversuche"])
        self.assertEqual("nachgeladen", m["bemerkung"])

    def test_fehlschlag_zaehlt_und_wird_gemeldet(self):
        w = self._binden("1D: zu alt", returncode=1)
        code = w.main()
        self.assertEqual(1, code, "ein Fehlschlag ist 1, nicht 0")
        with open(self.merk, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(1, m["fehlversuche"])


class FehlversucheTest(Attrappe):
    def test_nach_zwei_fehlversuchen_schweigt_er_stundenlang(self):
        """Zwei Fehlversuche am Tag - danach Pause, kein Dauerfehler."""
        with open(self.merk, "w", encoding="utf-8") as f:
            json.dump({"fehlversuche": 2, "letzter_fehlversuch": 9_999_999_999},
                      f)
        w = self._binden("1D: zu alt")
        code = w.main()
        self.assertEqual(0, code)
        self.assertEqual([], self.gelaufene,
                         "in der Pause darf kein Prozess laufen")

    def test_nach_der_pause_wird_wieder_versucht(self):
        with open(self.merk, "w", encoding="utf-8") as f:
            json.dump({"fehlversuche": 2, "letzter_fehlversuch": 1}, f)
        w = self._binden("1D: zu alt")
        w.main()
        self.assertEqual(1, len(self.gelaufene),
                         "nach der Pause wird neu versucht")


class KaputteWacheTest(Attrappe):
    """Der Grund des Skripts: ein Fehlpfad darf nicht 'frisch' heissen."""

    def test_fehlendes_wache_skript_bricht_laut_ab(self):
        w = _lade()
        w.MERKFILEI = self.merk
        alt_wache = w.WACHE
        w.WACHE = self.tmp / "gibt-es-nicht.py"
        try:
            with self.assertRaises(FileNotFoundError):
                w._zu_tun()
        finally:
            w.WACHE = alt_wache

    def test_wache_mit_fehlercode_bricht_laut_ab(self):
        w = _lade()
        import subprocess as sp

        class Kaputt:
            returncode = 2
            stdout = ""
            stderr = "Traceback ..."

        alt = sp.run
        sp.run = lambda *a, **kw: Kaputt()
        try:
            with self.assertRaises(RuntimeError):
                w._zu_tun()
        finally:
            sp.run = alt

    def test_main_meldet_den_fehler_statt_still_zu_sein(self):
        """Die Kette: ein Fehler in `_zu_tun` darf NIE zu 'frisch' werden."""
        w = _lade()
        w.MERKFILEI = self.merk

        def kaputt():
            raise FileNotFoundError("Wache fehlt")

        w._zu_tun = kaputt
        code = w.main()
        self.assertEqual(2, code, "2 = Befund, nicht 'alles frisch' (0)")
        with open(self.merk, encoding="utf-8") as f:
            m = json.load(f)
        self.assertEqual(1, m["fehlversuche"])


class PfadTest(unittest.TestCase):
    def test_die_werkzeuge_existieren(self):
        """`HIER` ist die DATEI - `HIER / "x.py"` ist ein Pfad, den es nicht
        gibt. Genau dieser Fehlpfad liess die Wette leer aussehen."""
        w = _lade()
        for pfad in (w.WACHE, w.NACHLADEN):
            self.assertTrue(pfad.is_file(), str(pfad))
        self.assertEqual(HIER, w.WACHE.parent,
                         "beide liegen neben der Auftragsdatei")


if __name__ == "__main__":
    unittest.main()