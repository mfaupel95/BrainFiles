"""Tests der Omniquant-Spur: Signalquelle, Einstiege, Ausstiege, keine Order.

Die Tests brauchen kein Netz: bericht_quelle und letzter_kurs_quelle sind
Seams in handeln.py (None -> echte Quelle), die Tests setzen Lambdas und
stellen in tearDown zurueck. Ein Test darf nie den echten Order-/Kurspfad
erreichen - letzter_kurs_quelle ist in jedem Lauf gesetzt.

Lauf:
    C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe
        -m unittest discover -s tests -p "test_*.py"
"""

import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
import sys
sys.path.insert(0, HIER)
sys.path.insert(0, HANDEL)

import handeln as h                               # noqa: E402


def _bericht(treffer, erzeugt=None):
    """Ein synthetischer Prognose-Bericht mit frischem Zeitstempel."""
    return {
        "datum": "2026-09-13",
        "erzeugt": (erzeugt or datetime.now(timezone.utc)).isoformat(
            timespec="seconds"),
        "maerkte_geprueft": 33,
        "treffer": treffer,
    }


def _treffer(inst, richtung, kurs, stop, ziel, score=67.0, cr=2.0):
    return {"inst": inst, "richtung": richtung, "preis": kurs, "stop": stop,
            "ziel": ziel, "score": score, "cr": cr}


class Basis(unittest.TestCase):
    def setUp(self):
        # Zustands- und Journal-Dateien der Spur nie anfassen: Tests laufen
        # gegen ein temp-Verzeichnis, in das handeln.py umgebogen wird.
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_zustand = h.ZUSTAND
        self.alt_journal = h.JOURNAL
        self.alt_wachen = h.WACHEN
        h.ZUSTAND = os.path.join(self.tmp.name, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp.name, "handelsjournal.csv")
        h.WACHEN = os.path.join(self.tmp.name, "wachen.json")
        with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        # Das Ziel der Kopie ausser Haus MUSS umgebogen werden. Bis zum
        # 14.09.2026 behielt die Kopie den echten Wert aus der wachen.json
        # ("Q:\\Handel_Journal\\omniquant"), und jeder Test, der lauf() aufrief,
        # ueberschrieb damit die echte Kopie auf Q: mit Testdaten. Jetzt zeigt
        # das Ziel in den Temp-Ordner: der Spiegelpfad bleibt getestet, trifft
        # aber nichts Echtes.
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        with open(h.WACHEN, "w", encoding="utf-8") as f:
            json.dump(w, f, ensure_ascii=False, indent=2)

    def tearDown(self):
        h.ZUSTAND = self.alt_zustand
        h.JOURNAL = self.alt_journal
        h.WACHEN = self.alt_wachen
        h.letzter_kurs_quelle = None
        h.bericht_quelle = None
        self.tmp.cleanup()

    def _fenster_zu(self):
        """Das Zeitfenster stumm schliessen, Guthaben gross (Sperrenkette).

        Der Zustand von `handel_erlaubt`/`freigabe.erfuellt` wird dabei NICHT
        angefasst: er ist Max' Entscheidung. Wer einen Test gegen ihn baut,
        meldet jede Entscheidung als Fehler.
        """
        import live_perp as lp
        alt = (lp.sitzung_da, lp.zeitfenster_offen,
               lp.kraken_perp.schluessel_vorhanden, lp.kraken_perp.guthaben_usd)
        self.addCleanup(lambda: self._setze(lp, alt))
        lp.sitzung_da = lambda: False
        lp.zeitfenster_offen = lambda: False
        lp.kraken_perp.schluessel_vorhanden = lambda: True
        lp.kraken_perp.guthaben_usd = lambda: 1000.0

    @staticmethod
    def _setze(lp, werte):
        (lp.sitzung_da, lp.zeitfenster_offen,
         lp.kraken_perp.schluessel_vorhanden, lp.kraken_perp.guthaben_usd) = werte


