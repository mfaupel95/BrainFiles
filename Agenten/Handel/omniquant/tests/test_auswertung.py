"""Tests der Omniquant-Auswertung: Bilanz aus dem Journal, ohne Behauptungen.

Kein Netz, keine echte Datei: jede Lage schreibt ihr eigenes Journal in ein
temp-Verzeichnis. Der wichtigste Fall ist der mit zu wenig Daten - die
Auswertung darf aus drei Trades keine Schwelle ableiten, und sie muss
dieselbe Kostenformel benutzen wie das Buch (sonst rechnet sie schoen).

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import csv
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HIER)

import auswertung as a                              # noqa: E402
import handeln as h                                 # noqa: E402

K = 0.0025            # Slippage 0,15 % + Gebuehr 0,10 % - Form, nicht Datei


def _journal(pfad, zeilen):
    """Ein Journal im echten Spaltenformat von handeln.py schreiben."""
    with open(pfad, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h.SPALTEN, extrasaction="ignore")
        w.writeheader()
        for z in zeilen:
            w.writerow({k: z.get(k, "") for k in h.SPALTEN})


def _zeile(einsatz, wert, seite="long", grund="ziel", score=None, cr=None,
           mfe=None, mae=None, tage=None):
    """Eine Ausstiegszeile, wie lade_ausstiege() sie liefert."""
    return {"zeit": "2026-09-13T10:00:00+00:00", "inst": "BTC-USDC",
            "seite": seite, "grund": grund,
            "einsatz": float(einsatz), "wert": float(wert),
            "netto_pct": (wert / einsatz - 1.0) * 100.0,
            "score": score, "cr": cr, "mfe_pct": mfe, "mae_pct": mae,
            "haltetage": tage}


def _roh(aktion="AUSSTIEG", einsatz="50", wert="55"):
    return {"zeit": "2026-09-13T10:00:00+00:00", "modus": "papier",
            "aktion": aktion, "inst": "BTC-USDC", "seite": "long", "preis": "100",
            "einsatz_usd": einsatz, "wert_usd": wert, "stop": "95",
            "ziel": "110", "grund": "ziel", "score": "67.5", "cr": "2.1"}


class LadeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_leeres_journal_sagt_ehrlich_dass_nichts_da_ist(self):
        self.assertEqual(a.lade_ausstiege(self.pfad), [])
        text = "\n".join(a.bericht([], K))
        self.assertIn("kein Ausstieg", text)

    def test_nur_ausstiege_werden_gelesen(self):
        _journal(self.pfad, [_roh(aktion="EINSTIEG", wert=""), _roh()])
        aus = a.lade_ausstiege(self.pfad)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["inst"], "BTC-USDC")

    def test_zeile_ohne_einsatz_faellt_raus(self):
        # Eine Zeile ohne Betrag ist keine Messung - Nullen wuerden die
        # Bilanz verzerren, eine fehlende Zeile nicht.
        _journal(self.pfad, [_roh(einsatz="")])
        self.assertEqual(a.lade_ausstiege(self.pfad), [])

    def test_alte_zeilen_ohne_score_kippen_nicht(self):
        _journal(self.pfad, [{"zeit": "2026-09-01T10:00:00+00:00",
                              "modus": "papier", "aktion": "AUSSTIEG",
                              "inst": "ETH-USDC", "seite": "long",
                              "einsatz_usd": "50", "wert_usd": "48",
                              "grund": "stop"}])
        aus = a.lade_ausstiege(self.pfad)
        self.assertEqual(len(aus), 1)
        self.assertIsNone(aus[0]["score"])
        self.assertTrue(a.bericht(aus, K))          # kein Absturz

    def test_leere_felder_werden_zu_none(self):
        self.assertIsNone(a._zahl(""))
        self.assertIsNone(a._zahl("None"))
        self.assertIsNone(a._zahl(None))
        self.assertEqual(a._zahl(" 2.5 "), 2.5)


class KennzahlenTest(unittest.TestCase):
    def test_bilanz_aus_vier_ausstiegen(self):
        aus = [_zeile(50, 55), _zeile(50, 45), _zeile(50, 60), _zeile(50, 50)]
        kz = a.kennzahlen(aus, K)
        self.assertEqual(kz["n"], 4)
        self.assertEqual(kz["einsatz"], 200.0)
        self.assertEqual(kz["wert"], 210.0)
        self.assertAlmostEqual(kz["gv_pct"], 5.0)
        # "Wert > Einsatz" ist der Treffer - 50 gegen 50 ist keiner.
        self.assertEqual(kz["treffer"], 2)
        self.assertAlmostEqual(kz["quote"], 50.0)
        self.assertAlmostEqual(kz["best"], 20.0)

    def test_brutto_ist_die_umkehrfunktion_des_buchs(self):
        # Dasselbe Papier wie handeln.py: die Netto-Rendite des Buchs
        # zurueckgerechnet muss die rohe Kursbewegung ergeben. Damit kann
        # die Auswertung "vor Kosten" ausweisen, ohne zu schaetzen - und
        # beide Seiten rechnen nachweislich dieselbe Formel.
        w = {"slippage_pct": 0.15, "gebuehr_pct": 0.1}
        p = {"seite": "long", "einstieg": 100.0, "nominal": 50.0}
        for kurs in (95.0, 100.0, 104.5):
            wert = h._ergebnis(p, kurs, w)
            netto = (wert / 50.0 - 1.0) * 100.0
            self.assertAlmostEqual(a.brutto_pct(netto, K),
                                   (kurs - 100.0) / 100.0 * 100.0, places=6)

    def test_ohne_bewegung_tragen_die_kosten_das_ganze_minus(self):
        # Netto 0 heisst nicht "kostenlos": vor Kosten stand ein Plus.
        self.assertAlmostEqual(a.brutto_pct(0.0, K), 2 * K / (1 - K) * 100.0,
                               places=6)

    def test_short_wird_richtig_herum_gerechnet(self):
        w = {"slippage_pct": 0.15, "gebuehr_pct": 0.1}
        p = {"seite": "short", "einstieg": 100.0, "nominal": 50.0}
        wert = h._ergebnis(p, 90.0, w)              # 10 % gefallen = Gewinn
        self.assertGreater(wert, 50.0)
        netto = (wert / 50.0 - 1.0) * 100.0
        self.assertAlmostEqual(a.brutto_pct(netto, K), 10.0, places=6)


class HinweisTest(unittest.TestCase):
    def test_keine_hinweise_unter_min_ausstiege(self):
        # Drei Trades sind kein Gegenbeweis gegen eine Kalibrierung an 41
        # Maerkten - die Auswertung sagt genau das.
        aus = [_zeile(50, 45, score=57.0) for _ in range(3)]
        h_ = a.hinweise(aus, K)
        self.assertTrue(any("Datenlage" in x for x in h_))
        self.assertFalse(any("pruefen (" in x for x in h_))

    def test_hinweis_wenn_ein_score_band_durchfaellt(self):
        # 8 Ausstiege: ueber der Gesamtschwelle, und das Band selbst hat
        # genug Beobachtungen (sonst waere es Rauschen).
        aus = [_zeile(50, 45, score=57.0) for _ in range(8)]
        h_ = a.hinweise(aus, K)
        self.assertTrue(any("Score 55-60" in x for x in h_))

    def test_kein_hinweis_bei_tragfaehigem_band(self):
        aus = [_zeile(50, 60, score=57.0) for _ in range(8)]
        h_ = a.hinweise(aus, K)
        self.assertTrue(any("Keine Auffaelligkeit" in x for x in h_))

    def test_stop_hinweis_erst_mit_buchgewinn_daten(self):
        # Der Stop-Hinweis braucht MFE: "lief erst ins Plus" ist die
        # Begruendung dafuer, die Stop-Breite anzusehen. Ohne die Extreme
        # gibt es keinen Stop-Hinweis (score=None -> kein Band-Hinweis).
        ohne_mfe = [_zeile(50, 45, grund="stop") for _ in range(8)]
        h_ = a.hinweise(ohne_mfe, K)
        self.assertFalse(any("Buchgewinn" in x for x in h_))
        mit_mfe = [_zeile(50, 45, grund="stop", mfe=4.0) for _ in range(8)]
        self.assertTrue(any("Buchgewinn" in x for x in a.hinweise(mit_mfe, K)))


class KernzeilenTest(unittest.TestCase):
    """kernzeile()/kernzeilen() sind die gemeinsame Quelle von GUI und
    Tagesbericht - zwei Formeln fuer dieselbe Frage waeren zwei Wahrheiten."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pfad = os.path.join(self.tmp.name, "handelsjournal.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_kernzeile_ohne_ausstiege_nennt_die_datenlage(self):
        z = a.kernzeile(self.pfad)
        self.assertIn("kein Ausstieg", z)
        self.assertIn(str(a.MIN_AUSSTIEGE), z)

    def test_kernzeile_mit_daten_zeigt_beide_kostenseiten(self):
        _journal(self.pfad, [_roh(einsatz="50", wert="55"),
                             _roh(einsatz="50", wert="45")])
        z = a.kernzeile(self.pfad, kosten=K)
        self.assertIn("2 Ausstiege", z)
        self.assertIn("nach Kosten", z)
        self.assertIn("davor", z)
        self.assertIn("Treffer 1/2", z)

    def test_kernzeilen_stimmen_mit_den_kennzahlen_ueberein(self):
        _journal(self.pfad, [_roh(einsatz="50", wert="55")])
        zeilen = a.kernzeilen(self.pfad, kosten=K)
        kz = a.kennzahlen(a.lade_ausstiege(self.pfad), K)
        self.assertIn("%+.2f" % kz["netto_pct"], zeilen[1])
        self.assertIn("%+.2f" % kz["brutto_pct"], zeilen[1])

    def test_kernzeilen_ohne_daten_bleiben_eine_lesbare_zeile(self):
        zeilen = a.kernzeilen(self.pfad)
        self.assertEqual(len(zeilen), 1)
        self.assertIn("kein Ausstieg", zeilen[0])


class BerichtTest(unittest.TestCase):
    def test_bericht_zeigt_vor_und_nach_kosten(self):
        aus = [_zeile(50, 55), _zeile(50, 45, grund="stop", mfe=1.0, mae=-6.0)]
        text = "\n".join(a.bericht(aus, K))
        self.assertIn("vor Kosten", text)
        self.assertIn("nach Kosten", text)
        self.assertIn("Treffer (Wert > Einsatz)", text)
        self.assertIn("Nach Richtung", text)
        self.assertIn("Nach Ausstiegsgrund", text)
        self.assertIn("Nach Score", text)
        self.assertIn("Nach C/R", text)
        self.assertIn("Hinweise", text)

    def test_bericht_schreibt_nichts(self):
        # Ein Bericht ist eine Lesung: keine Datei, kein Zustand, kein Netz.
        aus = [_zeile(50, 55)]
        vorher = sorted(os.listdir(HIER))
        a.bericht(aus, K)
        self.assertEqual(vorher, sorted(os.listdir(HIER)))


if __name__ == "__main__":
    unittest.main()
