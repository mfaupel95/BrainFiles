import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillsbot

class StatusTest(unittest.TestCase):
    def test_status_never_goes_to_a2a(self):
        with patch.object(skillsbot, 'frage', side_effect=AssertionError('A2A verboten')):
            text, _ = skillsbot.bearbeite('/status', 1)
        self.assertIn('xperp', text.lower())
        self.assertIn('SWAP', text)


class PrognoseTest(unittest.TestCase):
    def test_prognose_fixed_readonly_command(self):
        import subprocess
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, '0 guenstig', '')) as run:
            with patch.object(skillsbot, 'frage', side_effect=AssertionError('A2A verboten')):
                text, _ = skillsbot.bearbeite('/prognose 5', 1)
        self.assertIn('0 guenstig', text)
        args = run.call_args.args[0]
        self.assertEqual(args[-3:], ['--kurz', '--werte', '5'])
        self.assertNotIn('--live', args)

    def test_unknown_slash_never_reaches_agent(self):
        with patch.object(skillsbot, 'frage', side_effect=AssertionError('A2A verboten')):
            text, _ = skillsbot.bearbeite('/ja_xperp 1', 1)
        self.assertIn('Handelsbot', text)

class SkillsBotHandelsbefehleTest(unittest.TestCase):
    """Verdrahtung der neuen Handelsbefehle im SkillsBot.

    Geprueft wird das ROUTING (kein A2A, kein HTML, kein Traceback) - der
    Inhalt der Auskuenfte steht in Handel/tests/test_befehle.py, wo die echten
    Spuren liegen. Hier haengt ein Stub an der Stelle von befehle.py, damit
    dieser Test schnell bleibt und ohne Netz laeuft.
    """

    class _Stub:
        @staticmethod
        def lage():
            return "<b>LAGE-STUB</b>"

        @staticmethod
        def bericht():
            return "<b>BERICHT-STUB</b>"

        @staticmethod
        def spur(name):
            return "<b>SPUR %s</b>" % name

        @staticmethod
        def spuren():
            return ["xperp", "scanner"]

        @staticmethod
        def strategien():
            return "<b>STRATEGIEN-STUB</b>"

        @staticmethod
        def indikatoren():
            return "<b>INDIKATOREN-STUB</b>"

        @staticmethod
        def markt():
            return "<b>MARKT-STUB</b>"

        @staticmethod
        def klartext(text):
            return text.replace("<b>", "").replace("</b>", "")

    def setUp(self):
        import handel_befehle
        self.stub = patch.object(handel_befehle, "_handel",
                                 return_value=self._Stub())
        self.stub.start()
        self.addCleanup(self.stub.stop)

    def test_kein_handelsbefehl_geht_an_a2a_und_kein_html(self):
        with patch.object(skillsbot, "frage",
                          side_effect=AssertionError("A2A verboten")):
            for befehl in ("/lage", "/bericht", "/spuren", "/strategien",
                           "/indikatoren", "/markt", "/spur scanner"):
                text, _ = skillsbot.bearbeite(befehl, 1)
                self.assertNotIn("<b>", text, befehl)
                self.assertNotIn("</b>", text, befehl)
                self.assertTrue(text.strip(), befehl)

    def test_spur_reicht_den_namen_durch(self):
        text, _ = skillsbot.bearbeite("/spur macd_mtf", 1)
        self.assertIn("SPUR macd_mtf", text)

    def test_hilfe_kennt_die_neuen_befehle_ohne_html(self):
        text, _ = skillsbot.bearbeite("/hilfe", 1)
        for wort in ("/lage", "/spur NAME", "/strategien", "/indikatoren",
                     "/markt", "/bericht"):
            self.assertIn(wort, text)
        self.assertNotIn("<b>", text)

    def test_ausfall_der_handelsseite_ist_kein_traceback(self):
        # Die Handelsseite faellt aus (Import kaputt, Modul fehlt) - dann steht
        # ein Hinweis da und der Verweis auf den Handelsbot, kein Traceback.
        import handel_befehle
        with patch.object(handel_befehle, "_handel",
                          side_effect=RuntimeError("Handelsseite kaputt")):
            text, _ = skillsbot.bearbeite("/lage", 1)
        self.assertIn("nicht lesbar", text)
        self.assertIn("Handelsbot", text)


