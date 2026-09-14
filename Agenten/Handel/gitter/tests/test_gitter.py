"""Tests der Gitter-Spur: Leiter, Kerzendurchlauf, Kosten, keine Order.

Die Tests brauchen kein Netz: kerzen_quelle, letzter_kurs_quelle und
instrument_quelle sind Seams in handeln.py (None -> echte Quelle). Ein Test
darf nie den echten Kurs-/Orderpfad erreichen - in jedem Lauf sind die Seams
gesetzt und werden in tearDown zurueckgesetzt.

Lauf (aus dem gitter-Ordner):
    .../Handel/scanner/.venv/Scripts/python.exe -m unittest discover -s tests
"""

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HIER)
sys.path.insert(0, HANDEL)

import handeln as h                                        # noqa: E402
from grid import stufen_bauen                              # noqa: E402

W = {"waehrung": "USDT", "gebuehr_pct": 0.1, "slippage_pct": 0.05,
     "max_verlust_usd": 200.0, "handel_erlaubt": False, "instrument": "BTC-USDT"}

INST = {"instId": "BTC-USDT", "tickSz": 0.1, "lotSz": 0.00000001,
        "minSz": 0.00001}


def zustand(preise, mengen, kasse=1000.0, verluste=0.0):
    """Ein Zustand mit gesetzter Leiter - die Walk-Tests pruefen den Lauf,
    nicht die Leiterrechnung (die hat eigene Tests)."""
    return {
        "instrument": "BTC-USDT", "modus": "papier",
        "kasse_usd": kasse, "startwert_usd": kasse,
        "leiter": {"unten": preise[0], "oben": preise[-1], "stufen": len(preise),
                   "preise": list(preise), "mengen": list(mengen),
                   "zustand": ["frei"] * (len(preise) - 1),
                   "schritt_prozent": (preise[1] / preise[0] - 1) * 100,
                   "einsatz_in_orders": sum(m * p for m, p in
                                            zip(mengen, preise[:-1])),
                   "stufen_ohne_menge": 0},
        "lose": {}, "kaeufe": 0, "verkaeufe": 0, "zyklen": 0,
        "gw_usd": 0.0, "verluste_usd": verluste, "bestand": 0.0,
        # -1: noch keine Kerze verarbeitet (der Walk verwirft alles <= der
        # letzten verarbeiteten - mit 0 faellt eine Kerze mit Stempel 0 weg).
        "letzte_kerze_ts": -1, "letzter_kurs": None,
    }


def kerze(ts, o, hoch, tief, schluss):
    return [ts, o, hoch, tief, schluss, 1.0]


STUNDE = 3_600_000


class RasterTest(unittest.TestCase):

    def test_rundet_auf_das_raster(self):
        self.assertEqual(h.raster(78236.44, 0.1), 78236.4)
        self.assertEqual(h.raster(78236.46, 0.1), 78236.5)
        self.assertEqual(h.raster(1.0 / 3, 0.01), 0.33)

    def test_abrunden_geht_nach_unten(self):
        self.assertEqual(h.raster(78236.49, 0.1, abrunden=True), 78236.4)
        self.assertLessEqual(h.raster(78236.49, 0.1, abrunden=True), 78236.49)

    def test_ohne_raster_kein_ergebnis(self):
        with self.assertRaises(ValueError):
            h.raster(100.0, 0.0)


