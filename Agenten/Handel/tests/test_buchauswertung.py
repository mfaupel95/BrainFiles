"""Tests der gemeinsamen Buchauswertung (Handel/buchauswertung.py).

Kein Netz, keine echte Datei: jede Lage schreibt ihr eigenes Journal in ein
temp-Verzeichnis. Belegt wird, was beide Buecher teilen - und die zwei
Kostenformen, denn genau da unterscheiden sie sich:

  omniquant fasst slippage + gebuehr zu EINEM Satz je Seite zusammen,
  spiegel rechnet beide Saetze nacheinander ((1+s)(1+g) beim Kauf).

Beide Wege muessen dieselbe Rendite "vor Kosten" ergeben - sonst waere die
Zahl zwischen den Spuren nicht vergleichbar.

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest discover -s . -p "test_*.py"
"""

import csv
import datetime as dt
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import buchauswertung as b                                 # noqa: E402


def _zeile(einsatz, wert, grund="ziel", **extra):
    e = {"zeit": "", "name": "X", "grund": grund,
         "einsatz": float(einsatz), "wert": float(wert),
         "netto_pct": (wert / einsatz - 1.0) * 100.0}
    e.update(extra)
    return e


class KostenTest(unittest.TestCase):
    """Die Rueckrechnung vor Kosten - die Kernzahl beider Buecher."""

    def test_symmetrischer_satz_ist_die_omniquant_form(self):
        # Ein Skalar bedeutet: kauf = 1+k, verkauf = 1-k.
        k = 0.0025
        self.assertAlmostEqual(b.brutto_pct(0.0, k), 2 * k / (1 - k) * 100.0,
                               places=6)

    def test_getrennte_faktoren_sind_die_spiegel_form(self):
        # (1+s)(1+g) beim Kauf, (1-s)(1-g) beim Verkauf: ohne Bewegung
        # bleiben rund 7,7 % minus (3 % Slippage + 1 % Gebuehr je Seite).
        kauf, verkauf = b.faktoren(3.0, 1.0)
        self.assertAlmostEqual(kauf, 1.03 * 1.01, places=9)
        self.assertAlmostEqual(verkauf, 0.97 * 0.99, places=9)
        brutto_null = b.brutto_pct(0.0, kauf, verkauf)
        self.assertAlmostEqual(brutto_null, (kauf / verkauf - 1) * 100, places=6)
        self.assertGreater(brutto_null, 7.0)

    def test_umkehrformel_ist_exakt(self):
        for netto in (-30.0, -7.7, 0.0, 1.23, 110.0):
            kauf, verkauf = b.faktoren(3.0, 1.0)
            brutto = b.brutto_pct(netto, kauf, verkauf)
            wieder = ((1 + brutto / 100.0) * verkauf / kauf - 1.0) * 100.0
            self.assertAlmostEqual(wieder, netto, places=6)

    def test_zeile_mit_eigenen_kosten_hat_vorrang(self):
        # spiegel schreibt die Saetze je Zeile mit; die Zeile gilt, nicht die
        # Einstellung der Spur.
        teuer = _zeile(50, 50, kosten=b.faktoren(10.0, 5.0))
        kz = b.kennzahlen([teuer], b.faktoren(3.0, 1.0))
        self.assertGreater(kz["brutto_pct"], 15.0)


class LadeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "journal.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def _schreibe(self, zeilen, spalten=("zeit", "modus", "aktion", "inst",
                                         "symbol", "token", "preis",
                                         "einsatz_usd", "wert_usd", "grund",
                                         "kette", "marktkap_usd", "score",
                                         "slippage_pct", "gebuehr_pct")):
        with open(self.pfad, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
            w.writeheader()
            for z in zeilen:
                w.writerow(z)

    def test_aktionen_werden_ohne_grossschreibung_verglichen(self):
        # omniquant schreibt "AUSSTIEG", spiegel "schliessen".
        self._schreibe([
            {"aktion": "AUSSTIEG", "inst": "BTC-USDC", "einsatz_usd": "50",
             "wert_usd": "55"},
            {"aktion": "eroeffnen", "inst": "BTC-USDC", "einsatz_usd": "50"},
        ])
        aus = b.lade_zeilen(self.pfad, ("ausstieg",))
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["inst"], "BTC-USDC")

    def test_zeile_ohne_betrag_faellt_raus(self):
        self._schreibe([{"aktion": "AUSSTIEG", "inst": "X", "einsatz_usd": ""}])
        self.assertEqual(b.lade_zeilen(self.pfad, ("AUSSTIEG",)), [])

    def test_textspalten_bleiben_text_zahlspalten_werden_zahlen(self):
        # kette ist Text, marktkap_usd eine Zahl - eine Zahl-Funktion fuer
        # beide macht aus jeder Kette ein "?".
        self._schreibe([{"aktion": "schliessen", "symbol": "YOYO",
                         "token": "abc", "kette": "solana",
                         "marktkap_usd": "380414", "einsatz_usd": "50",
                         "wert_usd": "76.67", "grund": "ziel"}])
        e = b.lade_zeilen(self.pfad, ("schliessen",),
                          extra=("kette", "symbol", "token", "marktkap_usd"))[0]
        self.assertEqual(e["kette"], "solana")
        self.assertEqual(e["symbol"], "YOYO")
        self.assertEqual(e["name"], "YOYO")
        self.assertAlmostEqual(e["marktkap_usd"], 380414.0)

    def test_kostenspalten_werden_je_zeile_gelesen(self):
        self._schreibe([{"aktion": "schliessen", "inst": "X",
                         "einsatz_usd": "50", "wert_usd": "55",
                         "slippage_pct": "3.0", "gebuehr_pct": "1.0"}])
        e = b.lade_zeilen(self.pfad, ("schliessen",), mit_kosten=True)[0]
        kauf, verkauf = e["kosten"]
        self.assertAlmostEqual(kauf, 1.03 * 1.01, places=9)


