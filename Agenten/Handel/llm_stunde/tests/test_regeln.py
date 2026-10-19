import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # Agenten/Handel
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # llm_stunde
import regeln  # noqa: E402


def kerzen_aus(schluesse):
    # [ts, o, h, l, c, v]; h/l = c +- 0.5 %, damit der ATR nicht null ist
    return [[i * 3600000, c, c * 1.005, c * 0.995, c, 100.0]
            for i, c in enumerate(schluesse)]


W = {"ema_schnell_n": 3, "ema_langsam_n": 6, "rsi_n": 14, "rsi_unten": 30.0,
     "rsi_aus_long": 55.0, "trend_ema_n": 10, "atr_perioden": 14,
     "atr_multiplier": 2.3, "stop_prozent_pflicht_min": 1.5,
     "stop_prozent_pflicht_max": 5.0, "st_atr_n": 10, "st_atr_multiplier": 3.0}


class Kandidat(unittest.TestCase):
    def test_ema_kreuz_oben_gibt_long(self):
        # flach, dann ein Sprung auf der letzten Kerze: schnelle EMA kreuzt genau dort
        kurs = [10.0] * 20 + [30.0]
        self.assertEqual(regeln.kandidat("ema1h", kerzen_aus(kurs), W), "long")

    def test_ohne_kreuz_kein_kandidat(self):
        self.assertIsNone(regeln.kandidat("ema1h", kerzen_aus([10.0] * 30), W))

    def test_zu_wenig_kerzen_kein_signal(self):
        self.assertIsNone(regeln.kandidat("ema1h", kerzen_aus([10.0] * 5), W))

    def test_ausstieg_ema_gegenkreuz(self):
        kurs = [10.0] * 20 + [1.0]
        self.assertTrue(regeln.ausstieg("ema1h", kerzen_aus(kurs), W))

    def test_rsi_ausstieg_ueber_55(self):
        kurs = [10.0] * 20 + [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
        self.assertTrue(regeln.ausstieg("rsi1h", kerzen_aus(kurs), W))

    def test_unbekannte_variante_wirft(self):
        with self.assertRaises(ValueError):
            regeln.kandidat("gibtsnicht", kerzen_aus([10.0] * 30), W)


if __name__ == "__main__":
    unittest.main()
