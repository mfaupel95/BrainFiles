"""Papier-Altlasten im xperp-Live-Buch: der Live-Lauf bucht sie selbst aus.

Anlass (21.09.2026, gemessen): xperp lief live, sein Buch fuehrte aber vier
Positionen (ZEC, XAG, LINK, ETC), die es an der Boerse NICHT gibt - die Abfrage
/account/positions kennt nur die manuelle FIL-Position und einen XRP-Rest, die
ZEC- und LINK-Positionen stehen dort mit `pos 0`, XAG und ETC fehlen ganz. Das
Journal beweist die Herkunft: von 14 Live-Zeilen sind ALLE 14 `funding` - kein
einziger Live-Kauf, kein Live-Verkauf. Die vier stammen aus dem Papierlauf.

Dieser Test haelt fest: der Live-Lauf raeumt VOR dem Handeln auf, echte
Live-Positionen bleiben liegen, es geht keine Order an die Boerse, und ohne
Altlasten passiert nichts (idempotent).

Kein Netz: okxf wird durch eine Attrappe ersetzt, JOURNAL zeigt in eine
Temp-Datei. Direkt ausfuehrbar:  python tests/test_handeln_altlasten.py
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))          # xperp/ - handeln, okxf

import handeln as h                                            # noqa: E402


class AttrappeOkxf:
    """okxf ohne Netz. Merkt sich jeden Orderaufruf (darf nie kommen)."""

    def __init__(self):
        self.aufrufe = []

    def markt_schliessen(self, *a, **k):
        self.aufrufe.append(("markt_schliessen", a))
        return True

    def order_limit(self, *a, **k):
        self.aufrufe.append(("order_limit", a))
        return {"ordId": "TEST"}


def _position(inst, modus, margin=25.0, nominal=125.0):
    return {"inst": inst, "basis": inst.split("-")[0], "seite": "long",
            "familie": "krypto", "einstieg": 10.0, "stop": 9.0, "ziel": 12.0,
            "liq": 5.0, "kontrakte": 12, "nominal": nominal, "margin": margin,
            "hebel": 5, "gebuehr_taker": 0.0005, "modus": modus,
            "letzter_kurs": 11.0, "eroeffnet": "2026-09-20",
            "eroeffnet_zeit": "2026-09-20T00:00:00+00:00",
            "funding_zuletzt": "2026-09-20T00:00:00+00:00", "funding_summe": 0.0}


class AltlastenTest(unittest.TestCase):

    def setUp(self):
        self.alt_okxf, self.alt_journal = h.okxf, h.JOURNAL
        self.okxf = AttrappeOkxf()
        self.tmp = Path(tempfile.mkdtemp(prefix="xperp-altlast-"))
        h.okxf = self.okxf
        h.JOURNAL = self.tmp / "handelsjournal.csv"
        self.w = {"gebuehr_taker": 0.0005, "stop_atr_faktor": 1.5,
                  "risiko_je_anlauf_usd": 7.5, "max_margin_je_anlauf_usd": 80,
                  "max_margin_gesamt_usd": 600, "max_offene_anlaeufe": 4}

    def tearDown(self):
        h.okxf, h.JOURNAL = self.alt_okxf, self.alt_journal

    def _zeilen(self):
        if not Path(h.JOURNAL).is_file():
            return []
        with Path(h.JOURNAL).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def test_papier_position_wird_ausgebucht(self):
        z = {"positionen": [_position("ZEC-USD_UM_XPERP-310530", "papier")]}
        n = h.bueche_papier_altlasten_aus(z, self.w, still=True)
        self.assertEqual(n, 1)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.okxf.aufrufe, [], "keine Order an die Boerse")
        zeilen = self._zeilen()
        self.assertEqual(len(zeilen), 1)
        self.assertEqual(zeilen[0]["grund"], "buchbereinigung")
        self.assertEqual(zeilen[0]["modus"], "papier")

    def test_position_ohne_modus_gilt_als_papier(self):
        """Alte Positionen tragen das Feld nicht - genau die vom 21.09.2026."""
        p = _position("LINK-USD_UM_XPERP-310523", "live")
        del p["modus"]
        z = {"positionen": [p]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w, still=True), 1)
        self.assertEqual(z["positionen"], [])

    def test_live_position_bleibt(self):
        z = {"positionen": [_position("ZEC-USD_UM_XPERP-310530", "live"),
                            _position("XAG-USD_UM_XPERP-310509", "papier")]}
        n = h.bueche_papier_altlasten_aus(z, self.w, still=True)
        self.assertEqual(n, 1)
        self.assertEqual([p["inst"] for p in z["positionen"]],
                         ["ZEC-USD_UM_XPERP-310530"])

    def test_ohne_altlasten_passiert_nichts(self):
        z = {"positionen": [_position("ETC-USD_UM_XPERP-310808", "live")]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w, still=True), 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self._zeilen(), [], "idempotent: keine Zeile ohne Anlass")

    def test_neue_position_traegt_ihren_modus(self):
        """Der Massstab muss gesetzt werden, sonst raeumt der naechste Lauf zu viel."""
        quelle = (HIER.parent / "handeln.py").read_text(encoding="utf-8")
        self.assertIn('"modus": "live" if live else "papier"', quelle)
        self.assertIn("bueche_papier_altlasten_aus(z, w", quelle)


if __name__ == "__main__":
    unittest.main()