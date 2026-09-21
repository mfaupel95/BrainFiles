"""Tests fuer den Skill-Katalog (Agenten/Bus/skillkatalog.py).

WARUM DIESE TESTS
-----------------
Der Katalog beantwortet "was kann der Agent eigentlich?" aus einem
Telegram-Chat. Faellt er still aus, sucht man Faehigkeiten, die es gibt, und
findet sie nicht - oder schlimmer: er zeigt stillgelegte Skills als geladen.

Deshalb pruefen die Tests vier Dinge, die alle schon einmal schiefgingen:
1. Er liest die SKILL.md-Dateien (nicht die Agent-Card, die Werkzeugsets
   aufzaehlt).
2. Stillgelegte Skills (.archive) erscheinen NICHT.
3. Der Text passt in Telegram-Nachrichten (4096 Zeichen).
4. Der Bot-Befehl /skills haengt wirklich am Katalog.
5. Skills fremder Systeme (`platforms: [macos]`) erscheinen NICHT als geladen -
   sonst behauptet der Katalog Faehigkeiten, die es auf diesem Rechner nicht
   gibt (15.09.2026: 67 auf der Platte, 58 geladen).
"""

import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.dirname(HIER)
if BUS not in sys.path:
    sys.path.insert(0, BUS)

import skillkatalog  # noqa: E402


class KatalogTest(unittest.TestCase):

    def test_findet_bekannte_skills(self):
        namen = [e["name"] for e in skillkatalog.eintraege()]
        for erwartet in ("handel-spuren", "projectatlas", "brainfiles-auftrag"):
            self.assertIn(erwartet, namen)

    def test_kein_stillgelegter_skill(self):
        # .archive ist die Ablage der 70 aussortierten Skills (11.09.2026).
        # Wer dort liegt, wird NICHT geladen - und darf nicht wie geladen
        # aussehen.
        pfade = [e["pfad"] for e in skillkatalog.eintraege()]
        self.assertTrue(pfade, "Katalog ist leer")
        for p in pfade:
            self.assertNotIn(".archive", p.replace("\\", "/"))

    def test_fremdes_system_wird_nicht_als_geladen_gezeigt(self):
        # Skills mit platforms: [macos] bzw. [linux, macos] laedt Hermes auf
        # Windows nicht. Der Katalog darf sie nicht als Faehigkeit ausgeben.
        #
        # Seit dem Ausmisten am 21.09.2026 liegt der apple-Baum im Archiv
        # (nie benutzt), deshalb wird nicht mehr auf einen festen Namen
        # geprueft: der Test fragt, ob JEDER nicht-ladbare Eintrag aus der
        # Faehigkeitsliste verschwindet UND in der Schlusszeile auftaucht.
        # Ein Test, der an einem einzelnen Skillnamen haengt, geht beim
        # naechsten Aufraeumen wieder kaputt.
        eintraege = skillkatalog.eintraege()
        ladbar = [e["name"] for e in eintraege if e["ladbar"]]
        fremde = [e["name"] for e in eintraege if not e["ladbar"]]
        for fremd in fremde:
            self.assertNotIn(fremd, ladbar)
        # Verschweigen waere die andere Haelfte des Fehlers: die Liste nennt
        # sie in der Schlusszeile.
        text = skillkatalog.katalog()
        if fremde:
            self.assertIn("Hier nicht geladen", text)
            for fremd in fremde:
                self.assertIn(fremd, text)

    def test_katalog_ist_klartext(self):
        # Der SkillsBot sendet ohne parse_mode - HTML-Marken staenden
        # woertlich in der Telegram-Nachricht (so am 15.09.2026 gesehen).
        text = skillkatalog.katalog()
        self.assertNotIn("<b>", text)
        self.assertNotIn("</b>", text)

    def test_katalog_ohne_suchbegriff_passt_in_eine_nachricht(self):
        # Namen statt Saetze: 58 Skills in EINER Nachricht.
        text = skillkatalog.katalog()
        self.assertLessEqual(len(text), 4000)
        self.assertEqual(len(skillkatalog.katalog_bloecke()), 1)

    def test_suche_zeigt_die_beschreibung(self):
        text = skillkatalog.katalog("handel")
        self.assertIn("handel-spuren", text)
        self.assertIn("—", text)
        # Fremdes System bleibt auch bei der Suche draussen.
        self.assertNotIn("apple-notes", text)

    def test_plattformfilter_am_eigenen_baum(self):
        # Gegenprobe ohne die echte Bibliothek: ein Skill fuer ein fremdes
        # System und einer ohne platforms:-Eintrag.
        ordner = tempfile.mkdtemp(prefix="skillkatalog-")
        try:
            for name, kopf in (("nur-mac", "platforms: [macos]\n"),
                               ("ueberall", "")):
                pfad = os.path.join(ordner, name)
                os.makedirs(pfad)
                with open(os.path.join(pfad, "SKILL.md"), "w",
                          encoding="utf-8", newline="") as f:
                    f.write("---\nname: %s\ndescription: Test.\n%s---\n\nText\n"
                            % (name, kopf))
            lage = {e["name"]: e["ladbar"]
                    for e in skillkatalog.eintraege(ordner)}
            self.assertFalse(lage["nur-mac"])
            self.assertTrue(lage["ueberall"])
            text = skillkatalog.katalog(None, ordner)
            self.assertNotIn("  nur-mac", text)
            self.assertIn("  ueberall", text)
            self.assertIn("nur-mac", text)
        finally:
            shutil.rmtree(ordner, ignore_errors=True)

    def test_jeder_eintrag_hat_gruppe_und_beschreibung(self):
        for e in skillkatalog.eintraege():
            self.assertTrue(e["gruppe"], e)
            self.assertTrue(e["beschreibung"], e)
            self.assertLessEqual(len(e["beschreibung"]), 73, e)

    def test_katalog_ist_gruppiert_und_findbar(self):
        text = skillkatalog.katalog()
        self.assertIn("brainfiles", text)
        self.assertIn("handel-spuren", text)
        self.assertIn("/skill NAME", text)

    def test_filter_grenzt_ein(self):
        alle = skillkatalog.eintraege()
        treffer = skillkatalog.katalog("handel")
        # Weniger Zeilen als der volle Katalog, aber nicht leer.
        self.assertLess(len(treffer.splitlines()), len(skillkatalog.katalog().splitlines()))
        self.assertGreater(len(treffer.splitlines()), 1)
        self.assertTrue(any("handel" in e["name"] for e in alle))

    def test_bloecke_passen_in_telegram(self):
        for block in skillkatalog.katalog_bloecke():
            self.assertLessEqual(len(block), skillkatalog.BLOECKGROESSE)
        # Und es darf nichts verloren gehen: die Namen aller Skills stehen drin.
        zusammen = "\n".join(skillkatalog.katalog_bloecke())
        for e in skillkatalog.eintraege():
            self.assertIn(e["name"], zusammen)

    def test_volltext_liefert_den_skill(self):
        text = skillkatalog.volltext("handel-spuren")
        self.assertIn("handel-spuren", text)
        self.assertGreater(len(text), 500)

    def test_volltext_kuerzt_mit_hinweis(self):
        lang = skillkatalog.volltext("hermes-agent")
        if len(lang) > skillkatalog.TEXTGROESSE:
            self.assertIn("Zeichen fehlen", lang)

    def test_unbekannter_name_meldet_klar(self):
        text = skillkatalog.volltext("gibtesnicht")
        self.assertIn("Kein Skill", text)

    def test_teilname_ist_eindeutig_oder_leer(self):
        # "handel-spuren" existiert, ein Praefix darf nicht irgendeinen
        # anderen Skill liefern.
        e = skillkatalog.finde("handel-spuren")
        self.assertIsNotNone(e)
        self.assertEqual(e["name"], "handel-spuren")
        self.assertIsNone(skillkatalog.finde(""))


