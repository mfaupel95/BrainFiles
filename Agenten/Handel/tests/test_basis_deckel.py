"""Der Basis-Deckel an seiner Regel, nicht an heutigen Zahlen.

Geprueft wird, was gelten soll:
  1. Fuenf Schreibweisen derselben Basis werden EINE behandelt - inklusive
     XBT, das Kraken BTC nennt. Ohne diese Zuordnung waere ein Deckel, den
     man mit einem anderen Namen umgeht (am 03.10.2026 sperrte der Deckel
     BTC-USDT-SWAP und liess XBT-USD durch).
  2. Der Deckel bindet NEUE Einstiege; bestehende Positionen laufen weiter.
  3. Eine Basis, die noch nicht im Buch ist, kann den Deckel nicht reissen.
  4. `ueber_dem_deckel` gibt (GESPERRT, grund) zurueck - die Polaritaet ist
     Teil des Vertrags und wurde in einer Fassung verkehrt gelesen.

Die Tests lesen den echten Rueckgabewert; die Variable heisst `gesperrt`,
weil der Wert `gesperrt` bedeutet.
"""
import json
import os
import sys
import tempfile
import unittest

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import basis_deckel
import basis_deckel_tor
import risiko_beitrag


def alt_basisform(s):
    """Die Fassung VOR der XBT-Zuordnung - fuer die Gegenprobe."""
    s = str(s or "?").upper().replace("-SWAP", "").replace("_UM_XPERP", "")
    for tr in ("-USDC", "-USDT", "-USD", "-EUR"):
        s = s.split(tr)[0]
    return s or "?"


class BasisTest(unittest.TestCase):
    def test_xbt_ist_btc(self):
        for inst in ("XBT-USD", "BTC-USDT-SWAP", "BTC-USDC", "BTC-USDT",
                     "BTC-USD_UM_XPERP-310704"):
            self.assertEqual(risiko_beitrag.basisform(inst), "BTC", inst)

    def test_gegenprobe_ohne_xbt_zuordnung(self):
        """So sah es vorher aus: zwei Basen, ein Deckel, ein Loch."""
        self.assertEqual(alt_basisform("XBT-USD"), "XBT")
        self.assertNotEqual(alt_basisform("XBT-USD"),
                            alt_basisform("BTC-USDT-SWAP"),
                            "genau deshalb waeren die beiden Basen fuer den "
                            "Deckel verschiedene - BTC-USDT-SWAP waere "
                            "gesperrt, XBT-USD nicht")


class DeckelTest(unittest.TestCase):
    def setUp(self):
        self.ord = tempfile.mkdtemp()
        self._alt = (risiko_beitrag.HANDEL, basis_deckel.HANDEL,
                     basis_deckel_tor.HANDEL)

    def tearDown(self):
        (risiko_beitrag.HANDEL, basis_deckel.HANDEL,
         basis_deckel_tor.HANDEL) = self._alt

    def buch(self, positionen):
        ordner = os.path.join(self.ord, "test")
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "zustand.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"positionen": positionen}, fh)
        with open(os.path.join(ordner, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"waehrung": "USD"}, fh)
        for m in (risiko_beitrag, basis_deckel, basis_deckel_tor):
            m.HANDEL = self.ord

    @staticmethod
    def pos(inst, nominal):
        return {"inst": inst, "seite": "long", "einstieg": 100.0,
                "stop": 95.0, "nominal": nominal}

    # 1 -------------------------------------------------------------
    def test_basis_ueber_dem_deckel_ist_gesperrt(self):
        # BTC 3000 von 3700 = 81 %
        self.buch([self.pos("BTC-USDT", 1000.0) for _ in range(3)]
                  + [self.pos("ETH-USDT", 700.0)])
        for inst in ("BTC-USDT", "BTC-USDT-SWAP", "XBT-USD",
                     "BTC-USD_UM_XPERP-310704"):
            gesperrt, grund = basis_deckel_tor.ueber_dem_deckel(inst)
            self.assertTrue(gesperrt, "%s muss gesperrt sein: %s" % (inst, grund))
        gesperrt, grund = basis_deckel_tor.ueber_dem_deckel("ETH-USDT")
        self.assertFalse(gesperrt, "ETH liegt unter dem Deckel")

    # 2 -------------------------------------------------------------
    def test_basis_unter_dem_deckel_bleibt_offen(self):
        # BTC 1000 von 6000 = 17 %
        self.buch([self.pos("BTC-USDT", 1000.0), self.pos("ETH-USDT", 5000.0)])
        gesperrt, grund = basis_deckel_tor.ueber_dem_deckel("BTC-USDT")
        self.assertFalse(gesperrt, grund)

    # 3 -------------------------------------------------------------
    def test_unbekannte_basis_ist_offen(self):
        self.buch([self.pos("BTC-USDT", 1000.0)])
        gesperrt, grund = basis_deckel_tor.ueber_dem_deckel("XYZ-USDT")
        self.assertFalse(gesperrt, "0 % von 0 % reisst keinen Deckel")

    # 4 -------------------------------------------------------------
    def test_grund_nennt_basis_grenze_und_laufendes(self):
        self.buch([self.pos("BTC-USDT", 1000.0) for _ in range(3)]
                  + [self.pos("ETH-USDT", 700.0)])
        _g, grund = basis_deckel_tor.ueber_dem_deckel("BTC-USDT")
        self.assertIn("BTC", grund)
        self.assertIn("20", grund)
        self.assertIn("bestehende", grund.lower(),
                      "der Grund muss sagen, dass Bestehendes weiterlaeuft")

    # 5 - die Grenze ist eine Zahl, keine Eigenschaft
    def test_grenze_ist_eine_zahl(self):
        self.assertIsInstance(basis_deckel.DECKEL_PROZENT, float)
        self.assertAlmostEqual(basis_deckel.DECKEL_PROZENT, 20.0, places=6,
                               msg="Auftrag Max: Basis deckel 20%")


if __name__ == "__main__":
    unittest.main()