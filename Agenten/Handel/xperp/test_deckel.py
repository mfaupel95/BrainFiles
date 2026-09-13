"""Hebel-Deckel auf Tageskerzen - Regression fuer den Messfehler vom 01.09.2026.

auswahl.py leitete den Deckel aus 300 4H-Kerzen ab (= 50 Tage); SOLs
Ruecklauf vom 31.05.2026 lag ausserhalb dieses Fensters (9,5 % statt
27,9 %, Deckel 10x statt 3,5x). Der Deckel muss aus der 1D-Reihe kommen
(auswahl.mae_tage) - Test-Seam: bot.tages_kerzen_quelle.
"""

import unittest

import bot


def tages_kerzen(kurse):
    return [(i, p, p, p, p, 1.0) for i, p in enumerate(kurse)]


class DeckelTagesTest(unittest.TestCase):

    def tearDown(self):
        bot.tages_kerzen_quelle = None

    def test_abruf_ist_1d(self):
        gesehen = []
        bot.tages_kerzen_quelle = lambda inst_id, n=300: (
            gesehen.append((inst_id, n)) or tages_kerzen([100.0] * 30))
        bot.hebel_deckel("TEST-USDT-SWAP", tage=7)
        self.assertEqual(gesehen, [("TEST-USDT-SWAP", 300)])

    def test_deckel_aus_tagesmae(self):
        # 26 % Einbruch binnen 7 Tagen -> Deckel long 1/(0,26 + 0,005).
        kurse = [100.0] * 50 + [100, 95, 90, 85, 80, 75, 74] + [74.0] * 50
        bot.tages_kerzen_quelle = lambda inst_id, n=300: tages_kerzen(kurse)
        dl, ds = bot.hebel_deckel("TEST-USDT-SWAP", tage=7, wartung=0.005)
        self.assertAlmostEqual(dl, 1.0 / 0.265, places=4)
        self.assertEqual(ds, 20.0)      # kein Abwaertsrisiko -> Obergrenze

    def test_zu_kurz_konservativ(self):
        bot.tages_kerzen_quelle = lambda inst_id, n=300: tages_kerzen([100.0] * 7)
        self.assertEqual(bot.hebel_deckel("TEST-USDT-SWAP", tage=7), (1.0, 1.0))


if __name__ == "__main__":
    unittest.main()
