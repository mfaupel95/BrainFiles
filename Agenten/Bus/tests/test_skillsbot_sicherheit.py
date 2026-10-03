import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
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

class BotBefehle(unittest.TestCase):
    """/bots und /bot NAME - die Repo-Bots sind per Telegram erreichbar.

    Ein Test darf nie einen echten hermes.exe starten: der Kaltstart dauert
    30-60 s und schreibt in echte Sitzungsdateien. Der Aufruf wird gemockt,
    geprueft wird das Routing (Name gehoert zur Profilliste, sonst kein Ruf).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kontext = patch.object(s, "KONTEXT_PFAD",
                                    str(Path(self.tmp.name) / "kontext.json"))
        self.kontext.start()
        self.profile = patch.object(s, "_bot_profil_ordner",
                                    return_value=str(self.tmp.name))
        self.profile.start()
        # Zwei Profile auf der Platte, wie sie Hermes anlegen wuerde.
        for n in ("openterminal", "scrapling"):
            (Path(self.tmp.name) / n).mkdir()
            (Path(self.tmp.name) / n / "config.yaml").write_text("x")
        self.gesendet = []
        self.sende = patch.object(s, "sende",
                                  side_effect=lambda chat, text: self.gesendet.append(text))
        self.sende.start()

    def tearDown(self):
        self.sende.stop()
        self.profile.stop()
        self.kontext.stop()
        self.tmp.cleanup()

    def test_bots_listet_profile_mit_anzahl(self):
        text, _ = s.bearbeite("/bots", 1)
        self.assertIn("openterminal", text)
        self.assertIn("scrapling", text)
        self.assertIn("(2)", text)          # die Anzahl ist die Kontrolle

    def test_bots_ohne_profile_meldet_leere_liste(self):
        with patch.object(s, "_bot_profil_ordner",
                          return_value=str(Path(self.tmp.name) / "leer")):
            text, _ = s.bearbeite("/bots", 1)
        self.assertIn("Keine Profile", text)

    def test_bot_ohne_name_schaltet_ab_und_zeigt_die_syntax(self):
        """/bot allein ist jetzt "Bot aus" (Auftrag Max 03.10.2026).

        Vorher stand hier die Syntaxhilfe. Beides gehoert in EINEN Text:
        abschalten UND die Form zeigen, damit /bot nicht stumm wird.
        """
        with patch.object(s, "_bot_fragen") as frage, \
                patch.object(s, "_ziel_setzen", return_value=None) as ziel:
            text, _ = s.bearbeite("/bot", 1)
            frage.assert_not_called()
            ziel.assert_called_once_with(1, None)
        self.assertIn("abgeschaltet", text)
        self.assertIn("Syntax: /bot NAME", text)
        self.assertIn("/bots", text)

    def test_bot_unbekannter_name_startet_nichts(self):
        with patch.object(s, "_bot_fragen") as frage:
            text, _ = s.bearbeite("/bot gibt-es-nicht hallo", 1)
            frage.assert_not_called()
        self.assertIn("Kein Profil", text)

    def test_bot_ohne_nachricht_schaltet_ein_startet_nichts(self):
        """/bot NAME ohne Auftrag: Bot wird Adressat, es startet NOCH nichts.

        Genau hier lag der Befund vom 03.10.2026: /bot NAME fragte nach dem
        Auftrag (Syntaxhilfe), der danach gesendete Auftrag - am Handy ein
        Bild - ging an den Hauptagenten. Jetzt wird der Bot eingeschaltet
        und der naechste Freitext nimmt ihn (test_skillsbot_zielmodus).
        """
        with patch.object(s, "_bot_fragen") as frage, \
                patch.object(s, "_ziel_setzen") as ziel:
            text, _ = s.bearbeite("/bot openterminal", 1)
            frage.assert_not_called()
            ziel.assert_called_once_with(1, "openterminal")
        self.assertIn("Adressat", text)
        self.assertIn("/bot aus", text)

    def test_bot_gueltig_ruft_das_profil(self):
        with patch.object(s, "_bot_fragen", return_value="die Antwort") as frage:
            text, kontext = s.bearbeite("/bot scrapling was ist neu?", 1)
        frage.assert_called_once_with("scrapling", "was ist neu?")
        self.assertEqual(text, "die Antwort")
        self.assertIsNone(kontext)          # A2A-Kontext bleibt unberuehrt

    def test_bot_antwortet_nur_dem_eigenen_profil(self):
        # Der Name ist das ERSTE Wort; der Rest ist die Nachricht. Ein zweiter
        # Name in der Nachricht darf nicht als Ziel gelten.
        with patch.object(s, "_bot_fragen", return_value="ok") as frage:
            s.bearbeite("/bot openterminal und scrapling?", 1)
        frage.assert_called_once_with("openterminal", "und scrapling?")

    def test_bot_fehler_kommt_als_meldung(self):
        with patch.object(s, "_bot_fragen",
                          side_effect=s.SkillsBotFehler("weg")) as frage:
            text, _ = s.bearbeite("/bot scrapling hallo", 1)
        frage.assert_called_once()
        self.assertIn("gescheitert", text)
        self.assertIn("weg", text)

    def test_bot_kuendigt_vorher_an(self):
        # Kaltstart dauert 30-60 s: ohne Zwischenmeldung wirkt der Bot tot.
        with patch.object(s, "_bot_fragen", return_value="x"):
            s.bearbeite("/bot scrapling hallo", 1)
        self.assertTrue(any("dauern" in g for g in self.gesendet),
                        self.gesendet)

    def test_hilfe_nennt_bots(self):
        self.assertIn("/bots", s.hilfe_text())
        self.assertIn("/bot NAME", s.hilfe_text())

class BotFragenProzess(unittest.TestCase):
    """_bot_fragen: der echte hermes.exe-Aufruf wird NIE ausgefuehrt, aber der
    Aufruf muss die richtige Form haben (Name als -p, Text als -q, saubere
    Umgebung ohne PYTHONHOME/PYTHONPATH)."""
    def test_hermes_umgebung_raeumt_auf(self):
        with patch.dict(s.os.environ, {"PYTHONHOME": "x", "PYTHONPATH": "y"}):
            env = s._hermes_umgebung()
        self.assertNotIn("PYTHONHOME", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertTrue(env["HERMES_HOME"].endswith(
            os.path.join("Agenten", "Hermes")))

    def _popen(self, stdout="PONG\n", stderr="", code=0):
        """Ein Attrappen-Prozess fuer _bot_fragen.

        Die Tests hier mocken `subprocess.run`, der Code benutzt aber
        `subprocess.Popen` + `communicate` (seit dem Frist-Umbau vom
        21.09.2026: `run(timeout=)` wuerde den Bot mitten in der Arbeit
        toeten). Ein Run-Mock trifft darum nichts - der Test startete einen
        ECHTEN openmontinal-Bot (43 s Kaltstart pro Aufruf) und wertete
        dessen Antwort gegen 'PONG'. Deshalb wird Popen ersetzt.
        """
        ziel = {}

        def fake(argv, **kw):
            ziel["argv"] = argv

            class R:
                returncode = code

                def communicate(self, timeout=None):
                    return stdout, stderr

                def kill(self):
                    ziel["gekillt"] = True

            return R()

        return patch.object(s.subprocess, "Popen", side_effect=fake), ziel

    def test_subprozessform(self):
        mock, ziel = self._popen()
        with mock:
            antwort = s._bot_fragen("openterminal", "frage")
        argv = ziel["argv"]
        self.assertIn("-p", argv)
        self.assertEqual(argv[argv.index("-p") + 1], "openterminal")
        self.assertEqual(argv[argv.index("-q") + 1], "frage")
        self.assertEqual(antwort, "PONG")

    def test_session_id_zeile_wird_entfernt(self):
        mock, _ = self._popen(stdout="session_id: 123" + chr(10) + "PONG" + chr(10))
        with mock:
            self.assertEqual(s._bot_fragen("openterminal", "x"), "PONG")

    def test_fehlercode_nennt_grund(self):
        mock, _ = self._popen(stdout="", stderr="kaputt", code=1)
        with mock:
            with self.assertRaises(s.SkillsBotFehler) as k:
                s._bot_fragen("openterminal", "x")
        self.assertIn("kaputt", str(k.exception))

    def test_zeitlimit_bricht_ab_und_sagt_es(self):
        """Nach der Frist wird abgebrochen - und die Meldung sagt, dass der
        Auftrag NICHT gescheitert ist, sondern dort weiterlaeuft."""
        class R:
            returncode = None

            def communicate(self, timeout=None):
                if timeout is not None:
                    raise s.subprocess.TimeoutExpired("hermes", timeout)
                return "", ""

            def kill(self):
                pass

        with patch.object(s.subprocess, "Popen", return_value=R()), \
                patch.object(s, "BOT_FRIST_S", 5):
            with self.assertRaises(s.SkillsBotFehler) as k:
                s._bot_fragen("openterminal", "x")
        text = str(k.exception)
        self.assertIn("nicht geantwortet", text)


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

class NachrichtenZuverlaessigkeit(unittest.TestCase):
    """Eine fehlgeschlagene Nachricht darf nicht verloren gehen.

    Seit 19.09.2026: Ein NETZfehler (Gateway kurz weg, Port zu) wird
    wiederholt - der Offset bleibt stehen, der naechste Poll holt die
    Nachricht erneut. Ein FACHlicher Fehler wird einmal gemeldet und die
    Nachricht verworfen (eine Wiederholung koennte eine bereits angenommene
    Aufgabe doppelt ausfuehren). Der Log-Eintrag traegt den Fehlergrund.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.log_datei = t / "log.jsonl"
        self.offset_datei = t / "offset.json"
        self.pfad = patch.object(s, "LOG_PFAD", str(self.log_datei))
        self.pfad.start()
        self.offset = patch.object(s, "OFFSET_PFAD", str(self.offset_datei))
        self.offset.start()
        self.kontext = patch.object(s, "KONTEXT_PFAD", str(t / "kontext.json"))
        self.kontext.start()
        self.schlaf = patch.object(s.time, "sleep")
        self.schlaf.start()
        self.var = patch.object(s, "_variable",
                                side_effect=lambda n: {
                                    "SKILLSBOT_TOKEN": "bot-a",
                                    "TELEGRAM_TOKEN": "bot-b"}[n])
        self.var.start()
        self.chat = patch.object(s, "chat_id", return_value=7)
        self.chat.start()
        self.gesendet = []

    def tearDown(self):
        self.chat.stop()
        self.var.stop()
        self.schlaf.stop()
        self.kontext.stop()
        self.offset.stop()
        self.pfad.stop()
        self.tmp.cleanup()

    def nachricht(self, uid=42):
        return {"update_id": uid,
                "message": {"chat": {"id": 7}, "text": "hallo"}}

    def start(self, nachrichten, bearbeite):
        """schleife() mit gemockten Polls fahren; KeyboardInterrupt beendet."""
        with patch.object(s, "sende",
                          side_effect=lambda chat, text:
                          self.gesendet.append((chat, text))), \
                patch.object(s, "_nachrichten", side_effect=nachrichten), \
                patch.object(s, "bearbeite", side_effect=bearbeite):
            with self.assertRaises(KeyboardInterrupt):
                s.schleife()

    def test_netzfehler_nachricht_geht_nicht_verloren(self):
        # Poll 1 bringt die Nachricht (offset 0), bearbeite scheitert mit
        # Netzfehler -> Offset bleibt 0, Poll 2 liefert sie erneut, diesmal ok.
        aufrufe = {"n": 0}

        def nachrichten(offset):
            aufrufe["n"] += 1
            if aufrufe["n"] == 1:
                return [self.nachricht()]          # offset 0: kommt
            if aufrufe["n"] == 2 and offset == 0:  # Offset stehen geblieben
                return [self.nachricht()]
            raise KeyboardInterrupt()

        def bearbeite(text, chat):
            if aufrufe["n"] == 1:
                raise urllib.error.URLError("gateway weg")
            return "die antwort", None

        self.start(nachrichten, bearbeite)
        self.assertEqual(self.gesendet, [(7, "die antwort")])
        with open(self.offset_datei, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), 43)    # verarbeitet, kein Verlust
        zeilen = self.log_datei.read_text(encoding="utf-8").splitlines()
        fehler = [z for z in zeilen if '"fehler"' in z]
        self.assertTrue(fehler, "Netzfehler muss mit Grund geloggt sein")
        self.assertIn("gateway weg", fehler[0])

    def test_fachfehler_wird_einmal_gemeldet_und_verworfen(self):
        aufrufe = {"n": 0}

        def nachrichten(offset):
            aufrufe["n"] += 1
            if aufrufe["n"] == 1:
                return [self.nachricht()]
            raise KeyboardInterrupt()

        def bearbeite(text, chat):
            raise s.SkillsBotFehler("kaputt")

        self.start(nachrichten, bearbeite)
        self.assertEqual(self.gesendet, [(7, "Fehler: kaputt")])
        with open(self.offset_datei, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), 43)    # verworfen, kein Endlos-Poll

    def test_netzfehler_fachfehler_unterscheidung(self):
        self.assertTrue(s._ist_netzfehler(
            urllib.error.URLError("weg")))
        self.assertTrue(s._ist_netzfehler(ConnectionError("weg")))
        self.assertTrue(s._ist_netzfehler(TimeoutError("weg")))
        self.assertFalse(s._ist_netzfehler(s.SkillsBotFehler("kaputt")))
        self.assertFalse(s._ist_netzfehler(ValueError("kaputt")))

    def test_log_traegt_fehlergrund(self):
        s._log(7, "Test", 1.0, "fehler", 0, fehler="grund-xyz")
        zeilen = self.log_datei.read_text(encoding="utf-8").splitlines()
        self.assertTrue(any('"fehler": "grund-xyz"' in z for z in zeilen))
