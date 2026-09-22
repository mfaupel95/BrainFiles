"""Der Stop-Preis muss die Preisregeln des PAARES treffen.

Befund 22.09.2026 (Zyklus 42, Spur mosaic live auf Kraken):

    Stop fuer SOL-USDC fehlgeschlagen (Kraken meldet: EOrder:Invalid
    price:SOL/EUR price can only be specified up to 2 decimals.)
    - zurueckverkauft

mosaic hatte SOL gekauft, den Notausstieg nicht setzen koennen und die
Position daraufhin sofort zurueckverkauft: Spesen ohne Handel. Ursache war
nicht die Strategie, sondern kraken._add_order: es schrieb den rohen
Rechenwert (`str(preis)`) als Preis, und Kraken lehnt das ab. Der Fehler
trifft JEDES Paar mit wenigen Nachkommastellen (SOLEUR 2, XXBTZEUR 1) und
ist bei den vielen Stellen anderer Paare (AKEEUR 8) unsichtbar.

Kein Netz: kraken.paar_info wird ersetzt. Direkt ausfuehrbar:
    python tests/test_preis_gerundet.py
"""

import importlib.util
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))           # kraken/

import kraken as k                                        # noqa: E402

# pair_decimals der echten Paare, am 22.09.2026 aus /0/public/AssetPairs.
STELLEN = {"SOLEUR": 2, "XETHZEUR": 2, "XXBTZEUR": 1, "AKEEUR": 8, "KASEUR": 5}


class PreisGerundetTest(unittest.TestCase):

    def setUp(self):
        self.orig = k.paar_info
        k.paar_info = lambda paar: {"name": paar, "preis_stellen": STELLEN.get(paar, 2),
                                    "mengen_stellen": 8, "mindestmenge": 0.0,
                                    "mindestwert": 0.0}

    def tearDown(self):
        k.paar_info = self.orig

    def test_soleur_aufrunden(self):
        # Der gemeldete Fall: SOL/EUR mit zwei Stellen.
        self.assertEqual(k.preis_gerundet("SOLEUR", 128.5678), "128.57")

    def test_soleur_abrunden(self):
        self.assertEqual(k.preis_gerundet("SOLEUR", 128.5678, "ab"), "128.56")

    def test_bitcoin_eine_stelle(self):
        self.assertEqual(k.preis_gerundet("XXBTZEUR", 91234.567), "91234.6")

    def test_paar_mit_vielen_stellen_bleibt_genau(self):
        # Hier war der Fehler unsichtbar - trotzdem muss es exakt bleiben.
        self.assertEqual(k.preis_gerundet("AKEEUR", 0.001234567891),
                         "0.00123457")

    def test_schon_gerundeter_preis_bekommt_die_stellen(self):
        self.assertEqual(k.preis_gerundet("SOLEUR", 128.5), "128.50")

    def test_float_rauschen_kippt_nicht(self):
        # 128.995 * 100 ist binaer 12899.499999999998.
        self.assertEqual(k.preis_gerundet("SOLEUR", 128.995), "129.00")

    def test_kleiner_preis_nie_in_exponentialschreibweise(self):
        p = k.preis_gerundet("AKEEUR", 0.0000000041)
        self.assertNotIn("e", p.lower())

    def test_unbekannte_richtung_ist_ein_fehler(self):
        with self.assertRaises(ValueError):
            k.preis_gerundet("SOLEUR", 100.0, "schraeg")

    def test_ohne_preisregeln_kein_raten(self):
        # Attrappen (Tests) liefern kein preis_stellen: roh weitergeben,
        # statt eine Stellenzahl zu erfinden.
        k.paar_info = lambda paar: {"mengen_stellen": 8}
        self.assertEqual(k.preis_gerundet("SOLEUR", 128.5678), "128.5678")


class StopGehtGerundetRausTest(unittest.TestCase):
    """stop_setzen gibt den gerundeten Preis an _add_order weiter.

    Ohne diesen Test waere preis_gerundet nur eine nette Funktion, die
    niemand aufruft."""

    def setUp(self):
        self.orig_info = k.paar_info
        self.orig_add = k._add_order
        k.paar_info = lambda paar: {"name": paar, "preis_stellen": 2,
                                    "mengen_stellen": 8, "mindestmenge": 0.0,
                                    "mindestwert": 0.0}
        self.rufe = []

        def attrappe(paar, seite, menge, ordertyp="market", preis=None,
                     echt=False):
            self.rufe.append({"paar": paar, "seite": seite, "menge": menge,
                              "ordertyp": ordertyp, "preis": preis, "echt": echt})
            return "tx-1"

        k._add_order = attrappe

    def tearDown(self):
        k.paar_info = self.orig_info
        k._add_order = self.orig_add

    def test_stop_preis_hat_zwei_stellen(self):
        k.stop_setzen("SOLEUR", 0.7, 128.5678, echt=True)
        self.assertEqual(len(self.rufe), 1)
        r = self.rufe[0]
        self.assertEqual(r["ordertyp"], "stop-loss")
        self.assertEqual(r["seite"], "sell")
        self.assertEqual(r["preis"], "128.57")
        self.assertEqual(r["preis"].split(".")[1], "57")

    def test_stop_ist_nie_tiefer_als_gerechnet(self):
        for roh in (128.5678, 128.9901, 99.999, 1.005):
            gerundet = float(k.preis_gerundet("SOLEUR", roh))
            self.assertGreaterEqual(gerundet, roh, "Stop %s < %s" % (gerundet, roh))


if __name__ == "__main__":
    unittest.main(verbosity=2)
