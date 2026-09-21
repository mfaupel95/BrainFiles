"""Papier-Altlasten im Live-Buch: der Live-Lauf bucht sie selbst aus.

Anlass (21.09.2026, gemessen): Das scanner-Buch ist EINES fuer Papier und Live.
Der Zyklus um 23:48 lief im Papier (Fenster zu) und füllte dasselbe Buch; um
02:06 lief die Spur live - vier Positionen ohne jede OKX-Order standen im
Live-Buch, fünf von fünf Plätzen belegt, der Scanner konnte live nichts Neues
kaufen und jeder Ausstiegsversuch lief in einen Fehler (am Handelsplatz gibt es
nichts zu verkaufen). Von Hand war das am 20.09. schon einmal bereinigt worden
(buchbereinigung.py) - es wächst nach, solange es niemand automatisch tut.

Dieser Test hält fest: der Live-Lauf räumt VOR dem Handeln auf, echte
Order-Träger bleiben liegen, es geht keine Order an die Börse, und ohne
Altlasten passiert nichts (idempotent).

Kein Netz: handeln.okx wird durch eine Attrappe ersetzt, JOURNAL zeigt in eine
Temp-Datei. Direkt ausführbar:  python tests/test_handeln_altlasten.py
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # scanner/ - handeln, okx

import handeln as h                                            # noqa: E402


class AttrappeOKX:
    """Das okx-Modul ohne Netz. Merkt sich, wer eine Order ausgelöst hat."""

    def __init__(self, kurse=None, kurs_fehler=None):
        self.kurse = kurse or {}
        self.kurs_fehler = kurs_fehler or set()
        self.orders = []

    def letzter_kurs(self, inst):
        if inst in self.kurs_fehler:
            raise RuntimeError("kein Kurs (Attrappe)")
        return self.kurse.get(inst)

    def markt_verkauf(self, inst, menge):
        self.orders.append(("verkauf", inst, menge))

    def order_details(self, inst, ord_id):
        self.orders.append(("details", inst, ord_id))
        return {"accFillSz": "1"}


def p(inst, ord_id=None, einstieg=10.0, usd=100.0):
    return {"inst": inst, "einstieg": einstieg, "usd": usd, "stop": einstieg * 0.9,
            "ziel": einstieg * 1.2, "eroeffnet": "2026-09-20",
            "kauf_ord_id": ord_id, "stop_ord_id": None}


class AltlastenTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.alt_journal = h.JOURNAL
        h.JOURNAL = Path(self.tmp) / "handelsjournal.csv"   # Datei darf noch NICHT
        self.addCleanup(setattr, h, "JOURNAL", self.alt_journal)   # existieren, sonst
        self.alt_okx = h.okx                                       # fehlt die Kopfzeile
        self.addCleanup(setattr, h, "okx", self.alt_okx)

    def zeilen(self):
        if not h.JOURNAL.exists():
            return []
        with open(h.JOURNAL, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_papier_altlast_wird_ausgebucht(self):
        h.okx = AttrappeOKX({"NEAR-USDT": 2.80, "ZEC-USDC": 1400.0})
        z = {"positionen": [p("NEAR-USDT"), p("ZEC-USDC", ord_id="3940642")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual([x["inst"] for x in z["positionen"]], ["ZEC-USDC"],
                         "echte Order-Traeger muessen liegen bleiben")
        self.assertEqual(h.okx.orders, [], "keine Order an die Boerse")
        zeilen = self.zeilen()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["grund"], "buchbereinigung")
        self.assertEqual(zeilen[0]["modus"], "papier")
        self.assertEqual(zeilen[0]["aktion"], "verkauf")
        # G/V: 100 USD Einsatz, Kurs 2.80 gegen Einstieg 10.00 -> -72.00
        self.assertAlmostEqual(float(zeilen[0]["usd"]), 28.0, places=2)

    def test_idempotent_ohne_altlast(self):
        h.okx = AttrappeOKX({})
        z = {"positionen": [p("ZEC-USDC", ord_id="3940642")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.zeilen(), [])

    def test_ohne_kurs_bleibt_liegen(self):
        h.okx = AttrappeOKX(kurs_fehler={"NEAR-USDT"})
        z = {"positionen": [p("NEAR-USDT")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual([x["inst"] for x in z["positionen"]], ["NEAR-USDT"],
                         "ohne Kurs darf nichts verschwinden")
        self.assertEqual(self.zeilen(), [])

    def test_leeres_buch(self):
        h.okx = AttrappeOKX({})
        z = {"positionen": []}
        self.assertEqual(h.bueche_papier_altlasten_aus(z), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
