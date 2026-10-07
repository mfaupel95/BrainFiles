"""TP3 Teil 1: Kandidatenraum und Grenzen.

basis_kandidat() baut die Kandidat-Form aus wachen.json plus den beiden
Gewichtskonstanten. nachbarn() erzeugt ausschliesslich bounded Nachbarn -
Gate-Schritte an den Grenzen aus spuren.json geklemmt, Gewichte +-0,05 mit
Renormierung der Gruppe, sizing-Alternativen, watchlist-Drops. Deckel
(max_*) sind nie im Suchraum. im_rahmen() ist der Gegencheck.
"""

import random
import sys
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import bewertung  # noqa: E402
import suche  # noqa: E402

WACHEN = {"mindest_score": 60, "max_volatilitaet_pa": 1.2,
          "mindest_chance_risiko": 1.5, "pflicht_stop_prozent_min": 4.0,
          "pflicht_stop_prozent_max": 12.0, "abklingzeit_tage": 3,
          "max_pro_trade_usd": 50, "max_gesamt_usd": 200,
          "max_offene_positionen": 4,
          "watchlist": ["BTC-USDT", "ETH-USDT", "SOL-USDT"]}
GRENZEN = {"mindest_score": [55, 75], "max_volatilitaet_pa": [0.9, 1.4],
           "mindest_chance_risiko": [1.3, 2.2], "stop_min": [4, 8],
           "stop_max": [8, 15], "abklingzeit_tage": [2, 5],
           "watchlist": "liste"}


class TestRaum(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_basis_ist_im_rahmen(self):
        self.assertTrue(suche.im_rahmen(self.basis, GRENZEN, self.basis))

    def test_nachbarn_bleiben_im_rahmen(self):
        rng = random.Random(0)
        k = self.basis
        for _ in range(400):
            nb = suche.nachbarn(k, GRENZEN)
            self.assertTrue(nb)
            k = rng.choice(nb)
            self.assertTrue(suche.im_rahmen(k, GRENZEN, self.basis),
                            msg=repr(k))

    def test_gewichtsgruppen_summieren_auf_eins(self):
        for nb in suche.nachbarn(self.basis, GRENZEN):
            for gruppe in ("chance", "risiko"):
                self.assertAlmostEqual(
                    sum(nb["gewichte"][gruppe].values()), 1.0, 9)

    def test_gate_nachbarn_ohne_gleitkomma_rauschen(self):
        # 1.2 + 0.1 darf nicht als 1.3000000000000003 in einen Nachbarn (und
        # damit spaeter per repr in wachen.json) wandern.
        for nb in suche.nachbarn(self.basis, GRENZEN):
            for gate in ("max_volatilitaet_pa", "mindest_chance_risiko",
                         "mindest_score"):
                wert = nb["gates"][gate]
                self.assertEqual(wert, round(wert, 4),
                                 msg="%s: %r" % (gate, wert))

    def test_deckel_nie_veraendert(self):
        for nb in suche.nachbarn(self.basis, GRENZEN):
            for feld in ("max_pro_trade_usd", "max_gesamt_usd",
                         "max_offene_positionen"):
                self.assertEqual(nb["gates"][feld], self.basis["gates"][feld])

    def test_denylist_vollstaendig(self):
        for feld in ("handel_erlaubt", "freigabe", "kill_switch_gesamt_usd",
                     "herzschlag_max_minuten", "journal_zweitziel",
                     "max_pro_trade_usd", "max_gesamt_usd",
                     "max_offene_positionen", "drawdown_halbierung_prozent"):
            self.assertIn(feld, suche.DENYLIST)


class TestGewichteSchalter(unittest.TestCase):
    def setUp(self):
        self.basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)

    def test_gewichte_durchsuchbar_false_erzeugt_keine_gewichts_nachbarn(self):
        nb = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=False)
        for kandidat in nb:
            self.assertEqual(kandidat["gewichte"], self.basis["gewichte"])

    def test_gewichte_durchsuchbar_false_laesst_andere_nachbarn_unberuehrt(self):
        mit = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=True)
        ohne = suche.nachbarn(self.basis, GRENZEN, gewichte_durchsuchbar=False)
        # Gate-/Sizing-/Watchlist-Nachbarn sind identisch; nur die
        # Gewichts-Nachbarn fehlen bei ohne.
        gates_mit = [n["gates"] for n in mit if n["gewichte"] == self.basis["gewichte"]]
        self.assertEqual(gates_mit, [n["gates"] for n in ohne])

    def test_default_ist_true_bestandsverhalten(self):
        self.assertEqual(suche.nachbarn(self.basis, GRENZEN),
                         suche.nachbarn(self.basis, GRENZEN,
                                        gewichte_durchsuchbar=True))


class TestDeckelMapping(unittest.TestCase):
    def test_default_liest_usd_feldnamen(self):
        basis = suche.basis_kandidat(
            WACHEN, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE)
        self.assertEqual(basis["gates"]["max_pro_trade_usd"], 50)
        self.assertEqual(basis["gates"]["max_gesamt_usd"], 200)

    def test_eur_mapping_liest_eur_feldnamen_in_dieselben_gate_schluessel(self):
        wachen_eur = {**WACHEN, "max_pro_trade_eur": 50, "max_gesamt_eur": 200}
        del wachen_eur["max_pro_trade_usd"], wachen_eur["max_gesamt_usd"]
        basis = suche.basis_kandidat(
            wachen_eur, bewertung.CHANCE_GEWICHTE, bewertung.RISIKO_GEWICHTE,
            deckel_felder={"max_pro_trade_usd": "max_pro_trade_eur",
                           "max_gesamt_usd": "max_gesamt_eur"})
        # candidate-interner Schluessel bleibt "_usd", Wert kommt aus "_eur".
        self.assertEqual(basis["gates"]["max_pro_trade_usd"], 50)
        self.assertEqual(basis["gates"]["max_gesamt_usd"], 200)


class TestDenylistEurErweiterung(unittest.TestCase):
    def test_eur_deckel_in_denylist(self):
        for feld in ("max_pro_trade_eur", "max_gesamt_eur",
                     "drawdown_halbierung_usd", "kill_switch_gesamt_eur"):
            self.assertIn(feld, suche.DENYLIST)


if __name__ == "__main__":
    unittest.main()