class KandidatenTest(Basis):
    def test_uebernimmt_treffer_mit_richtung(self):
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        kand, fehler = h.kandidaten(z, w)
        self.assertIsNone(fehler)
        self.assertEqual(len(kand), 1)
        self.assertEqual(kand[0]["inst"], "BTC-USDC")
        self.assertEqual(kand[0]["seite"], "long")

    def test_treffer_ohne_richtung_wird_uebersprungen(self):
        # Altes Berichtsformat (vor dem Richtungsfeld): keine Auskunft.
        b = _bericht([])
        b["treffer"] = [{"inst": "HYPE-USDC", "preis": 79.79,
                         "stop": 75.8, "ziel": 89.67}]
        h.bericht_quelle = b
        h.letzter_kurs_quelle = lambda inst: 80.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    def test_signal_verfallen_wenn_kurs_ausserhalb(self):
        # long: Kurs muss zwischen Stop und Ziel liegen.
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 112.0   # schon uebers Ziel
        z = h.lade_zustand()
        w = h.lade_wachen()
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    def test_kein_doppelter_einstieg(self):
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long"}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    # --- Streuungs-Filter: gleicher Basiswert zaehlt nur begrenzt --------
    # Mechanik mit ausdruecklich gesetzten Werten pruefen (max_je_basiswert
    # wird in jedem Test explizit gesetzt, nie der Stand der echten Datei).

    def test_gleicher_basiswert_im_zyklus_nur_staerkster(self):
        # SOL-USDC und SOL-USDT sind zwei Treffer, aber ein Vermoegenswert.
        # Der Bericht ist nach C/R x Score sortiert - der Staerkste geht
        # zuerst durch und blockt das schwaechere Duplikat.
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDC", "long", 100.0, 95.0, 110.0,
                     score=71.8, cr=2.25),
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0,
                     score=61.9, cr=2.24)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 1)
        self.assertEqual(kand[0]["inst"], "SOL-USDC")

    def test_staerkster_verfallen_schwaecherer_geht_durch(self):
        # Verfallene Treffer zaehlen nicht als Kandidat: der Filter waehlt
        # unter den GUELTIGEN, nicht unter der Berichtsliste. Der staerkere
        # SOL-USDC ist uebers Ziel gelaufen (105 > 103), SOL-USDT gueltig.
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDC", "long", 100.0, 95.0, 103.0,
                     score=71.8, cr=2.25),
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0,
                     score=61.9, cr=2.24)])
        h.letzter_kurs_quelle = lambda inst: 105.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 1)
        self.assertEqual(kand[0]["inst"], "SOL-USDT")

    def test_max_je_basiswert_zwei_laesst_zwei_durch(self):
        # Die Mechanik, nicht der Wert: mit Grenze 2 gehen beide SOL-Paare
        # durch - der Filter ist konfigurierbar, kein fester Wert.
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDC", "long", 100.0, 95.0, 110.0,
                     score=71.8, cr=2.25),
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0,
                     score=61.9, cr=2.24)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 2
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 2)

    def test_basiswert_schon_offen_blockt_andere_quote(self):
        # SOL-USDC long ist offen - SOL-USDT bekommt keine zweite Position
        # im selben Vermoegenswert (Klumpen, keine Diversifikation).
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        z["positionen"] = [{"inst": "SOL-USDC", "seite": "long"}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    def test_basiswert_erledigt_heute_blockt_andere_quote(self):
        # SOL-USDC heute geschlossen: SOL-USDT kommt heute nicht mehr
        # (die Merkliste, erweitert um die Quote-Ebene).
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        z["erledigt"] = [{"inst": "SOL-USDC", "seite": "long",
                          "am": h._heute()}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    def test_basiswert_erledigt_gestern_blockt_nicht_mehr(self):
        # Das Tor geht auf: gestern geschlossen ist eine neue Lage heute.
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDT", "long", 101.0, 96.0, 111.0)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        gestern = (datetime.now(timezone.utc).date()
                   - timedelta(days=1)).isoformat()
        z["erledigt"] = [{"inst": "SOL-USDC", "seite": "long", "am": gestern}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 1)

    def test_verschiedene_basiswerte_kommen_alle_durch(self):
        h.bericht_quelle = _bericht([
            _treffer("SOL-USDC", "long", 100.0, 95.0, 110.0),
            _treffer("ETH-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 102.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        w["max_je_basiswert"] = 1
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 2)

    def test_kein_wiedereinstieg_aus_erledigt_heute(self):
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["erledigt"] = [{"inst": "BTC-USDC", "seite": "long",
                          "am": h._heute()}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(kand, [])

    def test_erledigt_von_gestern_blockiert_nicht(self):
        # Ein frischer Bericht mit neuen Grenzen ist eine neue Lage. Die
        # Merkliste darf nur den heutigen Tag sperren, sonst ist das Tor
        # zu (Pitfall aus handel-spuren: eine Sperre muss aufgehen koennen).
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        gestern = (datetime.now(timezone.utc).date()
                   - timedelta(days=1)).isoformat()
        z["erledigt"] = [{"inst": "BTC-USDC", "seite": "long", "am": gestern}]
        kand, _ = h.kandidaten(z, w)
        self.assertEqual(len(kand), 1)

    def test_alter_bericht_ist_abstention(self):
        alt = datetime.now(timezone.utc) - timedelta(hours=50)
        h.bericht_quelle = _bericht(
            [_treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)], erzeugt=alt)
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        kand, fehler = h.kandidaten(z, w)
        self.assertEqual(kand, [])
        self.assertIn("alt", fehler)


class EinstiegAusstiegTest(Basis):
    def test_eroeffnet_position_und_schreibt_journal(self):
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        kand, _ = h.kandidaten(z, w)
        h.eroeffne(z, w, kand[0])
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        self.assertEqual(p["inst"], "BTC-USDC")
        self.assertEqual(p["seite"], "long")
        self.assertAlmostEqual(p["nominal"], 50.0)
        with open(h.JOURNAL, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("EINSTIEG", inhalt)
        self.assertIn("BTC-USDC", inhalt)

    def test_ausstieg_stop_long(self):
        h.letzter_kurs_quelle = lambda inst: 94.0    # unter dem Stop
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": "2026-09-10"}]
        h.pruefe_ausstiege(z, w)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["erledigt"][0]["grund"], "stop")
        # Verlust gebucht: 5 % Bewegung + Kosten auf beiden Seiten (0,5 %).
        self.assertGreater(z["verluste_usd"], 0.0)
        with open(h.JOURNAL, encoding="utf-8") as f:
            inhalt = f.read()
        self.assertIn("AUSSTIEG", inhalt)
        self.assertIn("stop", inhalt)

    def test_ausstieg_ziel_long(self):
        h.letzter_kurs_quelle = lambda inst: 111.0   # ueber dem Ziel
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": "2026-09-10"}]
        h.pruefe_ausstiege(z, w)
        self.assertEqual(z["erledigt"][0]["grund"], "ziel")
        self.assertEqual(z["verluste_usd"], 0.0)

    def test_ausstieg_stop_short(self):
        h.letzter_kurs_quelle = lambda inst: 96.0    # ueber dem Stop
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "short",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 90.0,
                            "nominal": 50.0, "eroeffnet": "2026-09-10"}]
        h.pruefe_ausstiege(z, w)
        self.assertEqual(z["erledigt"][0]["grund"], "stop")

    def test_zwangsschluss_nach_halte_dauer(self):
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        alt = (datetime.now(timezone.utc) - timedelta(days=20)).date().isoformat()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": alt}]
        h.pruefe_ausstiege(z, w)
        self.assertEqual(z["erledigt"][0]["grund"], "zwangsschluss")

    def test_kein_zwangsschluss_bei_frischer_position(self):
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": h._heute()}]
        h.pruefe_ausstiege(z, w)
        self.assertEqual(len(z["positionen"]), 1)

    # --- Kosten: beide Seiten, kein Wunschdenken -------------------------

    def test_kosten_ohne_kursbewegung_ergeben_minus(self):
        # Der wichtigste Test eines Papierbuchs: eine Kopie ohne Bewegung
        # darf kein Plus ergeben. Und beide Ausfuehrungsseiten muessen
        # drin sein - mit nur einer Kostenseite waere das Minus halb so
        # gross, und die Kernfrage ("traegt die Prognose nach Kosten?")
        # waere systematisch zu optimistisch beantwortet.
        w = h.lade_wachen()
        k = h._kosten(w)
        for seite in ("long", "short"):
            p = {"inst": "BTC-USDC", "seite": seite, "einstieg": 100.0,
                 "stop": 95.0, "ziel": 110.0, "nominal": 50.0}
            wert = h._ergebnis(p, 100.0, w)
            self.assertLess(wert, 50.0)
            self.assertAlmostEqual(50.0 - wert,
                                   50.0 * 2 * k / (1.0 + k), places=6)

    def test_short_verliert_nicht_mehr_als_den_einsatz(self):
        # Ein Anstieg ueber 100 % (hier das Dreifache) darf keinen negativen
        # Erloes ergeben: real waere bei 0 Schluss gewesen (Liquidation).
        w = h.lade_wachen()
        p = {"inst": "BTC-USDC", "seite": "short", "einstieg": 100.0,
             "stop": 95.0, "ziel": 90.0, "nominal": 50.0}
        self.assertEqual(h._ergebnis(p, 300.0, w), 0.0)

    # --- Buchgewinn/-verlust und Journal-Spalten -------------------------

    def test_mfe_mae_werden_fortgeschrieben(self):
        # Ohne die Extreme kann die Auswertung nicht trennen, ob ein Stop zu
        # eng war (die Position lief erst ins Plus) oder das Signal falsch.
        h.letzter_kurs_quelle = lambda inst: 101.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": h._heute(),
                            "mfe_pct": 0.0, "mae_pct": 0.0}]
        p = z["positionen"][0]
        h._merke_extrem(p, 104.0)
        h._merke_extrem(p, 97.0)
        h._merke_extrem(p, 102.0)
        self.assertAlmostEqual(p["mfe_pct"], 4.0)
        self.assertAlmostEqual(p["mae_pct"], -3.0)

    def test_ausstieg_traegt_score_cr_und_extreme_ins_journal(self):
        # Die Auswertung liest das Journal, nicht den Zustand: was dort
        # fehlt, ist fuer die Kalibrierung verloren.
        h.letzter_kurs_quelle = lambda inst: 94.0
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["positionen"] = [{"inst": "BTC-USDC", "seite": "long",
                            "einstieg": 100.0, "stop": 95.0, "ziel": 110.0,
                            "nominal": 50.0, "eroeffnet": "2026-09-10",
                            "score": 67.5, "cr": 2.1,
                            "mfe_pct": 1.5, "mae_pct": -6.0}]
        h.pruefe_ausstiege(z, w)
        with open(h.JOURNAL, encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        a = [x for x in zeilen if x["aktion"] == "AUSSTIEG"][0]
        self.assertEqual(a["score"], "67.5")
        self.assertEqual(a["cr"], "2.1")
        self.assertEqual(a["mfe_pct"], "1.5")
        self.assertEqual(a["mae_pct"], "-6.0")
        self.assertNotEqual(a["haltetage"], "")


class BerichtRobustheitTest(Basis):
    def test_naiver_berichtszeitstempel_kippt_die_spur_nicht(self):
        # Ein Zeitstempel ohne Zone loeste bisher TypeError aus (nicht
        # ValueError) - die Spur braeche ab, statt zu handeln oder sich zu
        # enthalten. Er wird jetzt als UTC gelesen.
        b = _bericht([])
        naiv = datetime.now(timezone.utc).replace(tzinfo=None)
        b["erzeugt"] = naiv.isoformat(timespec="seconds")
        h.bericht_quelle = b
        h.letzter_kurs_quelle = lambda inst: 100.0
        kand, fehler = h.kandidaten(h.lade_zustand(), h.lade_wachen())
        self.assertIsNone(fehler)
        self.assertEqual(kand, [])

    def test_bericht_ohne_lesbaren_zeitstempel_ist_abstention(self):
        b = _bericht([])
        b["erzeugt"] = "keine-zeit"
        h.bericht_quelle = b
        h.letzter_kurs_quelle = lambda inst: 100.0
        kand, fehler = h.kandidaten(h.lade_zustand(), h.lade_wachen())
        self.assertEqual(kand, [])
        self.assertIsNotNone(fehler)

    def test_zu_alte_bericht_ist_abstention_mit_grund(self):
        alt = datetime.now(timezone.utc) - timedelta(hours=40)
        h.bericht_quelle = _bericht(
            [_treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)], erzeugt=alt)
        h.letzter_kurs_quelle = lambda inst: 101.0
        kand, fehler = h.kandidaten(h.lade_zustand(), h.lade_wachen())
        self.assertEqual(kand, [])
        self.assertIn("alt", fehler)


