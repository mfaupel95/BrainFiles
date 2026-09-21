import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillsbot as s

BEISPIEL = """model:
  default: auto/smart
  provider: smart
  base_url: http://127.0.0.1:20128/v1
providers:
  smart:
    api: http://127.0.0.1:20128/v1
    key_env: IRGENDEIN_KEY
    models:
      auto/smart:
        context_length: 400000
      auto/klein:
        context_length: 8000
    default_model: auto/smart
fallback_providers:
  - provider: nous
    model: deepseek/deepseek-v4.1-flash
  - provider: ollama-launch
    model: qwen35-8k:cpu
delegation:
  model: deepseek/deepseek-v4-flash-0731
  provider: nous
"""


NUR_MODELL = """model:
  default: x
  provider: y
"""


def _hash(pfad):
    with open(pfad, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class ModellBefehl(unittest.TestCase):
    def _config(self, inhalt):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "config.yaml"
        p.write_text(inhalt, encoding="utf-8")
        return str(p)

    def test_echte_config_wird_gelesen(self):
        """Kein Nachbau: der Befehl liest die echte Hermes-config."""
        text = s.modell_text()
        self.assertIn("auto/smart", text)
        self.assertIn("ueber  smart", text)
        self.assertIn("Fallback:", text)

    def test_kontextlaenge_kommt_aus_dem_providerblock(self):
        text = s.modell_text(self._config(BEISPIEL))
        self.assertIn("Kontext: 400000 Token", text)

    def test_fallbackkette_in_reihenfolge(self):
        text = s.modell_text(self._config(BEISPIEL))
        self.assertIn("nous/deepseek/deepseek-v4.1-flash -> ollama-launch/qwen35-8k:cpu", text)

    def test_fehlende_kontextangabe_wird_gesagt(self):
        text = s.modell_text(self._config('model:\n  default: x\n  provider: y\n'))
        self.assertIn("nicht in der config angegeben", text)
        self.assertIn("x  ueber  y", text)

    def test_nicht_lesbare_datei_ergibt_hinweis(self):
        text = s.modell_text(str(Path(tempfile.gettempdir()) / "gibt-es-nicht.yaml"))
        self.assertIn("nicht lesbar", text)

    def test_delegationsmodell_wird_genannt(self):
        """Subagenten fahren ein eigenes Modell - /model muss es zeigen.

        Seit 21.09.2026 steht das Haus auf nous/deepseek-v4-flash-0731 (vorher
        anthropic/claude-opus-5); wer nach dem Modell fragt, meint haeufig genau
        die Delegation.
        """
        text = s.modell_text(self._config(BEISPIEL))
        self.assertIn("Subagenten: deepseek/deepseek-v4-flash-0731 ueber nous", text)

    def test_ohne_delegationsblock_keine_zeile(self):
        """Eine Config ohne delegation: darf keine leere Zeile erfinden."""
        text = s.modell_text(self._config(NUR_MODELL))
        self.assertNotIn("Subagenten:", text)

    def test_echte_config_nennt_das_delegationsmodell(self):
        """Gegen die ECHTE Hermes-config: der Haus-Wert muss ankommen."""
        text = s.modell_text()
        self.assertIn("Subagenten:", text)

    def test_hilfe_kennt_den_befehl(self):
        self.assertIn("/model", s.hilfe_text())

    def test_bearbeite_model_ruft_kein_a2a(self):
        """Die Auskunft kommt aus der Datei, nicht vom Agenten."""
        with patch.object(s, "_a2a_ruf", side_effect=AssertionError("kein A2A-Aufruf")):
            antwort, kontext = s.bearbeite("/model", 424242)
        self.assertIn("auto/smart", antwort)


class ModellBefehlSchreibtNichts(unittest.TestCase):
    """Eine Auskunft darf die Hermes-config nicht anfassen."""

    @classmethod
    def setUpClass(cls):
        cls.pfad = s.CONFIG_HERMES
        cls.vorher = _hash(cls.pfad)

    @classmethod
    def tearDownClass(cls):
        if _hash(cls.pfad) != cls.vorher:
            raise AssertionError("config.yaml wurde veraendert - /model muss lesend bleiben")


if __name__ == "__main__":
    unittest.main()