class LeiterTest(unittest.TestCase):

    def test_stufen_gedeckelt_und_auf_dem_raster(self):
        leiter = h.leiter_bauen(1000.0, dict(W, spanne_prozent=20.0, stufen=10,
                                             einsatz_usd=1000.0), INST)
        self.assertEqual(leiter["stufen"], 10)
        self.assertAlmostEqual(leiter["unten"], 800.0, places=6)
        self.assertAlmostEqual(leiter["oben"], 1200.0, places=6)
        for p in leiter["preise"]:
            # Auf dem Raster heisst: nochmal runden aendert nichts.
            self.assertEqual(p, h.raster(p, INST["tickSz"]))
        self.assertEqual(leiter["preise"], sorted(leiter["preise"]))
        # Der Einsatz ist der Deckel - auch nach dem Rundungsverlust.
        self.assertLessEqual(leiter["einsatz_in_orders"], 1000.0)
        self.assertGreater(leiter["einsatz_in_orders"], 990.0)
        # Die oberste Stufe kauft nie.
        self.assertEqual(len(leiter["mengen"]), 9)

    def test_stufen_sind_die_formel_aus_grid_py(self):
        """Eine Rechnung, zwei Aufrufer: was hier als Leiter entsteht, sind die
        Stufen aus Handel/grid.py - nur auf das Raster der Boerse gerundet."""
        leiter = h.leiter_bauen(1000.0, dict(W, spanne_prozent=20.0, stufen=10),
                                INST)
        roh = stufen_bauen(leiter["unten"], leiter["oben"], leiter["stufen"],
                           True)
        self.assertEqual(len(roh), len(leiter["preise"]))
        for a, b in zip(leiter["preise"], roh):
            self.assertLess(abs(a - b), INST["tickSz"])       # nur das Raster

    def test_zu_kleine_stufe_bekommt_keine_menge(self):
        leiter = h.leiter_bauen(1000.0, dict(W, einsatz_usd=0.01, stufen=4),
                                INST)
        self.assertEqual(leiter["mengen"], [0.0, 0.0, 0.0])
        self.assertEqual(leiter["stufen_ohne_menge"], 3)

    def test_zu_enge_spanne_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            h.leiter_bauen(1000.0, dict(W, spanne_prozent=0.0001, stufen=12),
                           INST)

    def test_mengen_sind_abgerundet(self):
        leiter = h.leiter_bauen(1000.0, dict(W, stufen=4, einsatz_usd=300.0),
                                INST)
        for m in leiter["mengen"]:
            # Abgerundet heisst: nochmal abrunden aendert nichts.
            self.assertEqual(m, h.raster(m, INST["lotSz"], abrunden=True))


class KerzenTest(unittest.TestCase):

    def test_laufende_kerze_wird_verworfen(self):
        jetzt = h._jetzt()
        t = int(jetzt.timestamp() * 1000)
        offen = kerze(t - 600_000, 1, 1, 1, 1)        # vor 10 min begonnen
        fertig = kerze(t - STUNDE * 3, 1, 1, 1, 1)    # vor 3 h begonnen
        aus = h.abgeschlossene([fertig, offen], "1H", jetzt)
        self.assertEqual([k[0] for k in aus], [fertig[0]])

    def test_unbekannter_takt_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            h.takt_ms("7H")


