"""Tests fuer Agenten/Werkzeuge/zweige.py.

Jeder Test baut ein ECHTES temporaeres Repository (kein Mock): die Klassifikation
stuetzt sich auf `merge-base`, `cherry` und `worktree`, und ein Attrappen-Git
koennte genau die drei Faelle nicht zeigen, um die es hier geht.

Die Gegenprobe ist das eigentliche Ziel: das Werkzeug MUSS bei echtem Vorlauf
nichts anfassen. Ein Werkzeug zum Aufraeumen, das die Bremse nicht belegt, ist
schlimmer als keines - genau das hat in diesem Baum schon zweimal Arbeit
gekostet (Worktree-Zweige und der `aeeac180`-Fall vom 30.09.2026).

Ausfuehren (aus der Repo-Wurzel):
    python -m unittest discover -s Agenten/Werkzeuge/tests -p "test_zweige.py" -v
    oder einfach:
    python Agenten/Werkzeuge/tests/test_zweige.py
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_WERKZEUG = os.path.normpath(os.path.join(_HIER, "..", "zweige.py"))

_spec = importlib.util.spec_from_file_location("zweige_werkzeug", _WERKZEUG)
assert _spec and _spec.loader, "zweige.py nicht ladbar: %s" % _WERKZEUG
zg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zg)


def git(repo, *args, fehler_erlaubt=False):
    proc = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)
    if proc.returncode != 0 and not fehler_erlaubt:
        raise AssertionError("git %s -> %d: %s"
                             % (" ".join(args), proc.returncode,
                                (proc.stderr or proc.stdout).strip()))
    return proc


class Repo:
    """Ein Wegwerf-Repo mit fester Identitaet (ein Test ohne user.name
    scheitert an der globalen Git-Konfiguration des Rechners, nicht an der
    Sache)."""

    def __init__(self):
        self.pfad = tempfile.mkdtemp(prefix="zweige_test_")
        self._g("init", "-q", "-b", "master")
        self._g("config", "user.email", "test@local")
        self._g("config", "user.name", "Test")
        self._g("config", "commit.gpgsign", "false")

    def _g(self, *args, **kw):
        return git(self.pfad, *args, **kw)

    def datei(self, name, inhalt):
        p = os.path.join(self.pfad, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(inhalt)
        return p

    def commit(self, meldung, datei="a.txt", inhalt=None):
        inhalt = inhalt if inhalt is not None else meldung + "\n"
        self.datei(datei, inhalt)
        self._g("add", "--", datei)
        self._g("commit", "-q", "-m", meldung)
        return self._g("rev-parse", "HEAD").stdout.strip()

    def zweig(self, name):
        self._g("checkout", "-q", "-b", name)
        return name

    def master(self):
        self._g("checkout", "-q", "master")

    def klasse(self, zweig):
        b = zg.sammle(self.pfad)
        for e in b["lokal"] + b["remote"]:
            if e["pfad"] == zweig:
                return e["klasse"]
        return None

    def befund(self, zweig):
        b = zg.sammle(self.pfad)
        for e in b["lokal"] + b["remote"]:
            if e["pfad"] == zweig:
                return e
        return None

    def raeume(self):
        shutil.rmtree(self.pfad, ignore_errors=True)


class WerkzeugGrundTest(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r.raeume)


class KlassifikationTest(WerkzeugGrundTest):
    def test_zweig_ohne_eigenen_commit_ist_entfernen(self):
        """Ein Zweig, dessen Kopf in master steckt, ist wegwerfbar."""
        self.r.commit("basis")
        self.r.zweig("alt")
        b = self.r.befund("alt")
        self.assertEqual(b["klasse"], zg.ENTFERNEN)
        self.assertTrue(b["in_master"])
        self.assertEqual(b["echt_neu"], 0)

    def test_zweig_mit_echtem_vorlauf_bleibt_behalten(self):
        """DER Fall, der das Werkzeug wertlos machen wuerde, wenn er
        durchginge: ein Commit, den es sonst nirgends gibt."""
        self.r.commit("basis")
        self.r.zweig("arbeit")
        self.r.commit("echte arbeit", inhalt="nur hier\n")
        b = self.r.befund("arbeit")
        self.assertEqual(b["echt_neu"], 1)
        self.assertEqual(b["klasse"], zg.BEHALTEN)
        self.assertFalse(b["belegt_weg"])

    def test_inhaltlich_drin_anderer_kopf_ist_grenze(self):
        """Gemessen 30.09.2026: `aeeac180` lag inhaltlich schon in master,
        aber mit anderer sha. Inhaltlich wegwerfbar, `branch -d` verweigert -
        also eine eigene Klasse und KEINE automatische Entfernung."""
        self.r.commit("basis")
        self.r.zweig("fremd")
        sha = self.r.commit("wissen notiz", datei="w.txt", inhalt="inhalte\n")
        self.r.master()
        # master bekommt denselben INHALT mit anderer sha (Rebase/Cherry-Pick).
        self.r.datei("w.txt", "inhalte\n")
        self.r._g("add", "--", "w.txt")
        self.r._g("commit", "-q", "-m", "derselbe inhalt, andere sha")
        b = self.r.befund("fremd")
        self.assertEqual(b["echt_neu"], 0, "cherry muss den Inhalt als drin sehen")
        self.assertEqual(b["schon_dr"], 1)
        self.assertFalse(b["in_master"], "der Kopf steckt nicht in master")
        self.assertEqual(b["klasse"], zg.INHALT_DRIN)
        self.assertFalse(b["belegt_weg"])

    def test_master_und_zwischenstand_werden_nie_angefasst(self):
        """zwischenstand = Nachtsicherung der Routine (Wissen/Routinen.md).
        Das Werkzeug darf den Zweig nicht einmal AUFLISTEN."""
        self.r.commit("basis")
        self.r._g("branch", "zwischenstand")
        namen = zg.zweige_lokal(self.r.pfad)
        self.assertNotIn("master", namen)
        self.assertNotIn("zwischenstand", namen)


class GegenprobeTest(WerkzeugGrundTest):
    """Der Zweck des Ganzen: das Entfernen darf NICHTS mitnehmen, was die
    Messung als zu behalten ausgewiesen hat."""

    def test_entfernen_laesst_echten_vorlauf_stehen(self):
        """Der Kern des Werkzeugs in einem Lauf: der wegwerfbare Zweig muss
        verschwinden, der mit eigener Arbeit stehen bleiben - und die
        Klassifikation der Reste muss danach unveraendert sein.

        Aufbau: "weg" zeigt auf einen Commit, der in master steckt (keine
        eigene Arbeit), "bleibt" traegt einen Commit mit eigenem Inhalt, den es
        sonst nirgends gibt. Der erste Versuch dieses Tests gab "weg" ebenfalls
        einen Commit mit Inhalt - damit ist er per Definition echter Vorlauf und
        das Werkzeug waereZU RECHT stehengeblieben."""
        self.r.commit("basis")
        self.r.zweig("weg")
        self.r.master()
        self.r.zweig("bleibt")
        self.r.commit("bleib-arbeit", inhalt="nur hier drin\n")
        self.r.master()

        vorher = {e["pfad"]: e["klasse"] for e in zg.sammle(self.r.pfad)["lokal"]}
        self.assertEqual(vorher.get("weg"), zg.ENTFERNEN)
        self.assertEqual(vorher.get("bleibt"), zg.BEHALTEN)
        entfernt = zg.entfernen(self.r.pfad, zg.sammle(self.r.pfad))

        self.assertIn("lokal weg", entfernt)
        self.assertNotIn("lokal bleibt", entfernt)
        nachher = {e["pfad"]: e["klasse"] for e in zg.sammle(self.r.pfad)["lokal"]}
        # "weg" ist verschwunden, "bleibt" unveraendert - beides ist Teil des
        # Beweises: ein verschwundener Rest wuerde heissen, dass die Bremse auch
        # den echten Vorlauf genommen hat.
        self.assertNotIn("weg", nachher)
        self.assertEqual(nachher.get("bleibt"), zg.BEHALTEN)
        self.assertEqual(set(nachher), {"bleibt"})

    def test_entfernen_braucht_die_messung_nicht_selbst(self):
        """`entfernen()` liest `belegt_weg` aus dem uebergebenen Befund. Wer
        ihm einen fremdgebauten Befund ohne dieses Feld gibt, passiert nichts -
        die Bremse haengt an einem Feld, nicht an einer Absicht."""
        self.r.commit("basis")
        self.r.zweig("weg")
        befunde = {"lokal": [{"pfad": "weg", "kurz": "x", "belegt_weg": False,
                               "klasse": zg.BEHALTEN, "vorlauf": 0}],
                   "remote": [], "worktrees": []}
        entfernt = zg.entfernen(self.r.pfad, befunde)
        self.assertEqual(entfernt, [])
        self.assertEqual(self.r.befund("weg")["pfad"], "weg")

    def test_ohne_schalter_wird_nichts_entfernt(self):
        self.r.commit("basis")
        self.r.zweig("weg")
        vorher = git(self.r.pfad, "branch", "--list").stdout
        self.assertEqual(zg.main(["--wurzel", self.r.pfad]), 0)
        nachher = git(self.r.pfad, "branch", "--list").stdout
        self.assertEqual(vorher, nachher, "der Vorgabe-Aufruf loescht nichts")


class WorktreeTest(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r.raeume)
        self.r.commit("basis")

    def _wt(self, name="wt"):
        pfad = os.path.join(tempfile.gettempdir(), "zweige_wt_%s_%d" % (name, os.getpid()))
        git(self.r.pfad, "worktree", "add", "-q", pfad, "-b", "wtzweig")
        self.addCleanup(lambda: shutil.rmtree(pfad, ignore_errors=True))
        return pfad

    def _suche(self, pfad):
        """Den Befund zu einem Worktree finden - ueber den NORMALISIERTEN Pfad,
        nicht ueber `==`. git meldet `C:/Users/...` mit Schraegstrich, `add`
        lieferte `C:\\Users\\...` zurueck; ein Gleichheitsvergleich findet
        einen vorhandenen Worktree dann nicht (gemessen am 04.10.2026, zwei
        IndexError)."""
        key = zg._pfad_norm(pfad)
        treffer = [x for x in zg.worktrees(self.r.pfad)
                   if zg._pfad_norm(x["pfad"]) == key]
        self.assertEqual(len(treffer), 1,
                         "Worktree nicht gefunden: %s" % pfad)
        return treffer[0]

    def test_sauberer_worktree_in_master_ist_wegwerfbar(self):
        pfad = self._wt()
        w = self._suche(pfad)
        self.assertFalse(w["haupt"])
        self.assertTrue(w["in_master"])
        self.assertEqual(w["geaendert"], 0)
        self.assertEqual(w["klasse"], zg.ENTFERNEN)

    def test_worktree_mit_arbeit_bleibt_stehen(self):
        pfad = self._wt()
        with open(os.path.join(pfad, "neu.txt"), "w", encoding="utf-8") as f:
            f.write("arbeit\n")
        w = self._suche(pfad)
        self.assertGreaterEqual(w["geaendert"], 1)
        self.assertEqual(w["klasse"], zg.BEHALTEN)
        entfernt = zg.entfernen(self.r.pfad, {"worktrees": [w],
                                              "lokal": [], "remote": []})
        self.assertEqual(entfernt, [], "ein schmutziger Worktree wird nicht entfernt")
        self.assertTrue(os.path.isdir(pfad))

    def test_hauptbaum_ist_nie_wegwerfbar(self):
        haupt = [x for x in zg.worktrees(self.r.pfad) if x["haupt"]]
        self.assertEqual(len(haupt), 1)
        self.assertEqual(haupt[0]["klasse"], zg.BEHALTEN)


class BerichtTest(WerkzeugGrundTest):
    def test_bericht_nennt_echten_vorlauf_wortlich(self):
        """Ein Befund, den niemand benennen kann, wird nicht bearbeitet. Der
        Satz steht im Bericht, damit die Entscheidung beim Menschen bleibt."""
        self.r.commit("basis")
        self.r.zweig("arbeit")
        self.r.commit("echt", inhalt="echt\n")
        text = zg.bericht(zg.sammle(self.r.pfad))
        self.assertIn("arbeit", text)
        self.assertIn("behalten", text)

    def test_json_ist_vollstaendig_und_reproduzierbar(self):
        self.r.commit("basis")
        self.r.zweig("weg")
        import io
        import contextlib
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            zg.main(["--wurzel", self.r.pfad, "--json"])
        import json
        daten = json.loads(puffer.getvalue())
        self.assertEqual(daten["entfernt"], [])
        self.assertTrue(any(e["pfad"] == "weg" for e in daten["lokal"]))


class WurzelTest(unittest.TestCase):
    def test_wurzel_wird_gefunden_ohne_harte_Pfade(self):
        """Kein absoluter Pfad im Werkzeug: es laeuft aus jeder Lage."""
        hier = os.path.dirname(_WERKZEUG)
        alt, os.environ["HERMES_HOME"] = os.environ.get("HERMES_HOME"), hier
        try:
            gefunden = zg.wurzel()
        finally:
            if alt is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = alt
        self.assertTrue(os.path.isdir(os.path.join(gefunden, ".git")))


if __name__ == "__main__":
    unittest.main(verbosity=2)