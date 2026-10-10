"""T-312: futures_probe muss die Position auch dann absichern, wenn das
Fill-Polling nichts liefert (oder sich weigert).

Der Fehler vom 01.10.2026: der Kauf war gefuellt, `/fills` antwortete mit
`authenticationError`, der except-Zweig verliess die Funktion OHNE Schutz.
Die Regel, die jetzt gilt: ab dem abgesendeten Kauf ist die Position
moeglicherweise offen - JEDER Abbruchpfad ruft `notausstieg`.

Der Test ruft `lauf()` mit Attrappen auf (kein Netz, keine Order) und
verlangt, dass jeder der drei Abbruchpfade den Stop setzt. Gegenprobe: ohne
den Fix bleibt der Pfad 'keine Fuellung' OHNE Absicherung.
"""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)

import futures_probe as fp        # noqa: E402


class _Kf:
    """Attrappe fuer kraken_futures: kein Netz, keine echte Order."""
    PREISE = {"PF_STRKUSD": 0.04}

    def __init__(self, sells_moeglich=True):
        self.sells_moeglich = sells_moeglich
        self.stops = []

    # -- lesend -----------------------------------------------------------
    def letzter_kurs(self, symbol):
        return self.PREISE.get(symbol, 1.0)

    def guthaben(self, w="usd"):
        return 500.0

    def offene_positionen(self, symbol=None):
        return []

    def offene_orders(self, symbol=None):
        return []

    def instrument(self, symbol):
        return {"contractSize": 1.0, "tickSize": 0.0001}

    def einschuss(self, symbol, kontrakte, kurs):
        return 1.0

    def preis_gerundet(self, symbol, preis):
        return round(float(preis), 4)

    # -- schreibend -------------------------------------------------------
    def _order_aufgeben(self, werte):
        if werte.get("side") == "buy":
            return "KAUF-1"
        if not self.sells_moeglich:
            raise RuntimeError("authenticationError")
        return "VERKAUF-1"

    def stop_setzen(self, symbol, menge, stop, echt=False):
        self.stops.append((symbol, menge, stop, echt))
        return "STOP-1"

    # /fills weigert sich - genau der Fehlerfall vom 01.10.
    def _roh(self, pfad, werte=None, signiert=True, post=False, methode=None):
        raise RuntimeError("authenticationError")


class _PollingSchlaegtFehl:
    """fuelungen() liefert nichts (statt zu raisen)."""

    @staticmethod
    def fuelungen(order_id, seit, frist_s=15):
        return []


class NotausstiegTest(unittest.TestCase):
    def setUp(self):
        self.alt_kf = fp.kf
        self.alt_polling = fp.fuelungen
        fp.SYMBOL = "PF_STRKUSD"
        self.ausgabe = []

    def tearDown(self):
        fp.kf = self.alt_kf
        fp.fuelungen = self.alt_polling
        fp.SYMBOL = "PF_STRKUSD"

    def _fuehre(self, kf, fuelungen):
        fp.kf = kf
        fp.fuelungen = fuelungen
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fp.lauf(1, True)
        return rc, buf.getvalue()

    def test_keine_fuellung_und_verkauf_scheitert_setzt_stop(self):
        # T-312: bei unlesbarer Kauf-Fuellung wird der Verkauf (reduceOnly)
        # versucht. Scheitert auch der, greift der Schutz-Stop.
        kf = _Kf(sells_moeglich=False)
        rc, txt = self._fuehre(kf, _PollingSchlaegtFehl.fuelungen)
        self.assertEqual(rc, 1)
        self.assertIn("KEINE Kauf-Fuellung gelesen", txt)
        self.assertIn("VERKAUF GESCHEITERT", txt)
        self.assertEqual(len(kf.stops), 1,
                         "kein Schutz-Stop gesetzt:\n%s" % txt)
        self.assertTrue(kf.stops[0][3], "Stop muss echt sein, nicht Trockenlauf")
        # Der Stop haengt am LETZTEN BEKANNTEN Kurs (0.04), nicht an 0.
        self.assertAlmostEqual(kf.stops[0][2], 0.04 * 0.985, places=6)

    def test_keine_fuellung_aber_verkauf_geht_durch(self):
        # T-312: der Verkauf haengt NICHT am Fill-Polling. Bei unlesbarer
        # Kauf-Fuellung wird er trotzdem versucht; gelingt er, bleibt keine
        # Position offen und kein Stop noetig.
        kf = _Kf()
        zaehler = {"n": 0}

        def fills(order_id, seit, frist_s=15):
            zaehler["n"] += 1
            if zaehler["n"] == 1:      # Kauf-Fuellung unlesbar
                return []
            return [{"order_id": order_id, "price": "0.0500", "size": "1"}]

        rc, txt = self._fuehre(kf, fills)
        self.assertEqual(rc, 0)
        self.assertIn("KEINE Kauf-Fuellung gelesen", txt)
        self.assertIn("Verkauf gesendet (Kauf-Fuellung unlesbar)", txt)
        self.assertEqual(len(kf.stops), 0,
                         "kein Stop noetig, wenn der Verkauf durchging")

    def test_verkauf_abgelehnt_setzt_stop_mit_fuellungskurs(self):
        kf = _Kf(sells_moeglich=False)

        def fills(order_id, seit, frist_s=15):
            return [{"order_id": order_id, "price": "0.0500", "size": "1"}]

        rc, txt = self._fuehre(kf, fills)
        self.assertEqual(rc, 1)
        self.assertIn("VERKAUF GESCHEITERT", txt)
        self.assertEqual(len(kf.stops), 1, txt)
        self.assertAlmostEqual(kf.stops[0][2], 0.05 * 0.985, places=6)

    def test_verkaufsfuellung_fehlt_setzt_stop(self):
        """Der dritte Pfad: Verkauf ging raus, die Fuellung blieb aus."""
        kf = _Kf()
        zaehler = {"n": 0}

        def fills(order_id, seit, frist_s=15):
            zaehler["n"] += 1
            if zaehler["n"] == 1:      # Kauf
                return [{"order_id": order_id, "price": "0.0500", "size": "1"}]
            return []                  # Verkauf

        rc, txt = self._fuehre(kf, fills)
        self.assertEqual(rc, 1)
        self.assertIn("KEINE Verkaufsfuellung", txt)
        self.assertEqual(len(kf.stops), 1, txt)

    def test_gegenprobe_ohne_fix_bleibt_der_pfad_offen(self):
        """Der Weg 'keine Fuellung' hat OHNE die Absicherung keinen Stop."""
        quelle = open(fp.__file__, encoding="utf-8").read()
        block = quelle.split("KEINE Kauf-Fuellung gelesen")[1].split("return 1")[0]
        self.assertIn("notausstieg", block,
                      "der Pfad ohne Fuellung ruft die Absicherung nicht")


if __name__ == "__main__":
    unittest.main()