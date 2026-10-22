"""Brutto oder netto? - die Auswertung darf zwei Zahlen nicht gleich nennen.

T-192 (01.10.2026): Die Papierbuecher schreiben ihre Zeilen OHNE Kosten, die
Live-Spuren (scanner/kraken im Betrag, xperp/swap ueber gebuehr_pct) rechnen
sie ein. Bis hierher stand in beiden Faellen dieselbe Zeile, und der Bericht
behauptete bei den Papierbuechern "Kosten 0.00 %" - eine Zahl, die nicht
gemessen, sondern nicht vorhanden war.

Dazu die zweite Luecke: orb und orbk fuehren ein PUNKTE-Buch. Ohne Einsatz gibt
es keinen Prozentwert; die Summe der Kursstrecken als "USD" auszugeben war eine
Behauptung. Geprueft wird deshalb, dass die Zahl dann als Punkte und in R
erscheint - und dass das Prozentzeichen wegbleibt.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import auswertung_alle                                            # noqa: E402


def _runde(einsatz, ergebnis, grund=None):
    return {"inst": "BTC-USDT", "einsatz": einsatz, "ergebnis": ergebnis,
            "kosten": 0.0, "grund": grund, "halten": 1.0,
            "zeit": "2026-10-01T00:00:00+00:00"}


def _orbk_zeilen():
    """Zwei Runden im ORB-Journal (Punktebuch, kein Einsatz)."""
    return [
        {"zeit": "2026-09-13", "inst": "ETH_USD", "richtung": "short",
         "einstieg": "2523.44", "stop": "2527.0", "ziel": "2519.495",
         "ausgang": "ziel", "ausstieg": "2519.495", "gv_punkte": "3.945",
         "gv_usd": "3.95"},
        {"zeit": "2026-09-14", "inst": "ETH_USD", "richtung": "long",
         "einstieg": "2600.0", "stop": "2590.0", "ziel": "2620.0",
         "ausgang": "stop", "ausstieg": "2590.0", "gv_punkte": "-10.0",
         "gv_usd": "-10.0"},
    ]


class KennzahlenTest(unittest.TestCase):

    def test_ohne_gebuehr_bleibt_netto_gleich_brutto(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD")
        self.assertTrue(k["brutto"])
        self.assertEqual(k["gebuehr"], 0.0)
        self.assertAlmostEqual(k["netto"], k["ergebnis"])

    def test_gebuehr_wird_ausgewiesen_und_nicht_still_abgezogen(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006)
        self.assertTrue(k["brutto"])
        self.assertAlmostEqual(k["ergebnis"], 20.0)          # brutto bleibt
        self.assertAlmostEqual(k["kosten_netto"], 12.0)      # 2 x 0,6 %
        self.assertAlmostEqual(k["netto"], 8.0)
        self.assertAlmostEqual(k["netto_pct"], 0.8)

    def test_schon_eingerechnete_gebuehr_wird_nicht_zweimal_abgezogen(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006, brutto=False)
        self.assertFalse(k["brutto"])
        self.assertAlmostEqual(k["netto"], k["ergebnis"])

    def test_ohne_einsatz_gibt_es_keinen_prozentwert(self):
        k = auswertung_alle.kennzahlen([_runde(0.0, 3.95)], "Punkte",
                                       gebuehr=0.006)
        self.assertIsNone(k["netto_pct"])
        self.assertEqual(k["pct"], 0.0)


class TextTest(unittest.TestCase):
    """Die eine Zeile, die sagt, was die Zahl bedeutet."""

    def test_netto_im_journal(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006, brutto=False)
        self.assertIn("NETTO", auswertung_alle._brutto_netto_text(k))

    def test_brutto_mit_bekannter_gebuehr_nennt_die_netto_zahl(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006)
        text = auswertung_alle._brutto_netto_text(k)
        self.assertIn("BRUTTO", text)
        self.assertIn("+8.00", text)

    def test_brutto_ohne_gebuehr_sagt_unbekannt(self):
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD")
        self.assertIn("UNBEKANNT", auswertung_alle._brutto_netto_text(k))

    def test_punktebuch_sagt_dass_die_gebuehr_nicht_abziehbar_ist(self):
        k = auswertung_alle.kennzahlen([_runde(0.0, 3.95)], "Punkte",
                                       gebuehr=0.006)
        self.assertIn("NICHT", auswertung_alle._brutto_netto_text(k))


class RTest(unittest.TestCase):
    """Ergebnis in R - die groessenunabhaengige Zahl fuer Punktebuecher."""

    def test_r_ist_gewinn_geteilt_durch_die_risikostrecke(self):
        runden = auswertung_alle.runden_orbk(_orbk_zeilen())
        self.assertEqual(len(runden), 2)
        self.assertAlmostEqual(runden[0]["risiko"], abs(2523.44 - 2527.0))
        self.assertAlmostEqual(runden[0]["r_vielfaches"],
                               3.95 / abs(2523.44 - 2527.0), places=6)
        self.assertEqual(runden[0]["einsatz"], 0.0)          # nichts erfunden

    def test_gv_punkte_springt_ein_wenn_gv_usd_fehlt(self):
        zeilen = _orbk_zeilen()
        del zeilen[0]["gv_usd"]
        runden = auswertung_alle.runden_orbk(zeilen)
        self.assertAlmostEqual(runden[0]["ergebnis"], 3.945)

    def test_ohne_risikostrecke_wird_kein_r_behauptet(self):
        zeilen = _orbk_zeilen()
        del zeilen[0]["stop"]
        runden = auswertung_alle.runden_orbk(zeilen)
        self.assertIsNone(runden[0]["r_vielfaches"])
        self.assertIsNone(auswertung_alle.r_kennzahlen(runden[:1]))

    def test_r_kennzahlen_summiert_und_zaehlt_treffer(self):
        runden = auswertung_alle.runden_orbk(_orbk_zeilen())
        r = auswertung_alle.r_kennzahlen(runden)
        self.assertEqual(r["n"], 2)
        self.assertAlmostEqual(r["summe"],
                               runden[0]["r_vielfaches"]
                               + runden[1]["r_vielfaches"])
        self.assertAlmostEqual(r["treffer_pct"], 50.0)

    def test_ohne_jede_strecke_kein_r(self):
        self.assertIsNone(auswertung_alle.r_kennzahlen([{"einsatz": 0.0}]))


class VerdrahtungTest(unittest.TestCase):
    """Wer brutto rechnet und wer netto - die Zuordnung selbst."""

    def test_orbk_ist_brutto_und_traegt_die_okx_gebuehr(self):
        self.assertIn("orbk", auswertung_alle.SPUREN)
        self.assertIn("orb", auswertung_alle.SPUREN)
        self.assertNotIn("orbk", auswertung_alle.GEBUEHR_SCHON_DRIN)
        self.assertAlmostEqual(auswertung_alle.gebuehr_fuer("orbk"), 0.0005)

    def test_scanner_und_kraken_sind_schon_netto(self):
        for spur in ("scanner", "kraken", "xperp", "swap"):
            self.assertIn(spur, auswertung_alle.GEBUEHR_SCHON_DRIN)

    def test_unbekannte_spur_hat_keine_gebuehr(self):
        self.assertEqual(auswertung_alle.gebuehr_fuer("gibtesnicht"), 0.0)

    def test_kennzahlen_fuer_setzt_das_brutto_haeckchen(self):
        alt = auswertung_alle.zeilen
        auswertung_alle.zeilen = lambda spur: _orbk_zeilen()
        try:
            k = auswertung_alle.kennzahlen_fuer("orbk")
        finally:
            auswertung_alle.zeilen = alt
        self.assertTrue(k["brutto"])
        self.assertAlmostEqual(k["gebuehr"], 0.0005)
        self.assertIsNotNone(k["r"])
        self.assertIsNone(k["netto_pct"])          # kein Einsatz, kein Prozent

    def test_orb_ist_ein_punktebuch_nicht_usd(self):
        self.assertEqual(auswertung_alle.einheit_fuer("orbk"), "Punkte")
        self.assertEqual(auswertung_alle.einheit_fuer("orb"), "Punkte")


class AnzeigeTest(unittest.TestCase):
    """/strategien und der Tagesbericht sagen dasselbe (T-192)."""

    def test_strategien_haengt_netto_an(self):
        import befehle
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006)
        self.assertIn("netto", befehle._brutto_zusatz(k))

    def test_strategien_schweigt_wenn_schon_netto(self):
        import befehle
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006, brutto=False)
        self.assertEqual(befehle._brutto_zusatz(k), "")

    def test_strategien_erkennt_das_punktebuch(self):
        import befehle
        k = auswertung_alle.kennzahlen([_runde(0.0, 3.95)], "Punkte",
                                       gebuehr=0.006)
        self.assertIn("Punkte", befehle._brutto_zusatz(k))

    def test_strategien_sagt_unbekannt_statt_null(self):
        import befehle
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD")
        self.assertIn("unbekannt", befehle._brutto_zusatz(k))

    def test_tagesbericht_zeile_nennt_brutto_und_netto(self):
        import tagesbericht
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006)
        s = {"buchlage": "belastbar", "kennzahlen": k, "waehrung": "USD"}
        zeile = tagesbericht.rundenzeile(s)
        self.assertIn("7 Tage", zeile)
        self.assertIn("brutto", zeile)
        self.assertIn("+8.00", zeile)

    def test_tagesbericht_zeile_bleibt_ohne_zusatz_bei_netto(self):
        import tagesbericht
        k = auswertung_alle.kennzahlen([_runde(1000.0, 20.0)], "USD",
                                       gebuehr=0.006, brutto=False)
        s = {"buchlage": "belastbar", "kennzahlen": k, "waehrung": "USD"}
        self.assertNotIn("brutto", tagesbericht.rundenzeile(s))


if __name__ == "__main__":
    unittest.main()
