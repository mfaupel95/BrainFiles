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

class SkillAusfuehren(unittest.TestCase):
    """`/run NAME` fuehrt einen Skill aus - und zwar nur einen echten.

    Die Gefahr ist nicht der Aufruf, sondern ein geratener: ein Teiltreffer,
    ein Tippfehler oder ein Skill, der einem anderen System gehoert. Jeder
    dieser Faelle muss OHNE A2A enden - sonst laeuft irgendein Skill, und
    niemand erfaehrt welcher.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kontext = patch.object(s, "KONTEXT_PFAD",
                                    str(Path(self.tmp.name) / "kontext.json"))
        self.kontext.start()
        self.gesendet = []
        self.sende = patch.object(s, "sende",
                                  side_effect=lambda chat, text: self.gesendet.append(text))
        self.sende.start()

    def tearDown(self):
        self.sende.stop()
        self.kontext.stop()
        self.tmp.cleanup()

    def test_ohne_namen_keine_ausfuehrung(self):
        import skillkatalog
        with patch.object(skillkatalog, "finde") as finde, \
                patch.object(s, "frage") as frage:
            text, _ = s.bearbeite("/run", 1)
            finde.assert_not_called()
            frage.assert_not_called()
        self.assertIn("Syntax: /run NAME", text)

    def test_unbekannter_name_geht_nicht_an_a2a(self):
        import skillkatalog
        with patch.object(skillkatalog, "finde", return_value=None), \
                patch.object(s, "frage") as frage:
            text, _ = s.bearbeite("/run gibt-es-nicht", 1)
            frage.assert_not_called()
        self.assertIn("Kein eindeutiger Skill", text)

    def test_nicht_ladbarer_skill_wird_abgelehnt(self):
        import skillkatalog
        eintrag = {"name": "fremd", "gruppe": "anderes-system", "ladbar": False}
        with patch.object(skillkatalog, "finde", return_value=eintrag), \
                patch.object(s, "frage") as frage:
            text, _ = s.bearbeite("/run fremd", 1)
            frage.assert_not_called()
        self.assertIn("anderen System", text)

    def test_gueltiger_skill_wird_ausgefuehrt(self):
        import skillkatalog
        eintrag = {"name": "systemdiagnose", "gruppe": "brainfiles",
                   "ladbar": True}
        with patch.object(skillkatalog, "finde", return_value=eintrag), \
                patch.object(s, "frage", return_value=("erledigt", "k1")) as frage:
            text, kontext = s.bearbeite("/run systemdiagnose schnell", 1)
        # Der Auftrag muss den Skill NAMEN tragen - sonst fuehrt der Agent
        # irgendetwas aus, und der Nutzer meint, es sei der Skill gewesen.
        (auftrag,) = frage.call_args.args[:1]
        self.assertIn("systemdiagnose", auftrag)
        self.assertIn("schnell", auftrag)
        self.assertEqual(text, "erledigt")
        self.assertEqual(kontext, "k1")
        # Vorher ansagen, sonst wirkt der Bot haengend (Ausfuehrung bis 5 min).
        self.assertTrue(any("systemdiagnose" in g for g in self.gesendet),
                        self.gesendet)

    def test_hilfe_nennt_run(self):
        self.assertIn("/run NAME", s.hilfe_text())

class OhneDenken(unittest.TestCase):
    """Die Telegram-Antwort darf nicht halb aus Denkblock bestehen."""

    def test_block_wird_entfernt(self):
        roh = "\U0001f4ad **Reasoning:**\n```\nintern\n```\nDie Antwort"
        self.assertEqual(s.ohne_denken(roh), "Die Antwort")

    def test_text_vor_dem_block_bleibt(self):
        roh = "Kopf\n\U0001f4ad **Reasoning:**\n```\nNUR-INTERN\n```\nAntwort"
        aus = s.ohne_denken(roh)
        self.assertIn("Kopf", aus)
        self.assertIn("Antwort", aus)
        self.assertNotIn("NUR-INTERN", aus)
        self.assertNotIn("\U0001f4ad", aus)

    def test_ohne_block_unveraendert(self):
        self.assertEqual(s.ohne_denken("nur Text"), "nur Text")

    def test_abgeschnittener_block_kostet_keine_antwort(self):
        # Kein schliessendes ``` : nichts erfinden, aber auch nichts verlieren.
        roh = "Kopf\n\U0001f4ad **Reasoning:**\n```\nabgeschnitten"
        self.assertEqual(s.ohne_denken(roh), "Kopf")
        self.assertEqual(s.ohne_denken("\U0001f4ad **Reasoning:**"), "\U0001f4ad **Reasoning:**")

    def test_leerer_text(self):
        self.assertEqual(s.ohne_denken(""), "")
