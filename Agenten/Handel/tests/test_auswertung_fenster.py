"""Tests fuer das Zeitfenster in der Spurenauswertung.

Zwei Dinge, die still schiefgehen: ein Aufruf OHNE Fenster muss dieselbe
Zahl liefern wie vor dem Umbau (sonst aendert der Umbau die Buecher), und
MIN_RUNDEN muss JE FENSTER greifen (sonst behauptet ein Monat mit drei
Runden eine Trefferquote).

Gearbeitet wird auf erfundenen Journalen in einem Temp-Ordner.
"""

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import auswertung_alle as aa                                   # noqa: E402

# Das Format, das runden_indikator ueber _paare wirklich liest: die Spalte
# `inst` gruppiert die Runden, und `einsatz_usd` traegt beim Kauf den Einsatz
# und beim Verkauf den Erloes - derselbe Feldname, zwei Bedeutungen
# (auswertung_alle.py:285 und :223). Ohne `inst` baut _paare keine Runde.
KOPF = "zeit,aktion,inst,einsatz_usd,grund\n"

# Eine Runde im August (+10), eine im September (-10).
JOURNAL = KOPF + (
    "2026-08-01T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-08-02T10:00:00+00:00,verkauf,BTC,110,ziel\n"
    "2026-09-10T10:00:00+00:00,kauf,BTC,100,einstieg\n"
    "2026-09-11T10:00:00+00:00,verkauf,BTC,90,stop\n"
)


class TestFensterInZeilen(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "squeeze").mkdir()
        (wurzel / "squeeze" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_ohne_fenster_alle_zeilen(self):
        self.assertEqual(len(aa.zeilen("squeeze")), 4)

    def test_fenster_schneidet(self):
        von = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        self.assertEqual(len(aa.zeilen("squeeze", von=von, bis=None)), 2)

    def test_fenster_ohne_treffer_ist_leer_nicht_fehler(self):
        von = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        self.assertEqual(aa.zeilen("squeeze", von=von, bis=None), [])

    def test_kennzahlen_ohne_zeilen_sind_none(self):
        von = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        self.assertIsNone(aa.kennzahlen_fuer("squeeze", von=von, bis=None))


class TestMinRundenJeFenster(unittest.TestCase):

    def test_wenige_runden_gelten_als_nicht_belastbar(self):
        # Zwei Runden liegen unter MIN_RUNDEN. Die Kennzahlen duerfen
        # entstehen, aber die Belastbarkeit muss falsch sein.
        k = aa.kennzahlen([{"ergebnis": 10.0, "einsatz": 100.0, "grund": "ziel"},
                           {"ergebnis": -10.0, "einsatz": 100.0, "grund": "stop"}], "USD")
        self.assertFalse(aa.belastbar(k))

    def test_genug_runden_sind_belastbar(self):
        runden = [{"ergebnis": 1.0, "einsatz": 100.0, "grund": "ziel"}] * aa.MIN_RUNDEN
        self.assertTrue(aa.belastbar(aa.kennzahlen(runden, "USD")))

    def test_keine_kennzahlen_sind_nicht_belastbar(self):
        self.assertFalse(aa.belastbar(None))


if __name__ == "__main__":
    unittest.main()
