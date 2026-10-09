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

    def test_geaenderte_schluessel_hinzugefuegt(self):
        # ``neu`` fuegt einen Top-Level-Schluessel hinzu, den ``alt`` nicht
        # kennt -> er muss im Ergebnis auftauchen.
        neu = ('{\r\n  "mindest_score": 60,\r\n  "handel_erlaubt": false,\r\n'
               '  "neuer_gate": 5\r\n}\r\n')
        self.assertEqual(anwenden.geaenderte_schluessel(WACHEN_ALT, neu),
                         {"neuer_gate"})

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
        return {"wachen": str(wachen), "bewertung_datei": str(bew),
                "aenderbar": {"wachen.json": {
                    "mindest_score": [55, 75],
                    "max_volatilitaet_pa": [0.9, 1.4],
                    "mindest_chance_risiko": [1.3, 2.2],
                    "pflicht_stop_prozent_min": [4, 8],
                    "pflicht_stop_prozent_max": [8, 15],
                    "abklingzeit_tage": [2, 5],
                    "watchlist": "liste"}}}

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

    # --- Bereichs-/Whitelist-Pruefung (F2) -------------------------
    def test_wert_ausserhalb_bereich_bricht_ab(self):
        repo, wachen, bew = self._basis_repo()
        # mindest_score 95 liegt ausserhalb [55, 75] aus spuren.json.
        ordner = self._vorschlag(repo, score_neu="95", patch_text="")
        wachen_vorher = wachen.read_bytes()
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("Bereich", r["grund"])
        self.assertIsNone(r["commit"])
        # kein Byte an wachen.json, kein .bak, kein Commit
        self.assertEqual(wachen.read_bytes(), wachen_vorher)
        self.assertFalse((self.heim / "bak").exists())
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)

    def test_schluessel_nicht_auf_whitelist_bricht_ab(self):
        repo, wachen, bew = self._basis_repo()
        ordner = repo / "v"
        ordner.mkdir()
        neu = ('{\r\n  "mindest_score": 60,\r\n  "handel_erlaubt": false,\r\n'
               '  "irgendein_gate": 5\r\n}\r\n')
        (ordner / "wachen.neu.json").write_text(neu, "utf-8", newline="")
        (ordner / "bewertung.patch").write_text("", "utf-8")
        (ordner / "commit.txt").write_text(
            "verbesserer: Test\n\n" + CO_TRAILER + "\n", "utf-8")
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("Whitelist", r["grund"])
        self.assertIsNone(r["commit"])
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        self.assertFalse((self.heim / "bak").exists())

    def test_nichtnumerischer_bereichswert_bricht_ab(self):
        # Ein Bereichsschluessel ([min,max]) mit null/String statt Zahl -
        # oder ganz entfernt - muss fail-closed abbrechen, nicht durchrutschen.
        repo, wachen, bew = self._basis_repo()
        ordner = repo / "v"
        ordner.mkdir()
        neu = WACHEN_ALT.replace('"mindest_score": 60',
                                 '"mindest_score": null')
        (ordner / "wachen.neu.json").write_text(neu, "utf-8", newline="")
        (ordner / "bewertung.patch").write_text("", "utf-8")
        (ordner / "commit.txt").write_text(
            "verbesserer: Test\n\n" + CO_TRAILER + "\n", "utf-8")
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("numerischer Wert", r["grund"])
        self.assertIsNone(r["commit"])
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        self.assertFalse((self.heim / "bak").exists())
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)

    # --- "wirft nie" auch bei Ablage-Fehler (F8) -------------------
    def test_ablage_fehler_meldet_trotzdem_erfolg(self):
        repo, wachen, bew = self._basis_repo()
        ordner = self._vorschlag(repo, patch_text="")
        orig = anwenden._ablegen

        def boom(*a, **k):
            raise OSError("Platte voll")

        anwenden._ablegen = boom
        try:
            r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        finally:
            anwenden._ablegen = orig
        # Commit ist echt -> Erfolg, nur der Grund vermerkt die Ablage.
        self.assertTrue(r["ok"], r["grund"])
        self.assertTrue(r["commit"])
        self.assertIn("Ablage", r["grund"])
        log = _git(repo, "log", "--oneline").stdout.strip().splitlines()
        self.assertEqual(len(log), 2)
        self.assertEqual(
            r["commit"],
            _git(repo, "rev-parse", "--short", "HEAD").stdout.strip())

    # --- _ablegen loescht keinen Archivordner (F9) ----------------
    def test_ablegen_kollision_behaelt_beide(self):
        basis = Path(mkdtemp())
        (self.heim / "berichte" / "erledigt").mkdir(parents=True)
        erste = basis / "2026-01-01-spur1"
        erste.mkdir()
        (erste / "bericht.md").write_text("eins", "utf-8")
        z1 = anwenden._ablegen(erste, "erledigt")
        zweite = basis / "2026-01-01-spur1"
        zweite.mkdir()
        (zweite / "bericht.md").write_text("zwei", "utf-8")
        z2 = anwenden._ablegen(zweite, "erledigt")
        self.assertNotEqual(z1, z2)
        self.assertTrue(z1.is_dir())
        self.assertTrue(z2.is_dir())
        self.assertEqual((z1 / "bericht.md").read_text("utf-8"), "eins")
        self.assertEqual((z2 / "bericht.md").read_text("utf-8"), "zwei")

    # --- Patch-Pfad-Allowlist + Roll-back ---------------------------
    def test_patch_fremde_datei_wird_abgelehnt(self):
        repo, wachen, bew = self._basis_repo()
        fremd_patch = (
            "--- a/scanner/wachen.json\n"
            "+++ b/scanner/wachen.json\n"
            "@@ -1 +1 @@\n"
            "-{\"handel_erlaubt\": false}\n"
            "+{\"handel_erlaubt\": true}\n"
        )
        ordner = self._vorschlag(repo, patch_text=fremd_patch)
        wachen_vorher = wachen.read_bytes()
        bew_vorher = bew.read_bytes()
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("fremde Datei", r["grund"])
        self.assertIsNone(r["commit"])
        # Zieldateien byte-unveraendert (Schritt 4 wurde zurueckgerollt)
        self.assertEqual(wachen.read_bytes(), wachen_vorher)
        self.assertEqual(bew.read_bytes(), bew_vorher)
        # nichts committet, nichts gestaged, Arbeitsbaum sauber
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)
        self.assertEqual(
            _git(repo, "diff", "--cached", "--name-only").stdout, "")
        self.assertEqual(
            _git(repo, "status", "--porcelain", "--", str(wachen),
                 str(bew)).stdout, "")
        # .bak bleibt als Audit-Spur
        self.assertTrue((self.heim / "bak").exists())
        # Vorschlagsordner liegt noch da
        self.assertTrue(ordner.exists())

    def test_git_apply_fehler_stellt_wieder_her(self):
        repo, wachen, bew = self._basis_repo()
        # Header zielt korrekt auf b.py -> Pfad-Check passt; der Kontext
        # passt aber nicht -> ``git apply`` schlaegt fehl.
        schlecht = (
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -1 +1 @@\n"
            "-VOELLIG ANDERE ZEILE\n"
            "+neu\n"
        )
        ordner = self._vorschlag(repo, patch_text=schlecht)  # legit wachen.neu
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("wiederhergestellt", r["grund"])
        # wachen.json exakt auf die Ausgangsbytes zurueck (CRLF inklusive)
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        self.assertEqual(wachen.read_bytes().count(b"\r\n"),
                         WACHEN_ALT.count("\r\n"))
        self.assertEqual(
            _git(repo, "diff", "--cached", "--name-only").stdout, "")
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)
        self.assertTrue(ordner.exists())

    def test_commit_txt_fehlt(self):
        repo, wachen, bew = self._basis_repo()
        ordner = repo / "v"
        ordner.mkdir()
        (ordner / "wachen.neu.json").write_text(
            WACHEN_ALT.replace('"mindest_score": 60', '"mindest_score": 65'),
            "utf-8", newline="")
        (ordner / "bewertung.patch").write_text("", "utf-8")
        # kein commit.txt
        r = anwenden.anwenden(ordner, self._spur(wachen, bew), repo)
        self.assertFalse(r["ok"])
        self.assertIn("commit.txt", r["grund"])
        self.assertIsNone(r["commit"])
        self.assertEqual(wachen.read_bytes(), WACHEN_ALT.encode("utf-8"))
        # Abbruch vor Schritt 3 -> kein .bak
        self.assertFalse((self.heim / "bak").exists())
        self.assertEqual(
            len(_git(repo, "log", "--oneline").stdout.strip().splitlines()), 1)

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


