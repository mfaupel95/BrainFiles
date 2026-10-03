"""Schreibweisen der lesenden Handelsbefehle (SkillsBot).

Anlass (01.10.2026): Max tippte am Handy `/strategie` - der Bot antwortete
"Kein SkillsBot-Befehl. /hilfe zeigt die Liste." (207 Zeichen im Protokoll).
Die Einzahl ist keine falsche Frage, sie ist eine andere Schreibweise
desselben Befehls. Ein anderer Name darf keine Auskunft kosten.

Geprueft wird die REGEL, nicht eine Liste: jeder Alias zeigt auf einen Befehl,
den `_handelsantwort` wirklich kennt, und ein unbekanntes Wort bleibt
unbekannt (sonst waere jeder Tippfehler still ein Befehl).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import skillsbot as s                                             # noqa: E402


class AliasTest(unittest.TestCase):

    def test_einzahl_ist_derselbe_befehl(self):
        self.assertEqual(s._handelsbefehl("/strategie"), "/strategien")
        self.assertEqual(s._handelsbefehl("/indikator"), "/indikatoren")

    def test_kurze_schreibweise(self):
        self.assertEqual(s._handelsbefehl("/strat"), "/strategien")

    def test_mehrzahl_bleibt_wie_sie_war(self):
        for w in ("/lage", "/live", "/bericht", "/spuren", "/strategien",
                  "/indikatoren", "/markt"):
            self.assertEqual(s._handelsbefehl(w), w)

    def test_unbekanntes_bleibt_unbekannt(self):
        for w in ("/quatsch", "strategie", "/strategien!", ""):
            self.assertIsNone(s._handelsbefehl(w), w)

    def test_jeder_alias_zeigt_auf_einen_echten_befehl(self):
        """Kein Alias darf ins Leere zeigen: _handelsantwort muss ihn kennen."""
        for alias in set(s.HANDELS_ALIASE.values()):
            try:
                antwort = s._handelsantwort(alias)
            except Exception as e:                                # noqa: BLE001
                self.fail("Alias %s nicht bedienbar: %s" % (alias, e))
            self.assertTrue(antwort, "leere Antwort fuer %s" % alias)

    def test_alias_liefert_den_bericht_nicht_nur_eine_meldung(self):
        """Die Antwort ist der Bericht, nicht der Hinweis auf /hilfe."""
        text = s._handelsantwort(s._handelsbefehl("/strategie"))
        self.assertIn("Runden", text)
        self.assertNotIn("Kein SkillsBot-Befehl", text)


if __name__ == "__main__":
    unittest.main()