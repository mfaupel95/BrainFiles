"""auswertung_trading testen. Laesst sich von ueberall aus dem Handel-Ordner
starten (relative Imports ueber den Pfad, kein sys.path-Handling):
    cd Agenten/Handel/tests && ../../scanner/.venv/Scripts/python.exe -m unittest test_auswertung_trading
"""

import csv
import io
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
import auswertung_trading as at

KOPF = ["zeit", "token", "aktion", "confidence", "begruendung"]


def _csv(zeilen):
    puffer = io.StringIO(newline="")
    w = csv.writer(puffer)
    w.writerow(KOPF)
    for z in zeilen:
        w.writerow(z)
    puffer.seek(0)
    return csv.reader(puffer)


class LadenTest(unittest.TestCase):
    def test_kopfzeile_wird_uebersprungen(self):
        d = at.lade(_csv([
            ["2026-09-19 15:03:45", "9BB6NFEc...", "NOTHING", "20", "baerisch"],
            ["2026-09-19 15:04:00", "Eg2ymQ2a...", "BUY", "95", "bullisch"],
        ]))
        self.assertEqual(2, len(d))

    def test_aktion_wird_grossgeschrieben(self):
        d = at.lade(_csv([["t", "tok", "buy", "50", ""]]))
        self.assertEqual("BUY", d[0]["aktion"])

    def test_confidence_als_zahl(self):
        d = at.lade(_csv([["t", "tok", "SELL", "12.5", ""]]))
        self.assertEqual(12.5, d[0]["confidence"])

    def test_zu_wenige_spalten_wirft(self):
        with self.assertRaises(ValueError):
            at.lade(csv.reader(io.StringIO("nur;zwei\n")))  # kein Kopf, <4

    def test_kein_confidence_wirft(self):
        with self.assertRaises(ValueError):
            at.lade(_csv([["t", "tok", "BUY", "oder?", ""]]))


class VerteilungTest(unittest.TestCase):
    ZEILEN = [
        ["t1", "TOK-A", "BUY", "80", ""],
        ["t2", "TOK-A", "NOTHING", "20", ""],
        ["t3", "TOK-B", "SELL", "50", ""],
    ]

    def test_gesamtzaehler(self):
        daten = at.lade(_csv(self.ZEILEN))
        _, gesamt, confs, _ = at.verteilung(daten)
        self.assertEqual(1, gesamt.get("BUY", 0))
        self.assertEqual(1, gesamt.get("SELL", 0))
        self.assertEqual(1, gesamt.get("NOTHING", 0))
        self.assertEqual(50.0, sum(confs) / len(confs))

    def test_je_token_zeilen(self):
        daten = at.lade(_csv(self.ZEILEN))
        _, _, _, zeilen = at.verteilung(daten)
        self.assertEqual(2, len(zeilen))
        by = {z["token"]: z for z in zeilen}
        self.assertEqual(1, by["TOK-A"]["kauf"])
        self.assertEqual(1, by["TOK-B"]["verkauf"])

    def test_filter_teilstring_case_insensitiv(self):
        daten = at.lade(_csv(self.ZEILEN))
        gefiltert, _, _, zeilen = at.verteilung(daten, "tok-a")
        self.assertEqual(2, len(gefiltert))
        self.assertEqual(1, len(zeilen))
        # Filter ohne Treffer ergibt keine Daten.
        leer, _, _, _ = at.verteilung(daten, "gibtsnicht")
        self.assertEqual(0, len(leer))


if __name__ == "__main__":
    unittest.main()