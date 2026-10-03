"""Ablehnungsprotokoll: warum ein Kandidat NICHT gekauft wurde.

Das Journal protokolliert nur Buchungen. Damit sehen zwei voellig
verschiedene Lagen identisch aus - "die Tore filtern zu hart" und "das Buch
war voll". Beide erscheinen als fehlende Kaufzeile. Seit der Scan den ganzen
Spotmarkt sieht (14.09.2026), ist das die entscheidende Frage fuer den
Durchsatz der einzigen Spur mit echtem Geld.

Die Tests hier halten die vier Regeln fest, an denen so ein Protokoll
scheitert: jedes Signal in genau einen Zaehler, Kapazitaet ist kein Tor,
kein Abruf fuer ein billiges Tor, und die Vorschau schreibt nichts.
"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))
# spiegelstand.py liegt im Handel-Ordner und importiert `risikostufe` von dort.
# Ans ENDE haengen: scanner/handeln.py muss vorn bleiben (gleichnamige Module
# in den Spurordnern duerfen es nicht verdraengen).
sys.path.append(str(HIER.parent.parent))

import handeln as h                                          # noqa: E402


def _markt(inst, score=70.0, vola=0.8, verh=2.0, preis=100.0):
    """Eine Bericht-Zeile, wie scan.py sie liefert."""
    return {"inst": inst, "score": score, "preis": preis,
            "verhaeltnis": verh,
            "kennzahlen": {"volatilitaet_pa": vola}}


WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.20,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 5.0,
          "pflicht_stop_prozent_max": 12.0, "max_pro_trade_usd": 100,
          "max_offene_positionen": 6, "max_gesamt_usd": 400,
          "abklingzeit_tage": 4}


class Basis(unittest.TestCase):
    """Gemeinsame Naht: vorschlaege() fragt seit 03.10.2026 den MARKT-
    kurs (nicht den Berichtspreis) - das ist der einzige Netzabruf im
    Bewertungspfad. Die Tore selbst bleiben abruf-frei: ein Kandidat,
    der am Score scheitert, darf keinen Kurs holen. Deshalb wird hier
    marktkurs umgebogen und mitgezaehlt."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.abl_vorher = h.ABLEHNUNGEN
        self.journal_vorher = h.JOURNAL
        self.schreiben_vorher = h.SCHREIBEN
        self.marktkurs_vorher = h.marktkurs
        self.kursabrufe = []
        self.marktpreis = 100.0
        h.marktkurs = self._marktkurs
        h.ABLEHNUNGEN = Path(self.tmp.name) / "ablehnungen.csv"
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"
        h.SCHREIBEN = True

    def _marktkurs(self, inst):
        self.kursabrufe.append(inst)
        return self.marktpreis

    def tearDown(self):
        h.ABLEHNUNGEN = self.abl_vorher
        h.JOURNAL = self.journal_vorher
        h.SCHREIBEN = self.schreiben_vorher
        h.marktkurs = self.marktkurs_vorher
        self.tmp.cleanup()

    def zeilen(self):
        if not h.ABLEHNUNGEN.exists():
            return []
        with h.ABLEHNUNGEN.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def summe(self, grund):
        return sum(int(z["anzahl"] or 0) for z in self.zeilen()
                   if z["grund"] == grund)


class LageZaehlerTest(Basis):
    """Regel: jedes Signal in GENAU EINEN Zaehler."""

    def test_summe_der_gruende_ergibt_die_bewerteten_maerkte(self):
        werte = [
            _markt("A-USDT", score=50.0),                  # Score zu klein
            _markt("B-USDT", vola=2.0),                    # Vola zu hoch
            _markt("C-USDT", verh=1.0),                    # C/R zu klein
            _markt("D-USDT"),                              # geht durch
            _markt("E-USDT"),                              # geht durch
        ]
        aus = h.vorschlaege({"werte": werte}, WACHEN)
        self.assertEqual(len(aus), 2)

        gesamt = self.summe("bewertete Maerkte")
        self.assertEqual(gesamt, 5)
        abgelehnt = (self.summe("Score unter 60")
                     + self.summe("Vola ueber 1.2")
                     + self.summe("Chance/Risiko unter 1.5"))
        self.assertEqual(abgelehnt + self.summe("kaufbar"), gesamt,
                         "ein Kandidat steht in zwei Zaehlern oder in keinem")

    def test_erster_greifender_grund_gewinnt(self):
        """Ein Markt, der mehrere Tore reisst, zaehlt trotzdem einmal."""
        werte = [_markt("X-USDT", score=10.0, vola=5.0, verh=0.1)]
        h.vorschlaege({"werte": werte}, WACHEN)
        self.assertEqual(self.summe("bewertete Maerkte"), 1)
        self.assertEqual(self.summe("Score unter 60"), 1)
        self.assertEqual(self.summe("Vola ueber 1.2"), 0)
        self.assertEqual(self.summe("Chance/Risiko unter 1.5"), 0)


