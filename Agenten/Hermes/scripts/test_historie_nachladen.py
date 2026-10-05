"""Tests des Nachlade-Werkzeugs: die Rechnung, nicht der Abruf.

Das Werkzeug ruft Binance. Diese Tests tun das NICHT - sie bauen eine
Attrappe von `daten/historie` und pruefen die drei Entscheidungen, die der
Aufrufer braucht: was der Lauf tun wuerde, wie lange er dauert, und wann er
abbrechen muss.

VORSCHAU IST DER VORGABE. Das ist hier die Regel, die ein Fehler am
teuersten macht: `--anwenden` schreibt Hunderte Megabyte. Der Test haelt
beide Wege fest - ein Aufruf ohne `--anwenden` darf den Kindprozess NIE
starten.

HINWEIS (05.10.2026): Diese Datei verschwand dreimal Minuten nach dem
Schreiben (T-100, Dateischwund). Deshalb wird sie SOFORT gestaged und
committet, nicht am Ende einer laengeren Arbeit. Der Test
`test_drei_alte_und_27_fehlende` fand dabei einen echten Fehler im Werkzeug:
`vorhanden` zaehlte die alten Reihen doppelt (len(alt) + alle Dateien), so
dass drei alte Reihen als "6 vorhanden" galten und die geschaetzte Laufzeit
falsch wurde.
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
SCRIPT = HIER / "historie-nachladen.py"


def _lade():
    spec = importlib.util.spec_from_file_location("historie_nachladen", SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Attrappe(unittest.TestCase):
    TAG = 86_400_000
    JETZT_S = 1_800_000_000                       # ms = JETZT_S * 1000

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nachladen-"))
        self.ordner = self.tmp / "daten" / "historie" / "feed"
        self.ordner.mkdir(parents=True)
        w = _lade()
        self.alt_h, self.alt_p = w.HANDEL, str(w.PYTHON)
        self.alt_gb, self.alt_feed = w._groesse_gb, w.FEED_ORDNER
        w.HANDEL = self.tmp
        w.FEED_ORDNER = self.ordner
        # `_groesse_gb(ordner)` nimmt den Pfad als Argument - das Lambda
        # muss dieselbe Signatur haben, sonst bricht schon die Vorschau (der
        # eigene Erstlauf: 9 Fehlschlaege aus einem `lambda` ohne Parameter).
        w._groesse_gb = lambda _ordner=None: 0.0
        self.w = w
        self.addCleanup(self.aufraeumen)

    def aufraeumen(self):
        self.w.HANDEL = self.alt_h
        self.w.PYTHON = self.alt_p
        self.w._groesse_gb = self.alt_gb
        self.w.FEED_ORDNER = self.alt_feed
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.assertFalse(self.tmp.exists())

    def lege(self, sym, tage_alt=0, mb=0.0, takt="1D"):
        ende = self.JETZT_S * 1000 - int(tage_alt * self.TAG)
        reihe = [[ende - (40 - 1 - i) * self.TAG, "1", "2", "0.5", "100.0",
                  "1"] for i in range(40)]
        pfad = self.ordner / ("%s_%s.json" % (sym, takt))
        with open(pfad, "w", encoding="utf-8") as f:
            if mb:
                f.write("x" * int(mb * 1024 * 1024))
            f.write(json.dumps(reihe))

    def vorschau(self, top=30, takt="1D"):
        """IMMER mit der festen Attrappen-Uhr - sonst ist nichts pruefbar."""
        return self.w.vorschau(top, takt, jetzt=self.JETZT_S)


class VorschauRechnungTest(Attrappe):
    def test_ohne_dateien_ist_alles_fehlend(self):
        zeilen, dauer, tut = self.vorschau(30, "1D")
        self.assertTrue(tut, "ohne jede Reihe gibt es zu tun")
        self.assertTrue(any("fehlend:          30" in z for z in zeilen), zeilen)
        self.assertTrue(any("Laufzeit" in z for z in zeilen), zeilen)

    def test_drei_alte_und_27_fehlende(self):
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            self.lege(sym, tage_alt=10.0)
        zeilen, _dauer, _tut = self.vorschau(30, "1D")
        self.assertTrue(any("zu alt (>5 Tage): 3" in z for z in zeilen), zeilen)
        self.assertTrue(any("fehlend:          27" in z for z in zeilen), zeilen)

    def test_frische_reihen_stellen_keine_luecke_dar(self):
        for i in range(30):
            self.lege("S%02dUSDT" % i, tage_alt=0.0)
        zeilen, _d, tut = self.vorschau(30, "1D")
        self.assertFalse(tut, "30 frische Reihen brauchen keinen Nachlade")
        self.assertTrue(any("zu alt (>5 Tage): 0" in z for z in zeilen), zeilen)

    def test_laufzeit_ist_die_anzahl_mal_sekunden_pro_symbol(self):
        """Die Schaetzung haengt an der GEMESSENEN Zahl, nicht an einem Wert."""
        self.lege("BTCUSDT", tage_alt=10.0)
        _z, dauer, _t = self.vorschau(30, "1D")
        erwartet = int(30 * self.w.SEKUNDEN_PRO_SYMBOL * self.w.SICHERHEIT)
        self.assertEqual(erwartet, dauer,
                         "die Schätzung muss aus SEKUNDEN_PRO_SYMBOL und "
                         "SICHERHEIT folgen - eine freie Zahl hier waere "
                         "nicht mehr belegbar")

    def test_groessengrenze_bricht_ab(self):
        """Ueber der Grenze wird abgebrochen - nicht geschrieben."""
        alt = self.w.MAX_GB
        self.w.MAX_GB = 0.0
        try:
            zeilen, _d, _t = self.vorschau(30, "1D")
        finally:
            self.w.MAX_GB = alt
        self.assertTrue(any("Grenze" in z for z in zeilen), zeilen)

    def test_groessengrenze_bei_kleiner_ordnerzahl_schweigt(self):
        alt = self.w.MAX_GB
        self.w.MAX_GB = 4.0
        try:
            zeilen, _d, _t = self.vorschau(30, "1D")
        finally:
            self.w.MAX_GB = alt
        self.assertFalse(any("Grenze" in z for z in zeilen), zeilen)


class VorschauIstVorgabeTest(Attrappe):
    def test_ohne_anwenden_startet_kein_kindprozess(self):
        """Der teuerste Fehler waere ein Aufruf, der schreibt."""
        aufgerufen = []
        alt = self.w.anwenden
        self.w.anwenden = lambda *a, **kw: aufgerufen.append(a) or 0
        try:
            code = self.w.main([])
        finally:
            self.w.anwenden = alt
        self.assertEqual(0, code)
        self.assertEqual([], aufgerufen,
                         "ohne --anwenden darf `anwenden()` nicht laufen")

    def test_mit_anwenden_ruft_es_das_werkzeug(self):
        aufgerufen = []
        alt = self.w.anwenden
        self.w.anwenden = lambda top, takt, faeden: (
            aufgerufen.append((top, takt, faeden)) or 0)
        try:
            code = self.w.main(["--anwenden", "--top", "12"])
        finally:
            self.w.anwenden = alt
        self.assertEqual(0, code)
        self.assertEqual([(12, "1D", 4)], aufgerufen)

    def test_fehlender_interpreter_bricht_ab(self):
        """Ohne das Haus-Python gibt es keinen Lauf - das wird gemeldet."""
        alt = self.w.PYTHON
        self.w.PYTHON = Path("gibt-es-nicht/python.exe")
        try:
            code = self.w.anwenden(30, "1D", 4)
        finally:
            self.w.PYTHON = alt
        self.assertEqual(2, code, "Fehler, nicht 0 - ein stiller Erfolg waere "
                                  "hier eine leere Historie")


class TaktTest(Attrappe):
    def test_1d_und_1h_werden_getrennt_gezaehlt(self):
        self.lege("BTCUSDT", tage_alt=10.0, takt="1D")
        self.lege("ETHUSDT", tage_alt=10.0, takt="1H")
        z1d, _d1, _t1 = self.vorschau(30, "1D")
        z1h, _d2, _t2 = self.vorschau(30, "1H")
        self.assertTrue(any("zu alt (>5 Tage): 1" in z for z in z1d), z1d)
        self.assertTrue(any("zu alt (>5 Tage): 1" in z for z in z1h), z1h)


if __name__ == "__main__":
    unittest.main()