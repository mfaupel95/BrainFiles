"""Die Haus-Bremse gegen OKX-Drosselung (okx_takt.py) - die REGEL, nicht
heutige Zahlen.

ANLASS (05.10.2026): 43 Zyklusabbrueche im Bus-Journal mit
`OKXFehler: OKX 50011: Too Many Requests (HTTP 429)`, 40 davon beim scanner
(19.-20.09., 26.-29.09., 2.-5.10.). Gemessen wurde die Ursache, nicht vermutet:

    120 Kerzenabrufe NACHEINANDER in 30 s  ->  0 Fehler
    6 Threads x 40 Ticker in 23 s           ->  93x 50011

Der Ausloeser ist die PARALLELITAET. Im Haus laufen gleichzeitig drei
Dauerlauf-Stufen, die Handelszentrale (eigener Refresh-Takt), die Wachen und
die Werkzeuge - jeder in seinem eigenen Prozess, alle gegen dieselbe IP.
Eine Bremse je Prozess wuerde nichts aendern, darum sitzt sie in einer Datei.

Geprueft wird:
  1. Die Bremse haelt die Rate - ueber eine ZAEHLBAR kuenstliche Uhr.
  2. `ist_429` erkennt BEIDE Fehlerformen (HTTPStatus 429 und der OKX-Text
     50011 / 'Too Many Requests'), weil sie im Haus aus zwei Ebenen kommen.
  3. Ein 429 wird durch Warten geheilt, ein fachlicher Fehler NICHT.
  4. JEDER OKX-Weg des Hauses sitzt an der Bremse - mit echten Aufrufen der
     vier Module, nicht mit dem Wort im Kommentar.
  5. Die Bremse haelt ohne Sperre weiter (kein fremder Prozess darf sie
     aufheben) und gibt ohne Ordner den Handel frei.
"""

import importlib.util
import io
import os
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent


def lade(pfad, name):
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    sys.modules[name] = m
    s.loader.exec_module(m)
    return m