class StatistikTest(Basis):
    def test_statistik_erklaert_warum_treffer_wegfallen(self):
        # "0 Kandidaten" darf nicht wie "kein Signal" aussehen: die Zahlen
        # trennen verfallene Signale von gefilterten und Kursfehlern.
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0),      # gueltig
            _treffer("ETH-USDC", "long", 100.0, 95.0, 103.0),      # verfallen
            {"inst": "X-USDC", "preis": 1.0, "stop": 0.9, "ziel": 1.1}])
        h.letzter_kurs_quelle = lambda inst: 105.0
        st = {}
        h.kandidaten(h.lade_zustand(), h.lade_wachen(), st)
        self.assertEqual(st["treffer"], 3)
        self.assertEqual(st["verfallen"], 1)
        self.assertEqual(st["ohne_richtung"], 1)


class SperrenTest(Basis):
    def test_live_nennt_das_freigabefenster_als_eigenen_grund(self):
        """Der Vertrag hat sich am 01.10.2026 umgedreht.

        Frueher galt: das Wort "Freigabefenster" darf NICHT vorkommen - die
        Spur hatte keinen Orderpfad, eine Anfrage haette nichts oeffnen
        koennen. Mit dem Orderweg (Kraken Futures) ist das Fenster ein ECHTER
        Grund. Es muss ein EIGENER Grund sein, sonst findet
        `dauerlauf.nur_fenster_fehlt()` nichts.

        NICHT geprueft wird, ob die beiden Haken gesetzt sind: das ist Max'
        Entscheidung und stand am 01.10.2026 auf true ('auto freigabe erlaubt').
        Ein Test, der diesen Zustand einfriert, wird bei jeder Entscheidung rot
        statt bei einem Fehler.
        """
        self._fenster_zu()
        z = h.lade_zustand()
        w = h.lade_wachen()
        g = h.sperren_live(w, z)
        fenster = [x for x in g if "Freigabefenster" in x]
        self.assertEqual(1, len(fenster), g)
        # Der Satz nennt nur das Fenster, keine zweite Ursache.
        self.assertIn("keine Sitzung am Bildschirm", fenster[0])

    def test_kill_switch_bei_verlustgrenze(self):
        z = h.lade_zustand()
        w = h.lade_wachen()
        z["verluste_usd"] = w["max_gesamt_risiko_usd"] + 1
        g = h.sperren_live(w, z)
        self.assertTrue(any("Kill-Switch" in x for x in g))

    def test_live_modus_handelt_papier(self):
        """--live ohne offenes Zeitfenster: es wird Papier gehandelt.

        Der Test hiess frueher: '--live auf einer papierfesten Spur' und
        stuetzte sich darauf, dass handel_erlaubt=false ist. Seit dem
        01.10.2026 sind beide Haken gesetzt - der Papierzweig kommt jetzt aus
        dem GESCHLOSSENEN Zeitfenster. Geprueft wird die Wirkung: kein
        Live-Einstieg und 'papier' im Zustand.
        """
        import live_perp as lp
        self._fenster_zu()
        h.letzter_kurs_quelle = lambda inst: 94.0
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        gerufen = []
        alt_kaufe, lp.kaufe = lp.kaufe, lambda *a, **k: gerufen.append(a)
        self.addCleanup(setattr, lp, "kaufe", alt_kaufe)
        h.lauf("live")
        self.assertEqual([], gerufen, "es darf kein Live-Einstieg versucht werden")
        self.assertEqual("papier", h.lade_zustand().get("modus"))