class TestAnwendungslog(unittest.TestCase):
    """T-373: anwenden.py haengt je Anwendung einen Eintrag an."""

    def test_eintrag_mit_hash_und_lauf_ts(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        alt = anwenden.WURZEL
        try:
            with TemporaryDirectory() as d:
                anwenden.WURZEL = Path(d)
                ordner = Path(d) / "2026-10-07-spur1"
                ordner.mkdir(parents=True, exist_ok=True)
                (ordner / "wachen.neu.json").write_text(
                    '{"mindest_score": 60}', "utf-8")
                e = anwenden._anwendungslog(ordner, "angewendet")
                datei = Path(d) / "anwendungslog.json"
                self.assertTrue(datei.exists(), "anwendungslog.json fehlt")
                self.assertEqual(e["lauf_ts"], "2026-10-07")
                self.assertEqual(e["entscheidung"], "angewendet")
                self.assertEqual(e["grund_optional"], "")
                self.assertEqual(len(e["kandidat_hash"]), 16)
                gelesen = json.loads(datei.read_text("utf-8"))
                self.assertEqual(gelesen["lauf_ts"], "2026-10-07")
        finally:
            anwenden.WURZEL = alt

    def test_append_zwei_eintraege(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        alt = anwenden.WURZEL
        try:
            with TemporaryDirectory() as d:
                anwenden.WURZEL = Path(d)
                o1 = Path(d) / "2026-10-07-spur1"
                o1.mkdir()
                (o1 / "wachen.neu.json").write_text("{}", "utf-8")
                o2 = Path(d) / "2026-10-08-spur2"
                o2.mkdir()
                (o2 / "wachen.neu.json").write_text("{}", "utf-8")
                anwenden._anwendungslog(o1, "angewendet")
                anwenden._anwendungslog(o2, "angewendet", grund="Test")
                zeilen = (Path(d) / "anwendungslog.json").read_text(
                    "utf-8").splitlines()
                self.assertEqual(len(zeilen), 2, "zwei Eintraege erwartet")
                self.assertEqual(json.loads(zeilen[1])["lauf_ts"], "2026-10-08")
                self.assertEqual(json.loads(zeilen[1])["grund_optional"], "Test")
        finally:
            anwenden.WURZEL = alt
