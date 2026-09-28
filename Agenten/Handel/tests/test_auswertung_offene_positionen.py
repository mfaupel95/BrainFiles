"""Die Zeile "keine geschlossene Runde" darf nicht wie "tote Spur" klingen.

BEFUND 29.09.2026 (Max: "viele haben 0 runden, da stimmt doch etwas nicht"):
Die Auswertung sagte fuer jede Spur ohne HANDELSRUNDE denselben Satz - auch
fuer Spuren, die vier Positionen im Buch stehen hatten (macd_mtf, supertrend),
und fuer Spuren, deren Journal nur AUSBUCHUNGEN enthielt (nautilus_kraken, vier
buchbereinigung-Zeilen). Drei verschiedene Lagen, ein Text. Jetzt nennt die
Zeile die offenen Positionen und die Ausstiege ohne Handelsentscheidung.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)
if os.path.join(HANDEL, "scanner") not in sys.path:
    sys.path.insert(0, os.path.join(HANDEL, "scanner"))

import auswertung_alle as a  # noqa: E402


class OffenePositionenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = a.HIER
        a.HIER = a.HIER.__class__(self.tmp.name)      # Path erwartet
        self.spur = "bsp"

    def tearDown(self):
        a.HIER = self.alt
        self.tmp.cleanup()

    def _zustand(self, inhalt):
        p = os.path.join(self.tmp.name, self.spur, "zustand.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(inhalt)

    def test_positionen_werden_gezaehlt(self):
        self._zustand(json.dumps({"positionen": [{"inst": "ETH-USDC"},
                                                 {"inst": "BTC-USDC"}]}))
        self.assertEqual(a.offene_positionen(self.spur), 2)

    def test_leeres_buch_ist_null(self):
        self._zustand(json.dumps({"positionen": []}))
        self.assertEqual(a.offene_positionen(self.spur), 0)

    def test_fehlende_datei_ist_unbekannt(self):
        self.assertIsNone(a.offene_positionen(self.spur))

    def test_kaputtes_json_ist_unbekannt(self):
        self._zustand("{kaputt")
        self.assertIsNone(a.offene_positionen(self.spur))

    def test_kein_positionen_feld_ist_unbekannt(self):
        self._zustand(json.dumps({"letzter_lauf": "2026-09-29T00:00:00"}))
        self.assertIsNone(a.offene_positionen(self.spur))


class AnzeigeTest(unittest.TestCase):
    """zeige() muss die drei Lagen unterscheiden - Text, nicht Zustand."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (a.HIER, a.offene_positionen, a.runden_fuer)
        a.HIER = a.HIER.__class__(self.tmp.name)

    def tearDown(self):
        (a.HIER, a.offene_positionen, a.runden_fuer) = self.alt
        self.tmp.cleanup()

    def _text(self, spur, offen, runden=()):
        a.offene_positionen = lambda s: offen
        a.runden_fuer = lambda s: list(runden)
        buf = io.StringIO()
        with redirect_stdout(buf):
            a.zeige(spur, None)
        return buf.getvalue()

    def test_offene_position_wird_genannt(self):
        t = self._text("macd_mtf", 4)
        self.assertIn("keine geschlossenen Runden", t)
        self.assertIn("4 offene Position(en)", t)

    def test_leeres_buch_wartet_auf_das_erste_signal(self):
        t = self._text("iv_waelle", 0)
        self.assertIn("wartet auf ihr erstes Signal", t)

    def test_ausbuecher_werden_getrennt_genannt(self):
        t = self._text("nautilus_kraken", 0, [{"grund": "buchbereinigung"},
                                              {"grund": "buchbereinigung"}])
        self.assertIn("2 Ausstiege ohne Handelsentscheidung", t)

    def test_echte_runde_kommt_nicht_in_den_zweig(self):
        # Gegenprobe: mit Kennzahlen laeuft die normale Ausgabe, die Zeile
        # "keine geschlossenen Runden" darf dann NICHT erscheinen.
        t = self._text("scanner", 3, [{"grund": "ziel"}])
        # Die Kennzahlen kommen aus dem ECHTEN Erzeuger, nicht von Hand gebaut -
        # ein nachgebautes dict prueft die Anzeige gegen meine Annahme statt
        # gegen kennzahlen().
        k = a.kennzahlen([{"ergebnis": 1.0, "einsatz": 10.0, "grund": "ziel"}],
                         "USD")
        self.assertIsNotNone(k)
        buf = io.StringIO()
        with redirect_stdout(buf):
            a.zeige("scanner", k)
        aus = buf.getvalue()
        self.assertNotIn("keine geschlossenen Runden", aus)
        self.assertIn("geschlossene Runden", aus)


if __name__ == "__main__":
    unittest.main(verbosity=2)