class KapazitaetTest(Basis):
    """Regel: Kapazitaet ist kein Tor - und zaehlt Zyklen, nicht Kandidaten."""

    def test_volles_buch_zaehlt_nicht_als_ablehnung(self):
        z = {"positionen": [{"inst": "P%d" % i, "usd": 50.0}
                            for i in range(WACHEN["max_offene_positionen"])],
             "letzte_stops": {}}
        vs = [{"inst": "A-USDT", "score": 70.0, "einstieg": 100.0,
               "stop": 95.0, "stop_pct": 5.0, "ziel": 110.0, "usd": 100}
              for _ in range(3)]
        h.pruefe_einstiege(z, vs, WACHEN, False)

        self.assertEqual(self.summe("Buch voll"), 1, "zaehlt EINEN Zyklus")
        self.assertEqual(self.summe("nicht mehr erreicht"), 3)
        self.assertEqual(self.summe("bewertet"), 0)

    def test_kontrollzeile_geht_auf(self):
        """kaufbar == bewertet + nicht mehr erreicht."""
        z = {"positionen": [{"inst": "P%d" % i, "usd": 10.0}
                            for i in range(5)],
             "letzte_stops": {}}
        vs = [{"inst": "M%d-USDT" % i, "score": 70.0, "einstieg": 100.0,
               "stop": 95.0, "stop_pct": 5.0, "ziel": 110.0, "usd": 10}
              for i in range(4)]
        h.protokolliere("kaufbar", len(vs))
        h.pruefe_einstiege(z, vs, WACHEN, False)

        kaufbar = self.summe("kaufbar")
        bewertet = self.summe("bewertet")
        nicht = self.summe("nicht mehr erreicht")
        self.assertEqual(kaufbar, bewertet + nicht,
                         "Kontrollzeile geht nicht auf: %d != %d + %d"
                         % (kaufbar, bewertet, nicht))

    def test_kapazitaet_ist_aus_der_kandidatensumme_ausgenommen(self):
        for g in ("Buch voll", "Gesamtdeckel erreicht", "nicht mehr erreicht",
                  "bewertet", "kaufbar", "bewertete Maerkte"):
            self.assertIn(g, h.KAPAZITAET)


class KandidatTest(Basis):
    def test_schon_gehaltener_wert_wird_einzeln_vermerkt(self):
        z = {"positionen": [{"inst": "A-USDT", "usd": 100.0}],
             "letzte_stops": {}}
        vs = [{"inst": "A-USDT", "score": 70.0, "einstieg": 100.0,
               "stop": 95.0, "stop_pct": 5.0, "ziel": 110.0, "usd": 100}]
        h.pruefe_einstiege(z, vs, WACHEN, False)
        treffer = [x for x in self.zeilen()
                   if x["art"] == "kandidat" and x["inst"] == "A-USDT"]
        self.assertEqual(len(treffer), 1)
        self.assertEqual(treffer[0]["grund"], "schon im Buch")

    def test_doppelzaehl_sperre_greift(self):
        """Derselbe Kandidat, zwei Zyklen am selben Tag - eine Zeile."""
        z = {"positionen": [{"inst": "A-USDT", "usd": 100.0}],
             "letzte_stops": {}}
        vs = [{"inst": "A-USDT", "score": 70.0, "einstieg": 100.0,
               "stop": 95.0, "stop_pct": 5.0, "ziel": 110.0, "usd": 100}]
        h.pruefe_einstiege(z, vs, WACHEN, False)
        h.pruefe_einstiege(z, vs, WACHEN, False)
        h.pruefe_einstiege(z, vs, WACHEN, False)

        treffer = [x for x in self.zeilen()
                   if x["art"] == "kandidat" and x["inst"] == "A-USDT"]
        self.assertEqual(len(treffer), 1,
                         "ohne Sperre zaehlte ein gehaltener Wert 96x am Tag")