class VorschauTest(Basis):
    def test_vorschau_schreibt_nichts(self):
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        self.assertFalse(os.path.exists(h.ZUSTAND))
        self.assertFalse(os.path.exists(h.JOURNAL))
        h.lauf("vorschau")
        # Weder Zustand noch Journal angelegt: eine Vorschau schreibt nicht.
        self.assertFalse(os.path.exists(h.ZUSTAND))
        self.assertFalse(os.path.exists(h.JOURNAL))

    def test_vorschau_nennt_sperrenzeile(self):
        h.bericht_quelle = _bericht([])
        h.letzter_kurs_quelle = lambda inst: 101.0
        # Die --vorschau-Zeile ist die Schnittstelle zu dauerlauf.
        # nur_fenster_fehlt() liest sie - ohne das Wort "Freigabefenster"
        # fragt der Lauf nie, obwohl genau das der einzige Grund waere.
        # Geprueft wird also der VERTRAG (Zeile da, und sie nennt das Fenster,
        # wenn das Fenster der Grund ist), nicht ob Max' Haken gesetzt sind.
        self._fenster_zu()
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            h.lauf("vorschau")
        out = buf.getvalue()
        self.assertIn("Live waere gesperrt durch:", out)
        self.assertIn("Freigabefenster", out)


class ZustandsformTest(Basis):
    def test_zustandsform_passt_fuer_bus_und_tagesbericht(self):
        # handel_befehle.status() zaehlt d.get('positionen') als Liste und
        # beschriftet mit p.get('seite')/p.get('inst'); der Tagesbericht
        # liest seite/einstieg/stop/ziel/eroeffnet. Die Form muss diese
        # Feldnamen tragen, sonst liest sich die Spur dort als leer.
        h.bericht_quelle = _bericht([
            _treffer("BTC-USDC", "long", 100.0, 95.0, 110.0)])
        h.letzter_kurs_quelle = lambda inst: 101.0
        h.lauf("papier")
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(z["modus"], "papier")
        self.assertIsInstance(z["positionen"], list)
        if z["positionen"]:
            p = z["positionen"][0]
            for feld in ("inst", "seite", "einstieg", "stop", "ziel",
                         "eroeffnet", "nominal"):
                self.assertIn(feld, p)


if __name__ == "__main__":
    unittest.main()
