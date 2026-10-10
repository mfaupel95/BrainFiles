import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import mkdtemp

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL.parent / "scanner"))
import anwenden  # noqa: E402
import xperp_suche  # noqa: E402

SPUREN = json.loads((WURZEL / "spuren.json").read_text("utf-8"))
KONFIG = json.loads((WURZEL / "konfig.json").read_text("utf-8"))
CO = "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
WACHEN_ALT = ('{\n  "max_hebel": 5,\n  "handel_erlaubt": true,\n'
              '  "stop_atr_faktor": 1.5,\n  "ziel_atr_faktor": 3.0\n}\n')


def _git(repo, *a):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                          text=True, check=True)


class TestKonfig(unittest.TestCase):
    def test_spur2_eintrag_hat_acht_schluessel_ohne_bewertungsdatei(self):
        s = SPUREN["spur2"]
        self.assertNotIn("bewertung_datei", s)
        self.assertEqual(set(s["aenderbar"]["wachen.json"]),
                         set(xperp_suche.SCHRITT))

    def test_basiswerte_der_echten_wache_liegen_in_den_grenzen(self):
        wachen = json.loads(
            (WURZEL.parent / "xperp" / "wachen.json").read_text("utf-8"))
        grenzen = SPUREN["spur2"]["aenderbar"]["wachen.json"]
        for k, v in xperp_suche.basis_werte(wachen).items():
            lo, hi = grenzen[k]
            self.assertTrue(lo <= v <= hi, "%s=%s ausserhalb [%s, %s]"
                            % (k, v, lo, hi))

    def test_spur2_konfig_vollstaendig(self):
        k = KONFIG["spur2"]
        for feld in ("such_budget", "such_tage", "test_tage", "schritt_tage",
                     "holdout_tage", "holdout_min_runden",
                     "holdout_max_nutzungen", "overfit_min_fenster",
                     "overfit_min_runden"):
            self.assertIn(feld, k)
        self.assertEqual(k["holdout_max_nutzungen"], 8)

    def test_konfig_ergibt_mindestens_die_geforderte_fensterzahl(self):
        fenster, _ = xperp_suche.fenster_grenzen(10**12, KONFIG["spur2"])
        self.assertGreaterEqual(len(fenster),
                                KONFIG["spur2"]["overfit_min_fenster"])


class TestDenylist(unittest.TestCase):
    GESPERRT = ["max_hebel", "max_margin_je_anlauf_usd",
                "max_margin_gesamt_usd", "max_offene_anlaeufe",
                "risiko_je_anlauf_usd", "kill_switch_gesamt_usd",
                "drawdown_halbierung_usd", "freigabe", "herzschlag_max_minuten",
                "handel_erlaubt", "trailing_aktiv", "llm_aktiv", "llm_modell",
                "papier_faktor", "familien", "grid_stufen", "grid_spanne_atr"]

    def test_jeder_gesperrte_schluessel_wird_abgelehnt(self):
        for k in self.GESPERRT:
            self.assertFalse(anwenden.denylist_ok({k})[0], k)

    def test_alle_suchschluessel_sind_frei(self):
        self.assertTrue(anwenden.denylist_ok(set(xperp_suche.SCHRITT))[0])

    def test_whitelisten_von_spur1_und_spur3_bleiben_frei(self):
        for name in ("spur1", "spur3"):
            schluessel = set(SPUREN[name]["aenderbar"]["wachen.json"])
            self.assertTrue(anwenden.denylist_ok(schluessel)[0], name)


class TestAnwendenSpur2(unittest.TestCase):
    def setUp(self):
        self._orig = anwenden.WURZEL
        anwenden.WURZEL = Path(mkdtemp())
        self.addCleanup(setattr, anwenden, "WURZEL", self._orig)
        self.repo = Path(mkdtemp())
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")
        _git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "xperp").mkdir()
        self.wachen = self.repo / "xperp" / "wachen.json"
        self.wachen.write_text(WACHEN_ALT, "utf-8", newline="")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.spur = {
            "wachen": str(self.wachen),
            "aenderbar": {"wachen.json": {
                "stop_atr_faktor": [1.0, 2.5],
                "ziel_atr_faktor": [2.0, 4.5]}}}

    def _vorschlag(self, neu_text):
        ordner = self.repo / "v"
        ordner.mkdir()
        (ordner / "wachen.neu.json").write_text(neu_text, "utf-8", newline="")
        (ordner / "commit.txt").write_text(
            "verbesserer: spur2 Test\n\n" + CO + "\n", "utf-8")
        return ordner

    def test_vorschlag_ohne_bewertungsdatei_wird_angewandt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertTrue(r["ok"], r["grund"])
        self.assertIn('"stop_atr_faktor": 1.75', self.wachen.read_text("utf-8"))
        geaendert = _git(self.repo, "show", "--name-only",
                         "--format=", "HEAD").stdout.split()
        self.assertEqual(geaendert, ["xperp/wachen.json"])

    def test_denylist_blockt_max_hebel(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"max_hebel": 5', '"max_hebel": 8'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("max_hebel", r["grund"])
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_ALT)

    def test_wert_ausserhalb_des_bereichs_wird_abgelehnt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 3.0'))
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("ausserhalb", r["grund"])

    def test_veraltete_wache_wird_nicht_ueberschrieben(self):
        # Review Focus 1: Vorschlag stammt vom alten Stand; inzwischen hat der
        # Kill-Switch handel_erlaubt auf false gesetzt und committet.
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        self.wachen.write_text(
            WACHEN_ALT.replace('"handel_erlaubt": true',
                               '"handel_erlaubt": false'), "utf-8", newline="")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "kill-switch")
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("handel_erlaubt", r["grund"])
        self.assertIn('"handel_erlaubt": false', self.wachen.read_text("utf-8"))

    def _mit_pruefsumme(self, ziel_neu='"ziel_atr_faktor": 3.5'):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"ziel_atr_faktor": 3.0', ziel_neu))
        (ordner / "basis.sha256").write_text(
            hashlib.sha256(WACHEN_ALT.encode("utf-8")).hexdigest(), "utf-8")
        return ordner

    def test_passende_pruefsumme_wendet_an(self):
        r = anwenden.anwenden(self._mit_pruefsumme(), self.spur, self.repo)
        self.assertTrue(r["ok"], r["grund"])

    def test_handaenderung_an_whitelist_schluessel_wird_nicht_ueberschrieben(
            self):
        # Der Vorschlag aendert nur ziel_atr_faktor; stop_atr_faktor (auch
        # auf der Whitelist) hat inzwischen jemand von Hand geaendert.
        ordner = self._mit_pruefsumme()
        hand = WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                                  '"stop_atr_faktor": 2.0')
        self.wachen.write_text(hand, "utf-8", newline="")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "von Hand")
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertIn("seit dem Lauf", r["grund"])
        self.assertEqual(self.wachen.read_text("utf-8"), hand)

    def test_patch_ohne_bewertungsdatei_wird_abgelehnt(self):
        ordner = self._vorschlag(
            WACHEN_ALT.replace('"stop_atr_faktor": 1.5',
                               '"stop_atr_faktor": 1.75'))
        (ordner / "bewertung.patch").write_text(
            "--- a/b.py\n+++ b/b.py\n@@ -1 +1 @@\n-x\n+y\n", "utf-8")
        r = anwenden.anwenden(ordner, self.spur, self.repo)
        self.assertFalse(r["ok"])
        self.assertEqual(self.wachen.read_text("utf-8"), WACHEN_ALT)


if __name__ == "__main__":
    unittest.main()
