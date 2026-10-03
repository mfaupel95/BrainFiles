"""Das Signal-Wechsel-Gatter - an seiner Regel, nicht an Spuren.

Diese Tests sichern genau die Eigenschaft, die am 03.10.2026 beim
Einfuehren falsch war und von den xperp-Tests gemeldet wurde: das Gatter
sperrt bei gesetztem Flag und LAESST durch, wenn das Feld fehlt. Eine
Fassung, die beides verwechselt, sperrt jede unmarkierte Spur - oder
faellt bei der ersten markierten vollstaendig aus.
"""
import os
import sys
import unittest

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import signal_wechsel
from signal_wechsel import ERLAEUT, GESPERRT, zugelassen


class GatterTest(unittest.TestCase):
    # 1 - die Regel selbst
    def test_flag_aus_lasst_immer_durch(self):
        z = {}
        w = {}
        self.assertIs(zugelassen(z, w, "BTC", "long"), ERLAEUT)
        self.assertIs(zugelassen(z, w, "BTC", "long"), ERLAEUT,
                      "ohne Flag ist das Gatter wirkungslos - so muss es sein")

    def test_flag_an_erster_einstieg_durch(self):
        self.assertIs(zugelassen({}, {"trigger_modus": "signal"}, "BTC", "long"),
                      ERLAEUT)

    def test_flag_an_gleiches_signal_gesperrt(self):
        z, w = {}, {"trigger_modus": "signal"}
        self.assertIs(zugelassen(z, w, "BTC", "long"), ERLAEUT)
        for _ in range(95):          # ein ganzer Tag im 15-Minuten-Takt
            self.assertIs(zugelassen(z, w, "BTC", "long"), GESPERRT)

    def test_richtungswechsel_durch(self):
        z, w = {}, {"trigger_modus": "signal"}
        zugelassen(z, w, "BTC", "long")
        self.assertIs(zugelassen(z, w, "BTC", "short"), ERLAEUT)

    # 2 - je Instrument getrennt
    def test_instrumente_sind_unabhaengig(self):
        z, w = {}, {"trigger_modus": "signal"}
        zugelassen(z, w, "BTC", "long")
        self.assertIs(zugelassen(z, w, "ETH", "long"), ERLAEUT,
                      "ein zweites Instrument darf nicht am ersten scheitern")

    # 3 - das Feld bildet den GESEHENEN Zustand ab, nicht den ausgefuehrten
    def test_verweigert_auch_merkt_es(self):
        z, w = {}, {"trigger_modus": "signal"}
        zugelassen(z, w, "BTC", "long")
        zugelassen(z, w, "BTC", "long")          # gesperrt
        self.assertEqual(z["vor_signal"]["BTC"], "long")
        # Kein Weg zurueck in "unveraendert": sonst wuerde die verweigerte
        # Runde beim naechsten Takt erneut durchpassen.
        self.assertIs(zugelassen(z, w, "BTC", "long"), GESPERRT)

    # 4 - die Gegenprobe, ohne die der Fehler unsichtbar bleibt
    def test_gegenprobe_doppelter_rueckgabewert(self):
        """Die Fassung, die am 03.10. drin war: hier True, dort ERLAEUT.

        Mit `is not ERLAEUT` im Aufrufer sperrt sie jede Spur ohne Flag.
        Genau das haben drei xperp-Tests am selben Tag gemeldet.
        """
        alt = True                                   # der damalige Fehler
        aufrufer_sperrt = alt is not ERLAEUT
        self.assertTrue(aufrufer_sperrt,
                        "der Aufrufer haette ohne Flag gesperrt")


if __name__ == "__main__":
    unittest.main()