"""SkillsBot: aktiver Bot-Modus (Auftrag Max 03.10.2026).

ANLASS (skillsbot.log, 03.10.2026 21:52): Max schickte "/bot openmontage"
OHNE Auftrag und danach ein Bild. Die Antwort auf "/bot openmontage" waren
71 Zeichen = "Was soll ich Bot openmontage fragen? Syntax: /bot openmontage
NACHRICHT", das Bild kam als "(Bild ohne Unterschrift)" mit 11 Zeichen
("Angenommen.") beim HAUPTAGENTEN an - der Bot wurde nie gefragt. Der Bot
war gesund: Port 9900 offen, A2A antwortete in 10 s, `_bot_fragen` lieferte
in 43 s PONG. "Der Bot antwortet nicht" war eine Bedienungsluecke, kein
Defekt.

Geprueft wird deshalb:
  - /bot NAME ohne Auftrag schaltet den Bot ein und SAGT das (keine
    Syntaxhilfe, die wie eine Fehlermeldung liest),
  - der naechste Freitext geht an diesen Bot, nicht an den Hauptagenten,
    und nach EINEM Auftrag ist er wieder abgeschaltet,
  - /bot aus schaltet ab, ein abgelaufenes Ziel gilt als keins,
  - ein unbekanntes Profil schaltet NICHTS ein,
  - ein unbekannter Slashbefehl nennt den aktiven Bot statt ihn zu
    verschlucken,
  - der Zielzustand liegt in EINER Datei je Chat (zwei Chats storen
    einander nicht).

Die Gegenprobe laeuft auf einer KOPIE von skillsbot.py im Temp-Ordner: sie
aendert nie die echte Datei (dort arbeitet eine parallele Sitzung am
Bildfenster) und kann sie nicht zerstoeren.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BUS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUS))
import skillsbot as s                                             # noqa: E402

CHAT = 7648512088
PROFIL = "openmontage"          # existiert als Profil (bot_namen())
FREMD = "gibtsnicht"


class ZielTest(unittest.TestCase):
    """Der aktive Bot: /bot NAME ohne Auftrag, Freitext, Abschalten."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ziel = os.path.join(self.tmp.name, "ziel.json")
        p = patch.object(s, "ZIEL_PFAD", self.ziel)
        p.start()
        self.addCleanup(p.stop)
        # /bot ruft sende() - der darf in keinem Test wirklich Telegram
        # anlaufen. Der Sende-Aufruf wird hier ersetzt, nicht ausgefuehrt.
        q = patch.object(s, "sende", lambda chat, text: None)
        q.start()
        self.addCleanup(q.stop)
        # Die Bot-Antwort wird ersetzt, sonst startete jeder Test eine
        # echte Hermes-Sitzung (Kaltstart 30-60 s, Modellaufruf).
        r = patch.object(s, "_bot_fragen", lambda name, text, **kw: "ANTWORT:" + name)
        r.start()
        self.addCleanup(r.stop)
        self.assertIn(PROFIL, s.bot_namen())

    def test_bot_name_ohne_auftrag_schaltet_ein(self):
        antwort, _ = s._bot_befehl([PROFIL], CHAT)
        self.assertIn(PROFIL, antwort)
        self.assertIn("Adressat", antwort)
        self.assertNotIn("Syntax", antwort)
        self.assertEqual(s._ziel_lesen(CHAT), PROFIL)

    def test_freitext_geht_an_den_aktiven_bot(self):
        s._ziel_setzen(CHAT, PROFIL)
        antwort, _ = s.bearbeite("mach was", CHAT)
        self.assertEqual(antwort, "ANTWORT:" + PROFIL)

    def test_nur_ein_auftrag_je_bot(self):
        s._ziel_setzen(CHAT, PROFIL)
        s.bearbeite("erster auftrag", CHAT)
        self.assertIsNone(s._ziel_lesen(CHAT))

    def test_ohne_ziel_kein_bot(self):
        self.assertIsNone(s._ziel_lesen(CHAT))

    def test_bot_aus_schaltet_ab(self):
        s._ziel_setzen(CHAT, PROFIL)
        antwort, _ = s._bot_befehl(["aus"], CHAT)
        self.assertIn("abgeschaltet", antwort)
        self.assertIsNone(s._ziel_lesen(CHAT))

    def test_abgelaufenes_ziel_zaehlt_nicht(self):
        s._ziel_setzen(CHAT, PROFIL)
        with open(self.ziel, encoding="utf-8") as f:
            alt = json.load(f)
        alt[str(CHAT)]["zeit"] -= s.ZIEL_FRIST_S + 60
        with open(self.ziel, "w", encoding="utf-8") as f:
            json.dump(alt, f)
        self.assertIsNone(s._ziel_lesen(CHAT))

    def test_frist_traegt_eine_arbeitsfrage(self):
        """Ein Bot-Auftrag dauert 30-60 s plus Arbeit - 10 min waeren zu wenig."""
        self.assertGreaterEqual(s.ZIEL_FRIST_S, 900)

    def test_unbekanntes_profil_schaltet_nichts_ein(self):
        antwort, _ = s._bot_befehl([FREMD, "hallo"], CHAT)
        self.assertIn(FREMD, antwort)
        self.assertIsNone(s._ziel_lesen(CHAT))

    def test_unbekannter_befehl_nennt_den_aktiven_bot(self):
        s._ziel_setzen(CHAT, PROFIL)
        antwort, _ = s.bearbeite("/gibtsnicht", CHAT)
        self.assertIn(PROFIL, antwort)
        # Der Befehl darf den Bot NICHT verbrauchen - er ging nicht an ihn.
        self.assertEqual(s._ziel_lesen(CHAT), PROFIL)

    def test_zwei_chats_storen_einander_nicht(self):
        s._ziel_setzen(CHAT, PROFIL)
        self.assertIsNone(s._ziel_lesen(1))
        self.assertEqual(s._ziel_lesen(CHAT), PROFIL)

    def test_zustand_ist_eine_datei_je_chat(self):
        s._ziel_setzen(CHAT, PROFIL)
        s._ziel_setzen(99, "caveman")
        with open(self.ziel, encoding="utf-8") as f:
            datei = json.load(f)
        self.assertEqual(sorted(datei), sorted([str(CHAT), "99"]))

    def test_geloeschtes_profil_zaehlt_als_kein_ziel(self):
        """Ein Profil, das weg ist (Bot geloescht), darf nicht haengen."""
        s._ziel_setzen(CHAT, PROFIL)
        r = patch.object(s, "bot_namen", lambda: ["caveman"])
        r.start()
        self.assertIsNone(s._ziel_lesen(CHAT))
        r.stop()


