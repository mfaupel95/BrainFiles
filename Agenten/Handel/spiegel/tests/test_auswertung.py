"""Tests der Spiegel-Auswertung - ohne Netz, ohne Feed, ohne Order.

Die Mechanik liegt in Handel/buchauswertung.py und hat eigene Tests; hier
steht, was spiegel anders macht: die Aktion heisst "schliessen", die
Kostensaetze stehen je Zeile (oder es gilt der Satz der Wachen), die Tiefe
kommt aus dem Join ueber den Token, und die Gruppen sind Kette und Grund.

Lauf:
    ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL, os.path.join(HANDEL, "scanner")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auswertung as a                                     # noqa: E402
import buchauswertung as b                                 # noqa: E402

SPALTEN = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol",
           "preis", "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
           "slippage_pct", "gebuehr_pct", "grund"]


def _zeile(aktion="schliessen", token="tok1", mk="", einsatz="50",
           wert="76.67", grund="ziel", s="", g=""):
    return {"zeit": "2026-09-12T20:39:40+00:00", "modus": "papier",
            "aktion": aktion, "kette": "solana", "wallet": "W1", "token": token,
            "symbol": "PUMPTHING", "preis": "0.000288", "menge": "276989",
            "einsatz_usd": einsatz, "wert_usd": wert, "marktkap_usd": mk,
            "slippage_pct": s, "gebuehr_pct": g, "grund": grund}


def _journal(pfad, zeilen):
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        w.writeheader()
        for z in zeilen:
            w.writerow(z)


class LadeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_nur_geschlossene_kopien_zaehlen(self):
        _journal(self.pfad, [
            _zeile(aktion="eroeffnen", mk="380414", wert=""),
            _zeile(),
        ])
        aus = a.lade_ausstiege(self.pfad)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["symbol"], "PUMPTHING")
        self.assertEqual(aus[0]["grund"], "ziel")

    def test_tiefe_kommt_aus_der_eroeffnen_zeile(self):
        # Die Schliessen-Zeile traegt keine Marktkapitalisierung - ohne den
        # Join ueber den Token liesse sich kein Tiefenband bilden.
        _journal(self.pfad, [
            _zeile(aktion="eroeffnen", token="tok1", mk="380414", wert=""),
            _zeile(token="tok1"),
        ])
        aus = a.lade_ausstiege(self.pfad)
        self.assertAlmostEqual(aus[0]["marktkap_usd"], 380414.0)

    def test_kosten_je_zeile_haben_vorrang_vor_den_wachen(self):
        _journal(self.pfad, [_zeile(s="3.0", g="1.0")])
        aus = a.lade_ausstiege(self.pfad)
        kauf, verkauf = aus[0]["kosten"]
        self.assertAlmostEqual(kauf, 1.03 * 1.01, places=9)

    def test_ohne_kostenspalten_gilt_der_satz_der_wachen(self):
        _journal(self.pfad, [_zeile()])
        aus = a.lade_ausstiege(self.pfad)
        self.assertIsNone(aus[0]["kosten"])
        k = a._kosten()
        w = a._wachen()
        self.assertAlmostEqual(k[0], b.faktoren(w["slippage_pct"],
                                                w["gebuehr_pct"])[0], places=9)


class BerichtTest(unittest.TestCase):
    def test_gruppen_und_baender_stehen_drin(self):
        # 8 Zeilen: ab MIN_AUSSTIEGE greifen die Hinweise, darunter steht die
        # Datenlage (auch das ist ein Ergebnis, aber ein anderes).
        aus = []
        for i in range(8):
            aus.append({"zeit": "", "name": "S%d" % i, "grund": "ziel",
                        "einsatz": 50.0, "wert": 80.0, "netto_pct": 60.0,
                        "kette": "solana", "marktkap_usd": 100_000.0})
        text = "\n".join(a.bericht(aus, a._kosten()))
        self.assertIn("Nach Kette", text)
        self.assertIn("Nach Ausstiegsgrund", text)
        self.assertIn("Nach Marktkapitalisierung", text)
        self.assertIn("< 250k", text)
        self.assertIn("Keine Auffaelligkeit", text)

    def test_tiefenband_das_nicht_traegt_wird_genannt(self):
        aus = [{"zeit": "", "name": "S%d" % i, "grund": "stop",
                "einsatz": 50.0, "wert": 30.0, "netto_pct": -40.0,
                "kette": "solana", "marktkap_usd": 90_000.0} for i in range(9)]
        h = a.hinweise(aus, a._kosten())
        self.assertTrue(any("Marktkapitalisierung < 250k" in x for x in h))

    def test_kein_stop_hinweis_ohne_buchgewinne(self):
        # Das Buch fuehrt kein MFE - "der Stop war zu eng" waere geraten.
        aus = [{"zeit": "", "name": "S%d" % i, "grund": "stop",
                "einsatz": 50.0, "wert": 30.0, "netto_pct": -40.0,
                "kette": "solana", "marktkap_usd": None} for i in range(9)]
        self.assertFalse(any("Buchgewinn" in x for x in a.hinweise(aus, a._kosten())))

    def test_leeres_journal_sagt_was_fehlt(self):
        text = "\n".join(a.bericht([], a._kosten()))
        self.assertIn("keine geschlossene Kopie", text)


class KernzeilenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ohne_daten_die_datenlage(self):
        self.assertIn("kein Ausstieg", a.kernzeile(self.pfad))
        self.assertEqual(len(a.kernzeilen(self.pfad)), 1)

    def test_mit_daten_die_bilanz(self):
        _journal(self.pfad, [_zeile()])
        z = a.kernzeile(self.pfad)
        self.assertIn("1 Ausstiege", z)
        self.assertIn("nach Kosten", z)


class TagesberichtTest(unittest.TestCase):
    """Die Bilanzzeile im Bericht - ueber den Dateipfad, nicht den Modulnamen.

    Beide Buch-Spuren haben ein auswertung.py; laedt der Bericht ueber
    sys.modules, traegt die Spiegel-Zeile die Zahlen von Omniquant.
    """

    def test_spur_spiegel_traegt_eine_bilanzzeile(self):
        import tagesbericht
        t = tempfile.mkdtemp(prefix="bericht-spiegel-")
        os.makedirs(os.path.join(t, "spiegel"))
        for name in ("wachen.json",):
            shutil.copy(os.path.join(HIER, name),
                        os.path.join(t, "spiegel", name))
        _journal(os.path.join(t, "spiegel", "handelsjournal.csv"), [_zeile()])
        with io.open(os.path.join(t, "spiegel", "zustand.json"), "w",
                     encoding="utf-8") as f:
            json.dump({"modus": "papier", "positionen": []}, f)
        shutil.copy(os.path.join(HIER, "auswertung.py"),
                    os.path.join(t, "spiegel", "auswertung.py"))
        import lage
        # spur_spiegel/_bilanz leben seit dem Umzug nach lage.py - HIER dort
        # mitpatchen, sonst liest der Test das ECHTE Journal (datenabhaengig,
        # Befund 18.09.2026: 875 statt 1 Ausstiege).
        with patch.object(tagesbericht, "HIER", t), \
                patch.object(lage, "HIER", t):
            s = tagesbericht.spur_spiegel()
        self.assertIn("bilanz", s)
        self.assertIn("1 Ausstiege", s["bilanz"])
        self.assertIn("nach Kosten", s["bilanz"])


if __name__ == "__main__":
    unittest.main()
