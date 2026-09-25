"""Buchbereinigung der Kraken-Spur: Papier-Altlasten blockieren kein Live.

Anlass 25.09.2026 (gemessen): Vier Papier-Positionen belegten alle vier
Plaetze. Die Spur ist armiert (handel_erlaubt=true, freigabe.erfuellt=true) -
jeder Live-Zyklus lief aber in "Buch voll", eine echte Order kam nie zustande.

Hier steht die REGEL, nicht der Tagesstand: eine Position ohne modus=live
wird ausgebucht, eine echte (modus=live) bleibt stehen, und der Live-Lauf
raeumt VOR dem Sammeln der Quoten auf (sonst wirkt die Bereinigung erst einen
Zyklus spaeter).
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import handeln as h                                                  # noqa: E402


def _wachen():
    return h.lade_wachen()


class BuchbereinigungTest(unittest.TestCase):

    def setUp(self):
        # NUR fuer diese Klasse abschalten: ein Modul-weites SCHREIBEN=False
        # legt die Journale der NACHBAR-Testmodule still, wenn die Suite mit
        # discover laeuft (25.09.2026 erlebt: test_papier_laesst_live_stehen
        # fand danach keine Zeile mehr).
        self.schreiben = h.SCHREIBEN
        h.SCHREIBEN = False
        self.w = _wachen()
        self.echt_kurs = h.kraken_rest.letzter_kurs
        h.kraken_rest.letzter_kurs = lambda paar: 70000.0

    def tearDown(self):
        h.SCHREIBEN = self.schreiben
        h.kraken_rest.letzter_kurs = self.echt_kurs

    def _papier(self, symbol="KOP:A", einsatz=50.0):
        return {"kette": "kraken", "token": "BTC/EUR", "symbol": symbol,
                "menge": einsatz / 70000.0, "preis_einstieg": 70000.0,
                "letzter_kurs": 70000.0, "einsatz_eur": einsatz,
                "modus": "papier"}

    def _live(self):
        p = self._papier("KOP:LIVE")
        p["modus"] = "live"
        p["txid"] = "OXXXXX-YYYYY-ZZZZZZ"
        return p

    def test_papier_wird_ausgebucht_live_bleibt(self):
        z = {"positionen": [self._papier(), self._live()]}
        n = h.bueche_papier_altlasten_aus(z, self.w)
        self.assertEqual(n, 1)
        self.assertEqual([p["modus"] for p in z["positionen"]], ["live"])

    def test_ohne_modus_gilt_als_papier(self):
        """Altbestand ohne Stempel hat nie eine Order gehabt."""
        p = self._papier()
        del p["modus"]
        z = {"positionen": [p]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w), 1)
        self.assertEqual(z["positionen"], [])

    def test_leeres_buch_ist_kein_fehler(self):
        self.assertEqual(h.bueche_papier_altlasten_aus({"positionen": []},
                                                      self.w), 0)

    def test_idempotent(self):
        z = {"positionen": [self._papier()]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w), 1)
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w), 0)

    def test_ohne_kurs_bleibt_die_position_stehen(self):
        """Lieber ein belegter Platz als eine Buchung ohne Kurs."""
        h.kraken_rest.letzter_kurs = lambda paar: None
        p = self._papier()
        p["letzter_kurs"] = None
        z = {"positionen": [p]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_rueckfall_auf_letzten_kurs(self):
        h.kraken_rest.letzter_kurs = lambda paar: None
        p = self._papier()
        p["letzter_kurs"] = 71000.0
        z = {"positionen": [p]}
        self.assertEqual(h.bueche_papier_altlasten_aus(z, self.w), 1)


class LiveLaufRaeumtVorDemSammelnTest(unittest.TestCase):
    """Die Bereinigung muss VOR sammle_quoten stehen - die Platzzahl wird
    dort geprueft. Dahinter waere sie wirkungslos fuer diesen Zyklus."""

    def test_quelle(self):
        quelle = open(os.path.join(HIER, "handeln.py"), encoding="utf-8").read()
        aufraeumen = quelle.index("bueche_papier_altlasten_aus(z, w)")
        sammeln = quelle.index("quotes, positionen, buchungen = sammle_quoten(")
        self.assertLess(aufraeumen, sammeln)

    def test_nur_im_live_lauf(self):
        quelle = open(os.path.join(HIER, "handeln.py"), encoding="utf-8").read()
        stelle = quelle.index("n_alt = bueche_papier_altlasten_aus(z, w)")
        davor = quelle[stelle - 300:stelle]
        # Der Aufruf steht in einem live_vorab-Zweig - sonst raeumte auch der
        # Papierlauf das Buch um, in dem er selbst lebt.
        self.assertIn("if live_vorab:", davor)
        self.assertIn("live_vorab = not sperren", quelle)


class LiveLaufEndeZuEndeTest(unittest.TestCase):
    """Der Live-Lauf selbst: er bucht die Papier-Altlast aus, VOR dem Sammeln.

    Gefahren wird `lauf("live")` mit Attrappen - kein Netz, keine Order, keine
    Datei ausserhalb des Temp-Ordners (Lehre 16.09.2026: ein Test darf nie in
    einen echten Zielpfad schreiben).
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nk_altlast_")
        self.echt = (h.ZUSTAND, h.JOURNAL, h.SCHREIBEN, h.schreibe_zustand,
                     h.spiegle_journal, h.vermerke_spiegelung, h.sperren_zeile,
                     h.sammle_quoten, h.lies_kopier_signale,
                     h.kraken_rest.letzter_kurs)
        h.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        h.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        h.SCHREIBEN = True
        self.papier = {"kette": "kraken", "token": "BTC/EUR",
                       "symbol": "KOP:A", "menge": 50.0 / 70000.0,
                       "preis_einstieg": 70000.0, "letzter_kurs": 70000.0,
                       "einsatz_eur": 50.0, "modus": "papier",
                       "frist": "2099-01-01T00:00:00+00:00"}
        self.live = dict(self.papier, symbol="KOP:LIVE", modus="live",
                         txid="OXXXXX-YYYYY-ZZZZZZ")
        with open(h.ZUSTAND, "w", encoding="utf-8") as f:
            json.dump({"positionen": [self.papier, self.live]}, f)
        h.schreibe_zustand = self._schreibe
        h.spiegle_journal = lambda ziel, dateien=None: (True, "temp")
        h.vermerke_spiegelung = lambda *a, **k: False
        h.sperren_zeile = lambda w: None            # Live ist erlaubt
        h.lies_kopier_signale = lambda seit: []
        h.kraken_rest.letzter_kurs = lambda paar: 70000.0
        self.gesammelt = []

        def _sammle(**k):
            # Merkt, WELCHE Positionen der Strategie angeboten werden - genau
            # hier entscheidet die Platzzahl.
            self.gesammelt.append([p.get("modus") for p in k["positionen"]])
            return [], k["positionen"], []

        h.sammle_quoten = _sammle

    def _schreibe(self, z):
        with open(h.ZUSTAND, "w", encoding="utf-8") as f:
            json.dump(z, f, ensure_ascii=False)

    def tearDown(self):
        (h.ZUSTAND, h.JOURNAL, h.SCHREIBEN, h.schreibe_zustand,
         h.spiegle_journal, h.vermerke_spiegelung, h.sperren_zeile,
         h.sammle_quoten, h.lies_kopier_signale,
         h.kraken_rest.letzter_kurs) = self.echt
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_live_lauf_sieht_nur_noch_die_echte_position(self):
        h.lauf("live")
        # Was der Strategie angeboten wurde: kein Papier mehr.
        self.assertTrue(self.gesammelt, "sammle_quoten wurde nicht gerufen")
        for modi in self.gesammelt:
            self.assertEqual(modi, ["live"])
        # Und im geschriebenen Zustand steht nur die echte Position.
        with open(h.ZUSTAND, encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual([p["modus"] for p in z["positionen"]], ["live"])
        # Die Buchung ist im Journal, mit dem Hausgrund.
        with open(h.JOURNAL, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("buchbereinigung", text)
        self.assertIn("KOP:A", text)


if __name__ == "__main__":
    unittest.main()