class BilligeToreTest(Basis):
    """Regel: ein billiges Tor kostet keinen Netzabruf.

    Seit 03.10.2026 fragt vorschlaege() fuer jeden KAUFBAREN Kandidaten
    den Marktpreis (das war der Fehler vom 19.09.: Einstieg aus dem
    Vortagesbericht, Ziel damit schon erfuellt). Ein Kandidat, der an
    Score, Volatilitaet oder Chance/Risiko scheitert, darf weiterhin
    keinen einzigen Abruf kosten - die Tore muessen billig bleiben,
    sonst waere der ganze Markt (500+ Paare) teuer."""

    def test_gescheiterte_tore_rufen_keinen_kurs(self):
        h.vorschlaege({"werte": [_markt("A-USDT", score=10.0),
                                 _markt("B-USDT", score=70.0, vola=9.0),
                                 _markt("C-USDT", score=70.0, verh=0.5)]},
                      WACHEN)
        self.assertEqual(self.kursabrufe, [],
                         "ein gescheitertes Tor darf keinen Kurs holen")

    def test_nur_kaufbare_kandidaten_fragen_den_markt(self):
        vs = h.vorschlaege({"werte": [_markt("A-USDT", score=10.0),
                                      _markt("B-USDT")]}, WACHEN)
        self.assertEqual(self.kursabrufe, ["B-USDT"])
        self.assertEqual(len(vs), 1)
        self.assertAlmostEqual(vs[0]["einstieg"], self.marktpreis, places=6)

    def test_kein_kurs_ablehnt_statt_zu_raten(self):
        h.marktkurs = lambda inst: None
        vs = h.vorschlaege({"werte": [_markt("B-USDT")]}, WACHEN)
        self.assertEqual(vs, [])
        self.assertEqual(self.summe("Kurs nicht abrufbar"), 1)


class VorschauTest(Basis):
    """Regel: eine Vorschau, die schreibt, ist keine Vorschau."""

    def test_vorschau_schreibt_keine_ablehnungszeile(self):
        h.SCHREIBEN = False
        h.vorschlaege({"werte": [_markt("A-USDT", score=10.0)]}, WACHEN)
        h.protokolliere("irgendwas", 5)
        h.protokolliere_kandidat("B-USDT", "Abklingzeit nach Stop")
        self.assertFalse(h.ABLEHNUNGEN.exists(),
                         "die Vorschau hat das Protokoll angelegt")


class LeserTest(Basis):
    def test_leeres_protokoll_meldet_sauber(self):
        zeilen = h.lies_ablehnungen()
        self.assertTrue(any("Noch kein" in z for z in zeilen))

    def test_kontrollzeile_erscheint(self):
        h.protokolliere("kaufbar", 5)
        h.protokolliere("bewertet", 3)
        h.protokolliere("nicht mehr erreicht", 2)
        zeilen = h.lies_ablehnungen()
        text = "\n".join(zeilen)
        self.assertIn("Kontrolle: kaufbar 5 = bewertet 3 + nicht mehr erreicht 2",
                      text)
        self.assertNotIn("ACHTUNG", text)

    def test_schieflage_wird_gemeldet(self):
        h.protokolliere("kaufbar", 9)
        h.protokolliere("bewertet", 3)
        h.protokolliere("nicht mehr erreicht", 2)
        text = "\n".join(h.lies_ablehnungen())
        self.assertIn("ACHTUNG", text)

    def test_kapazitaet_steht_getrennt(self):
        h.protokolliere("Buch voll", 4)
        text = "\n".join(h.lies_ablehnungen())
        self.assertIn("Kapazitaet (ZYKLEN", text)


class SpiegelungTest(unittest.TestCase):
    def test_ablehnungen_gehen_ausser_haus(self):
        """Bedingung 4: faellt die Platte aus, fehlt sonst die Begruendung."""
        import inspect                                       # noqa: PLC0415
        quelle = inspect.getsource(h._spiegeln)
        self.assertIn("ABLEHNUNGEN", quelle)

    def test_spiegelstand_kennt_die_zusatzdatei(self):
        import importlib.util                                # noqa: PLC0415
        pfad = HIER.parent.parent / "spiegelstand.py"
        spec = importlib.util.spec_from_file_location("spiegelstand_t", pfad)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertIn("ablehnungen.csv", m.ZUSATZ.get("scanner", ()))


if __name__ == "__main__":
    unittest.main()
