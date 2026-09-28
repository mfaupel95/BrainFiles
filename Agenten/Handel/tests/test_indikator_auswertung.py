"""Die Auswertung der vier Indikator-Spuren rechnet auf dem Nominalwert.

Anlass: Bis zum 15.09.2026 schrieben squeeze, wavetrend, macd_mtf und
supertrend den Erloes als `nominal + (kurs - einstieg)` in ihr Journal - die
rohe Kursdifferenz statt des Anteils am Nominalwert. Bei BTC ist das ein
Faktor von rund 70.000: eine Runde mit 100 USD Nominal und 3 % Gewinn stand
als "Erloes 3000 USD" im Journal. Aufgefallen ist es beim Bau dieser
Auswertung, nicht im Betrieb - die Spuren sind jung und hatten bis dahin keine
Auswertung.

Dieser Test haelt beide Haelften fest:
  (a) runden_indikator() rechnet den G/V auf den Einsatz, nicht auf den Kurs.
  (b) Die vier Spuren haengen wirklich in auswertung_alle.SPUREN und werden
      von kennzahlen_fuer() bedient - nicht nur im Modul, sondern im Aufruf.
"""
import csv
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import auswertung_alle as aa  # noqa: E402

KOPF = ("zeit,modus,aktion,inst,seite,preis,einsatz_usd,stop,ziel,stop_pct,"
        "grund")


def journal_text(*zeilen):
    return KOPF + "\n" + "\n".join(zeilen) + "\n"


class TestIndikatorRunden(unittest.TestCase):

    def _runden(self, text):
        """Journal schreiben, einlesen, Runden bauen - wie main() es tut."""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "handelsjournal.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            with open(p, encoding="utf-8", newline="") as f:
                zeilen = list(csv.DictReader(f))
            return aa.runden_indikator(zeilen)

    def test_gewinn_rechnet_auf_den_einsatz_nicht_auf_den_kurs(self):
        """3 % Kursgewinn bei 100 USD Einsatz sind +3 USD, nicht +3000."""
        runden = self._runden(journal_text(
            "2026-09-15T10:00:00+00:00,papier,kauf,BTC-USDT,long,100000.00,"
            "100.00,95000.00,110000.00,5.00,wavetrend",
            "2026-09-15T12:00:00+00:00,papier,verkauf,BTC-USDT,long,103000.00,"
            "103.00,95000.00,110000.00,5.00,ziel"))
        self.assertEqual(len(runden), 1)
        self.assertAlmostEqual(runden[0]["ergebnis"], 3.0, places=6)
        self.assertAlmostEqual(runden[0]["einsatz"], 100.0, places=6)

    def test_verlust_bei_short(self):
        """Short: fallender Kurs ist Gewinn, steigender Verlust."""
        runden = self._runden(journal_text(
            "2026-09-15T10:00:00+00:00,papier,kauf,SOL-USDT,short,100.00,"
            "100.00,105.00,90.00,5.00,wavetrend",
            "2026-09-15T12:00:00+00:00,papier,verkauf,SOL-USDT,short,105.00,"
            "95.00,105.00,90.00,5.00,stop"))
        self.assertAlmostEqual(runden[0]["ergebnis"], -5.0, places=6)

    def test_alter_fehler_haette_den_kurs_gezahlt(self):
        """Gegenprobe: die alte Formel ergaebe hier 3000 statt 3 USD."""
        runden = self._runden(journal_text(
            "2026-09-15T10:00:00+00:00,papier,kauf,BTC-USDT,long,100000.00,"
            "100.00,95000.00,110000.00,5.00,wavetrend",
            "2026-09-15T12:00:00+00:00,papier,verkauf,BTC-USDT,long,103000.00,"
            "103.00,95000.00,110000.00,5.00,ziel"))
        alt = (103000.00 - 100000.00)      # rohe Kursdifferenz
        self.assertGreater(alt, 1000.0)
        self.assertNotAlmostEqual(runden[0]["ergebnis"], alt, places=1)

    def test_offene_position_ergibt_keine_runde(self):
        """Ein Kauf ohne Verkauf ist keine geschlossene Runde."""
        runden = self._runden(journal_text(
            "2026-09-15T10:00:00+00:00,papier,kauf,BTC-USDT,long,100000.00,"
            "100.00,95000.00,110000.00,5.00,wavetrend"))
        self.assertEqual(runden, [])

    def test_alle_vier_spuren_sind_angeschlossen(self):
        """Die Zuordnung Spur -> Rechenweg ist der eigentliche Anschluss - eine
        Spur in SPUREN ohne eigenen Zweig faellt in den leeren else-Zweig.

        Sie steht seit dem 29.09.2026 in `runden_fuer()` (vorher in
        `kennzahlen_fuer`, das sie jetzt aufruft). Der Test prueft deshalb die
        REGEL und nicht eine Quelltextzeile der einen Funktion: sonst meldet er
        die Verlagerung als Fehler, ohne dass sich am Verhalten etwas geaendert
        hat (Befund 29.09.2026).
        """
        import inspect
        for spur in ("squeeze", "wavetrend", "macd_mtf", "supertrend"):
            self.assertIn(spur, aa.SPUREN)
            self.assertIn(spur, aa.INDIKATOR_SPUREN)
        self.assertIn("INDIKATOR_SPUREN", inspect.getsource(aa.runden_fuer))
        self.assertIn("runden_fuer(spur", inspect.getsource(aa.kennzahlen_fuer))


if __name__ == "__main__":
    unittest.main()