class WalkTest(unittest.TestCase):

    def setUp(self):
        h.SCHREIBEN = False           # kein Journal aus dem Walk
        self.preise = [100.0, 110.0, 121.0]
        self.mengen = [1.0, 1.0]

    def tearDown(self):
        h.SCHREIBEN = True

    def _walk(self, z, kerzen, w=None):
        return h.walk(z, kerzen, w or W, "1H")

    def test_kauf_dann_zyklus(self):
        """Tief beruehrt die Stufe -> Kauf; Hoch beruehrt das Ziel -> AUSSTIEG.
        Das Ergebnis ist der Stufenabstand minus beide Kostensaetze."""
        z = zustand(self.preise, self.mengen)
        zeilen, zahlen = self._walk(z, [
            kerze(0, 121, 122, 120.5, 121),          # armiert 100 und 110
            kerze(STUNDE, 120, 120.5, 109.0, 110),   # Tief <= 110 -> Kauf
            kerze(2 * STUNDE, 110, 121.5, 110.0, 120),  # Hoch >= 121 -> Verkauf
        ])
        self.assertEqual(zahlen["kaeufe"], 1)
        self.assertEqual(zahlen["zyklen"], 1)
        self.assertEqual(z["lose"], {})
        self.assertAlmostEqual(z["bestand"], 0.0, places=12)
        brutto_kauf = 110.0
        brutto_verkauf = 121.0
        kosten = brutto_kauf * (1.0005 * 1.001 - 1) \
            + brutto_verkauf * (1 - 0.9995 * 0.999)
        erwartet = (brutto_verkauf - brutto_kauf) - kosten
        self.assertAlmostEqual(zahlen["gw_usd"], erwartet, places=9)
        self.assertAlmostEqual(z["kasse_usd"], 1000.0 + erwartet, places=9)
        self.assertTrue(any("AUSSTIEG (verkauf) gitter BTC-USDT" in zl
                            for zl in zeilen),
                        "die Ausstiegszeile muss Instrument und Stufe nennen")

    def test_kein_zyklus_in_derselben_kerze(self):
        """Eine Kerze, die tief taucht UND hoch geht, bucht nur den Kauf: was
        in dieser Kerze gekauft wurde, verkauft fruehestens in der naechsten."""
        z = zustand(self.preise, self.mengen)
        _, zahlen = self._walk(z, [
            kerze(0, 121, 122, 120.5, 121),
            kerze(STUNDE, 120, 122, 109.0, 121),
        ])
        self.assertEqual(zahlen["kaeufe"], 1)
        self.assertEqual(zahlen["zyklen"], 0)
        self.assertIn("1", z["lose"])

    def test_kein_verkauf_ohne_bestand(self):
        """Ein steigender Kurs erzeugt keine Verkaeufe - ohne Bestand gibt es
        nichts zu verkaufen."""
        z = zustand(self.preise, self.mengen)
        zeilen, zahlen = self._walk(z, [
            kerze(i * STUNDE, 121 + i, 130 + i, 120 + i, 122 + i)
            for i in range(5)
        ])
        self.assertEqual(zahlen["verkaeufe"], 0)
        self.assertEqual(z["lose"], {})
        self.assertFalse([zl for zl in zeilen if "AUSSTIEG" in zl])

    def test_kosten_auf_beiden_seiten(self):
        """Gegenprobe: ohne Gebuehr und Slippage bleibt genau der Stufenabstand
        uebrig, mit Kosten weniger - und der Unterschied ist die Kostensumme."""
        kerzen = [kerze(0, 121, 122, 120.5, 121),
                  kerze(STUNDE, 120, 120.5, 109.0, 110),
                  kerze(2 * STUNDE, 110, 121.5, 110.0, 120)]
        z1 = zustand(self.preise, self.mengen)
        _, zahlen1 = self._walk(z1, kerzen, dict(W, gebuehr_pct=0.0,
                                                 slippage_pct=0.0))
        z2 = zustand(self.preise, self.mengen)
        _, zahlen2 = self._walk(z2, kerzen)
        self.assertAlmostEqual(zahlen1["gw_usd"], 11.0, places=9)
        self.assertLess(zahlen2["gw_usd"], zahlen1["gw_usd"])
        self.assertGreater(zahlen1["gw_usd"] - zahlen2["gw_usd"], 0.2)

    def test_keine_kauforders_ueber_dem_kurs(self):
        """Armiert wird nur unter dem Kurs - sonst waere die Limitorder eine
        getarnte Marketorder."""
        z = zustand(self.preise, self.mengen)
        h.arme(z, 105.0)
        self.assertEqual(z["leiter"]["zustand"], ["armiert", "frei"])

    def test_walk_ist_fortsetzbar(self):
        """In zwei Schritten dasselbe wie in einem: der Durchlauf haengt am
        Kerzenstempel, nicht am Prozessleben (der Dauerlauf startet neu)."""
        kerzen = [kerze(0, 121, 122, 120.5, 121),
                  kerze(STUNDE, 120, 120.5, 109.0, 110),
                  kerze(2 * STUNDE, 110, 121.5, 110.0, 120),
                  kerze(3 * STUNDE, 120, 120.5, 99.0, 100),
                  kerze(4 * STUNDE, 100, 111.0, 100.0, 110)]
        ganz = zustand(self.preise, self.mengen)
        self._walk(ganz, kerzen)
        halb = zustand(self.preise, self.mengen)
        self._walk(halb, kerzen[:2])
        halb = json.loads(json.dumps(halb))         # Zustands-Roundtrip
        self._walk(halb, kerzen[2:])
        for feld in ("kasse_usd", "kaeufe", "verkaeufe", "zyklen", "bestand"):
            self.assertAlmostEqual(ganz[feld], halb[feld], places=9, msg=feld)
        self.assertEqual(ganz["lose"].keys(), halb["lose"].keys())
        self.assertEqual(ganz["leiter"]["zustand"], halb["leiter"]["zustand"])

    def test_kill_switch_stoppt_neue_kaeufe(self):
        """Ueber der Verlustgrenze werden keine neuen Stufen armiert - was
        liegt, verkauft weiter."""
        z = zustand(self.preise, self.mengen, verluste=W["max_verlust_usd"])
        _, zahlen = self._walk(z, [
            kerze(0, 121, 122, 120.5, 121),
            kerze(STUNDE, 120, 120.5, 99.0, 100),
        ])
        self.assertEqual(zahlen["kaeufe"], 0)
        self.assertEqual(z["lose"], {})
        self.assertTrue(h._kill(z, W).startswith("KILL-SWITCH gitter"))

    def test_kasse_reicht_nicht(self):
        z = zustand(self.preise, self.mengen, kasse=1.0)
        zeilen, zahlen = self._walk(z, [
            kerze(0, 121, 122, 120.5, 121),
            kerze(STUNDE, 120, 120.5, 109.0, 110),
        ])
        self.assertEqual(zahlen["kaeufe"], 0)
        self.assertTrue(any("Kasse" in zl for zl in zeilen))

    def test_bestand_ist_die_summe_der_lose(self):
        z = zustand(self.preise, self.mengen)
        self._walk(z, [kerze(0, 121, 122, 120.5, 121),
                       kerze(STUNDE, 120, 120.5, 99.0, 100)])
        self.assertAlmostEqual(
            z["bestand"], sum(los["menge"] for los in z["lose"].values()),
            places=12)


