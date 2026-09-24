"""Das Tor zum echten Orderweg: freigabebeleg.schreibe() (24.09.2026).

Der Beleg ist die EINZIGE Erlaubnis, mit der das Kraken-MCP eine echte Order
ausfuehren darf (`kraken_order_mit_beleg`). Er darf nur entstehen, wenn
  * fuer die Spur ein Freigabefenster offen ist UND
  * handel_erlaubt=true in ihrer wachen.json steht.

BEFUND 24.09.2026: `_fenster()` liefert das MODUL, der Aufruf war aber
`fenster.offen(spur)` - das Modul hat keine Funktion `offen`. Jeder Beleg
scheiterte deshalb still mit "Freigabefenster nicht lesbar", und die Spur
verbuchte das als gewoehnlichen Sperrgrund. Kein Beleg heisst: keine echte
Order, nirgends. Die Tests hier halten beide Richtungen fest.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HIER))

import freigabebeleg as fb                                             # noqa: E402

assert Path(fb.__file__).resolve().parent == HIER


class _Fenster:
    def __init__(self, offen):
        self._offen = offen

    def offen(self):
        return self._offen


class _FensterModul:
    """Steht fuer freigabefenster.py: Modul mit lade(spur) -> Fenster."""

    def __init__(self, offen):
        self._offen = offen

    def lade(self, spur):
        return _Fenster(self._offen)


class BelegTor(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = [
            patch.object(fb, "CACHE", os.path.join(self.tmp.name, "belege")),
            patch.object(fb, "_wachen_handel_erlaubt", return_value=True),
        ]
        for q in self.p:
            q.start()

    def tearDown(self):
        for q in self.p:
            q.stop()
        self.tmp.cleanup()

    def test_offenes_fenster_gibt_einen_beleg(self):
        with patch.object(fb, "_fenster", return_value=_FensterModul(True)):
            beleg = fb.schreibe("kraken", "buy", "XXBTZEUR", 0.001,
                                preis_max=50000.0, grund="Test")
        self.assertTrue(beleg.get("kennung"), "Beleg ohne Kennung: %s" % beleg)
        self.assertEqual(beleg["spur"], "kraken")
        self.assertTrue(os.path.exists(fb.datei("kraken")))

    def test_geschlossenes_fenster_verweigert(self):
        with patch.object(fb, "_fenster", return_value=_FensterModul(False)):
            beleg = fb.schreibe("kraken", "buy", "XXBTZEUR", 0.001,
                                preis_max=50000.0, grund="Test")
        self.assertFalse(beleg.get("kennung"))
        self.assertIn("kein offenes Freigabefenster", beleg["grund"])

    def test_kaputtes_fenster_verweigert_und_nennt_den_grund(self):
        """Der alte Fehler (Modul statt Fenster) muss als Sperre sichtbar sein."""
        with patch.object(fb, "_fenster", return_value=object()):
            beleg = fb.schreibe("kraken", "buy", "XXBTZEUR", 0.001,
                                preis_max=50000.0, grund="Test")
        self.assertFalse(beleg.get("kennung"))
        self.assertIn("Freigabefenster nicht lesbar", beleg["grund"])

    def test_handel_erlaubt_false_verweigert_auch_bei_offenem_fenster(self):
        with patch.object(fb, "_wachen_handel_erlaubt", return_value=False), \
             patch.object(fb, "_fenster", return_value=_FensterModul(True)):
            beleg = fb.schreibe("kraken", "buy", "XXBTZEUR", 0.001,
                                preis_max=50000.0, grund="Test")
        self.assertFalse(beleg.get("kennung"))
        self.assertIn("handel_erlaubt=false", beleg["grund"])

    def test_beleg_ist_einmalig(self):
        with patch.object(fb, "_fenster", return_value=_FensterModul(True)):
            beleg = fb.schreibe("kraken", "buy", "XXBTZEUR", 0.001,
                                preis_max=50000.0, grund="Test")
            ok, _ = fb.pruefe(beleg["kennung"], "kraken", "buy", "XXBTZEUR", 0.001)
            self.assertTrue(ok, "frischer Beleg muss passen")
            fb.verbrauche("kraken", beleg["kennung"], "test")
            zweite, grund = fb.pruefe(beleg["kennung"], "kraken", "buy",
                                      "XXBTZEUR", 0.001)
        self.assertFalse(zweite)
        self.assertIn("verbraucht", grund.lower())

    def test_mit_abgeschaltetem_fenster_funktioniert_der_alte_aufruf_nicht(self):
        """Gegenprobe zum Befund: fenster.offen(spur) auf dem MODUL gibt es nicht."""
        modul = _FensterModul(True)
        self.assertFalse(hasattr(modul, "offen"),
                         "das Modul darf kein offen() haben - sonst prueft dieser "
                         "Test die falsche Sache")
        with self.assertRaises(AttributeError):
            modul.offen("kraken")                                  # noqa: B018


if __name__ == "__main__":
    unittest.main()