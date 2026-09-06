"""TP4, Teil 1: Vorschlag anwenden (anwenden.py).

``anwenden.anwenden()`` ist der einzige schreibende Pfad auf
``scanner/wachen.json`` und ``scanner/bewertung.py`` und die einzige Stelle,
die einen Commit erzeugt. Geprueft wird: Arbeitsbaum sauber (+ Index leer),
geaenderte JSON-Schluessel gegen eine FEST verdrahtete Denylist (gewinnt immer,
egal was ``spuren.json`` erlaubt), ``.bak`` beider Zieldateien, byteweises
Schreiben von ``wachen.json`` (CRLF bleibt), Gewichts-Patch per ``git apply``
(nur wenn nicht leer) und genau ein Commit mit genau den zwei Zieldateien.

Die Tests bauen Wegwerf-Repos in Temp-Ordnern. ``anwenden.WURZEL`` wird je
Test auf einen eigenen Temp-Ordner umgebogen, damit nichts in das echte
``verbesserer/bak`` oder ``verbesserer/berichte`` geschrieben wird.
"""

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import anwenden  # noqa: E402

WACHEN_ALT = '{\r\n  "mindest_score": 60,\r\n  "handel_erlaubt": false\r\n}\r\n'
CO_TRAILER = "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
PATCH_B_PY = (
    "--- a/b.py\n"
    "+++ b/b.py\n"
    "@@ -1 +1 @@\n"
    "-CHANCE_GEWICHTE = {'trend': 0.30}\n"
    "+CHANCE_GEWICHTE = {'trend': 0.35}\n"
)


def _git(repo, *a):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                          text=True, check=True)


def _repo():
    d = Path(mkdtemp())
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@t")
    _git(d, "config", "user.name", "t")
    _git(d, "config", "commit.gpgsign", "false")
    return d


class TestReineFunktionen(unittest.TestCase):
    def test_geaenderte_schluessel(self):
        neu = WACHEN_ALT.replace("60", "65")
        self.assertEqual(anwenden.geaenderte_schluessel(WACHEN_ALT, neu),
                         {"mindest_score"})

    def test_geaenderte_schluessel_kein_json(self):
        with self.assertRaises(ValueError):
            anwenden.geaenderte_schluessel("kein json", "{}")

    def test_denylist_faengt_handel_erlaubt(self):
        ok, name = anwenden.denylist_ok({"mindest_score", "handel_erlaubt"})
        self.assertFalse(ok)
        self.assertEqual(name, "handel_erlaubt")

    def test_denylist_faengt_freigabe_praefix(self):
        ok, _ = anwenden.denylist_ok({"freigabe"})
        self.assertFalse(ok)

    def test_denylist_faengt_weitere_praefixe(self):
        self.assertFalse(anwenden.denylist_ok({"kill_switch_gesamt_usd"})[0])
        self.assertFalse(anwenden.denylist_ok({"herzschlag_max_minuten"})[0])
        self.assertFalse(anwenden.denylist_ok({"drawdown_etwas_neues"})[0])

    def test_denylist_laesst_normale_gates_durch(self):
        ok, name = anwenden.denylist_ok({"mindest_score",
                                         "max_volatilitaet_pa"})
        self.assertTrue(ok)
        self.assertEqual(name, "")


