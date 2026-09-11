import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dauerlauf
import freigabefenster as f

class FreigabeTest(unittest.TestCase):
    def test_xperp_only_never_spot(self):
        with tempfile.TemporaryDirectory() as t, patch.object(f, 'DATEI', str(Path(t) / 'fenster.json')):
            f.anfrage_stellen('xperp', 60)
            f.anfrage_stellen('scanner', 60)
            lauf = dauerlauf.Lauf(15, trocken=True)
            with patch.object(dauerlauf, 'protokoll'):
                text = lauf.befehl('/ja_xperp 1')
            self.assertTrue(f.lade('xperp').offen(), text)
            self.assertFalse(f.lade('scanner').offen())
            self.assertTrue(f.lade('scanner').anfrage_offen())


class SafetyTest(unittest.TestCase):
    def test_no_request_invalid_hours_and_expired_request(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as t, patch.object(f, 'DATEI', str(Path(t) / 'f.json')):
            lauf = dauerlauf.Lauf(15, trocken=True)
            self.assertIn('Keine', lauf.befehl('/ja_xperp 1'))
            f.anfrage_stellen('xperp', 60)
            for value in ('', '0', '-1', 'nan', 'inf', '25', '1 extra'):
                self.assertIn('Syntax', lauf.befehl('/ja_xperp ' + value))
                self.assertFalse(f.lade('xperp').offen())
            with patch.object(f, '_jetzt', return_value=f._jetzt() + dt.timedelta(hours=1)):
                self.assertIn('Keine', lauf.befehl('/ja_xperp 1'))
            self.assertFalse(f.lade('xperp').offen())

    def test_stop_xperp_keeps_spot_window(self):
        with tempfile.TemporaryDirectory() as t, patch.object(f, 'DATEI', str(Path(t) / 'f.json')):
            for spur in ('xperp', 'scanner'):
                f.anfrage_stellen(spur, 60)
                f.oeffnen(spur, 1)
            dauerlauf.Lauf(15, trocken=True).befehl('/stop_xperp')
            self.assertFalse(f.lade('xperp').offen())
            self.assertTrue(f.lade('scanner').offen())