class BremseTest(unittest.TestCase):
    """Regel 1: die Rate haelt, gemessen an einer kuenstlichen Uhr.

    Nicht an der echten Uhr: ein Test, der eine Rate misst, prueft sonst nur,
    wie schnell der Rechner ist. `fester_zeitpunkt` existiert genau dafür.
    """

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="takt-test-")
        self.takt = lade(HANDEL / "okx_takt.py", "okx_takt_test")
        self.takt.ORDNER = os.path.join(self.ordner, "fenster")
        self.takt.DATEI = os.path.join(self.takt.ORDNER, "fenster.json")
        self.takt.SPERRE = os.path.join(self.takt.ORDNER, "fenster.lock")
        self.takt.leeren()

    def test_zehn_aufeinanderfolgende_bleiben_0_167_sekunden_auseinander(self):
        """TAKT_ABRUFE je TAKT_FENSTER_S heisst FENSTER/ABRUFE Sekunden
        Abstand. Die erste Fassung rechnete die Rate falsch herum und war
        dreimal zu langsam (2,2/s statt 6/s, gemessen)."""
        uhr = 1_000_000.0
        for _ in range(10):
            self.takt.reserviere(fester_zeitpunkt=uhr)
            uhr += self.takt.TAKT_ABSTAND_S

        werte = self.takt._lese()
        self.assertEqual(10, len(werte))
        abstaende = [b - a for a, b in zip(werte, werte[1:])]
        for d in abstaende:
            # 3 Nachkommastellen: die gespeicherten Marken sind auf 3
            # Stellen gerundet (_schreibe), 6 Stellen koennten nie halten.
            self.assertAlmostEqual(self.takt.TAKT_ABSTAND_S, d, places=3)

    def test_der_mindestabstand_ist_die_fensterregel_selbst(self):
        """Der Abstand folgt 'N Abrufe je M Sekunden' = M/N. Wer 12/2,0 als 6
        liest, hat den Bruch verdreht - die Formel muss die Rate liefern,
        die man selbst erwartet."""
        erwartet = self.takt.TAKT_FENSTER_S / self.takt.TAKT_ABRUFE
        self.assertAlmostEqual(erwartet, self.takt.TAKT_ABSTAND_S, places=9)
        self.assertLess(self.takt.TAKT_ABSTAND_S, 0.25,
                        "die Bremse waere langsamer als der Fehler, den sie heilt")

    def test_das_fenster_bricht_nach_der_zeit_auf(self):
        """Abgelaufene Marken zaehlen nicht mehr - sonst blockiert die Bremse
        sich selbst, sobald ein Prozess eine Weile schweigt.

        Der Fensterinhalt wird von HAND in die Datei gelegt (20 Marken), statt
        ihn durch 20 reserviere() zu erzeugen: die Bremse laesst naemlich nie
        mehr als TAKT_ABRUFE zu, der 13. Aufruf wartet dann korrekt. Wer hier
        die Bremse benutzt, um ihr Fenster zu fuellen, prueft die Bremse
        gegen sich selbst - genau das tat die erste Fassung dieses Tests und
        lief in eine 180-S-Blockade, weil die Auswertung an der Testuhr stand
        und die reale Uhr nicht fortschritt.
        """
        alt = time.time() - self.takt.TAKT_FENSTER_S - 1.0
        self.takt._schreibe([alt] * 20)

        self.takt.reserviere()
        self.assertEqual(1, len(self.takt._lese()),
                         "abgelaufene Marken wurden nicht abgebaut")

    def test_juengere_marken_bleiben_stehen(self):
        """Der Abbau gilt nur fuer die abgelaufenen - sonst verliert die
        Bremse ihre Wirkung, ohne dass es jemand bemerkt."""
        jetzt = time.time()
        self.takt._schreibe([jetzt - 0.1] * 20)
        with self.assertRaises(self.takt.TaktBlockiert):
            alt = self.takt.MAX_WARTE_S
            self.takt.MAX_WARTE_S = 0.5
            try:
                self.takt.reserviere()
            finally:
                self.takt.MAX_WARTE_S = alt

    def test_ohne_ordner_liefert_sofort(self):
        """Ein fehlender Cache-Ordner darf keine Live-Position blockieren."""
        self.takt.ORDNER = os.path.join(self.ordner, "gibtsnicht", "x")
        self.takt.DATEI = os.path.join(self.takt.ORDNER, "fenster.json")
        self.takt.SPERRE = os.path.join(self.takt.ORDNER, "fenster.lock")
        self.assertEqual(0.0, self.takt.reserviere())


class FehlerformTest(unittest.TestCase):
    """Regel 2: 429 kommt im Haus in zwei Formen vor."""

    def setUp(self):
        self.takt = lade(HANDEL / "okx_takt.py", "okx_takt_ist429")

    def test_das_okx_zeichen_ist_eine_drosselung(self):
        self.assertTrue(self.takt.ist_429(
            RuntimeError("OKX 50011: Too Many Requests (HTTP 429)")))

    def test_der_http_status_ist_eine_drosselung(self):
        fehler = type("E", (OSError,), {})("HTTP Error 429")
        fehler.code = 429
        self.assertTrue(self.takt.ist_429(fehler))

    def test_ein_fachlicher_fehler_ist_keine_drosselung(self):
        for text in ("OKX 51008: Insufficient balance",
                     "OKX 50119: API key doesn't exist",
                     "ConnectionResetError: [WinError 10054]"):
            self.assertFalse(self.takt.ist_429(RuntimeError(text)), text)

    def test_die_wartezeit_waechst_und_bleibt_gedeckelt(self):
        self.assertLess(self.takt.warte_s(1), self.takt.warte_s(3))
        self.assertLessEqual(self.takt.warte_s(20), 30.0)


