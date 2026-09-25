"""Buchbereinigung der Kraken-Spur: Papier-Altlasten blockieren kein Live.

Anlass 25.09.2026 (gemessen): Vier Papier-Positionen belegten alle vier
Plaetze. Die Spur ist armiert (handel_erlaubt=true, freigabe.erfuellt=true) -
jeder Live-Zyklus lief aber in "Buch voll", eine echte Order kam nie zustande.

Hier steht die REGEL, nicht der Tagesstand: eine Position ohne modus=live
wird ausgebucht, eine echte (modus=live) bleibt stehen, und der Live-Lauf
raeumt VOR dem Sammeln der Quoten auf (sonst wirkt die Bereinigung erst einen
Zyklus spaeter).
"""

import os
import sys
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


if __name__ == "__main__":
    unittest.main()