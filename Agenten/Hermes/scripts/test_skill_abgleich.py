#!/usr/bin/env python3
"""Tests fuer skill-abgleich.py - laufen auf Fixtures, nie auf echten Daten.

Der wichtigste Test ist `test_belegter_schadensfall`: er baut den Zustand vom
07.10.2026 nach (Vault alt, Kopie weiter) und prueft, dass der Abgleich die
Kopie NICHT ueberschreibt - genau der Fehler, der damals 15.678 Bytes in
`rueckschau/sitzungen_auswerten.py` geloescht hat.

    python test_skill_abgleich.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SKRIPT = Path(__file__).resolve().parent / "skill-abgleich.py"

ALT = """---
name: rueckschau
---

# Sitzungen auswerten

Optionen: `--seit`, `--anweisungen`, `--ausgabe`.

## Fallen

Sitzungen liegen mehrfach vor.
"""

# Die Kopie ist weiter: sie hat zusaetzlich `--umwege`, `--hermes-db` und
# einen ganzen Abschnitt, den die Quelle nie bekam.
NEU = """---
name: rueckschau
---

# Sitzungen auswerten

Optionen: `--seit`, `--anweisungen`, `--ausgabe`, `--umwege`, `--hermes-db`.

## Fallen

Sitzungen liegen mehrfach vor.

## Umwege zaehlen

