"""Tests der IV-Wand-Spur - ohne Netz, mit erfundenen Ketten und Kerzen."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import iv_waelle as k  # noqa: E402


def kette_bauen(spot: float, strikes_und_oi: list) -> list:
    """Baut eine Ersatz-Optionskette. strikes_und_oi = [(strike, seite, oi), ...]"""
    kette = []
    for strike, seite, oi in strikes_und_oi:
        kette.append({
            "instrument_name": f"BTC-25DEC26-{int(strike)}-{seite}",
            "open_interest": oi,
            "mark_iv": 40.0,
        })
    return kette


class TestVolatilitaet(unittest.TestCase):
    def test_sigma_passt_zur_formel(self):
        # 40 % im Jahr -> Tagessigma = Kurs * 0.40 / sqrt(365)
        sigma = k.tages_sigma(100000.0, 40.0)
        self.assertAlmostEqual(sigma, 100000.0 * 0.40 / math.sqrt(365), places=6)

    def test_hist_vol_konstante_rendite_ist_null(self):
        # gleiche Rendite jeden Tag -> Streuung 0
        reihe = [100.0 * (1.01 ** i) for i in range(30)]
        self.assertAlmostEqual(k.hist_vol_prozent(reihe, 20), 0.0, places=6)

    def test_hist_vol_zu_kurze_reihe(self):
        self.assertIsNone(k.hist_vol_prozent([100.0, 101.0], 20))

    def test_hist_vol_ordnet_groesserer_schwankung_groesseren_wert_zu(self):
        ruhig = [100.0, 100.2, 100.1, 100.3, 100.2, 100.4, 100.3, 100.5]
        wild = [100.0, 106.0, 99.0, 108.0, 97.0, 110.0, 96.0, 112.0]
        self.assertLess(k.hist_vol_prozent(ruhig, 5), k.hist_vol_prozent(wild, 5))

    def test_mische_ohne_hv_nimmt_iv(self):
        self.assertEqual(k.mische_iv_hv(40.0, None), 40.0)

    def test_mische_ohne_iv_nimmt_hv(self):
        self.assertEqual(k.mische_iv_hv(None, 55.0), 55.0)

    def test_mische_haelfte_haelfte(self):
        self.assertAlmostEqual(k.mische_iv_hv(40.0, 60.0), 50.0, places=6)

    def test_spanne_ist_symmetrisch(self):
        sp = k.spanne(100000.0, 40.0, k.K_90)
        self.assertAlmostEqual(100000.0 - sp["unten"], sp["oben"] - 100000.0, places=6)
        self.assertAlmostEqual(sp["mitte"], 100000.0, places=6)

    def test_90_prozent_ist_breiter_als_68(self):
        eng = k.spanne(100000.0, 40.0, k.K_68)
        weit = k.spanne(100000.0, 40.0, k.K_90)
        self.assertLess(eng["breite_prozent"], weit["breite_prozent"])


class TestStrikes(unittest.TestCase):
    def test_strike_aus_name(self):
        self.assertEqual(k.strike_aus_name("BTC-25DEC26-220000-C"), (220000.0, "C"))
        self.assertEqual(k.strike_aus_name("BTC-25DEC26-80000-P"), (80000.0, "P"))

    def test_unbrauchbarer_name(self):
        self.assertEqual(k.strike_aus_name("quatsch"), (None, None))


class TestWaende(unittest.TestCase):
    def setUp(self):
        self.spot = 100000.0
        self.kette = kette_bauen(self.spot, [
            (105000.0, "C", 500.0),
            (110000.0, "C", 900.0),
            (120000.0, "C", 300.0),
            (90000.0, "P", 400.0),
            (95000.0, "P", 800.0),
            (85000.0, "P", 200.0),
            (100000.0, "C", 5000.0),  # direkt am Kurs - darf keine Wand sein
        ])

    def test_call_wand_ist_groesstes_oi_ueber_kurs(self):
        w = k.waende(self.kette, self.spot)
        self.assertEqual(w["call_wand"]["strike"], 110000.0)
        self.assertEqual(w["call_wand"]["oi"], 900.0)

    def test_put_wand_ist_groesstes_oi_unter_kurs(self):
        w = k.waende(self.kette, self.spot)
        self.assertEqual(w["put_wand"]["strike"], 95000.0)
        self.assertEqual(w["put_wand"]["oi"], 800.0)

    def test_strike_am_kurs_ist_keine_wand(self):
        w = k.waende(self.kette, self.spot)
        self.assertNotEqual(w["call_wand"]["strike"], self.spot)

    def test_abstand_prozent_hat_vorzeichen(self):
        w = k.waende(self.kette, self.spot)
        self.assertAlmostEqual(w["call_wand"]["abstand_prozent"], 10.0, places=6)
        self.assertAlmostEqual(w["put_wand"]["abstand_prozent"], -5.0, places=6)

    def test_leere_kette_gibt_keine_wand(self):
        w = k.waende([], self.spot)
        self.assertIsNone(w["call_wand"])
        self.assertIsNone(w["put_wand"])

    def test_oi_je_strike_summiert_faelligkeiten(self):
        kette = kette_bauen(self.spot, [(110000.0, "C", 100.0)])
        kette.append({"instrument_name": "BTC-30JAN27-110000-C",
                      "open_interest": 250.0, "mark_iv": 45.0})
        summen = k.offenes_interesse_je_strike(kette)
        self.assertEqual(summen[(110000.0, "C")]["oi"], 350.0)


class TestWandelage(unittest.TestCase):
    def test_wand_im_bereich_ist_nicht_handelbar(self):
        sp = k.spanne(100000.0, 40.0)            # Tagessigma rund 2094
        waende = {"call_wand": {"strike": 101000.0, "oi": 100.0,
                                "abstand_prozent": 1.0}, "put_wand": None}
        lage = k.wandelage(waende, sp)
        self.assertEqual(lage["call_wand"]["lage"], "im_bereich")

    def test_wand_zwei_sigma_entfernt_ist_handelbar(self):
        sp = k.spanne(100000.0, 40.0)
        waende = {"call_wand": {"strike": 100000.0 + 2 * sp["sigma"], "oi": 100.0,
                                "abstand_prozent": 4.0}, "put_wand": None}
        self.assertEqual(k.wandelage(waende, sp)["call_wand"]["lage"], "handelbar")

    def test_wand_weit_draussen_ist_zu_weit(self):
        sp = k.spanne(100000.0, 40.0)
        waende = {"call_wand": {"strike": 100000.0 + 5 * sp["sigma"], "oi": 100.0,
                                "abstand_prozent": 10.0}, "put_wand": None}
        self.assertEqual(k.wandelage(waende, sp)["call_wand"]["lage"], "zu_weit")

    def test_fehlende_wand(self):
        sp = k.spanne(100000.0, 40.0)
        self.assertEqual(k.wandelage({"call_wand": None, "put_wand": None}, sp)
                         ["call_wand"]["lage"], "keine")


class TestSignal(unittest.TestCase):
    def setUp(self):
        self.sp = k.spanne(100000.0, 40.0)
        self.sigma = self.sp["sigma"]

    def _waende(self, strike, seite):
        wand = {"strike": strike, "oi": 1000.0,
                "abstand_prozent": (strike - 100000.0) / 1000.0}
        return {"call_wand": wand if seite == "C" else None,
                "put_wand": wand if seite == "P" else None}

    def test_keine_wand_kein_signal(self):
        s = k.signal(100000.0, {"call_wand": None, "put_wand": None}, self.sp)
        self.assertEqual(s["richtung"], "kein_signal")

    def test_wand_innerhalb_der_spanne_gibt_kein_signal(self):
        # Wand 0.3 % ueber dem Kurs liegt im normalen Bereich -> gesperrt
        s = k.signal(100300.0, self._waende(100600.0, "C"), self.sp)
        self.assertEqual(s["richtung"], "kein_signal")

    def test_short_an_der_call_wand(self):
        strike = 100000.0 + 2.0 * self.sigma
        s = k.signal(strike - 10.0, self._waende(strike, "C"), self.sp)
        self.assertEqual(s["richtung"], "short")
        self.assertGreater(s["stop"], strike)          # Stop hinter der Wand
        self.assertLess(s["ziel"], s["einstieg"])      # Ziel darunter
        self.assertAlmostEqual(s["ziel_anteil"], 0.5, places=6)

    def test_long_an_der_put_wand(self):
        strike = 100000.0 - 2.0 * self.sigma
        s = k.signal(strike + 10.0, self._waende(strike, "P"), self.sp)
        self.assertEqual(s["richtung"], "long")
        self.assertLess(s["stop"], strike)
        self.assertGreater(s["ziel"], s["einstieg"])

    def test_ziel_ist_die_haelfte_des_rueckwegs(self):
        strike = 100000.0 + 2.0 * self.sigma
        einstieg = strike - 10.0
        s = k.signal(einstieg, self._waende(strike, "C"), self.sp)
        erwartet = einstieg - 0.5 * (einstieg - self.sp["mitte"])
        self.assertAlmostEqual(s["ziel"], erwartet, places=6)

    def test_chance_risiko_wird_gerechnet(self):
        strike = 100000.0 + 2.0 * self.sigma
        s = k.signal(strike - 10.0, self._waende(strike, "C"), self.sp)
        self.assertIsNotNone(s["chance_risiko"])
        self.assertGreater(s["chance_risiko"], 0)

    def test_gesperrte_wand_kann_umgangen_werden(self):
        s = k.signal(100300.0, self._waende(100600.0, "C"), self.sp,
                     nur_handelbare_wand=False)
        self.assertEqual(s["richtung"], "short")


if __name__ == "__main__":
    unittest.main()
