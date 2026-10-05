"""Gegenprobe: kein Startbefehl im Manifest ohne echten Lauf.

Die Regel aus der Spezifikation lautet: ein Befehl kommt erst ins Manifest, wenn
er einmal gelaufen ist und eine Logdatei das belegt. Dieser Test prueft genau
das - Manifest gegen `logs/`.

Auf einem frischen Klon gibt es keine Logs (sie sind Laufzeit und nicht
versioniert). Dann wird der Test uebersprungen, mit klarem Text, statt gruen zu
luegen.

Ein zweiter Umgebungsbefund (05.10.2026): auch in einem WORKTREE fehlt `logs/`
- dort meldete der Test 112 von 115 Startbefehlen als unbelegt, waehrend im
Hausbaum alle 114 einen Beleg haben. Der Test prueft deshalb den HAUSBAUM,
denn dort liegen die Belege.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import manifest  # noqa: E402

HIER = Path(__file__).resolve().parent.parent


def _hauslogs():
    """Der Log-Ordner des HAUSBAUMS - auch wenn der Test aus einem Worktree
    laeuft. Ohne diesen Anker meldet der Test jeden Startbefehl als unbelegt."""
    haus = Path("C:/Users/faupe/Documents/BrainFiles/Agenten/Werkzeuge/repos-zentrale")
    if haus.is_dir() and any((haus / "logs").glob("*.log")):
        return haus / "logs"
    return HIER / "logs"


LOGS = _hauslogs()


class GegenprobeTest(unittest.TestCase):
    def test_jeder_startbefehl_hat_einen_beleg_im_log(self):
        if not LOGS.is_dir() or not any(LOGS.glob("*.log")):
            self.skipTest(f"keine Logs unter {LOGS} - auf dieser Platte nie gestartet")
        ohne_beleg = [
            e.ordner
            for e in manifest.manifest_laden(HIER / "repos-zentrale.json")
            if e.start and not any(LOGS.glob(f"{e.ordner}-*.log"))
        ]
        self.assertEqual(
            ohne_beleg, [],
            "Startbefehl ohne Logbeleg - Befehl erst echt laufen lassen, dann eintragen",
        )

    def test_der_beleg_enthaelt_das_repo_und_einen_rueckkehrcode(self):
        # Ein BELEG ist ein Log, dessen Name mit einem Repo-Ordner beginnt
        # (`<ordner>-<JJJJMMTT-HHMM>.log`) - dieselbe Kennung wie im Test
        # darueber. Eine Fremddatei in logs/ ist kein Beleg und darf nicht
        # gegen die Beleg-Regeln geprueft werden: sie hat keine Startzeile,
        # weil sie keinen Start belegt. (Befund 30.09.2026: eine Logdatei des
        # Zentrale-Fensters liess den Test rot werden, ohne dass ein Beleg
        # fehlte.)
        if not LOGS.is_dir():
            self.skipTest(f"keine Logs unter {LOGS}")
        ordner = [e.ordner for e in manifest.manifest_laden(HIER / "repos-zentrale.json")]
        belege = sorted(
            p for p in LOGS.glob("*.log")
            if any(p.name.startswith(f"{o}-") for o in ordner)
        )
        if not belege:
            self.skipTest(f"keine Logs unter {LOGS}")
        angefasst = 0
        for log in belege:
            text = log.read_text(encoding="utf-8", errors="replace")
            self.assertIn("#", text, f"{log.name} hat keine Startzeile")
            if "beendet (Code" in text:
                angefasst += 1
        self.assertGreater(angefasst, 0, "kein Log nennt einen Rueckkehrcode")


if __name__ == "__main__":
    unittest.main()
