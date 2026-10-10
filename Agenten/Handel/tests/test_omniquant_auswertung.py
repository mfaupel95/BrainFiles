"""omniquant-Auswertung: EINSTIEG/eroeffnen paaren mit AUSSTIEG/schliessen.

Anlass (T-389, 11.10.2026): omniquant stand in BOT_SPUREN und fiel damit in
runden_indikator, der kauf/verkauf paart. Die Spur schreibt aber
EINSTIEG/AUSSTIEG (Papierzweig, handeln.py) und eroeffnen/schliessen
(Live-Zweig, live_perp.py) - die Auswertung meldete 0 Runden trotz 37
EINSTIEG- und 20 AUSSTIEG-Zeilen.

Dieser Test haelt beide Haelften fest:
  (a) runden_omniquant() paart beide Aktionspaare und rechnet den G/V auf
      den Einsatz (wert_usd - einsatz_usd).
  (b) buchbereinigung-Zeilen zaehlen NICHT als Runde (Buchhaltung, keine
      Handelsentscheidung).
  (c) omniquant haengt in runden_fuer() an einem eigenen Rechenweg.
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

KOPF = ("zeit,modus,aktion,inst,seite,preis,einsatz_usd,wert_usd,stop,ziel,"
        "grund,score,cr,mfe_pct,mae_pct,haltetage,pos_id")


def journal_text(*zeilen):
    return KOPF + "\n" + "\n".join(zeilen) + "\n"


class TestOmniquantRunden(unittest.TestCase):

    def _runden(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "handelsjournal.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            with open(p, encoding="utf-8", newline="") as f:
                zeilen = list(csv.DictReader(f))
            return aa.runden_omniquant(zeilen)

    def test_papier_einstieg_ausstieg(self):
        """EINSTIEG/AUSSTIEG paaren, G/V = wert_usd - einsatz_usd."""
        runden = self._runden(journal_text(
            "2026-09-13T10:57:58+00:00,papier,EINSTIEG,SOL-USDC,long,99.5,"
            "50,,94.506,110.65,prognose-treffer,,,,,",
            "2026-09-16T08:36:00+00:00,papier,AUSSTIEG,SOL-USDC,long,96.6,"
            "50,48.3,94.506,110.65,herzschlag,71.8,2.25,5.0754,-3.1256,3"))
        self.assertEqual(len(runden), 1)
        self.assertAlmostEqual(runden[0]["ergebnis"], -1.7, places=6)
        self.assertAlmostEqual(runden[0]["einsatz"], 50.0, places=6)
        self.assertEqual(runden[0]["grund"], "herzschlag")

    def test_live_eroeffnen_schliessen(self):
        """eroeffnen/schliessen paaren wie EINSTIEG/AUSSTIEG."""
        runden = self._runden(journal_text(
            "2026-10-01T22:00:00+00:00,live,eroeffnen,HBAR-USDT,long,0.10223,"
            "50.0,,0.090693,0.13101,prognose-treffer-live,,,,,,",
            "2026-10-02T10:00:00+00:00,live,schliessen,HBAR-USDT,long,0.12,"
            "50.0,58.0,0.090693,0.13101,ziel,,,,,,"))
        self.assertEqual(len(runden), 1)
        self.assertAlmostEqual(runden[0]["ergebnis"], 8.0, places=6)

    def test_buchbereinigung_zaehlt_nicht_als_runde(self):
        """schliessen mit grund=buchbereinigung ist Buchhaltung, keine Runde."""
        runden = self._runden(journal_text(
            "2026-10-05T02:51:04+00:00,live,eroeffnen,NEAR-USDC,long,4.9556,"
            "50.0,,4.2856,5.592,prognose-treffer-live,,,,,,",
            "2026-10-08T15:16:36+00:00,live,schliessen,NEAR-USDC,long,4.8014,"
            "50.0,40.37,,,buchbereinigung,,,,,,"))
        self.assertEqual(len(runden), 0)

    def test_omniquant_haengt_an_eigenem_rechenweg(self):
        """runden_fuer('omniquant') nutzt runden_omniquant, nicht indikator."""
        zeilen = [
            {"zeit": "2026-09-13T10:57:58+00:00", "modus": "papier",
             "aktion": "EINSTIEG", "inst": "SOL-USDC", "seite": "long",
             "preis": "99.5", "einsatz_usd": "50", "wert_usd": "",
             "stop": "94.506", "ziel": "110.65", "grund": "prognose-treffer"},
            {"zeit": "2026-09-16T08:36:00+00:00", "modus": "papier",
             "aktion": "AUSSTIEG", "inst": "SOL-USDC", "seite": "long",
             "preis": "96.6", "einsatz_usd": "50", "wert_usd": "48.3",
             "stop": "94.506", "ziel": "110.65", "grund": "herzschlag"},
        ]
        runden = aa.runden_fuer("omniquant", z=zeilen)
        self.assertEqual(len(runden), 1)
        self.assertAlmostEqual(runden[0]["ergebnis"], -1.7, places=6)


if __name__ == "__main__":
    unittest.main()
