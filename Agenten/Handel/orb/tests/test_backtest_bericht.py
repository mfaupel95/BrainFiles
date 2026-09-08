import unittest

import backtest

INST = {"eroeffnung": "09:00", "zone": "Europe/Berlin", "cash_close": "17:30"}


def _erg(gv, ausgang, mehrdeutig=False, tag="2025-01-15"):
    from datetime import date
    y, m, d = (int(x) for x in tag.split("-"))
    return {"tag": date(y, m, d), "inst": "X", "richtung": "long",
            "einstieg": 100.0, "stop": 90.0, "ziel": 120.0, "ausgang": ausgang,
            "ausstieg": 100.0 + gv, "range_punkte": 10.0,
            "mehrdeutig": mehrdeutig, "gv_punkte": gv}


class TestKosten(unittest.TestCase):
    def test_ein_spread_plus_slippage_je_runde(self):
        e = _erg(10.0, "ziel")
        self.assertAlmostEqual(backtest.mit_kosten(e, spread_punkte=1.2, slippage_punkte=0.5),
                               10.0 - 1.2 - 0.5)


class TestBericht(unittest.TestCase):
    def test_kennzahlen_und_urteil(self):
        # 7 Gewinner a +9.0 Netto, 3 Verlierer a -10.2 Netto (nach Kosten)
        erg = [_erg(9.7, "ziel") for _ in range(7)] + [_erg(-9.5, "stop") for _ in range(3)]
        b = backtest.bericht(erg, INST, spread_punkte=0.2, kursreihe=[100, 101, 99, 105])
        self.assertEqual(b["verlierer"], 3)
        self.assertTrue(b["verlierer_warnung"])           # >= 10? nein -> Warnung an
        self.assertAlmostEqual(b["trefferquote"], 0.7, places=2)
        self.assertGreater(b["ev_je_runde"], 0)
        self.assertIn("81", b["urteil"])
        self.assertIsInstance(b["haelt_81"], bool)

    def test_warnung_bei_unter_10_verlierern(self):
        erg = [_erg(9.0, "ziel") for _ in range(30)] + [_erg(-9.0, "stop") for _ in range(4)]
        b = backtest.bericht(erg, INST, spread_punkte=0.2, kursreihe=[100, 110])
        self.assertTrue(b["verlierer_warnung"])           # 4 < 10

    def test_negatives_quartal_zieht_urteil_auf_nein(self):
        gut = [_erg(9.0, "ziel", tag="2025-01-%02d" % (d + 1)) for d in range(20)]
        schlecht = [_erg(-30.0, "stop", tag="2025-04-%02d" % (d + 1)) for d in range(12)]
        b = backtest.bericht(gut + schlecht, INST, spread_punkte=0.2, kursreihe=[100, 105])
        self.assertFalse(b["haelt_81"])
        self.assertIn("Nein", b["urteil"])


if __name__ == "__main__":
    unittest.main()
