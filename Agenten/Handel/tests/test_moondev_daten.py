"""Tests fuer `moondev_daten.pump_letzter_preis` - KEIN Netz.

Der Kursabruf bei swap-api.pump.fun ist der einzige Aufruf der Moon-Dev-Spuren,
der einen Fehler BIS IN DEN DAUERLAUF durchliess: gefangen war nur HTTP 429.
Ein Verbindungsabbruch (WinError 10054, 22.09.2026 dreimal) wurde zur
Rueckgabe 1 und damit zu einer Bus-Meldung, obwohl der Zyklus weiterlaufen
konnte. Hier stehen die Faelle, die vorher durchfielen.

`urlopen` wird durch Doubles ersetzt - kein Test haengt an der Boerse.

Aufruf aus `Agenten/Handel/tests`:
    ..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_moondev_daten
"""

import io
import json
import os
import sys
import unittest
import urllib.error

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import moondev_daten as d  # noqa: E402

ORDNER = "3wKQScVShTMEmoF9AFmVk74cqBm64DLzaPJhiGuVpump"


class Antwort(io.BytesIO):
    """Was urlopen sonst liefert: lesbar, mit Kontextmanager."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Abbruch:
    """Die Leitung ist weg (WinError 10054)."""

    def __enter__(self):
        raise urllib.error.URLError(ConnectionResetError(10054, "reset"))

    def __exit__(self, *a):
        return False


class PreisTest(unittest.TestCase):
    """Der Kurspfad stellt nie eine Ausnahme in den Zyklus."""

    def setUp(self):
        self.alt = d.urllib.request.urlopen
        self.aufrufe = 0

    def tearDown(self):
        d.urllib.request.urlopen = self.alt

    def _urlopen(self, verhalten):
        def ruf(*a, **k):
            self.aufrufe += 1
            if isinstance(verhalten, Exception):
                raise verhalten
            return verhalten
        d.urllib.request.urlopen = ruf

    def test_abbruch_ergibt_none_und_fasst_einmal_nach(self):
        self._urlopen(urllib.error.URLError(ConnectionResetError(10054, "x")))
        self.assertIsNone(d.pump_letzter_preis(ORDNER))
        self.assertEqual(self.aufrufe, 2)      # einmal nachgefasst, dann Ruhe

    def test_zeitueberschreitung_ergibt_none(self):
        self._urlopen(TimeoutError("timed out"))
        self.assertIsNone(d.pump_letzter_preis(ORDNER))

    def test_abgeschnittene_antwort_ergibt_none(self):
        """Die Verbindung brach mitten im Rumpf ab - JSONDecodeError."""
        self._urlopen(Antwort(b'{"trades": [{"price'))
        self.assertIsNone(d.pump_letzter_preis(ORDNER))

    def test_zweiter_versuch_traegt(self):
        """Der erste Versuch reisst ab, der zweite liefert - dann gibt es einen Preis."""
        antworten = [urllib.error.URLError(ConnectionResetError(10054, "x")),
                     Antwort(json.dumps({"trades": [{"priceUsd": "0.00042"}]})
                             .encode("utf-8"))]

        def ruf(*a, **k):
            self.aufrufe += 1
            a_ = antworten.pop(0)
            if isinstance(a_, Exception):
                raise a_
            return a_
        d.urllib.request.urlopen = ruf
        self.assertAlmostEqual(d.pump_letzter_preis(ORDNER), 0.00042)

    def test_gesunde_antwort_liefert_den_preis(self):
        self._urlopen(Antwort(json.dumps(
            {"trades": [{"priceUsd": "0.00042"}]}).encode("utf-8")))
        self.assertAlmostEqual(d.pump_letzter_preis(ORDNER), 0.00042)

    def test_keine_trades_ist_kein_fehler(self):
        self._urlopen(Antwort(b'{"trades": []}'))
        self.assertIsNone(d.pump_letzter_preis(ORDNER))

    def test_fremde_antwortform_ist_kein_fehler(self):
        """Eine Liste statt eines Objekts darf nicht in .get() laufen."""
        self._urlopen(Antwort(b'[]'))
        self.assertIsNone(d.pump_letzter_preis(ORDNER))

    def test_429_fasst_einmal_nach(self):
        fehler = urllib.error.HTTPError("u", 429, "zu viele", {}, None)
        self._urlopen(fehler)
        self.assertIsNone(d.pump_letzter_preis(ORDNER))
        self.assertEqual(self.aufrufe, 2)

    def test_500_ergibt_sofort_none(self):
        fehler = urllib.error.HTTPError("u", 500, "serverfehler", {}, None)
        self._urlopen(fehler)
        self.assertIsNone(d.pump_letzter_preis(ORDNER))
        self.assertEqual(self.aufrufe, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)