class GegenprobeTest(unittest.TestCase):
    """Fallen die Aussagen ohne den Fix wirklich um?

    Die Gegenprobe laeuft auf KOPIEN: skillsbot.py wird nie angefasst (dort
    arbeitet eine parallele Sitzung am Bildfenster). Fuer "vorher" wird die
    Fassung aus HEAD geladen, nicht aus einer Textkopie - so kann ein
    Anker, der nicht mehr passt, nicht still einen gruenen Test erzeugen.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        with open(BUS / "skillsbot.py", "rb") as f:
            self.roh = f.read()

    def modul(self, txt, name):
        pfad = os.path.join(self.tmp.name, name + ".py")
        with open(pfad, "wb") as f:
            f.write(txt)
        spec = importlib.util.spec_from_file_location(name, pfad)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(mod)
        return mod

    def _bereite(self, mod):
        # Die Kopie liegt im Temp-Ordner; ohne WURZEL findet bot_namen()
        # keine Profile und jedes Ziel waere ungueltig.
        mod.WURZEL = str(BUS.parent.parent)
        mod.ZIEL_PFAD = os.path.join(self.tmp.name, "ziel.json")
        mod.sende = lambda chat, text: None
        mod._bot_fragen = lambda name, text, **kw: "ANTWORT:" + name
        mod._ziel_setzen(CHAT, PROFIL)
        return mod.bearbeite("mach was", CHAT)[0]

    def test_mit_dem_fix_geht_der_auftrag_an_den_bot(self):
        mod = self.modul(self.roh, "skillsbot_mit_fix")
        self.assertEqual(self._bereite(mod), "ANTWORT:" + PROFIL)

    def vor_fassung(self):
        """skillsbot.py OHNE den Ziel-Modus - aus der Datei selbst gebaut.

        Bewusst NICHT aus git: ein Test gegen einen Commit-Hash meldet
        spaeter eine Aenderung statt eines Fehlers, und sobald eine andere
        Sitzung den Ziel-Modus committet (am 03.10.2026 passiert), zeigt
        HEAD nur noch die reparierte Fassung. Gebaut wird deshalb aus dem
        aktuellen Stand: Konstanten, drei Funktionen und die beiden
        Verwendungen in bearbeite/_bot_befehl entfallen.
        """
        CR = chr(13) + chr(10)
        txt = self.roh.decode("utf-8")

        def weg(a, b):
            """a bis ENDE VON b entfernen - b selbst bleibt erhalten.

            txt[j:] allein wuerde den Endanker mit wegnehmen und die
            Vor-Fassung Syntaxfehler werfen lassen (b ist ein def).
            """
            nonlocal txt
            assert a in txt, "Gegenprobe-Anker fehlt: " + a[:40]
            i = txt.index(a)
            j = txt.index(b, i) + len(b)
            txt = txt[:i] + b + txt[j:]

        # (1) die Konstante
        weg('ZIEL_PFAD = os.path.join(HIER, "skillsbot.ziel.json")' + CR,
            '                         # der naechste Freitext wieder dem Hauptagenten' + CR)
        # (2) die drei Funktionen
        # Achtung: weg() BEHAELTT den Endanker nicht. Deshalb endet hier
        # der Block auf _ziel_meldung - das kommt VOR _bot_profil_ordner
        # und traegt den Anker mit, sonst fehlt die Funktion spaeter.
        weg("def _ziel_lesen(chat):", "def _bot_profil_ordner():")
        # (3) /bot NAME ohne Auftrag: zurueck auf die Syntaxhilfe
        alt = ("    if not texte:" + CR
               + "        # Bot einschalten, NICHT fragen: am Handy kommt der "
                 "Auftrag als" + CR
               + "        # naechste Nachricht (oft ein Bild) - dafuer ist dieser "
                 "Weg da." + CR
               + "        _ziel_setzen(chat, name)" + CR
               + "        return _ziel_meldung(name), None")
        neu_ = ("    if not texte:" + CR
                + "        return (" + chr(34) + "Was soll ich Bot %s fragen? "
                  "Syntax: /bot %s NACHRICHT" + chr(92) + "n" + chr(34) + CR
                + "                % (name, name)), None")
        assert alt in txt, "Gegenprobe-Anker /bot fehlt"
        txt = txt.replace(alt, neu_, 1)
        # (4) Freitext-Zweig
        weg("    # Aktiver Bot? Dann geht der Auftrag an ihn",
            "        return ohne_denken(antwort), kontext" + CR)
        return txt.encode("utf-8")

    def test_die_vor_fassung_kennt_den_ziel_modus_nicht(self):
        """Die gebaute Vor-Fassung muss wirklich die alte sein."""
        mod = self.modul(self.vor_fassung(), "skillsbot_vor")
        mod.WURZEL = str(BUS.parent.parent)
        self.assertFalse(hasattr(mod, "_ziel_lesen"),
                         "die gebaute Vor-Fassung hat den Ziel-Modus doch")
        antwort, _ = mod._bot_befehl([PROFIL], CHAT)
        self.assertIn("Syntax", antwort)

    def test_ohne_die_fassung_geht_der_auftrag_ins_leere(self):
        """Ohne Ziel geht der Auftrag an den Hauptagenten - und der Bot
        bekommt ihn nie. Genau der Zustand, den Max am 03.10.2026 sah."""
        mod = self.modul(self.vor_fassung(), "skillsbot_vor2")
        mod.WURZEL = str(BUS.parent.parent)
        mod.sende = lambda chat, text: None
        gerufen = []
        mod._bot_fragen = lambda name, text, **kw: gerufen.append(name) or "X"
        antwort = mod.bearbeite("mach was", CHAT)[0]
        self.assertNotIn("X", str(antwort))
        self.assertEqual(gerufen, [], "im Vorzustand darf kein Bot laufen")

    def test_ohne_die_aenderung_kommt_wieder_die_syntaxhilfe(self):
        """Gegenprobe zu test_bot_name_ohne_auftrag_schaltet_ein."""
        mod = self.modul(self.vor_fassung(), "skillsbot_vor3")
        mod.WURZEL = str(BUS.parent.parent)
        mod.sende = lambda chat, text: None
        antwort, _ = mod._bot_befehl([PROFIL], CHAT)
        # Ohne die Aenderung fragt der Bot nach dem Auftrag statt ihn
        # anzunehmen - Max sah eine Syntaxhilfe und sendete danach woanders.
        self.assertNotIn("Adressat", antwort)

    def test_ohne_die_zusage_bekommt_max_nichts_zu_wissen(self):
        """Gegenprobe zur Meldung: die Zusage traegt die Bedienung."""
        antwort = s._ziel_meldung(PROFIL)
        for pflicht in ("Adressat", "/bot aus", "Bild"):
            self.assertIn(pflicht, antwort)


if __name__ == "__main__":
    unittest.main()
