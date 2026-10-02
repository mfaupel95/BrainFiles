"""MFE/MAE: Buchgewinn und Buchverlust je Position werden fortgeschrieben.

Ohne diese zwei Zahlen laesst sich aus dem Journal nicht trennen, ob ein Stop
zu eng war (die Position lief erst ins Plus und drehte dann) oder ob das
Signal falsch war (sie lief sofort gegen den Einstieg). Gemessen wird an den
Zykluspunkten - die Zahl ist eine Untergrenze, kein echtes Extrem.

Kein Test hier erreicht das Netz oder den Orderpfad: okx wird je Testfall
durch eine Attrappe ersetzt, Journal und Zustand liegen im Temp-Ordner.
"""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                          # noqa: E402


class OkxAttrappe:
    """Nur was die Ausstiegs-/Einstiegspfade lesen. Kein Orderweg.

    markt_kauf/markt_verkauf/stop_setzen werfen bewusst: ein Test, der sie
    erreicht, soll laut scheitern und nicht still eine Order bauen.
    """

    def __init__(self, kurse):
        self.kurse = kurse

    def letzter_kurs(self, inst):
        return self.kurse[inst]

    def _nie(self, *a, **k):                                  # noqa: D401
        raise AssertionError("Orderpfad im Test erreicht")

    markt_kauf = markt_verkauf = stop_setzen = _nie
    stop_stornieren = order_details = stop_details = _nie


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal_vorher = h.JOURNAL
        self.zustand_vorher = h.ZUSTAND
        self.okx_vorher = h.okx
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        h.ZUSTAND = Path(self.tmp.name) / "zustand.json"
        # Auch das Ablehnungsprotokoll: pruefe_einstiege schreibt es mit,
        # und ein Test darf in keinen echten Zielpfad schreiben.
        self.abl_vorher = h.ABLEHNUNGEN
        h.ABLEHNUNGEN = Path(self.tmp.name) / "ablehnungen.csv"

    def tearDown(self):
        h.JOURNAL = self.journal_vorher
        h.ZUSTAND = self.zustand_vorher
        h.ABLEHNUNGEN = self.abl_vorher
        h.okx = self.okx_vorher
        self.tmp.cleanup()

    def zeilen(self):
        with h.JOURNAL.open(encoding="utf-8", newline="") as f:
            return list(csv.reader(f))


class MerkeExtremTest(Basis):
    def test_extreme_werden_fortgeschrieben(self):
        """MFE steigt nie zurueck, MAE faellt nie zurueck."""
        p = {"einstieg": 100.0, "mfe_pct": 0.0, "mae_pct": 0.0}
        for kurs in (105.0, 112.0, 96.0, 101.0, 88.0, 99.0):
            h._merke_extrem(p, kurs)
        self.assertAlmostEqual(p["mfe_pct"], 12.0, places=6)
        self.assertAlmostEqual(p["mae_pct"], -12.0, places=6)

    def test_ein_gewinner_hat_keinen_positiven_mae(self):
        """Eine Position, die nur steigt, behaelt MAE 0 - nicht None."""
        p = {"einstieg": 50.0, "mfe_pct": 0.0, "mae_pct": 0.0}
        for kurs in (51.0, 55.0, 60.0):
            h._merke_extrem(p, kurs)
        self.assertAlmostEqual(p["mfe_pct"], 20.0, places=6)
        self.assertEqual(p["mae_pct"], 0.0)

    def test_altbestand_ohne_felder_laeuft_durch(self):
        """Position aus der Zeit vor dieser Spalte: kein KeyError."""
        p = {"inst": "LTC-USDC", "einstieg": 54.22}       # wie in zustand.json
        h._merke_extrem(p, 57.0)
        self.assertGreater(p["mfe_pct"], 0.0)
        self.assertEqual(p["mae_pct"], 0.0)


class HaltetageTest(Basis):
    def test_fehlendes_feld_gibt_leer_statt_null(self):
        """Ohne eroeffnet wird nichts geraten - die Spalte bleibt leer."""
        self.assertEqual(h._haltetage({}), "")
        self.assertEqual(h._haltetage({"eroeffnet": None}), "")
        self.assertEqual(h._haltetage({"eroeffnet": "kaputt"}), "")

    def test_zaehlt_kalendertage(self):
        self.assertEqual(h._haltetage({"eroeffnet": h._heute()}), 0)


