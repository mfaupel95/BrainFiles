import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillsbot as s

class Sicherheit(unittest.TestCase):
    def test_probe_telegram_error_is_failure(self):
        with patch.object(s, 'bereit', return_value=[]), patch.object(s, 'token', return_value='test'), patch.object(s, '_ruf', side_effect=RuntimeError('offline')), patch.object(s, 'karten_skills', return_value=['test']), patch.object(s, 'frage', return_value=('PONG', None)), contextlib.redirect_stdout(io.StringIO()):
            self.assertNotEqual(s.probe(), 0)

    def test_plaintext_chunks_preserve_special_characters(self):
        text = 'a' * 3999 + '&<' + '🙂' * 3000
        with patch.object(s, '_ruf') as call:
            s.sende(1, text)
        chunks = [c.args[1] for c in call.call_args_list]
        self.assertEqual(''.join(c['text'] for c in chunks), text)
        self.assertTrue(all(len(c['text'].encode('utf-16-le')) // 2 <= 4000 for c in chunks))
        self.assertTrue(all('parse_mode' not in c for c in chunks))

    def test_lock_never_signals_process_and_rejects_second(self):
        with tempfile.TemporaryDirectory() as d, patch.object(s, 'PID_PFAD', str(Path(d)/'bot.pid')), patch.object(s.os, 'kill', side_effect=AssertionError('no process signals')):
            with s.Sperre():
                with self.assertRaises(s.SkillsBotFehler):
                    with s.Sperre():
                        pass

    def test_shared_token_cannot_start_poller(self):
        with patch.object(s, '_variable', return_value='same'), patch.object(s, '_nachrichten', side_effect=AssertionError('shared polling forbidden')):
            with self.assertRaises(s.SkillsBotFehler):
                s.schleife()

    def test_lock_can_be_reused_after_exit(self):
        with tempfile.TemporaryDirectory() as d, patch.object(s, 'PID_PFAD', str(Path(d)/'bot.pid')):
            with s.Sperre():
                pass
            with s.Sperre():
                pass
