"""Bot ohne Befehlswort ansprechen - `name: auftrag` und `@name auftrag`.

ANLASS (21.10.2026, Auftrag Max): "/bot NAME NACHRICHT ist super umstaendlich."
Am Handy ist das Befehlswort mit Unterstrich das Hindernis, nicht der Bot.

Geprueft wird die REGEL, nicht eine Namensliste:
  - ein BEKANNTES Profil am Anfang adressiert es (Doppelpunkt oder @),
  - ein UNBEKANNTES Wort startet keinen Bot (ein Tippfehler darf keinen
    fremden Agenten wecken und keine 5-Minuten-Frist kosten),
  - ein Doppelpunkt mitten im Satz ist Freitext,
  - explizit geschriebener Name schlaegt den gerade aktiven Bot,
  - `/b` ist `/bot`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BUS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUS))
import skillsbot as s                                             # noqa: E402

PROFILE = s.bot_namen()


class AdressatTest(unittest.TestCase):
    """Die reine Funktion - kein Netz, kein Prozess, keine Datei."""

    def test_profil_mit_doppelpunkt(self):
        name = PROFILE[0]
        self.assertEqual(s._adressat_am_anfang("%s: Was steht im Buch?" % name),
                         (name, "Was steht im Buch?"))

    def test_profil_mit_klammeraffe(self):
        name = PROFILE[0]
        self.assertEqual(s._adressat_am_anfang("@%s Was steht im Buch?" % name),
                         (name, "Was steht im Buch?"))

    def test_name_ohne_auftrag_schaltet_nur_ein(self):
        name = PROFILE[0]
        self.assertEqual(s._adressat_am_anfang("%s:" % name), (name, ""))
        self.assertEqual(s._adressat_am_anfang("@%s" % name), (name, ""))

    def test_grossschreibung_ist_egal(self):
        """Max tippt am Handy; Grossschreibung ist keine falsche Adresse."""
        name = PROFILE[0].upper()
        treffer = s._adressat_am_anfang("%s: frage" % name)
        self.assertIsNotNone(treffer, "Grossschreibung wurde nicht erkannt")
        self.assertEqual(treffer[0], PROFILE[0].lower())

    def test_unbekanntes_wort_startet_keinen_bot(self):
        for text in ("quatsch: frage", "@quatsch frage", "handel: frage"):
            self.assertIsNone(s._adressat_am_anfang(text), text)

    def test_tippfehler_im_namen_startet_keinen_bot(self):
        name = PROFILE[0]
        self.assertIsNone(s._adressat_am_anfang("%sx: frage" % name))
        self.assertIsNone(s._adressat_am_anfang("@%sx frage" % name))

    def test_doppelpunkt_im_satz_ist_freitext(self):
        for text in ("Ich sage: das war gut", "Bericht: alles gruen",
                     "Was steht im Buch?", ""):
            self.assertIsNone(s._adressat_am_anfang(text), text)

    def test_rueckgabe_nennt_nur_echte_profile(self):
        """Gegenprobe: die Funktion kann nichts erfinden, was /bots nicht kennt."""
        for text in ("%s: x" % PROFILE[0], "@%s x" % PROFILE[-1]):
            treffer = s._adressat_am_anfang(text)
            self.assertIn(treffer[0], PROFILE)


class VerdrahtungTest(unittest.TestCase):
    """bearbeite() nimmt die Adresse an - mit gefaelschtem Sprechweg."""

    def setUp(self):
        self.gefragt = []
        self.gesendet = []
        self.ziele = {}

        def fragen(name, text):
            self.gefragt.append((name, text))
            return "Antwort von %s" % name

        def senden(chat, text):
            self.gesendet.append(text)

        self.patches = [
            patch.object(s, "_bot_fragen", fragen),
            patch.object(s, "sende", senden),
            patch.object(s, "_ziel_lesen", lambda chat: self.ziele.get(str(chat))),
            patch.object(s, "_ziel_setzen",
                         lambda chat, name: self.ziele.__setitem__(str(chat), name)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_adresse_geht_direkt_an_das_profil(self):
        name = PROFILE[0]
        antwort, _ = s.bearbeite("%s: Was steht im Buch?" % name, 12345)
        self.assertEqual(self.gefragt, [(name, "Was steht im Buch?")])
        self.assertIn(name, antwort)

    def test_aktiver_bot_wird_von_klarem_namen_ueberstimmt(self):
        """Wer den Namen hinschreibt, meint ihn - auch wenn ein anderer aktiv ist."""
        aktiv, genannt = PROFILE[0], PROFILE[-1]
        self.ziele["99"] = aktiv
        s.bearbeite("%s: frage" % genannt, 99)
        self.assertEqual(self.gefragt, [(genannt, "frage")])
        self.assertEqual(self.ziele["99"], aktiv, "der aktive Bot darf bleiben")

    def test_b_ist_bot(self):
        name = PROFILE[0]
        antwort_b, _ = s.bearbeite("/b %s frage" % name, 1)
        antwort_voll, _ = s.bearbeite("/bot %s frage" % name, 2)
        self.assertEqual(self.gefragt, [(name, "frage"), (name, "frage")])
        self.assertEqual(antwort_b, antwort_voll)

    def test_freitext_ohne_namen_ruft_keinen_bot(self):
        """Ein Satz bleibt ein Satz - sonst waere jede Nachricht ein Bot-Start."""
        with patch.object(s, "_freitext_im_thread", lambda *a, **k: None):
            s.bearbeite("Ich sage: das war gut", 3)
        self.assertEqual(self.gefragt, [])


class HilfeTest(unittest.TestCase):

    def test_hilfe_nennt_die_neue_form(self):
        text = s.hilfe_text() if hasattr(s, "hilfe_text") else None
        if text is None:
            quelle = Path(s.__file__).read_text(encoding="utf-8")
            text = quelle
        self.assertIn("NAME: AUFTRAG", text)
        self.assertIn("/b =", text)


if __name__ == "__main__":
    unittest.main()
