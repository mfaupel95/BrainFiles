"""Der Orderweg von moondev_signalwelle - an seinen Regeln, nicht am Netz.

Der Weg ist eine Freigabekette ohne Freigabe: er muss beweisen, dass er
  1. ein Instrument ohne Börsenmarkt ablehnt statt es zu ersetzen,
  2. einen Ausfall der Markliste NICHT als "kein Markt" liest,
  3. eine gebaute Schnittstelle vollständig bereitstellt,
  4. die Quote wählt, in der das Konto tatsächlich liegt.

Netz wird nicht gebraucht: die Markliste ist ein Einspeisepunkt.
"""
import importlib.util
import os
import sys
import unittest

HANDEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", ".."))


def spurmodul():
    pfad = os.path.join(HANDEL, "moondev_signalwelle", "weg.py")
    spec = importlib.util.spec_from_file_location("sw_weg", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


MARKT = {"AI-USDC", "AI-USDT", "AR-USDC", "NEAR-USDT", "STX-EUR"}


class WegTest(unittest.TestCase):
    def setUp(self):
        self.m = spurmodul()
        self.m._MAERKTE[0] = set(MARKT)

    # 1 -------------------------------------------------------------
    def test_ohne_markt_wird_verweigert_und_nicht_ersetzt(self):
        # XDC hat laut Messung vom 03.10.2026 keinen OKX-Spotmarkt.
        self.assertIsNone(self.m.boersenpaar("XDC"))
        with self.assertRaises(self.m.Meldend) as f:
            self.m.markt_kauf("XDC", 1.0)
        self.assertIn("nicht auf ein anderes Paar", str(f.exception))
        with self.assertRaises(self.m.Meldend):
            self.m.markt_verkauf("XDC", 1.0)

    # 2 -------------------------------------------------------------
    def test_leere_marktliste_ist_ein_ausfall_kein_befund(self):
        self.m._MAERKTE[0] = set()          # der Abruf ist gescheitert
        # KEIN "XDC hat keinen Markt" - das waere eine erfundene Tatsache
        # aus einem Ausfall, und ein Token mit Markt wuerde dauerhaft
        # gesperrt, nur weil der Abruf einmal gehetzt hat.
        with self.assertRaises(self.m.Meldend) as f:
            self.m.boersenpaar("XDC")
        self.assertIn("nicht lesbar", str(f.exception))
        with self.assertRaises(self.m.Meldend):
            self.m.markt_verkauf("XDC", 1.0)
        with self.assertRaises(self.m.Meldend):
            self.m.markt_kauf("XDC", 1.0)

    # 3 -------------------------------------------------------------
    def test_die_schnittstelle_ist_vollstaendig(self):
        for name in ("schluessel_vorhanden", "demo_modus", "guthaben_waehrung",
                     "letzter_kurs", "menge_fuer", "markt_kauf", "markt_verkauf",
                     "algo_stop_setzen", "algo_stornieren", "stop_nachziehen",
                     "gefuellte_menge"):
            self.assertTrue(callable(getattr(self.m, name, None)),
                            "%s fehlt - spur_buch.orderweg() braucht es" % name)

    # 4 -------------------------------------------------------------
    def test_quote_wird_gewaehlt_nicht_geraten(self):
        self.assertEqual(self.m.boersenpaar("AI"), "AI-USDC")   # USDC zuerst
        self.assertEqual(self.m.boersenpaar("NEAR"), "NEAR-USDT")  # nur USDT da
        self.assertEqual(self.m.boersenpaar("STX"), "STX-EUR")    # nur EUR da

    # 5 - die Gegenprobe zu 1
    def test_gegenprobe_ohne_pruefung_kaeufe_er_in_fremdes_paar(self):
        """Ohne den Test waere die Verweigerung nicht belegbar."""
        behauptet = []
        original = self.m.markt_kauf

        def ohne_pruefung(inst, menge):
            behauptet.append("%s -> %s-USDC" % (inst, inst))
            return "order"
        self.m.markt_kauf = ohne_pruefung
        self.assertEqual(self.m.markt_kauf("XDC", 1.0), "order")
        self.assertEqual(behauptet, ["XDC -> XDC-USDC"],
                         "das ist der Fehler, den die Pruefung verhindert")
        self.m.markt_kauf = original


if __name__ == "__main__":
    unittest.main()