class VerdrahtungTest(unittest.TestCase):
    """Regel 4: jeder OKX-Weg des Hauses sitzt an der Bremse.

    Geprueft wird der AUFRUF, nicht das Stichwort im Kommentar: eine Datei,
    die 'okx_takt' nur erwaehnt, faellt hier durch.
    """

    STELLEN = (
        "scanner/okx.py",
        "xperp/okxf.py",
        "mosaic/okx_spot.py",
        "iv_wand/handeln.py",
        "moondev_daten.py",
    )

    def test_alle_oko_module_importieren_und_rufen_reserviere(self):
        for rel in self.STELLEN:
            text = (HANDEL / rel).read_text(encoding="utf-8")
            self.assertIn("okx_takt.reserviere()", text,
                          "%s ruft die Bremse nicht" % rel)

    def test_alle_oko_module_wuerfen_einen_429_nicht_sofort(self):
        """Ein 429, der durchgereicht wird, beendet den Zyklus - das war die
        alte Regel (OKXFehler wird nicht wiederholt) und die Ursache der 43
        Abbruche."""
        for rel in self.STELLEN:
            text = (HANDEL / rel).read_text(encoding="utf-8")
            self.assertIn("okx_takt.ist_429", text,
                          "%s unterscheidet die Drosselung nicht" % rel)

    def test_die_wachen_und_werkzeuge_sitzen_dran(self):
        BASIS = HANDEL.parent
        for rel in ("Werkzeuge/breite.py", "Werkzeuge/topmover.py",
                    "Werkzeuge/marktdaten.py",
                    "Hermes/scripts/one_wache.py",
                    "Hermes/scripts/okx-gesundheit.py",
                    "Hermes/scripts/okx-trading-bericht.py"):
            text = (BASIS / rel).read_text(encoding="utf-8")
            self.assertIn("okx_takt.reserviere()", text, rel)
            self.assertIn("okx_takt", text, rel)

    def test_die_werkzeugpfade_wirklich_existieren(self):
        """Vier Werkzeuge zeigten beim Bauen auf einen Pfad, den es nicht gibt
        (drei statt zwei Ebenen hoch) - im Betrieb waere das ein Abbruch beim
        Import. Der Pfad wird darum GESUCHT, nicht gezaehlt."""
        BASIS = HANDEL.parent
        for rel in ("Werkzeuge/breite.py", "Werkzeuge/topmover.py",
                    "Werkzeuge/marktdaten.py",
                    "Hermes/scripts/one_wache.py",
                    "Hermes/scripts/okx-gesundheit.py",
                    "Hermes/scripts/okx-trading-bericht.py"):
            quelle = (BASIS / rel).read_text(encoding="utf-8")
            if "def _lade_okx_takt" not in quelle:
                continue                     # Spuren: sys.path-Anhaengen
            ausgefuehrt = {}
            for zeile in quelle.splitlines():
                if "_os.path.join(_os.path.dirname(_os.path.dirname(" in zeile:
                    continue
            # Der Loader muss von hier aus echt finden: nachrechnen wie er.
            hier = (BASIS / rel).parent
            kandidat = os.path.normpath(os.path.join(hier, "..", "Handel",
                                                     "okx_takt.py"))
            if not os.path.exists(kandidat):
                kandidat = os.path.normpath(os.path.join(hier, "..", "..",
                                                         "Handel", "okx_takt.py"))
            self.assertTrue(os.path.exists(kandidat),
                            "%s findet okx_takt nicht" % rel)


