"""Papier-Altlasten im Kraken-Live-Buch: der Live-Lauf bucht sie selbst aus.

Anlass 21.09.2026, gemessen: kraken ist seit 08:43 live (Freigabefenster der
Auto-Freigabe offen, EUR-Guthaben ueber der Schwelle 60). Sein Buch trug aber
die vier Positionen der Papierphase - alle ohne `kauf_txid`. Damit sind alle
vier Plaetze belegt (live wird nichts gekauft) und der Live-Ausstieg versucht,
Coins zu verkaufen, die am Konto nicht liegen.

Derselbe Fehler stand am selben Tag beim scanner; die Probe dort hat den Fix
bestanden (scanner/handeln.bueche_papier_altlasten_aus).

Kein Netz: `kraken.letzter_kurs` wird ersetzt, das Journal zeigt in eine
Temp-Datei. Direkt ausfuehrbar (aus dem kraken-Ordner):
    python tests/test_handeln_altlasten.py
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                              # noqa: E402


def p(paar, txid=None, einstieg=100.0, eur=50.0):
    return {"paar": paar, "einstieg": einstieg, "eur": eur, "menge": 0.5,
            "stop": einstieg * 0.9, "ziel": einstieg * 1.2,
            "eroeffnet": "2026-09-19", "kauf_txid": txid, "stop_txid": None}


class AltlastenTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()) / "handelsjournal.csv"
        self.alt_journal = h.JOURNAL
        self.alt_kraken = h.kraken
        h.JOURNAL = self.tmp
        self.addCleanup(setattr, h, "JOURNAL", self.alt_journal)
        self.addCleanup(setattr, h, "kraken", self.alt_kraken)

    def zeilen(self):
        if not h.JOURNAL.exists():
            return []
        with h.JOURNAL.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_nur_positionen_ohne_order_werden_ausgebucht(self):
        class Attrappe:
            @staticmethod
            def letzter_kurs(paar):
                return {"XETHZEUR": 2200.0, "XXBTZEUR": 70000.0}[paar]

        h.kraken = Attrappe
        z = {"positionen": [p("XETHZEUR"), p("XXBTZEUR", txid="TX-1")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual([x["paar"] for x in z["positionen"]], ["XXBTZEUR"],
                         "echte Order-Traeger bleiben liegen")
        zeilen = self.zeilen()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["grund"], "buchbereinigung")
        self.assertEqual(zeilen[0]["modus"], "papier")
        self.assertEqual(zeilen[0]["aktion"], "verkauf")

    def test_idempotent(self):
        class Attrappe:
            @staticmethod
            def letzter_kurs(paar):
                return 100.0

        h.kraken = Attrappe
        z = {"positionen": [p("XXBTZEUR", txid="TX-1")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self.zeilen(), [])

    def test_ohne_kurs_bleibt_liegen(self):
        class Attrappe:
            @staticmethod
            def letzter_kurs(paar):
                raise RuntimeError("kein Kurs")

        h.kraken = Attrappe
        z = {"positionen": [p("XETHZEUR")]}
        h.bueche_papier_altlasten_aus(z)
        self.assertEqual([x["paar"] for x in z["positionen"]], ["XETHZEUR"])
        self.assertEqual(self.zeilen(), [])

    def test_leeres_buch(self):
        h.kraken = object()
        self.assertEqual(h.bueche_papier_altlasten_aus({"positionen": []}), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
