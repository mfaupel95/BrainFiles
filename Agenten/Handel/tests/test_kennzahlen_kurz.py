"""Die fuenf Spuren mit eigener Auswertung muessen summierbar werden.

Geprueft wird nicht die RECHNUNG - die bleibt, wie sie ist - sondern die
FORM: fuenf Module, eine Rueckgabe, damit die Gesamtbilanz sie addieren
kann, ohne fuenf Sonderfaelle zu kennen.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(WURZEL))

# Geladen wird ueber den Dateipfad, nicht ueber den Punktnamen. Die Spuren
# sind keine Pakete (kein __init__.py), und jede legt beim Import ihren
# eigenen Ordner in sys.path - ein "import spiegel.auswertung" haengt damit
# davon ab, was vorher lief. Der Dateipfad haengt von nichts ab.
SPUREN = ("spiegel", "omniquant", "kopier", "kopier1zu1", "gitter")


def lade(spur):
    """Laedt <spur>/auswertung.py unter eigenem Modulnamen."""
    name = "spur_%s_auswertung" % spur
    if name in sys.modules:
        return sys.modules[name]
    pfad = WURZEL / spur / "auswertung.py"
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul

PFLICHTFELDER = ("n", "ergebnis", "treffer", "waehrung", "live")


class TestMindestform(unittest.TestCase):

    def test_jedes_modul_hat_kennzahlen_kurz(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                m = lade(spur)
                self.assertTrue(hasattr(m, "kennzahlen_kurz"),
                                "%s fehlt kennzahlen_kurz()" % spur)

    def test_rueckgabe_ist_none_oder_vollstaendig(self):
        for spur in SPUREN:
            with self.subTest(spur=spur):
                k = lade(spur).kennzahlen_kurz()
                if k is None:
                    continue
                for feld in PFLICHTFELDER:
                    self.assertIn(feld, k, "%s: %s fehlt" % (spur, feld))
                self.assertIsInstance(k["waehrung"], str)
                self.assertIsInstance(k["live"], bool)

    def test_fenster_wird_angenommen_und_schneidet(self):
        # Ein Fenster in der Zukunft darf nichts mehr enthalten. Wuerde das
        # Fenster nur entgegengenommen und nicht durchgereicht, kaeme hier
        # weiter die Zahl seit Anfang - die stille Falschzahl.
        import datetime as dt
        kuenftig = dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc)
        for spur in SPUREN:
            with self.subTest(spur=spur):
                self.assertIsNone(lade(spur).kennzahlen_kurz(von=kuenftig))


if __name__ == "__main__":
    unittest.main()