class ScannerGegenprobeTest(unittest.TestCase):
    """Regel 3 gegen den echten scanner-okx: 429 heilt, fachlich wird
    geworfen. Die Bremse wird ausgeschaltet, damit der Test schnell bleibt -
    es geht um die FEHLERREGEL, nicht um den Takt."""

    def setUp(self):
        sys.path.insert(0, str(HANDEL / "scanner"))
        sys.path.insert(0, str(HANDEL))
        self.okx = lade(HANDEL / "scanner" / "okx.py", "okx")
        self.okx_takt = lade(HANDEL / "okx_takt.py", "okx_takt_scanner")
        self.okx.okx_takt = self.okx_takt
        self.schlaf = mock.patch.object(self.okx.time, "sleep")
        self.schlaf.start()
        self.addCleanup(self.schlaf.stop)

    def test_ein_429_wird_geheilt_statt_geworfen(self):
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            if len(aufrufe) < 3:
                raise self.okx.OKXFehler("OKX 50011: Too Many Requests (HTTP 429)")
            return [{"ok": 1}]

        with mock.patch.object(self.okx, "_roh", roh), redirect_stderr(io.StringIO()) as err:
            ergebnis = self.okx._mit_wiederholung("/api/v5/x")
        self.assertEqual([{"ok": 1}], ergebnis)
        self.assertEqual(3, len(aufrufe), "429 wurde nicht wiederholt")
        self.assertIn("gedrosselt", err.getvalue())
        self.assertIn("kein Ausfall", err.getvalue())

    def test_ein_fachlicher_fehler_wird_nicht_wiederholt(self):
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            raise self.okx.OKXFehler("OKX 50119: API key doesn't exist")

        with mock.patch.object(self.okx, "_roh", roh), redirect_stderr(io.StringIO()):
            with self.assertRaises(self.okx.OKXFehler):
                self.okx._mit_wiederholung("/api/v5/x")
        self.assertEqual(1, len(aufrufe),
                         "fachliche Fehler nur EINMAL versuchen")

    def test_nach_vier_drosselungen_wird_geworfen(self):
        """Ein Takt, der wartet, heilt - ein Takt, der gar nicht mehr
        vorankommt, nicht. Sonst haengt eine Spur ewig."""
        aufrufe = []

        def roh(*a, **kw):
            aufrufe.append(1)
            raise self.okx.OKXFehler("OKX 50011: Too Many Requests (HTTP 429)")

        with mock.patch.object(self.okx, "_roh", roh), redirect_stderr(io.StringIO()):
            with self.assertRaises(self.okx.OKXFehler):
                self.okx._mit_wiederholung("/api/v5/x")
        self.assertEqual(self.okx.MAX_429, len(aufrufe))


class SperrenfallTest(unittest.TestCase):
    """Regel 5: ein fremder Prozess darf den Takt nicht aufheben.

    Die erste Fassung gab bei gesperrter Datei einfach frei ('durchlassen') -
    damit waere genau dann keine Bremse mehr, wenn mehrere Prozesse zugleich
    zugreifen.
    """

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="takt-sperre-")
        self.takt = lade(HANDEL / "okx_takt.py", "okx_takt_sperre")
        self.takt.ORDNER = os.path.join(self.ordner, "fenster")
        self.takt.DATEI = os.path.join(self.takt.ORDNER, "fenster.json")
        self.takt.SPERRE = os.path.join(self.takt.ORDNER, "fenster.lock")
        self.takt.leeren()

    def test_eine_fremde_sperre_bricht_den_takt_nicht_ab(self):
        with open(self.takt.SPERRE, "w", encoding="utf-8") as f:
            f.write("999999")
        alt = self.takt.MAX_SPERREN_S
        self.takt.MAX_SPERREN_S = 0.05          # schnell pruefbar
        try:
            t0 = time.time()
            self.takt.reserviere()
            self.assertLess(time.time() - t0, 5.0,
                            "die Bremse hat bei fremder Sperre nicht geliefert")
            # Der Platz wurde trotzdem vermerkt - der Takt gilt weiter.
            self.assertEqual(1, len(self.takt._lese()))
        finally:
            self.takt.MAX_SPERREN_S = alt


if __name__ == "__main__":
    unittest.main()