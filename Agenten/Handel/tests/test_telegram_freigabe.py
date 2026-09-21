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


class WiedervorlageTest(unittest.TestCase):
    """Die Wiedervorlage-Fristen: freigabefenster.neue_anfrage_erlaubt().

    Ohne sie fragte der Dauerlauf im Halbstundentakt dieselbe Freigabe erneut -
    auch direkt nach einem /nein. Eine gerade abgelehnte Frage wird
    weggewischt, und mit ihr die naechste, auf die es ankommt.
    """

    def setUp(self):
        import datetime as dt
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (f.DATEI, f._jetzt)
        f.DATEI = str(Path(self.tmp.name) / 'f.json')
        self.jetzt = self.alt[1]()
        f._jetzt = lambda: self.jetzt
        self.dt = dt

    def tearDown(self):
        f.DATEI, f._jetzt = self.alt
        self.tmp.cleanup()

    def vorspulen(self, **kw):
        self.jetzt += self.dt.timedelta(**kw)

    def test_leere_spur_darf_gefragt_werden(self):
        self.assertTrue(f.neue_anfrage_erlaubt('scanner'))

    def test_laueft_ein_fenster_ist_die_frage_ohnehin_erledigt(self):
        f.anfrage_stellen('scanner', 60)
        f.oeffnen('scanner', 1)
        self.assertTrue(f.lade('scanner').offen())

    def test_unbeantwortete_anfrage_wird_nicht_im_halbstundentakt_wiederholt(self):
        f.anfrage_stellen('scanner', 720)
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        self.vorspulen(minutes=90)                    # Antwortfrist (30) laengst um
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        self.vorspulen(minutes=40)                    # 130 min seit der Frage
        self.assertTrue(f.neue_anfrage_erlaubt('scanner'))

    def test_nach_ablehnung_zwoelf_stunden_ruhe(self):
        f.anfrage_stellen('scanner', 720)
        f.schliessen('scanner', 'abgelehnt')
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        self.vorspulen(hours=11)
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        self.vorspulen(hours=1)
        self.assertTrue(f.neue_anfrage_erlaubt('scanner'))

    def test_stop_zaehlt_wie_ablehnung_das_laufende_ende_nicht(self):
        f.schliessen('scanner', 'Befehl /stop')
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        f.schliessen('xperp', 'Dauerlauf beendet')
        self.assertTrue(f.neue_anfrage_erlaubt('xperp'),
                        'ein beendeter Lauf darf nach dem Start wieder fragen')

    def test_die_spaetere_frist_gilt(self):
        # Nach der Ruhe neu gefragt, dann zaehlt die 2-h-Frist der neuen Frage -
        # nicht die alte Ablehnung.
        f.schliessen('scanner', 'abgelehnt')
        self.vorspulen(hours=13)
        f.anfrage_stellen('scanner', 720)
        self.vorspulen(minutes=10)
        self.assertFalse(f.neue_anfrage_erlaubt('scanner'))
        self.vorspulen(minutes=115)
        self.assertTrue(f.neue_anfrage_erlaubt('scanner'))


class WiedervorlageImLaufTest(unittest.TestCase):
    """Die Frist muss im Dauerlauf ankommen, nicht nur in der Hilfsfunktion."""

    def setUp(self):
        import datetime as dt
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = (f.DATEI, f._jetzt, dauerlauf.protokoll,
                    dauerlauf.Lauf.nur_fenster_fehlt, dauerlauf.Lauf.pruefe_verbesserer,
                    dauerlauf.AUTO_FREIGABE)
        # Auto-Freigabe (20.09.2026) stilllegen: sie bestaetigt eine Anfrage
        # SOFORT, damit steht gar keine Frage mehr offen - und genau die ist
        # hier der Pruefgegenstand. Ohne diese Zeile faellt der Test seit dem
        # 20.09. (Befund 21.09.2026), weil scanner in AUTO_FREIGABE steht.
        dauerlauf.AUTO_FREIGABE = ()
        f.DATEI = str(Path(self.tmp.name) / 'f.json')
        self.jetzt = self.alt[1]()
        f._jetzt = lambda: self.jetzt
        self.dt = dt
        dauerlauf.protokoll = lambda *a, **kw: None
        dauerlauf.Lauf.nur_fenster_fehlt = lambda self, spur, d: (
            {'handel_erlaubt': True} if spur == 'scanner' else None)
        # Der Verbesserer schreibt in echte Ordner - hier nicht sein Thema.
        dauerlauf.Lauf.pruefe_verbesserer = lambda self: None
        self.lauf = dauerlauf.Lauf(15, trocken=True)
        self.lauf.sende = lambda *a, **kw: True

    def tearDown(self):
        (f.DATEI, f._jetzt, dauerlauf.protokoll, dauerlauf.Lauf.nur_fenster_fehlt,
         dauerlauf.Lauf.pruefe_verbesserer, dauerlauf.AUTO_FREIGABE) = self.alt
        self.tmp.cleanup()

    def test_abgelehnte_spur_wird_nicht_erneut_gefragt(self):
        f.schliessen('scanner', 'abgelehnt')
        self.lauf.pruefe_anfragen()
        self.assertFalse(f.lade('scanner').anfrage_offen())

    def test_nach_der_frist_kommt_die_frage_wieder(self):
        f.schliessen('scanner', 'abgelehnt')
        self.jetzt += self.dt.timedelta(hours=13)
        self.lauf.pruefe_anfragen()
        self.assertTrue(f.lade('scanner').anfrage_offen())