Gezaehlt wird je Signatur die Zahl verschiedener Sitzungen und Tage.
"""

NUR_QUELLE = ALT  # Quelle hat nur das, was auch die Kopie hat


def schreibe(p: Path, text: str, crlf: bool = False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    daten = text.replace("\n", "\r\n") if crlf else text
    p.write_bytes(daten.encode("utf-8"))


def md5(p: Path) -> str:
    import hashlib
    return hashlib.md5(p.read_bytes()).hexdigest()


class Basis(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="skillabgleich-test-"))
        self.vault = self.tmp / "vault"
        self.kopien = self.tmp / "kopien"
        self.sicher = self.tmp / "sicherung"
        self.vault.mkdir()
        self.kopien.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lauf(self, *extra: str) -> subprocess.CompletedProcess:
        umg = dict(os.environ)
        for k in ("PYTHONHOME", "PYTHONPATH"):
            umg.pop(k, None)
        return subprocess.run(
            [sys.executable, str(SKRIPT),
             "--vault", str(self.vault), "--kopien", str(self.kopien),
             "--sicherung", str(self.sicher), "--min-alter", "0", *extra],
            capture_output=True, text=True, env=umg, timeout=120)

    def alten_stand(self) -> None:
        """Vault alt, Kopie weiter - der belegte Schadensfall."""
        schreibe(self.vault / "rueckschau" / "SKILL.md", ALT)
        schreibe(self.kopien / "rueckschau" / "SKILL.md", NEU)
        alt = time.time() - 86400
        os.utime(self.kopien / "rueckschau" / "SKILL.md", (alt, alt))


class TestSchadensfall(Basis):
    def test_belegter_schadensfall(self):
        """Die Kopie ist weiter -> Trockenlauf sperrt, --anwenden fasst sie nicht an."""
        self.alten_stand()
        kopie = self.kopien / "rueckschau" / "SKILL.md"
        vorher = md5(kopie)

        r = self.lauf()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("GESPERRT", r.stdout)
        self.assertIn("nur in der Kopie", r.stdout)
        self.assertEqual(md5(kopie), vorher, "Trockenlauf hat die Kopie angefasst")

        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(md5(kopie), vorher, "Kopie wurde ueberschrieben!")
        self.assertIn("--umwege", kopie.read_text(encoding="utf-8"),
                      "Weiterarbeit der Kopie ist verloren")

    def test_zusammenfuehren_zieht_in_die_quelle(self):
        """--zusammenfuehren holt den Abschnitt in die Quelle, ohne Verlust."""
        self.alten_stand()
        quelle = self.vault / "rueckschau" / "SKILL.md"
        kopie = self.kopien / "rueckschau" / "SKILL.md"

        r = self.lauf("--anwenden", "--zusammenfuehren")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        tq = quelle.read_text(encoding="utf-8")
        self.assertIn("--umwege", tq, "Option der Kopie fehlt in der Quelle")
        self.assertIn("## Umwege zaehlen", tq, "Abschnitt fehlt in der Quelle")
        self.assertIn("--seit", tq, "alter Inhalt der Quelle verloren")
        # Beide Seiten tragen jetzt denselben Text
        self.assertEqual(quelle.read_bytes(), kopie.read_bytes())
        # Sicherungen liegen
        self.assertTrue(list(self.sicher.rglob("SKILL.md")), "keine Sicherung")
        self.assertTrue(list(self.vault.rglob("*.bak-*")), "kein .bak in der Quelle")


class TestRueckstand(Basis):
    def test_reiner_rueckstand_wird_kopiert(self):
        """Quelle hat Zeilen, die der Kopie fehlen -> wird kopiert (der Normalfall)."""
        schreibe(self.vault / "notiz" / "SKILL.md", ALT + "\n## Neu\n\nZeile der Quelle.\n")
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT)
        alt = time.time() - 86400
        os.utime(self.kopien / "notiz" / "SKILL.md", (alt, alt))

        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Zeile der Quelle",
                      (self.kopien / "notiz" / "SKILL.md").read_text(encoding="utf-8"))
        # Die alte Fassung liegt in der Sicherung
        self.assertTrue(list(self.sicher.rglob("SKILL.md")))

    def test_frischer_schutz(self):
        """Eine eben geschriebene Kopie wird nicht angefasst."""
        schreibe(self.vault / "notiz" / "SKILL.md", ALT + "\n## Neu\n")
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT)   # mtime = jetzt
        vorher = md5(self.kopien / "notiz" / "SKILL.md")

        umg = dict(os.environ)
        for k in ("PYTHONHOME", "PYTHONPATH"):
            umg.pop(k, None)
        r = subprocess.run(
            [sys.executable, str(SKRIPT), "--vault", str(self.vault),
             "--kopien", str(self.kopien), "--sicherung", str(self.sicher),
             "--min-alter", "10", "--anwenden"],
            capture_output=True, text=True, env=umg, timeout=120)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(md5(self.kopien / "notiz" / "SKILL.md"), vorher)
        self.assertIn("juenger als 10 min", r.stdout)


class TestBestand(Basis):
    def test_fehlender_skill_wird_angelegt(self):
        schreibe(self.vault / "scanner-papier" / "SKILL.md", ALT)
        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.kopien / "scanner-papier" / "SKILL.md").exists())

    def test_fremder_skill_wird_nie_angefasst(self):
        """Skills, die es nur in den Kopien gibt (okx-*, sprache), bleiben."""
        schreibe(self.vault / "notiz" / "SKILL.md", ALT)
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT)
        schreibe(self.kopien / "okx-defi" / "SKILL.md", "# fremd\n")
        vorher = md5(self.kopien / "okx-defi" / "SKILL.md")

        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(md5(self.kopien / "okx-defi" / "SKILL.md"), vorher)
        self.assertIn("okx-defi", r.stdout)

    def test_gleiche_datei_bleibt_unberuehrt(self):
        schreibe(self.vault / "notiz" / "SKILL.md", ALT)
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT)
        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("gleich: 1", r.stdout)

    def test_zeilenenden_bleiben(self):
        """CRLF bleibt CRLF, LF bleibt LF."""
        schreibe(self.vault / "notiz" / "SKILL.md", ALT + "\n## Neu\n", crlf=True)
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT, crlf=True)
        alt = time.time() - 86400
        os.utime(self.kopien / "notiz" / "SKILL.md", (alt, alt))

        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        roh = (self.kopien / "notiz" / "SKILL.md").read_bytes()
        self.assertGreater(roh.count(b"\r\n"), 0, "CRLF verloren")
        self.assertEqual(roh.count(b"\n") - roh.count(b"\r\n"), 0, "LF eingestreut")

    def test_beidseitig_eigen_wird_gesperrt(self):
        schreibe(self.vault / "notiz" / "SKILL.md", ALT + "\n## NurQuelle\n")
        schreibe(self.kopien / "notiz" / "SKILL.md", ALT + "\n## NurKopie\n")
        alt = time.time() - 86400
        os.utime(self.kopien / "notiz" / "SKILL.md", (alt, alt))

        r = self.lauf("--anwenden")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("NurKopie", (self.kopien / "notiz" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("beide Seiten eigen", r.stdout)

    def test_nur_filter(self):
        schreibe(self.vault / "notiz" / "SKILL.md", ALT)
        schreibe(self.vault / "geld" / "SKILL.md", ALT)
        r = self.lauf("--nur", "geld", "--anwenden")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.kopien / "geld" / "SKILL.md").exists())
        self.assertFalse((self.kopien / "notiz" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
