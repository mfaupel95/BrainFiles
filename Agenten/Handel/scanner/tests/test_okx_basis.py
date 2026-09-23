"""Der Host fuer echte Orders muss denselben Rueckfall haben wie die Schluessel.

BEFUND 23.09.2026: Der scanner signierte mit dem LIVE-Schluessel gegen
www.okx.com, weil OKX_BASE im Prozess fehlte (aus einem MCP-Server oder einer
geplanten Aufgabe gestartet erbt der Prozess die Windows-Benutzervariablen
nicht). Der Schluessel kam ueber die Registry, der HOST nicht - OKX antwortete
mit 50119 "API key doesn't exist", und der Verkauf ZEC-USDC scheiterte jede
Runde. xperp und mosaic hatten den Rueckfall laengst; dem scanner fehlte er.

Diese Tests halten die Regel fest, ohne Netz:
  1. OKX_BASE aus der Registry wird benutzt, wenn die Prozessumgebung leer ist.
  2. Ohne Registry-Wert bleibt der Standard (www.okx.com).
  3. Der Schluessel-Rueckfall selbst gilt weiter.
"""
import os
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)
import okx  # noqa: E402

assert okx.__file__.startswith(SPUR), okx.__file__


class BasisTest(unittest.TestCase):
    def setUp(self):
        self.umgebung = os.environ.pop("OKX_BASE", None)
        self.registry = okx._aus_registry
        self.umgebung_sicherung = dict(os.environ)

    def tearDown(self):
        if self.umgebung is not None:
            os.environ["OKX_BASE"] = self.umgebung
        okx._aus_registry = self.registry
        os.environ.clear()
        os.environ.update(self.umgebung_sicherung)

    def test_registry_wird_benutzt(self):
        # So sah der Fehlerfall aus: Prozess leer, Registry gefuellt.
        okx._aus_registry = lambda name: ("https://eea.okx.com"
                                         if name == "OKX_BASE" else None)
        self.assertEqual(okx._live_basis(), "https://eea.okx.com")

    def test_prozessumgebung_schlaegt_registry(self):
        os.environ["OKX_BASE"] = "https://eea.okx.com/"
        okx._aus_registry = lambda name: "https://www.okx.com"
        self.assertEqual(okx._live_basis(), "https://eea.okx.com")

    def test_ohne_angabe_standard(self):
        okx._aus_registry = lambda name: None
        self.assertEqual(okx._live_basis(), "https://www.okx.com")

    def test_schluessel_rueckfall_gilt_weiter(self):
        for n in okx.LI:
            os.environ.pop(n, None)
        okx._aus_registry = lambda name: "wert" if name in okx.LI else None
        self.assertTrue(okx.schluessel_vorhanden())


if __name__ == "__main__":
    unittest.main()