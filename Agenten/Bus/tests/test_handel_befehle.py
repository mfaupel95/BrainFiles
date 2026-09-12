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
