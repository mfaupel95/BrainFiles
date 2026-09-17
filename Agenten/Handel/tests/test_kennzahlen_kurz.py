"""Die fuenf Spuren mit eigener Auswertung muessen summierbar werden.

Geprueft wird nicht die RECHNUNG - die bleibt, wie sie ist - sondern die
FORM: fuenf Module, eine Rueckgabe, damit die Gesamtbilanz sie addieren
kann, ohne fuenf Sonderfaelle zu kennen.
"""

import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

MODULE = ("spiegel.auswertung", "omniquant.auswertung", "kopier.auswertung",
          "kopier1zu1.auswertung", "gitter.auswertung")

PFLICHTFELDER = ("n", "ergebnis", "treffer", "waehrung", "live")


class TestMindestform(unittest.TestCase):

    def test_jedes_modul_hat_kennzahlen_kurz(self):
        import importlib
        for name in MODULE:
            with self.subTest(modul=name):
                m = importlib.import_module(name)
                self.assertTrue(hasattr(m, "kennzahlen_kurz"),
                                "%s fehlt kennzahlen_kurz()" % name)

    def test_rueckgabe_ist_none_oder_vollstaendig(self):
        import importlib
        for name in MODULE:
            with self.subTest(modul=name):
                k = importlib.import_module(name).kennzahlen_kurz()
                if k is None:
                    continue
                for feld in PFLICHTFELDER:
                    self.assertIn(feld, k, "%s: %s fehlt" % (name, feld))
                self.assertIsInstance(k["waehrung"], str)
                self.assertIsInstance(k["live"], bool)

    def test_fenster_wird_angenommen_und_schneidet(self):
        # Ein Fenster in der Zukunft darf nichts mehr enthalten. Wuerde das
        # Fenster nur entgegengenommen und nicht durchgereicht, kaeme hier
        # weiter die Zahl seit Anfang - die stille Falschzahl.
        import datetime as dt
        import importlib
        kuenftig = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        for name in MODULE:
            with self.subTest(modul=name):
                m = importlib.import_module(name)
                self.assertIsNone(m.kennzahlen_kurz(von=kuenftig))


if __name__ == "__main__":
    unittest.main()