class HandelsbefehleDurchreicherTest(unittest.TestCase):
    def test_spurliste_nimmt_dauerlauf_spuren(self):
        # handel_befehle holt die Liste ueber befehle.py aus dauerlauf.SPUREN;
        # nur wenn das faellt, gilt die eigene Rueckfall-Liste.
        import handel_befehle as h
        with patch.object(h, "_handel") as m:
            m.return_value.spuren.return_value = ["eins", "zwei"]
            self.assertEqual(h._spurliste(), ["eins", "zwei"])
        with patch.object(h, "_handel", side_effect=RuntimeError("kaputt")):
            self.assertEqual(h._spurliste(), list(h.SPUREN))


class ReadOnlyTest(unittest.TestCase):
    def test_paper_does_not_claim_live_positions(self):
        import handel_befehle as h
        with tempfile.TemporaryDirectory() as t, patch.object(h, 'HANDEL', Path(t)):
            for spur, mode in [('xperp', 'papier'), ('scanner', 'live')]:
                folder = Path(t) / spur
                folder.mkdir()
                (folder / 'zustand.json').write_text(json.dumps({'modus': mode, 'positionen': [{'inst': spur + '-MARKER'}]}))
            text = h.status(papier=True)
        self.assertIn('xperp-MARKER', text)
        self.assertNotIn('scanner-MARKER', text)

    def test_bad_prognose_arguments_never_spawn(self):
        import handel_befehle as h
        with patch('subprocess.run', side_effect=AssertionError('spawn verboten')):
            for text in ('/prognose 0', '/prognose -1', '/prognose 201', '/prognose 2 --live'):
                self.assertIn('Syntax', h.prognose(text))

    def test_swap_stand_wird_gelesen_nicht_behauptet(self):
        # /status meldete SWAP bis zum 12.09.2026 aus einer festen Zeile im
        # Code ("bewachte Anbindung unvollstaendig"). Eine feste Zeile altert
        # still. Hier muss der Stand aus der Datei der Spur kommen.
        import handel_befehle as h
        with tempfile.TemporaryDirectory() as t, patch.object(h, 'HANDEL', Path(t)):
            swap = Path(t) / 'swap'
            swap.mkdir()
            (swap / 'zustand.json').write_text(json.dumps(
                {'modus': 'papier', 'letzter_lauf': '2026-09-12T17:00:00+00:00',
                 'positionen': [{'inst': 'CHIP-USDT-SWAP-MARKER'}]}))
            (swap / 'wachen.json').write_text(json.dumps(
                {'handel_erlaubt': False, 'freigabe': {'erfuellt': False}}))
            text = h.status()
        self.assertIn('swap', text)
        self.assertIn('CHIP-USDT-SWAP-MARKER', text)
        self.assertIn('handel_erlaubt=False', text)
        self.assertIn('Freigabe erfuellt=False', text)

    def test_swap_ohne_wachen_sagt_unbekannt_statt_gesperrt(self):
        # Fehlt die Datei, ist die Lage unbekannt - nicht "gesperrt". Wer
        # "gesperrt" liest, hoert auf zu pruefen.
        import handel_befehle as h
        with tempfile.TemporaryDirectory() as t, patch.object(h, 'HANDEL', Path(t)):
            text = h.status()
        self.assertIn('SWAP: wachen.json nicht lesbar', text)
        self.assertNotIn('Live gesperrt', text)

    def test_status_startet_nichts(self):
        # Status ist ein Leser: kein Unterprozess, kein Broker, keine Order.
        import handel_befehle as h
        with patch('subprocess.run', side_effect=AssertionError('spawn verboten')):
            self.assertIn('Dateistand', h.status())
