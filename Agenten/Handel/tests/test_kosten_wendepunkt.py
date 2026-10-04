"""Das Urteil des Kosten-Wendepunkts - Einheiten und Grenzen, ohne Netz.

Anlass: Bis zum 30.09.2026 druckte `kosten_wendepunkt.py` den Bruch
`gebuehr_taker` unveraendert mit Prozentzeichen (0.0005 -> "0.001 %" statt
"0.050 %") und verglich ihn direkt mit `f_max`, das in Prozent JE RUNDE steht.
Damit war jede Gebuehrenaussage um Faktor 100 zu klein und der Vergleich
bedeutungslos - sichtbar wurde das erst, als fuenf Spuren ueberhaupt erst ein
Gebuehrenfeld bekamen.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import kosten_wendepunkt                                        # noqa: E402


class EinheitenTest(unittest.TestCase):
    """Der Bruch wird in Prozent umgerechnet - je Seite UND je Runde."""

    def test_kraken_gebuehr_wird_als_prozent_gedruckt(self):
        t = kosten_wendepunkt.urteil(0.006, 0.03)
        self.assertIn("0.600 % je Seite", t)
        self.assertIn("1.200 % je Runde", t)

    def test_der_alte_fehler_kommt_nicht_zurueck(self):
        # Gegenprobe: die rohe Zahl mit Prozentzeichen war die Fehlanzeige.
        t = kosten_wendepunkt.urteil(0.0005, 0.07)
        self.assertNotIn("0.001 %", t)
        self.assertIn("0.050 % je Seite", t)
        self.assertIn("0.100 % je Runde", t)

    def test_runde_zaehlt_beide_seiten(self):
        # Eine Runde ist Kauf UND Verkauf: die Grenze muss gegen den doppelten
        # Satz geprueft werden, nicht gegen eine Seite.
        self.assertIn("liegt darueber", kosten_wendepunkt.urteil(0.0005, 0.09))
        self.assertNotIn("liegt darueber", kosten_wendepunkt.urteil(0.0005, 0.11))


class GrenzenTest(unittest.TestCase):
    """Der Hinweis haengt an f_max, nicht an der Tagesform."""

    def test_ohne_gebuehrfeld_kein_gebuehrenhinweis(self):
        for geb in (None, 0, 0.0):
            t = kosten_wendepunkt.urteil(geb, 0.03)
            self.assertIn("haengt an der Gebuehrfreiheit", t)
            self.assertNotIn("gesetzte Gebuehr", t)

    def test_tote_spur_wird_deutlicher_benannt(self):
        t = kosten_wendepunkt.urteil(0.006, -0.09)
        self.assertIn("schon bei 0 % Gebuehr nicht tragfaehig", t)

    def test_gesunde_spur_bleibt_ohne_gebuehrenhinweis(self):
        # Der Scanner liegt bei +9,81 % je Runde - 0,1 % Gebuehr kippen ihn nicht.
        t = kosten_wendepunkt.urteil(0.0005, 9.81)
        self.assertEqual("", t)

    def test_schwelle_0_4_prozent_bleibt_erhalten(self):
        self.assertIn("unter 0,4 %", kosten_wendepunkt.urteil(0.0005, 0.39))
        self.assertNotIn("Gebuehrfreiheit", kosten_wendepunkt.urteil(0.0005, 0.41))


class FelderTest(unittest.TestCase):
    """Jede Spur, die live ordern kann, muss ihr Gebuehrenfeld tragen.

    Geprueft wird die REGEL, nicht ein eingefrorener Wert: der Markt der Spur
    bestimmt den Satz. Am 01.10.2026 wurde er gemessen (eigenes OKX-/Kraken-
    Konto, je Seite) - ein Test mit festen Zahlen war danach rot, obwohl der
    Code stimmte (er froze den alten, zu freundlichen Satz von 0,05 % fuer
    OKX-SPOT ein).
    """

    # Markt je Kernspur - daraus folgt der Satz.
    MAERKTE = {
        "scanner": "okx_spot",            # BTC-/...-USDC auf dem OKX-Spot
        "iv_wand": "okx_spot",            # OKX-Optionszone, Spot-Ausfuehrung
        "orb": "okx_perp",                # BTC-USDT-SWAP
        "orbk": "kraken_spot",            # ETHUSD
        "moondev_signalwelle": "okx_perp",
        "liq_wand": "okx_perp",
        "xperp": "okx_perp",
        "swap": "okx_perp",
        "kraken": "kraken_spot",
        # 04.10.2026: mosaic wurde am 30.09.2026 (Commit e6f2715c, Auftrag Max
        # "nur noch omnitrade auf kraken handel erlaubt") von Kraken auf OKX
        # umgestellt - `boersen: ["okx"]`, Instrumente BTC/ETH/SOL-USDC, also
        # OKX SPOT (0,10 %/Seite, gemessen 01.10.2026). Die Zuordnung hier stand
        # noch auf kraken_spot und verlangte 0,6 % von einer OKX-Runde.
        "mosaic": "okx_spot",
    }
    SAETZE = {"okx_spot": 0.001, "okx_perp": 0.0005, "kraken_spot": 0.006}

    def test_kernspuren_haben_ein_gebuehrenfeld(self):
        import json
        from pathlib import Path
        for spur, markt in self.MAERKTE.items():
            p = Path(HANDEL) / spur / "wachen.json"
            if not p.is_file():
                self.skipTest("Spur %s fehlt" % spur)
            w = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(self.SAETZE[markt], w.get("gebuehr_taker"),
                             "%s (%s): Gebuehrenfeld fehlt oder hat den falschen Wert"
                             % (spur, markt))
            # Belegt heisst: EINE Notiz zur Gebuehr steht dabei. Der Name darf
            # verschieden sein - aeltere Wachen fuehren `_gebuehren` bzw.
            # `_gebuehren_abo_widerlegt`, neue `_gebuehr_quelle`.
            notizen = [k for k in w if k.startswith("_gebuehr")]
            self.assertTrue(notizen, "%s: Gebuehr ohne Quelle ist nicht nachpruefbar" % spur)

    def test_gebuehr_ist_ein_bruch_kein_prozentwert(self):
        # Ein Wert ueber 0,05 waere ein Prozentwert (5 %) und damit ein
        # Einheitenfehler - genau die Verwechslung, die hier passiert war.
        import json
        from pathlib import Path
        for p in sorted(Path(HANDEL).glob("*/wachen.json")):
            w = json.loads(p.read_text(encoding="utf-8"))
            if "gebuehr_taker" in w:
                self.assertLessEqual(w["gebuehr_taker"], 0.05,
                                     "%s: gebuehr_taker sieht wie Prozent aus" % p.parent.name)


class RichtungTest(unittest.TestCase):
    """Ein Short, der im Ziel schliesst, ist ein GEWINN - nicht ein Verlust.

    Anlass: bis zum 30.09.2026 rechnete `_paarung_form_b` das Ergebnis als
    `preis/einstieg - 1` ohne Richtung. Fuer eine gemischt handelnde Spur
    (wavetrend, 2021-2026) ergab das die Summe +679 statt -513, und `f_max`,
    die Trefferquote und jede Summe darauf waren verkehrt. Der Test faehrt
    beide Richtungen auf Tempjournalen - ohne die Vorzeichen-Regel faellt die
    Short-Runde hier durch.
    """

    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.mkdtemp(prefix="richtung_")
        self.pfad = Path(self.tmp) / "handelsjournal.csv"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _journal(self, zeilen):
        kopf = ("zeit,modus,aktion,inst,seite,preis,einsatz_usd,stop,ziel,"
                "stop_pct,grund\n")
        with open(self.pfad, "w", encoding="utf-8", newline="") as f:
            f.write(kopf)
            f.writelines(zeilen)

    def test_long_und_short_gewinn_haben_dasselbe_vorzeichen(self):
        self._journal([
            # Long im Ziel: 100 -> 110
            "2021-01-02T00:00:00+00:00,papier,kauf,BTC,long,100.0000,62.50,"
            "92.0000,110.0000,8.00,signal\n",
            "2021-01-03T00:00:00+00:00,papier,verkauf,BTC,long,110.0000,62.50,"
            "92.0000,110.0000,8.00,ziel\n",
            # Short im Ziel: 100 -> 90 (Preis faellt = Gewinn)
            "2021-01-02T00:00:00+00:00,papier,kauf,ETH,short,100.0000,62.50,"
            "108.0000,90.0000,8.00,signal\n",
            "2021-01-03T00:00:00+00:00,papier,verkauf,ETH,short,90.0000,62.50,"
            "108.0000,90.0000,8.00,ziel\n",
        ])
        runden = kosten_wendepunkt.paarung(self.pfad)["runden"]
        self.assertEqual(2, len(runden))
        ergebnisse = sorted(r[2] for r in runden)
        self.assertAlmostEqual(10.0, ergebnisse[0], places=6)
        self.assertAlmostEqual(10.0, ergebnisse[1], places=6)
        self.assertEqual(2, len([r for r in runden if r[2] > 0]),
                         "beide Runden sind Gewinner")

    def test_short_verlust_ist_negativ(self):
        self._journal([
            "2021-01-02T00:00:00+00:00,papier,kauf,ETH,short,100.0000,62.50,"
            "108.0000,90.0000,8.00,signal\n",
            "2021-01-03T00:00:00+00:00,papier,verkauf,ETH,short,108.0000,62.50,"
            "108.0000,90.0000,8.00,stop\n",
        ])
        runden = kosten_wendepunkt.paarung(self.pfad)["runden"]
        self.assertAlmostEqual(-8.0, runden[0][2], places=6)

    def test_fehlende_seite_zaehlt_als_long_und_wird_ausgewiesen(self):
        self._journal([
            "2021-01-02T00:00:00+00:00,papier,kauf,BTC,,100.0000,62.50,"
            "92.0000,110.0000,8.00,signal\n",
            "2021-01-03T00:00:00+00:00,papier,verkauf,BTC,,110.0000,62.50,"
            "92.0000,110.0000,8.00,ziel\n",
        ])
        p = kosten_wendepunkt.paarung(self.pfad)
        self.assertAlmostEqual(10.0, p["runden"][0][2], places=6)
        self.assertEqual(1, p["ohne_seite"],
                         "eine Zeile ohne Seite muss ausgewiesen werden")


if __name__ == "__main__":
    unittest.main()