class JournalSpaltenTest(Basis):
    """Jede geschriebene Zeile hat 14 Spalten - sonst legt DictReader die
    neuen Werte unter None ab und jede Auswertung wird still falsch.

    Die Spalten sind (in Reihenfolge):
    zeit, modus, aktion, inst, preis, usd, stop, ziel, grund,
    mfe_pct, mae_pct, haltetage, herkunft, pos_id

    Die vierzehnte ist `pos_id` (T-095): die Kennung, mit der die Auswertung
    Einstieg und Ausstieg paart. Sie steht am ENDE, damit ein Altjournal ohne
    die Spalte seine Werte behaelt. `herkunft` (trigger vs zyklus) steht davor.
    """

    KOPF = ["zeit", "modus", "aktion", "inst", "preis", "usd",
            "stop", "ziel", "grund", "mfe_pct", "mae_pct", "haltetage",
            "herkunft", "pos_id"]

    def test_kopfzeile_hat_vierzehn_spalten(self):
        h.journal(*([""] * 14))
        self.assertEqual(self.zeilen()[0], self.KOPF)

    def test_ausstiegszeile_traegt_mfe_und_mae(self):
        h.okx = OkxAttrappe({"LTC-USDC": 61.0})
        z = {"positionen": [{"inst": "LTC-USDC", "einstieg": 54.22,
                             "usd": 100.0, "stop": 51.07, "ziel": 60.5,
                             "eroeffnet": h._heute(),
                             "mfe_pct": 3.0, "mae_pct": -1.5}],
              "letzte_stops": {}}
        h.pruefe_ausstiege(z, False)

        self.assertEqual(z["positionen"], [])
        zeilen = self.zeilen()
        self.assertEqual(zeilen[0], self.KOPF)
        zeile = zeilen[1]
        self.assertEqual(len(zeile), 14)
        self.assertEqual(zeile[2], "verkauf")
        self.assertEqual(zeile[8], "ziel")
        # Der Kurs 61.0 liegt ueber dem bisherigen MFE -> fortgeschrieben.
        self.assertAlmostEqual(float(zeile[9]), 12.5046, places=3)
        self.assertAlmostEqual(float(zeile[10]), -1.5, places=3)
        self.assertEqual(zeile[11], "0")
        # herkunft = "zyklus" (Standard im 15-Minuten-Zyklus)
        self.assertEqual(zeile[12], "zyklus")
        # Die Kennung der Position steht in der Ausstiegszeile (Stufe 1 der
        # Paarung) - hier leer, weil die Position von Hand gebaut wurde.
        self.assertEqual(zeile[13], "")

    def test_ausstieg_eines_altbestands_bricht_nicht(self):
        """Position ohne die neuen Felder: Zeile entsteht trotzdem, 14 Spalten."""
        h.okx = OkxAttrappe({"TRX-USDC": 0.30})
        z = {"positionen": [{"inst": "TRX-USDC", "einstieg": 0.34017,
                             "usd": 100.0, "stop": 0.323161, "ziel": 0.374188,
                             "eroeffnet": "2026-09-10"}],
              "letzte_stops": {}}
        h.pruefe_ausstiege(z, False)

        zeile = self.zeilen()[1]
        self.assertEqual(len(zeile), 14)
        self.assertEqual(zeile[8], "stop")
        self.assertEqual(float(zeile[9]), 0.0)          # nie im Plus gewesen
        self.assertLess(float(zeile[10]), 0.0)
        self.assertEqual(zeile[12], "zyklus")
        self.assertEqual(z["letzte_stops"]["TRX-USDC"], h._heute())

    def test_kaufzeile_traegt_die_kennung(self):
        h.okx = OkxAttrappe({"BTC-USDC": 78000.0})
        z = {"positionen": [], "letzte_stops": {}}
        w = {"max_offene_positionen": 6, "max_gesamt_usd": 400,
             "max_pro_trade_usd": 100, "abklingzeit_tage": 4}
        v = [{"inst": "BTC-USDC", "score": 70.0, "einstieg": 78000.0,
              "stop": 74000.0, "stop_pct": 5.1, "ziel": 86000.0, "usd": 100}]
        h.pruefe_einstiege(z, v, w, False)

        zeile = self.zeilen()[1]
        self.assertEqual(len(zeile), 14)
        self.assertEqual(zeile[2], "kauf")
        self.assertEqual(zeile[9:13], ["", "", "", "zyklus"])      # mfe/mae/haltetage/herkunft
        # Die Kaufzeile traegt die Kennung der Position - die Ausstiegszeile
        # uebernimmt sie (Stufe 1 der Paarung).
        self.assertEqual(zeile[13], z["positionen"][0]["pos_id"])
        self.assertTrue(zeile[13])

    def test_neue_position_traegt_die_felder(self):
        h.okx = OkxAttrappe({"BTC-USDC": 78000.0})
        z = {"positionen": [], "letzte_stops": {}}
        w = {"max_offene_positionen": 6, "max_gesamt_usd": 400,
             "max_pro_trade_usd": 100, "abklingzeit_tage": 4}
        v = [{"inst": "BTC-USDC", "score": 70.0, "einstieg": 78000.0,
              "stop": 74000.0, "stop_pct": 5.1, "ziel": 86000.0, "usd": 100}]
        h.pruefe_einstiege(z, v, w, False)

        p = z["positionen"][0]
        self.assertEqual(p["mfe_pct"], 0.0)
        self.assertEqual(p["mae_pct"], 0.0)


class FlachStellenTest(Basis):
    def test_notausstieg_schreibt_ebenfalls_vierzehn_spalten(self):
        """Der Notausstieg (Kill-Switch, Herzschlag) ist der zweite Schreiber."""
        h.okx = OkxAttrappe({"DOT-USDC": 1.10})
        z = {"positionen": [{"inst": "DOT-USDC", "einstieg": 1.0466,
                             "usd": 100.0, "stop": 0.972291, "ziel": 1.195218,
                             "eroeffnet": h._heute()}],
              "letzte_stops": {}}
        h.flach_stellen(z, False, "herzschlag_alt")

        zeile = self.zeilen()[1]
        self.assertEqual(len(zeile), 14)
        self.assertEqual(zeile[8], "herzschlag_alt")
        self.assertGreater(float(zeile[9]), 0.0)
        self.assertEqual(zeile[12], "zyklus")
        self.assertEqual(z["positionen"], [])


class SchreibschutzTest(unittest.TestCase):
    """Kein Test darf das echte Buch beruehren."""

    def test_echte_pfade_unveraendert(self):
        self.assertTrue(str(h.JOURNAL).endswith("handelsjournal.csv"))
        self.assertIn("scanner", str(h.JOURNAL))


if __name__ == "__main__":
    unittest.main()
