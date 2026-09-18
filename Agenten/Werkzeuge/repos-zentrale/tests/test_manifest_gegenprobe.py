"""Gegenprobe: kein Startbefehl im Manifest ohne echten Lauf.

Die Regel aus der Spezifikation lautet: ein Befehl kommt erst ins Manifest, wenn
er einmal gelaufen ist und eine Logdatei das belegt. Dieser Test prueft genau
das - Manifest gegen `logs/`.

Auf einem frischen Klon gibt es keine Logs (sie sind Laufzeit und nicht
versioniert). Dann wird der Test uebersprungen, mit klarem Text, statt gruen zu
luegen.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import manifest  # noqa: E402

HIER = Path(__file__).resolve().parent.parent
LOGS = HIER / "logs"


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
        belege = sorted(LOGS.glob("*.log")) if LOGS.is_dir() else []
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
