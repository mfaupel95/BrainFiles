"""quant.py: gesunder Trend, Zappeln, Spitze, zu kurze Reihe, Korrelation."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import quant                                                  # noqa: E402


def reihe(schluesse, spanne=0.01):
    k = []
    for i, c in enumerate(schluesse):
        k.append([i * 86400000, c, c * (1 + spanne), c * (1 - spanne), c, 1000.0])
    return k


def trend(n=260, steigung=0.002):
    return reihe([100.0 * math.exp(steigung * i) for i in range(n)])


def zappeln(n=260):
    return reihe([100.0 + (3.0 if i % 2 else -3.0) for i in range(n)])


class UrteilTest(unittest.TestCase):
    def test_zu_kurze_reihe_gibt_none(self):
        self.assertIsNone(quant.urteil(trend(n=quant.LANG + quant.LUFT - 1)))

    def test_kuerzere_lang_laenge_urteilt_frueher(self):
        k = trend(n=120)
        self.assertIsNone(quant.urteil(k))                  # 200 braucht 210
        u = quant.urteil(k, lang=100)
        self.assertEqual(u["lang"], 100)
        self.assertEqual(u["ordnung"], 4)

    def test_gesunder_trend_hat_hohe_ordnung_und_guete(self):
        u = quant.urteil(trend())
        self.assertEqual(u["ordnung"], 4)
        self.assertGreater(u["effizienz30"], 0.95)
        self.assertGreater(u["quant_score"], 60)

    def test_normaler_trend_ist_nicht_gedehnt(self):
        self.assertFalse(quant.urteil(trend())["zu_gedehnt"])

    def test_zappeln_ist_kein_trend(self):
        u = quant.urteil(zappeln())
        self.assertLess(u["effizienz30"], 0.1)
        self.assertLess(u["quant_score"], 40)

    def test_spitze_wird_als_gedehnt_erkannt(self):
        s = [100.0 + 0.01 * i for i in range(240)]
        s += [s[-1] * (1 + 0.05 * j) for j in range(1, 21)]
        u = quant.urteil(reihe(s))
        self.assertTrue(u["zu_gedehnt"])
        self.assertGreater(u["dehnung_atr"], 6.0)
        # Der Deckel haelt die Spitze unter jedem sinnvollen Score-Tor.
        self.assertLessEqual(u["quant_score"], 50.0)

    def test_flache_reihe_teilt_nicht_durch_null(self):
        u = quant.urteil(reihe([100.0] * 260, spanne=0.0))
        self.assertEqual(u["effizienz30"], 0.0)
        self.assertEqual(u["dehnung_z"], 0.0)
        self.assertEqual(u["dehnung_atr"], 0.0)
        self.assertEqual(u["schwung_je_atr"], 0.0)


class ShortTest(unittest.TestCase):
    def test_abwaertstrend_ist_fuer_short_gesund(self):
        k = trend(steigung=-0.002)
        us, ul = quant.urteil(k, richtung="short"), quant.urteil(k)
        self.assertEqual(us["ordnung"], 4)
        self.assertGreater(us["quant_score"], 60)
        self.assertLess(ul["quant_score"], 40)       # derselbe Chart fuer long: schlecht
        self.assertEqual(us["richtung"], "short")

    def test_aufwaertstrend_ist_fuer_short_schlecht(self):
        us = quant.urteil(trend(), richtung="short")
        self.assertEqual(us["ordnung"], 0)
        self.assertLess(us["quant_score"], 40)

    def test_absturz_ist_fuer_short_gedehnt(self):
        s = [100.0 - 0.01 * i for i in range(240)]
        s += [s[-1] * (1 - 0.03 * j) for j in range(1, 21)]
        u = quant.urteil(reihe(s), richtung="short")
        self.assertTrue(u["zu_gedehnt"])
        self.assertLessEqual(u["quant_score"], 50.0)

    def test_gespiegelte_reihe_gibt_gleiche_ordnung(self):
        auf = trend()
        ab = reihe([1.0e4 / k[4] for k in auf])
        self.assertEqual(quant.urteil(auf)["ordnung"],
                         quant.urteil(ab, richtung="short")["ordnung"])

    def test_unbekannte_richtung_scheitert_laut(self):
        with self.assertRaises(ValueError):
            quant.urteil(trend(), richtung="seitwaerts")


class ReferenzTest(unittest.TestCase):
    def test_identische_reihe_korreliert_mit_eins(self):
        k = reihe([100 + 5 * math.sin(i / 3.0) + 0.1 * i for i in range(260)])
        u = quant.urteil(k, ref=k)
        self.assertAlmostEqual(u["korr_ref_60t"], 1.0, places=2)
        self.assertEqual(u["rel_staerke_30t_pct"], 0.0)

    def test_ohne_referenz_keine_referenzfelder(self):
        u = quant.urteil(trend())
        self.assertNotIn("korr_ref_60t", u)


if __name__ == "__main__":
    unittest.main()
