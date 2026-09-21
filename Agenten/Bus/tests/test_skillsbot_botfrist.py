"""Tests fuer /bot im SkillsBot - Frist und Abbruchverhalten.

ANLASS (21.09.2026, gemeldet von Max): "/bot"-Befehle brachen mit Zeitlimit ab.
Gemessen lag die Grenze bei A2A_TIMEOUT_S + 30 = 330 s, und der Abbruch kam von
subprocess.run(timeout=...) - das KILLT den Bot mitten in der Arbeit, die ganze
Aufgabe ist verloren. Ein Bot, der ein Repo liest oder ein Buch auswertet,
braucht laenger; nichts war kaputt, nur die Frist zu kurz.

Geprueft wird jetzt:
  - die Frist ist gross genug fuer echte Arbeit (>= 900 s),
  - ein Bot, der laenger braucht als die Frist, wird mit einer ERKLAERENDEN
    Meldung abgebrochen (nicht mit einem nackten TimeoutError),
  - innerhalb der Frist kommt die Antwort vollstaendig an.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

BUS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUS))
import skillsbot as s                                                # noqa: E402


def _stub(koerper):
    """Ein Ersatz-'hermes.exe', das genau tut, was der Test braucht."""
    d = tempfile.TemporaryDirectory()
    p = Path(d.name) / "hermes-stub.py"
    p.write_text(textwrap.dedent(koerper), encoding="utf-8")
    bat = Path(d.name) / "hermes-stub.bat"
    bat.write_text('@echo off\n"%s" "%s" %%*\n' % (sys.executable, p), encoding="utf-8")
    return d, str(bat)


class Frist(unittest.TestCase):
    def test_frist_traegt_echte_arbeit(self):
        # 330 s waren zu kurz - die Frist muss deutlich darueber liegen.
        self.assertGreaterEqual(s.BOT_FRIST_S, 900)


class Abbruch(unittest.TestCase):
    def test_langer_lauf_wird_erklaert_abgebrochen(self):
        d, stub = _stub("""
            import time
            time.sleep(30)
            print("zu spaet")
        """)
        self.addCleanup(d.cleanup)
        alt = s.HERMES_EXE
        s.HERMES_EXE = stub
        self.addCleanup(lambda: setattr(s, "HERMES_EXE", alt))
        with self.assertRaises(s.SkillsBotFehler) as ctx:
            s._bot_fragen("testbot", "egal", frist=2)
        text = str(ctx.exception)
        self.assertIn("testbot", text)
        self.assertIn("Teilstuecke", text, "die Meldung muss sagen, was zu tun ist")

    def test_schneller_lauf_liefert_die_antwort(self):
        d, stub = _stub("""
            print("Antwort vom Bot")
        """)
        self.addCleanup(d.cleanup)
        alt = s.HERMES_EXE
        s.HERMES_EXE = stub
        self.addCleanup(lambda: setattr(s, "HERMES_EXE", alt))
        self.assertEqual(s._bot_fragen("testbot", "egal", frist=60), "Antwort vom Bot")

    def test_fehlender_bot_wird_gemeldet(self):
        d, stub = _stub("""
            import sys
            print("kaputt", file=sys.stderr)
            sys.exit(3)
        """)
        self.addCleanup(d.cleanup)
        alt = s.HERMES_EXE
        s.HERMES_EXE = stub
        self.addCleanup(lambda: setattr(s, "HERMES_EXE", alt))
        with self.assertRaises(s.SkillsBotFehler) as ctx:
            s._bot_fragen("testbot", "egal", frist=60)
        self.assertIn("gescheitert", str(ctx.exception))


class KeinKillMittenInDerArbeit(unittest.TestCase):
    """Die alte Fassung rief subprocess.run(timeout=...) - der Bot wurde
    mitten in der Arbeit beendet und die Arbeit war weg. Wer das zurueckbaut,
    faellt hier auf."""

    def test_quelle_benutzt_popen_mit_kommunikation(self):
        quelle = (BUS / "skillsbot.py").read_text(encoding="utf-8")
        i = quelle.index("def _bot_fragen")
        rumpf = quelle[i:i + 3000]
        # Kommentarzeilen zaehlen nicht - im Kommentar steht der alte Weg
        # absichtlich als Warnung.
        code = "\n".join(z for z in rumpf.splitlines()
                         if not z.lstrip().startswith("#"))
        self.assertIn("subprocess.Popen", code)
        self.assertNotIn("timeout=zeit", code)
        self.assertNotIn("subprocess.run(", code)


if __name__ == "__main__":
    unittest.main()