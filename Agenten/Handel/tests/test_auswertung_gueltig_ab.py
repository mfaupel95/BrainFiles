"""Auswertung: Scanner-Runden mit Einstieg vor dem Preisfix zaehlen nicht.

Der Scanner nahm bis 03.10.2026 den Preis des Vortagesberichts als Einstieg
(scanner/BEFUND-einstiegspreis-20261003.md). Die Runden davor messen den
Rechenfehler. Geschnitten wird am EINSTIEG: eine Runde, die vor dem Fix
einstieg und danach ausstieg, traegt den falschen Einstiegspreis im Ergebnis.

Erfundene Journale in einem Temp-Ordner, wie test_auswertung_fenster.py.
"""

import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import auswertung_alle as aa                                   # noqa: E402

KOPF = "zeit,modus,aktion,inst,usd,grund,pos_id\n"

# A: komplett vor dem Fix (Scheingewinn)      B: Einstieg VOR, Ausstieg NACH dem Fix
# C: komplett nach dem Fix, Verlust            D: Einstieg ohne lesbare Zeit
JOURNAL = KOPF + (
    "2026-09-19T02:50:00+00:00,papier,kauf,AAA-USDC,100,score 70,pa\n"
    "2026-09-19T03:05:00+00:00,papier,verkauf,AAA-USDC,115,ziel,pa\n"
    "2026-10-02T20:00:00+00:00,papier,kauf,BBB-USDC,100,score 70,pb\n"
    "2026-10-04T10:00:00+00:00,papier,verkauf,BBB-USDC,130,ziel,pb\n"
    "2026-10-03T08:00:00+00:00,papier,kauf,CCC-USDC,100,score 70,pc\n"
    "2026-10-04T08:00:00+00:00,papier,verkauf,CCC-USDC,94,stop,pc\n"
    "unlesbar,papier,kauf,DDD-USDC,100,score 70,pd\n"
    "2026-10-04T09:00:00+00:00,papier,verkauf,DDD-USDC,120,ziel,pd\n"
)


class GueltigAbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        (wurzel / "scanner").mkdir()
        (wurzel / "scanner" / "handelsjournal.csv").write_text(
            JOURNAL, encoding="utf-8")
        (wurzel / "squeeze").mkdir()
        (wurzel / "squeeze" / "handelsjournal.csv").write_text(
            "zeit,aktion,inst,einsatz_usd,grund\n"
            "2026-08-01T10:00:00+00:00,kauf,BTC,100,einstieg\n"
            "2026-08-02T10:00:00+00:00,verkauf,BTC,110,ziel\n", encoding="utf-8")
        self._alt = aa.HIER
        aa.HIER = wurzel

    def tearDown(self):
        aa.HIER = self._alt
        self.tmp.cleanup()

    def test_nur_die_runde_nach_dem_fix_zaehlt(self):
        k = aa.kennzahlen_fuer("scanner")
        self.assertEqual(k["n"], 1)
        self.assertEqual(k["treffer"], 0)
        self.assertLess(k["ergebnis"], 0)

    def test_einstieg_vor_dem_fix_zaehlt_auch_bei_ausstieg_danach(self):
        # B steigt nach dem Fix aus (+30), zaehlt aber nicht.
        k = aa.kennzahlen_fuer("scanner")
        # Uebrig ist nur C (-6). Zaehlte B (+30) mit, laege die Summe bei +24.
        self.assertAlmostEqual(k["ergebnis"], -6.0, delta=0.5)
        self.assertEqual(k["paarung"]["vor_fix"], 3)      # A, B, D

    def test_unlesbare_einstiegszeit_gilt_als_nicht_belegt(self):
        k = aa.kennzahlen_fuer("scanner")
        self.assertEqual(k["paarung"]["vor_fix"], 3)

    def test_ausgewiesen_nicht_verschwiegen(self):
        k = aa.kennzahlen_fuer("scanner")
        self.assertAlmostEqual(k["paarung"]["vor_fix_ergebnis"], 15 + 30 + 20)
        self.assertIn("NICHT mitgezaehlt", aa.paarung_text(k["paarung"]))

    def test_alles_schaltet_den_filter_ab(self):
        k = aa.kennzahlen_fuer("scanner", nur_gueltige=False)
        self.assertEqual(k["n"], 4)
        self.assertNotIn("vor_fix", k["paarung"])

    def test_andere_spuren_bleiben_unberuehrt(self):
        k = aa.kennzahlen_fuer("squeeze")
        self.assertEqual(k["n"], 1)
        self.assertNotIn("vor_fix", k["paarung"])

    def test_nach_dem_fix_ohne_runden_ist_kein_absturz(self):
        # Nur Altrunden im Journal: kein Absturz, sondern keine Kennzahl.
        pfad = Path(self.tmp.name) / "scanner" / "handelsjournal.csv"
        pfad.write_text(KOPF + (
            "2026-09-19T02:50:00+00:00,papier,kauf,AAA-USDC,100,x,pa\n"
            "2026-09-19T03:05:00+00:00,papier,verkauf,AAA-USDC,115,ziel,pa\n"),
            encoding="utf-8")
        self.assertIsNone(aa.kennzahlen_fuer("scanner"))


if __name__ == "__main__":
    unittest.main()
