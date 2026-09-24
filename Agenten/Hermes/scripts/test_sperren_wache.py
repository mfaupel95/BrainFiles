"""Tests fuer sperren-wache.py - ohne Netz, ohne echten Cron.

Die Wache wird per Pfad geladen und ihre Pfade (MERKDATEI, FREMDARBEIT_LOG,
REPOS) werden auf einen Temp-Baum umgebogen. So laeuft das ORIGINAL, aber
gegen Attrappen - kein Test schreibt in den echten cache/ oder in echte Repos.
"""

import importlib.util
import io
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKRIPT = Path(__file__).resolve().parent / "sperren-wache.py"


def lade():
    spec = importlib.util.spec_from_file_location("sperren_wache_test", str(SKRIPT))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wurzel = Path(self.tmp.name)
        self.repo = self.wurzel / "Repo"
        (self.repo / ".git").mkdir(parents=True)
        self.log = self.wurzel / "fremdarbeit.log"
        self.merk = self.wurzel / "sperren-wache.json"
        self.w = lade()
        self.w.REPOS = [self.repo]
        self.w.MERKDATEI = self.merk
        self.w.FREMDARBEIT_LOG = self.log

    def sperre(self, alter_min, groesse=0, repo=None):
        p = (repo or self.repo) / ".git" / "index.lock"
        p.write_bytes(b"x" * groesse)
        alt = time.time() - alter_min * 60
        os.utime(p, (alt, alt))
        return p

    def lauf(self, *args):
        """main() mit abgefangener Ausgabe -> (text, rc)."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = self.w.main(list(args))
        return buf.getvalue(), rc

    def schreibe_log(self, text):
        self.log.write_text(text, encoding="utf-8")


class OhneSperre(Basis):
    def test_keine_sperre_ist_still(self):
        text, rc = self.lauf("--ohne-prozesse")
        self.assertEqual(rc, 0)
        self.assertEqual(text, "")

    def test_frische_sperre_ist_still(self):
        self.sperre(2)
        text, _ = self.lauf("--ohne-prozesse")
        self.assertEqual(text, "")

    def test_alte_sperre_wird_gemeldet(self):
        self.sperre(25)
        text, rc = self.lauf("--ohne-prozesse")
        self.assertEqual(rc, 0)
        self.assertIn("index.lock liegt seit", text)
        self.assertIn("Repo", text)

    def test_frist_null_meldet_auch_frisches(self):
        self.sperre(0)
        text, _ = self.lauf("--ohne-prozesse", "--frist", "0")
        self.assertIn("index.lock", text)

    def test_repo_ohne_git_wird_nicht_gezaehlt(self):
        leer = self.wurzel / "Leer"
        leer.mkdir()
        self.w.REPOS = [leer]
        zeilen, geprueft, _ = self.w.befund(repos=[leer])
        self.assertEqual(zeilen, [])
        self.assertEqual(geprueft, 0)


class ProzessHinweis(Basis):
    def test_kein_echter_prozess_wird_genannt(self):
        self.sperre(25)
        zeilen, _, _ = self.w.befund(prozesse=0)
        self.assertEqual(len(zeilen), 1)
        self.assertIn("kein echter git-Prozess", zeilen[0])

    def test_laufender_prozess_wird_genannt(self):
        self.sperre(25)
        zeilen, _, _ = self.w.befund(prozesse=2)
        self.assertIn("2 git-Prozess(e)", zeilen[0])

    def test_unbekannt_ist_kein_falscher_vorwurf(self):
        self.sperre(25)
        zeilen, _, _ = self.w.befund(prozesse="unbekannt")
        self.assertNotIn("git-Prozess", zeilen[0])


class SkipZeile(Basis):
    def test_uebersprungen_wird_gemeldet(self):
        self.schreibe_log("=== Lauf 2026-09-23 20:40:00 (Schwelle 30 Min) ===\n"
                          "ENDE uebersprungen - .git\\index.lock liegt vor\n")
        text, _ = self.lauf("--ohne-prozesse")
        self.assertIn("Fremdarbeit: ENDE uebersprungen", text)

    def test_ok_lauf_wird_nicht_gemeldet(self):
        self.schreibe_log("=== Lauf 2026-09-24 20:40:00 ===\n"
                          "ENDE ok - aae26a9 mit 51 uebernommenen Datei(en)\n")
        text, _ = self.lauf("--ohne-prozesse")
        self.assertEqual(text, "")

    def test_letzter_lauf_zaehlt_nicht_ein_alter_skip(self):
        self.schreibe_log("=== Lauf 2026-09-23 20:40:00 ===\n"
                          "ENDE uebersprungen - .git\\index.lock liegt vor\n"
                          "=== Lauf 2026-09-24 20:40:00 ===\n"
                          "ENDE ok - aae26a9 mit 51 uebernommenen Datei(en)\n")
        self.assertIsNone(self.w.skip_zeile())

    def test_fehlendes_log_ist_kein_befund(self):
        self.assertIsNone(self.w.skip_zeile())


class VerwaisteSperren(Basis):
    def test_erster_lauf_legt_nur_den_bestand_fest(self):
        """Der Bestand allein ist kein Befund - sonst Alarm bei der Einrichtung."""
        (self.repo / ".git" / "index.lock.verwaist-20260924-1737").write_bytes(b"")
        (self.repo / ".git" / "index.lock.verwaist-20260924-1710").write_bytes(b"")
        text, _ = self.lauf("--ohne-prozesse")
        self.assertEqual(text, "")
        self.assertEqual(self.w._merker().get("_verwaist_gesamt"), 2)

    def test_zuwachs_wird_gemeldet_bestand_nicht(self):
        (self.repo / ".git" / "index.lock.verwaist-20260924-1737").write_bytes(b"")
        self.lauf("--ohne-prozesse")                     # Bestand 1 merken
        (self.repo / ".git" / "index.lock.verwaist-20260924-1710").write_bytes(b"")
        text, _ = self.lauf("--ohne-prozesse")
        self.assertIn("1 neue weggeraeumte Sperre(n)", text)
        self.assertNotIn("2 neue", text)

    def test_gleicher_bestand_bleibt_still(self):
        (self.repo / ".git" / "index.lock.verwaist-20260924-1737").write_bytes(b"")
        self.lauf("--ohne-prozesse")                     # merkt Bestand 1
        text, _ = self.lauf("--ohne-prozesse")
        self.assertEqual(text, "")

    def test_bestand_im_merker_ueberlebt(self):
        (self.repo / ".git" / "index.lock.verwaist-20260924-1737").write_bytes(b"")
        self.lauf("--ohne-prozesse")
        self.assertEqual(self.w._merker().get("_verwaist_gesamt"), 1)


class Entdopplung(Basis):
    def test_zweiter_lauf_ist_still(self):
        self.sperre(25)
        erster, _ = self.lauf("--ohne-prozesse")
        zweiter, _ = self.lauf("--ohne-prozesse")
        self.assertIn("index.lock", erster)
        self.assertEqual(zweiter, "")

    def test_wachsende_sperre_bleibt_dieselbe_feststellung(self):
        self.sperre(25)
        self.lauf("--ohne-prozesse")
        p = self.repo / ".git" / "index.lock"
        alt = time.time() - 90 * 60
        os.utime(p, (alt, alt))                          # jetzt 90 min alt
        text, _ = self.lauf("--ohne-prozesse")
        self.assertEqual(text, "")

    def test_nach_der_wiederholungsfrist_wieder_gemeldet(self):
        zeilen = ["Repo: .git/index.lock liegt seit 25 min (0 Byte)"]
        alt = "2020-01-01T00:00:00+00:00"
        zu, _ = self.w.entdopple(zeilen, {"Repo": alt})
        self.assertEqual(zu, zeilen)


class GanzePruefung(Basis):
    def test_sperre_und_skip_in_einem_lauf(self):
        self.sperre(30)
        self.schreibe_log("ENDE uebersprungen - .git\\index.lock liegt vor\n")
        text, rc = self.lauf("--ohne-prozesse")
        self.assertEqual(rc, 0)
        self.assertIn("Git-Sperre klemmt:", text)
        self.assertIn("index.lock liegt seit", text)
        self.assertIn("Fremdarbeit: ENDE uebersprungen", text)

    def test_alle_zeigt_den_umfang(self):
        text, _ = self.lauf("--ohne-prozesse", "--alle")
        self.assertIn("1 Repository(s) geprueft", text)

    def test_wache_raeumt_nichts_weg(self):
        p = self.sperre(30)
        self.lauf("--ohne-prozesse")
        self.assertTrue(p.exists(), "die Wache darf keine Sperre anfassen")

    def test_merker_wird_geschrieben(self):
        self.sperre(30)
        self.lauf("--ohne-prozesse")
        self.assertTrue(self.merk.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)