class ZustandTest(unittest.TestCase):

    def test_positionen_kommen_aus_den_losen(self):
        z = zustand([100.0, 110.0, 121.0], [1.0, 2.0])
        z["lose"] = {"1": {"menge": 2.0, "einstieg": 110.0, "brutto": 220.0,
                           "kosten": 220.2, "eroeffnet": "2026-09-13"}}
        pos = h.positionen_aus(z)
        self.assertEqual(len(pos), 1)
        p = pos[0]
        self.assertEqual((p["inst"], p["seite"], p["einstieg"], p["menge"]),
                         ("BTC-USDT", "long", 110.0, 2.0))
        self.assertEqual(p["ziel"], 121.0)          # die naechste Stufe
        self.assertEqual(p["nominal"], 220.2)

    def test_geschriebener_zustand_ist_fuer_die_leser_lesbar(self):
        """Die abgeleitete Positionsliste muss das sein, was Bus und Fenster
        lesen - sonst steht in der Anzeige "0 Positionen" bei offenem Bestand."""
        import handelszentrale as gui
        z = zustand([100.0, 110.0, 121.0], [1.0, 2.0])
        z["lose"] = {"0": {"menge": 1.0, "einstieg": 100.0, "brutto": 100.0,
                           "kosten": 100.2, "eroeffnet": "2026-09-13"}}
        z["positionen"] = h.positionen_aus(z)
        gelesen = gui.positionen_aus(z)
        self.assertEqual(len(gelesen), len(z["lose"]))
        self.assertEqual(gelesen[0]["wert_usd"], 100.2)
        self.assertEqual(gelesen[0]["schluessel"], "BTC-USDT")
        self.assertEqual(gelesen[0]["ziel"], 110.0)

    def test_buchwert_ist_kasse_plus_bestand(self):
        z = zustand([100.0, 110.0, 121.0], [1.0, 1.0], kasse=500.0)
        z["letzter_kurs"] = 120.0
        z["lose"] = {"0": {"menge": 2.0, "einstieg": 100.0, "brutto": 200.0,
                           "kosten": 200.0, "eroeffnet": "2026-09-13"}}
        self.assertAlmostEqual(h.buchwert(z), 500.0 + 240.0, places=9)


