"""Der Live-Einsatz wird auf das FREIE Guthaben gedeckelt (25.09.2026).

ANLASS: Auftrag Max "Moondev_listingarb mindestguthaben senken" (50 -> 5 USDC).
Beim Nachrechnen fiel auf, dass `mindest_guthaben` nur eine Schwelle ist
("darf ich ueberhaupt anfangen") und NICHT sagt, ob der GEPLANTE Betrag
bezahlbar ist: listingarb rechnet 5 USD Risiko / 7 % Stop = 71,43 Nominale,
die Live-Grenze kappt auf 50 - bei 5 USDC im Konto waere die Order an der
Boerse gescheitert (OKX: insufficient balance), und zwar erst NACH dem
Kaufversuch. Zwei Folgen, beide hier festgenagelt:

  1. Der Einsatz wird auf `frei * (1 - Gebuehr - Puffer)` gedeckelt,
     vor der Order.
  2. Das BUCH fuehrt den GEDECKELTEN Betrag, nicht die Wunschnominale -
     sonst rechnet jeder Ausstieg den G/V auf einen Einsatz, den es nicht gab.

Kein Netz, keine Boerse: der Orderweg ist eine Attrappe.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
sys.path.insert(0, str(HANDEL))

import spur_buch as buch                                          # noqa: E402


class Attrappe:
    """Orderweg-Attrappe mit einstellbarem Guthaben."""

    def __init__(self, frei=500.0, kauf_ok=True, guthaben_fehler=None):
        self.aufrufe = []
        self.frei = frei
        self.kauf_ok = kauf_ok
        self.guthaben_fehler = guthaben_fehler
        self.gefragt_nach = []

    def schluessel_vorhanden(self):
        return True

    def demo_modus(self):
        return False

    def guthaben_waehrung(self, ccy="USDC"):
        self.gefragt_nach.append(ccy)
        if self.guthaben_fehler:
            raise RuntimeError(self.guthaben_fehler)
        return self.frei

    def letzter_kurs(self, inst):
        return 100.0

    def menge_fuer(self, inst, betrag, kurs):
        self.aufrufe.append(("menge", inst, round(betrag, 4)))
        return round(betrag / kurs, 6), None

    def markt_kauf(self, inst, menge):
        self.aufrufe.append(("kauf", inst, menge))
        return "ORD-1" if self.kauf_ok else None

    def markt_verkauf(self, inst, menge):
        self.aufrufe.append(("verkauf", inst, menge))
        return "ORD-2"

    def algo_stop_setzen(self, inst, menge, seite, trigger):
        self.aufrufe.append(("stop", inst, round(trigger, 4)))
        return "STOP-1"


# Risiko 5 USD, Stop 7 % -> Nominale 71,43; Live-Grenze 50. Genau die Lage
# von moondev_listingarb.
W = {"risiko_je_position_usd": 5.0, "max_pro_trade_usd": 100.0,
     "live_max_pro_trade_usd": 50.0, "stop_prozent": 7.0,
     "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
     "ziel_r_vielfaches": 2.0, "max_offene_positionen": 3,
     "guthaben_waehrung": "USDC"}


def lauf(weg, w=None, inst="ABC-USDC", kurs=100.0):
    z = {"positionen": []}
    p = buch.einstieg(z, inst, "long", kurs, w or dict(W), 1.0, "test",
                      live=True, weg=weg)
    return z, p


class DeckelTest(unittest.TestCase):

    def test_deckelt_auf_freies_guthaben(self):
        """5 USDC frei -> 5 * (1 - 0,6 % - 0,2 %) = 4,96 USD Einsatz."""
        weg = Attrappe(frei=5.0)
        z, p = lauf(weg)
        self.assertIsNotNone(p, "ein kleiner Einsatz ist besser als keine Order")
        self.assertAlmostEqual(p["nominal"], 5.0 * (1 - 0.006 - 0.002), places=6)
        self.assertAlmostEqual(weg.aufrufe[1][2], 0.0496, places=4)  # kauf-Menge
        self.assertEqual(z["positionen"][0]["menge"], 0.0496)

    def test_gebuehr_kommt_aus_der_wachen(self):
        """OKX-Spot (0,1 %) deckelt weniger als der Standardfall (0,6 %)."""
        w = dict(W, gebuehr_taker=0.001)
        _, p_okx = lauf(Attrappe(frei=5.0), w)
        _, p_std = lauf(Attrappe(frei=5.0))
        self.assertAlmostEqual(p_okx["nominal"], 5.0 * (1 - 0.001 - 0.002), places=6)
        self.assertGreater(p_okx["nominal"], p_std["nominal"])

    def test_buch_fuehrt_den_wirklich_georderten_betrag(self):
        """Der Kern des Befunds: die Live-Grenze kappt 71,43 auf 50 - und genau
        50 muss im Buch stehen (sonst rechnet der Ausstieg den G/V auf einen
        Einsatz, den es nie gab)."""
        weg = Attrappe(frei=500.0)
        z, p = lauf(weg)
        self.assertAlmostEqual(p["nominal"], 50.0, places=6)
        self.assertAlmostEqual(z["positionen"][0]["nominal"], 50.0, places=6)
        self.assertLess(p["nominal"], 5.0 / 0.07,
                        "die Risikonormale wird nicht mehr behauptet")
        self.assertAlmostEqual(p["menge"] * p["einstieg"], p["nominal"], places=4)

    def test_guthaben_deckt_den_geplanten_einsatz_nicht_ganz(self):
        """30 USDC frei, geplant sind 50 -> gedeckelt, aber geordert."""
        weg = Attrappe(frei=30.0)
        z, p = lauf(weg)
        self.assertIsNotNone(p)
        self.assertAlmostEqual(p["nominal"], 30.0 * 0.992, places=6)
        self.assertIn(("kauf", "ABC-USDC", round(30.0 * 0.992 / 100.0, 6)),
                      weg.aufrufe)

    def test_kein_guthaben_keine_order(self):
        weg = Attrappe(frei=0.0)
        z, p = lauf(weg)
        self.assertIsNone(p)
        self.assertEqual(z["positionen"], [])
        self.assertEqual([a for a in weg.aufrufe if a[0] == "kauf"], [],
                         "ohne Geld wird gar nicht erst geordert")

    def test_guthaben_nicht_abrufbar_keine_order(self):
        weg = Attrappe(guthaben_fehler="EAPI:Invalid nonce")
        z, p = lauf(weg)
        self.assertIsNone(p, "ohne Guthabenzahl wird nicht blind gekauft")
        self.assertEqual(weg.aufrufe, [])

    def test_fragt_die_waehrung_der_wachen(self):
        weg = Attrappe(frei=50.0)
        lauf(weg, dict(W, guthaben_waehrung="EUR"))
        self.assertIn("EUR", weg.gefragt_nach)

    def test_stop_haengt_am_gedeckelten_einsatz_nicht_an_der_groesse(self):
        """Ein kleinerer Einsatz senkt die GROESSE, nicht den Schutz: der Stop
        bleibt bei 7 % unter dem Boersenkurs."""
        weg = Attrappe(frei=5.0)
        _, p = lauf(weg)
        self.assertAlmostEqual(p["stop"], 93.0, places=4)
        self.assertAlmostEqual(p["stop_pct"], 7.0, places=4)


class PapierUnberuehrtTest(unittest.TestCase):

    def test_papier_kennt_keinen_guthaben_deckel(self):
        weg = Attrappe(frei=0.0)
        z = {"positionen": []}
        p = buch.einstieg(z, "ABC-USDC", "long", 100.0, dict(W), 1.0, "t", weg=weg)
        self.assertEqual(p["modus"], "papier")
        self.assertAlmostEqual(p["nominal"], 5.0 / 0.07, places=4)
        self.assertEqual(weg.aufrufe, [], "Papier geht nie an die Boerse")

    def test_papier_fragt_kein_guthaben_ab(self):
        weg = Attrappe(frei=0.0, guthaben_fehler="darf nicht gefragt werden")
        z = {"positionen": []}
        p = buch.einstieg(z, "ABC-USDC", "long", 100.0, dict(W), 1.0, "t", weg=weg)
        self.assertIsNotNone(p)


class RechnungTest(unittest.TestCase):
    """Die Formel selbst - ohne Buch, damit ein Fehler dort auffaellt."""

    def test_formel(self):
        weg = Attrappe(frei=100.0)
        self.assertAlmostEqual(buch.einsatz_gedeckelt(weg, {}, 500.0), 99.2,
                               places=6)

    def test_kein_deckel_bei_kleinem_wunsch(self):
        weg = Attrappe(frei=100.0)
        self.assertAlmostEqual(buch.einsatz_gedeckelt(weg, {}, 10.0), 10.0,
                               places=6)

    def test_gebuehr_ueber_eins(self):
        """Unsinnige Gebuehr darf den Einsatz nicht negativ machen."""
        weg = Attrappe(frei=100.0)
        self.assertEqual(buch.einsatz_gedeckelt(weg, {"gebuehr_taker": 2.0}, 10.0),
                         0.0)


if __name__ == "__main__":
    unittest.main()