class BandTest(unittest.TestCase):
    def test_bandnamen_sind_lesbar(self):
        self.assertEqual(b.band(57.0, (55.0, 60.0, 65.0)), "55-60")
        self.assertEqual(b.band(50.0, (55.0, 60.0)), "< 55")
        self.assertEqual(b.band(70.0, (55.0, 60.0)), ">= 60")
        # Grosse Zahlen ohne Exponentialschreibweise.
        self.assertEqual(b.band(100_000, (250_000, 1_000_000)), "< 250k")
        self.assertEqual(b.band(500_000, (250_000, 1_000_000)), "250k-1M")
        self.assertEqual(b.band(9_000_000, (250_000, 1_000_000)), ">= 1M")

    def test_none_ist_kein_band(self):
        self.assertEqual(b.band(None, (1, 2)), "?")


class HinweisTest(unittest.TestCase):
    def test_ohne_daten_keine_behauptung(self):
        aus = [_zeile(50, 45, score=57.0) for _ in range(3)]
        h = b.hinweise(aus, 0.0025)
        self.assertTrue(any("Datenlage" in x for x in h))

    def test_band_muster_wird_gefuellt(self):
        aus = [_zeile(50, 45, score=57.0) for _ in range(8)]
        h = b.hinweise(aus, 0.0025, baender=[
            ("score", (55.0, 60.0), "Nach Score", "Score %(band)s: %(n)d")])
        self.assertTrue(any(x.startswith("Score 55-60: 8") for x in h))

    def test_stop_hinweis_laesst_sich_abschalten(self):
        # spiegel fuehrt keine MFE - "der Stop war zu eng" waere geraten.
        aus = [_zeile(50, 45, grund="stop", mfe_pct=4.0) for _ in range(8)]
        mit = b.hinweise(aus, 0.0025)
        ohne = b.hinweise(aus, 0.0025, mit_stop_hinweis=False)
        self.assertTrue(any("Buchgewinn" in x for x in mit))
        self.assertFalse(any("Buchgewinn" in x for x in ohne))

    def test_ohne_mfe_kein_stop_hinweis(self):
        aus = [_zeile(50, 45, grund="stop") for _ in range(8)]
        self.assertFalse(any("Buchgewinn" in x for x in b.hinweise(aus, 0.0025)))


class KernzeilenTest(unittest.TestCase):
    def test_leer_ist_eine_datenlage_keine_nullbilanz(self):
        z = b.kernzeile([], 0.0025)
        self.assertIn("kein Ausstieg", z)
        self.assertIn(str(b.MIN_AUSSTIEGE), z)
        self.assertEqual(len(b.kernzeilen([], 0.0025)), 1)

    def test_mit_daten_stehen_beide_kostenseiten_da(self):
        z = b.kernzeile([_zeile(50, 55)], 0.0025)
        self.assertIn("1 Ausstiege", z)
        self.assertIn("nach Kosten", z)
        self.assertIn("davor", z)


class TestLadeZeilenFenster(unittest.TestCase):
    """Das Fenster in der gemeinsamen Mechanik der Papierbuecher."""

    KOPF = "zeit,aktion,einsatz_usd,wert_usd\n"
    ZEILEN = (
        "2026-08-01T10:00:00+00:00,verkauf,100,110\n"
        "2026-09-10T10:00:00+00:00,verkauf,100,90\n"
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = Path(self.tmp.name) / "handelsjournal.csv"
        self.pfad.write_text(self.KOPF + self.ZEILEN, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ohne_fenster_alle(self):
        aus = b.lade_zeilen(str(self.pfad), ("verkauf",))
        self.assertEqual(len(aus), 2)

    def test_mit_fenster_geschnitten(self):
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        aus = b.lade_zeilen(str(self.pfad), ("verkauf",), von=von)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["wert"], 90.0)


if __name__ == "__main__":
    unittest.main()