class TestAnwenden(unittest.TestCase):
    def setUp(self):
        self._orig_wurzel = anwenden.WURZEL
        self.heim = Path(mkdtemp())
        anwenden.WURZEL = self.heim

    def tearDown(self):
        anwenden.WURZEL = self._orig_wurzel

    # --- Helfer ---------------------------------------------------------
    def _basis_repo(self):
        repo = _repo()
        wachen = repo / "wachen.json"
        bew = repo / "b.py"
        wachen.write_text(WACHEN_ALT, "utf-8", newline="")
        bew.write_text("CHANCE_GEWICHTE = {'trend': 0.30}\n", "utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "init")
        return repo, wachen, bew

    def _vorschlag(self, repo, *, wachen_neu=True, patch_text="",
                   score_neu="65", handel_true=False):
        ordner = repo / "v"
        ordner.mkdir()
        if wachen_neu:
            text = WACHEN_ALT
            if handel_true:
                text = text.replace("false", "true")
            else:
                text = text.replace('"mindest_score": 60',
                                    '"mindest_score": ' + score_neu)
            (ordner / "wachen.neu.json").write_text(text, "utf-8", newline="")
        (ordner / "bewertung.patch").write_text(patch_text, "utf-8")
        (ordner / "commit.txt").write_text(
            "verbesserer: Test\n\n"
            "Gebuehr/Trefferquote/Funding/Liquidations n/a\n\n"
            + CO_TRAILER + "\n", "utf-8")
        return ordner

    def _spur(self, wachen, bew):
        return {"wachen": str(wachen), "bewertung_datei": str(bew)}

    # --- baum_sauber ---------------------------------------------------
    def test_baum_sauber_direkt(self):
        repo, wachen, bew = self._basis_repo()
        ok, grund = anwenden.baum_sauber([str(wachen), str(bew)], repo)
        self.assertTrue(ok, grund)
        (repo / "z.txt").write_text("z", "utf-8")
        _git(repo, "add", "z.txt")
        ok2, _ = anwenden.baum_sauber([str(wachen)], repo)
        self.assertFalse(ok2)

    def test_schmutziger_baum_bricht_ab(self):
        repo, wachen, bew = self._basis_repo()
        wachen.write_text(WACHEN_ALT.replace("60", "61"), "utf-8", newline="")
        r = anwenden.anwenden(repo / "v", self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("Baum", r["grund"])
        self.assertIsNone(r["commit"])

    def test_gestagte_aenderung_bricht_ab(self):
        repo, wachen, bew = self._basis_repo()
        (repo / "other.txt").write_text("x", "utf-8")
        _git(repo, "add", "other.txt")
        ordner = self._vorschlag(repo)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("Baum", r["grund"])

    # --- Denylist ----------------------------------------------------
    def test_denylist_blockt_wachen_neu(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, handel_true=True)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("Denylist", r["grund"])
        self.assertIn("handel_erlaubt", r["grund"])
        self.assertIsNone(r["commit"])
        # nichts angefasst
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)
        self.assertFalse((self.heim / "bak").exists())

    # --- Erfolgspfad -------------------------------------------------
    def test_erfolg_crlf_bleibt_und_ein_commit(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, patch_text="")
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertEqual(r["grund"], "angewandt")
        self.assertEqual(wachen.read_bytes().count(b"\r\n"),
                         WACHEN_ALT.count("\r\n"))
        self.assertIn('"mindest_score": 65', wachen.read_text("utf-8"))
        log = _git(repo, "log", "--oneline").stdout.strip().splitlines()
        self.assertEqual(len(log), 2)  # init + ein Vorschlag
        body = _git(repo, "log", "-1", "--format=%B").stdout
        self.assertIn("Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>",
                      body)
        self.assertEqual(
            r["commit"],
            _git(repo, "rev-parse", "--short", "HEAD").stdout.strip())

    def test_bak_liegt_unter_wurzel_bak_zeitstempel(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        kopien = sorted(p.name for p in (self.heim / "bak").glob("*/*"))
        self.assertEqual(kopien, ["b.py", "wachen.json"])

    def test_commit_beruehrt_nur_zwei_dateien(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, patch_text="")
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        geaendert = set(_git(repo, "show", "--name-only", "--format=",
                             "HEAD").stdout.split())
        # leerer Patch -> b.py unveraendert, nur wachen.json im Commit
        self.assertEqual(geaendert, {"wachen.json"})

    def test_gewichts_patch_wird_angewandt(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, patch_text=PATCH_B_PY)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertIn("0.35", bew.read_text("utf-8"))
        geaendert = set(_git(repo, "show", "--name-only", "--format=",
                             "HEAD").stdout.split())
        self.assertEqual(geaendert, {"wachen.json", "b.py"})

    def test_leerer_patch_kein_git_apply(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, patch_text="   \n")
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertEqual(bew.read_text("utf-8"),
                         "CHANCE_GEWICHTE = {'trend': 0.30}\n")

    def test_nur_gewichte_ohne_wachen_neu(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, wachen_neu=False, patch_text=PATCH_B_PY)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        self.assertIn("0.35", bew.read_text("utf-8"))

    def test_erledigt_ordner_verschoben(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo)
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertFalse(ordner.exists())
        self.assertTrue(
            (self.heim / "berichte" / "erledigt" / "v").is_dir())

    # --- ablehnen --------------------------------------------------
    def test_ablehnen_verschiebt_und_schreibt_grund(self):
        basis = Path(mkdtemp())
        ordner = basis / "v7"
        ordner.mkdir()
        (ordner / "bericht.md").write_text("x", "utf-8")
        anwenden.ablehnen(ordner, "Denylist: handel_erlaubt")
        ziel = self.heim / "berichte" / "abgelehnt" / "v7"
        self.assertTrue(ziel.is_dir())
        self.assertFalse(ordner.exists())
        self.assertEqual((ziel / "ABGELEHNT.txt").read_text("utf-8"),
                         "Denylist: handel_erlaubt")


if __name__ == "__main__":
    unittest.main()