class BotAnbindungTest(unittest.TestCase):
    """/skills und /skill muessen am Katalog haengen, nicht an der alten Card."""

    def setUp(self):
        try:
            import skillsbot  # noqa: F401
        except Exception as fehler:                      # noqa: BLE001
            self.skipTest("skillsbot nicht importierbar: %s" % fehler)

    def test_skills_befehl_zeigt_den_katalog(self):
        import skillsbot
        antwort, _ = skillsbot.bearbeite("/skills", "test")
        self.assertIn("Skills", antwort)
        self.assertIn("brainfiles", antwort)
        # Die alte Fassung zaehlte Werkzeugsets auf - die kamen aus der
        # Agent-Card und hiessen "toolset.*".
        self.assertNotIn("toolset.", antwort)

    def test_skills_mit_suchbegriff(self):
        import skillsbot
        antwort, _ = skillsbot.bearbeite("/skills projectatlas", "test")
        self.assertIn("projectatlas", antwort)

    def test_skills_antwort_passt_als_klartext_nach_telegram(self):
        # Der SkillsBot sendet ohne parse_mode: HTML-Marken waeren sichtbar,
        # und ueber MAX_ZEICHEN wuerde sende() die Antwort zerschneiden.
        import skillsbot
        antwort, _ = skillsbot.bearbeite("/skills", "test")
        self.assertNotIn("<b>", antwort)
        self.assertLessEqual(len(antwort), skillsbot.MAX_ZEICHEN)

    def test_skill_befehl_gibt_volltext(self):
        import skillsbot
        antwort, _ = skillsbot.bearbeite("/skill projectatlas", "test")
        self.assertIn("ProjectAtlas", antwort)

    def test_leerer_skill_befehl_erklaert_sich(self):
        import skillsbot
        antwort, _ = skillsbot.bearbeite("/skill", "test")
        self.assertIn("Kein Skill", antwort)


if __name__ == "__main__":
    unittest.main(verbosity=2)
