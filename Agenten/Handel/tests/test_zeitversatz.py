"""Zeitversatz: Leser, Stufen und Auswertung - ohne Netz.

Der Messwert selbst kommt aus dem Markt und aendert sich mit jedem Signal;
festgehalten wird hier, was das Werkzeug RECHNET: welcher Einstieg ins Fenster
faellt, in welche Altersstufe er gehoert, was doppelt ist und wie der Bericht
rechnet.

Kein Netz: `_preise` wird ersetzt, die Messdatei zeigt in einen Temp-Ordner.
Direkt ausfuehrbar:  python tests/test_zeitversatz.py
"""

import csv
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import zeitversatz_messen as zm                                 # noqa: E402


def _iso(minuten_zurueck):
    return (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(minutes=minuten_zurueck)).isoformat(timespec="seconds")


class StufenTest(unittest.TestCase):

    def test_stufen_grenzen(self):
        self.assertEqual(zm.stufe(0.5), "0-5")
        self.assertEqual(zm.stufe(5.0), "5-15")
        self.assertEqual(zm.stufe(14.9), "5-15")
        self.assertEqual(zm.stufe(180.0), "180-720")
        self.assertIsNone(zm.stufe(720.0), "ab dem Fenster gibt es keine Stufe")
        self.assertIsNone(zm.stufe(9999))


class EinstiegeTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.alt = zm.HIER
        zm.HIER = self.tmp
        self.addCleanup(setattr, zm, "HIER", self.alt)
        self.pfad = self.tmp / "kopier"
        self.pfad.mkdir()
        self.datei = self.pfad / "handelsjournal.csv"
        with self.datei.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "aktion", "kette", "token", "symbol",
                        "preis_vorbild", "preis_einstieg", "grund"])
            # frisch, im Fenster
            w.writerow([_iso(9), "eroeffnen", "solana", "AAA", "A",
                        "0.001", "0.00105", "kopie"])
            # zu alt (ausserhalb 720 min)
            w.writerow([_iso(900), "eroeffnen", "solana", "BBB", "B",
                        "0.002", "0.0021", "kopie"])
            # kein Einstieg
            w.writerow([_iso(3), "schliessen", "solana", "CCC", "C",
                        "0.003", "0.0031", "ziel"])
            # ohne Preis
            w.writerow([_iso(4), "eroeffnen", "solana", "DDD", "D", "", "x", "kopie"])

    def test_nur_frische_einstiege_mit_preis(self):
        e = zm.einstiege("kopier", "kopier/handelsjournal.csv",
                         "preis_vorbild")
        self.assertEqual([x["token"] for x in e], ["AAA"])
        self.assertEqual(e[0]["kette"], "solana")
        self.assertLess(e[0]["alter_min"], 15)


class DoppelteMessungTest(unittest.TestCase):

    def test_schon_gemessen_liest_die_datei(self):
        tmp = Path(tempfile.mkdtemp()) / "zeitversatz.csv"
        alt = zm.MESSDATEI
        zm.MESSDATEI = tmp
        self.addCleanup(setattr, zm, "MESSDATEI", alt)
        self.assertEqual(zm.schon_gemessen(), set())
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=zm.SPALTEN)
            w.writeheader()
            w.writerow({"signal_zeit": "2026-09-21T06:00:00+00:00", "spur": "kopier",
                        "symbol": "X", "token": "TTT", "alter_min": "7.5",
                        "preis_signal": "1", "preis_jetzt": "1.05"})
        self.assertEqual(zm.schon_gemessen(),
                         {("2026-09-21T06:00:00+00:00", "kopier", "TTT", "5-15")})


class SammelnTest(unittest.TestCase):

    def test_sammeln_schreibt_je_stufe_eine_zeile(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "kopier").mkdir()
        alt_hier, alt_datei = zm.HIER, zm.MESSDATEI
        zm.HIER = tmp
        zm.MESSDATEI = tmp / "zeitversatz.csv"
        self.addCleanup(setattr, zm, "HIER", alt_hier)
        self.addCleanup(setattr, zm, "MESSDATEI", alt_datei)
        with (tmp / "kopier" / "handelsjournal.csv").open(
                "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "aktion", "kette", "token", "symbol", "preis"])
            w.writerow([_iso(2), "eroeffnen", "solana", "AAA", "A", "1.0"])
            w.writerow([_iso(12), "eroeffnen", "solana", "AAA", "A", "1.0"])
        zm._preise = lambda punkte: {("solana", "AAA"): 1.2}
        geschrieben = zm.sammeln()
        self.assertEqual(geschrieben, 2, "zwei Altersstufen, zwei Zeilen")
        with zm.MESSDATEI.open(newline="", encoding="utf-8") as fh:
            zeilen = list(csv.DictReader(fh))
        self.assertEqual(len(zeilen), 2)
        self.assertEqual({z["preis_jetzt"] for z in zeilen}, {"1.2"})
        # Zweiter Lauf: dieselben Einstiege und Stufen sind belegt -> nichts neu
        self.assertEqual(zm.sammeln(), 0)

    def test_ohne_preis_keine_zeile(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "kopier").mkdir()
        alt_hier, alt_datei = zm.HIER, zm.MESSDATEI
        zm.HIER = tmp
        zm.MESSDATEI = tmp / "zeitversatz.csv"
        self.addCleanup(setattr, zm, "HIER", alt_hier)
        self.addCleanup(setattr, zm, "MESSDATEI", alt_datei)
        with (tmp / "kopier" / "handelsjournal.csv").open(
                "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["zeit", "aktion", "kette", "token", "symbol", "preis"])
            w.writerow([_iso(2), "eroeffnen", "solana", "AAA", "A", "1.0"])
        zm._preise = lambda punkte: {}
        self.assertEqual(zm.sammeln(), 0)
        self.assertFalse(zm.MESSDATEI.exists(), "keine Zeile, keine Datei")


class BerichtTest(unittest.TestCase):

    def test_bericht_rechnet_median_gegen_signalpreis(self):
        tmp = Path(tempfile.mkdtemp()) / "zeitversatz.csv"
        alt = zm.MESSDATEI
        zm.MESSDATEI = tmp
        self.addCleanup(setattr, zm, "MESSDATEI", alt)
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=zm.SPALTEN)
            w.writeheader()
            for alter, jetzt in ((2, "1.05"), (3, "1.10"), (20, "0.90")):
                w.writerow({"signal_zeit": _iso(1), "spur": "kopier", "symbol": "A",
                            "token": "AAA", "alter_min": str(alter),
                            "preis_signal": "1.0", "preis_jetzt": jetzt})
        import io
        from contextlib import redirect_stdout
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            rc = zm.bericht()
        text = puffer.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("0-5", text)
        self.assertIn("+10.00", text)      # Median von +5 % und +10 %
        self.assertIn("15-30", text)
        self.assertIn("-10.00", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)