class LaufTest(unittest.TestCase):
    """Der ganze Zyklus ueber lauf() - mit Temp-Dateien und Seams."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gitter-test-")
        self._wachen, self._zustand, self._journal = h.WACHEN, h.ZUSTAND, h.JOURNAL
        h.WACHEN = os.path.join(self.tmp, "wachen.json")
        h.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        w = dict(W)
        w.update({"spanne_prozent": 20.0, "stufen": 6, "einsatz_usd": 600.0,
                  "kerzen_takt": "1H", "kerzen_anzahl": 10,
                  "geometrisch": True, "journal_zweitziel": None})
        with open(h.WACHEN, "w", encoding="utf-8") as f:
            json.dump(w, f)
        self.kerzen = [kerze(i * STUNDE, 100, 101, 99, 100) for i in range(5)]
        h.kerzen_quelle = lambda inst, takt, anzahl: list(self.kerzen)
        h.letzter_kurs_quelle = lambda inst: 100.0
        h.instrument_quelle = lambda inst: dict(INST)
        h.SCHREIBEN = True

    def tearDown(self):
        h.WACHEN, h.ZUSTAND, h.JOURNAL = self._wachen, self._zustand, self._journal
        h.kerzen_quelle = None
        h.letzter_kurs_quelle = None
        h.instrument_quelle = None
        h.SCHREIBEN = True

    def _lauf(self, modus):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            h.lauf(modus)
        return puffer.getvalue()

    def test_erster_lauf_legt_die_leiter_an(self):
        aus = self._lauf("papier")
        self.assertIn("GITTER anlegen", aus)
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertAlmostEqual(z["anker_preis"], 100.0, places=9)
        self.assertEqual(z["leiter"]["stufen"], 6)
        self.assertLessEqual(z["leiter"]["einsatz_in_orders"], 600.0)
        # Der Erstlauf bucht nichts, legt aber die Journaldatei mit Kopfzeile
        # an: die Kopie ausser Haus vergleicht Dateien, und eine fehlende
        # Datei liest sich dort wie ein Unterschied.
        self.assertTrue(os.path.exists(h.JOURNAL))
        with open(h.JOURNAL, newline="", encoding="utf-8") as f:
            self.assertEqual(list(csv.DictReader(f)), [])

    def test_erster_kauf_schreibt_das_journal(self):
        self._lauf("papier")
        # Leiter aus Kurs 100 (Stufen 80 / 86.76 / 94.09 / 102.03 / 110.65 /
        # 120): ein Tief von 84 beruehrt die Stufe 86.76.
        self.kerzen = [kerze((5 + i) * STUNDE, 91, 92, 84, 85)
                       for i in range(2)]
        self.kerzen_quelle = lambda inst, takt, anzahl: list(self.kerzen)
        self._lauf("papier")
        with open(h.JOURNAL, newline="", encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        self.assertTrue(zeilen)
        self.assertEqual(zeilen[0]["aktion"], "KAUF")
        self.assertEqual(zeilen[0]["inst"], "BTC-USDT")

    def test_zweiter_lauf_zieht_kerzen_nach(self):
        self._lauf("papier")
        self.kerzen = [kerze((5 + i) * STUNDE, 100, 101, 90, 91)
                       for i in range(3)]
        self.kerzen_quelle = lambda inst, takt, anzahl: list(self.kerzen)
        aus = self._lauf("papier")
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertIn("Kerzen nachgezogen", aus)
        self.assertEqual(z["letzte_kerze_ts"], 7 * STUNDE)

    def test_vorschau_legt_nichts_an(self):
        aus = self._lauf("vorschau")
        self.assertFalse(os.path.exists(h.ZUSTAND),
                         "eine Vorschau darf keinen Zustand anlegen")
        self.assertFalse(os.path.exists(h.JOURNAL),
                         "eine Vorschau darf kein Journal anlegen")
        self.assertIn("Live waere gesperrt durch:", aus)
        self.assertNotIn("Freigabefenster", aus)

    def test_live_verweigert_ohne_freigabefenster(self):
        self._lauf("papier")                     # Leiter anlegen
        aus = self._lauf("live")
        self.assertIn("gesperrt", aus)
        self.assertIn("es wird Papier gebucht", aus)
        self.assertNotIn("Freigabefenster", aus)

    def test_spur_verweigert_wenn_keine_kerzen_kommen(self):
        h.kerzen_quelle = lambda inst, takt, anzahl: []
        aus = self._lauf("papier")
        self.assertIn("Kursdaten nicht abrufbar", aus)
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertTrue(z.get("letzter_lauf"), "Herzschlag trotz Datenausfall")

    def test_zweiter_lauf_traegt_positionen_fuer_die_leser(self):
        self._lauf("papier")
        self.kerzen = [kerze((5 + i) * STUNDE, 100, 101, 79, 80)
                       for i in range(2)]
        self.kerzen_quelle = lambda inst, takt, anzahl: list(self.kerzen)
        self._lauf("papier")
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(len(z["positionen"]), len(z["lose"]))
        for p in z["positionen"]:
            self.assertEqual(p["inst"], "BTC-USDT")
            self.assertIn("einstieg", p)
            self.assertIn("nominal", p)


class QuelltextTest(unittest.TestCase):

    def test_kein_orderpfad_und_kein_unterprozess(self):
        quelle = open(os.path.join(HIER, "handeln.py"), encoding="utf-8").read()
        for wort in ("markt_kauf", "markt_verkauf", "signiert", "subprocess",
                     "order_limit"):
            self.assertNotIn(wort, quelle,
                             f"{wort!r} gehoert nicht in eine Papierspur")


if __name__ == "__main__":
    unittest.main(verbosity=2)
