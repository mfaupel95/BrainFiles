"""Tests fuer Agenten/Werkzeuge/bereiche.py (Besitz-Register).

Der Kern ist nicht "die Zuordnung funktioniert", sondern die DREI Gegenproben,
ohne die das Werkzeug eine Dekoration waere:

1. Ein Aufrufer, der nicht der Besitzer ist, bekommt `gesperrt`. Andernfalls
   haette man einen Text gebaut, der nichts verhindert - und das waere die
   Hausloesung fuer ein Zuordnungsproblem, die gar keines ist.
2. Ein Pfad ohne Bereich ist IMMER frei. Andernfalls wuerde das Register den
   groessten Teil des Baums stilllegen (Routinen, Werkzeuge, Archiv), und die
   Regel wuerde unbenutzbar.
3. Dasselbe Urteil bei zwei Aufrufen. Ein Werkzeug, dessen Antwort vom Aufruf
   abhaengt (Zaehler, Caching, cwd), ist nicht pruefbar.

Der Pfadsatz wird GEGEN das echte Repo geprueft (Ordner existieren) - dort
faellt ein Tippfehler im Register auf, der sonst monatelang niemand merkt.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_WERKZEUG = os.path.normpath(os.path.join(_HIER, "..", "bereiche.py"))
_REGISTER = os.path.normpath(os.path.join(_HIER, "..", "..", "BEREICHE.json"))

_spec = importlib.util.spec_from_file_location("bereiche_werkzeug", _WERKZEUG)
assert _spec and _spec.loader, "bereiche.py nicht ladbar: %s" % _WERKZEUG
bg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bg)

ECHTE_WURZEL = os.path.normpath(os.path.join(_HIER, "..", "..", ".."))


def daten():
    with open(_REGISTER, encoding="utf-8") as f:
        return json.load(f)


class RegisterTest(unittest.TestCase):
    def test_register_ist_in_ordnung(self):
        """Drei Bereiche, jeder genau einmal, jeder Pfad wirklich im Repo."""
        fehler, besitzer_von = bg.pruefe_register(daten(), ECHTE_WURZEL)
        self.assertEqual(fehler, [], "Registerfehler: %s" % fehler)
        self.assertEqual(len(daten()["_bereiche"]), 3)
        self.assertEqual(len(set(besitzer_von.values())), 3,
                         "jeder Bereich soll einen eigenen Besitzer haben")

    def test_kein_bereich_sperrt_seinen_elternordner(self):
        """Freiheit ist der Normalfall: Agenten/Routinen/ und Werkstatt/
        gehoeren niemandem. Waere das anders, waere das Register unbrauchbar
        statt streng."""
        for p in ("Agenten/Routinen/datensortierung.ps1",
                  "Werkstatt/plan-x.md", ".gitignore",
                  "Agenten/Werkzeuge/bereiche.py"):
            self.assertIsNone(bg.besitzer(p, daten(), ECHTE_WURZEL),
                              "%s darf nicht gesperrt sein" % p)


class UrteilsTest(unittest.TestCase):
    """Die drei Gegenproben."""

    def test_besitzer_darf_in_seinen_bereich(self):
        for aufrufer, pfad in (("handel", "Agenten/Handel/scanner/wachen.json"),
                               ("bot", "Agenten/Bus/bus.py"),
                               ("wissen", "MaxHirn/Wissen/Handelsregeln.md")):
            urteil, grund = bg.pruefe(aufrufer, pfad, daten(), ECHTE_WURZEL)
            self.assertEqual(urteil, bg.FREI, "%s -> %s (%s)" % (aufrufer, pfad, grund))

    def test_fremder_ist_gesperrt_mit_begruendung(self):
        """Gegenprobe 1: ohne diesen Fall waere alles andere Dekoration."""
        urteil, grund = bg.pruefe("bot", "Agenten/Handel/befehle.py",
                                  daten(), ECHTE_WURZEL)
        self.assertEqual(urteil, bg.GESPERRT)
        self.assertIn("handel", grund)
        self.assertIn("bot", grund)
        urteil, grund = bg.pruefe("handel", "MaxHirn/Archiv/TASKS.md",
                                  daten(), ECHTE_WURZEL)
        self.assertEqual(urteil, bg.GESPERRT)

    def test_freier_pfad_ist_immer_erlaubt(self):
        """Gegenprobe 2: ein Register, das alles sperrt, wird umgangen."""
        for aufrufer in ("handel", "bot", "wissen"):
            urteil, _ = bg.pruefe(aufrufer, "Agenten/Routinen/x.ps1",
                                  daten(), ECHTE_WURZEL)
            self.assertEqual(urteil, bg.FREI)

    def test_urteil_ist_vom_aufruf_unabhaengig(self):
        """Gegenprobe 3: zweimal dieselbe Frage, zweimal dieselbe Antwort."""
        for pfad in ("Agenten/Handel/befehle.py", "Agenten/Routinen/x.ps1",
                     "Agenten/Bus/bus.py"):
            for aufrufer in ("handel", "bot", "wissen"):
                a = bg.pruefe(aufrufer, pfad, daten(), ECHTE_WURZEL)
                b = bg.pruefe(aufrufer, pfad, daten(), ECHTE_WURZEL)
                self.assertEqual(a, b, "%s/%s war nicht stabil" % (aufrufer, pfad))


class PfadTest(unittest.TestCase):
    def test_praefix_grenzt_nicht_halbwegs(self):
        """`Agenten/Handelskript/` ist NICHT `Agenten/Handel/` - ohne
        Trennzeichen im Vergleich waere ein fremder Ordner gesperrt."""
        self.assertIsNone(bg.besitzer("Agenten/Handelskript/x.py", daten(), ECHTE_WURZEL))
        self.assertIsNotNone(bg.besitzer("Agenten/Handel/xperp/x.py", daten(), ECHTE_WURZEL))

    def test_gross_klein_und_slashes_egal(self):
        """git liefert Schraegstriche und gemischte Grossschreibung; die
        Zuordnung darf daran nicht haengen."""
        erwartet = bg.besitzer("Agenten/Handel/befehle.py", daten(), ECHTE_WURZEL)["id"]
        for variante in ("agenten\\handel\\befehle.py",
                         "Agenten/Handel/befehle.py",
                         "Agenten\\Handel\\befehle.py",
                         "Agenten/Handel//befehle.py"):
            b = bg.besitzer(variante, daten(), ECHTE_WURZEL)
            self.assertIsNotNone(b, variante)
            self.assertEqual(b["id"], erwartet, variante)

    def test_unterordner_erbt_den_besitzer(self):
        """Laengster Praefix gewinnt: ein Unterordner darf nicht durch seinen
        Elternordner falsch zugeordnet werden."""
        b = bg.besitzer("Agenten/Hermes/skills/brainfiles/handel-spuren/SKILL.md",
                        daten(), ECHTE_WURZEL)
        self.assertEqual(b["id"], "bot")

    def test_absoluter_pfad_unter_der_wurzel_wird_erkannt(self):
        pfad = os.path.join(ECHTE_WURZEL, "Agenten", "Handel", "befehle.py")
        b = bg.besitzer(pfad, daten(), ECHTE_WURZEL)
        self.assertIsNotNone(b, "ein absoluter Pfad unter der Wurzel muss greifen")
        self.assertEqual(b["id"], "handel")


class BerichtTest(unittest.TestCase):
    def test_bericht_unterscheidet_drei_ausgaenge(self):
        """Die Zahl 'frei: 1' statt 'gehoeren bot' - ein freier Pfad gehoert
        niemandem, und die alte Form las sich wie eine Zusage (gemessen
        04.10.2026)."""
        text = bg.text_bericht(
            daten(),
            ["Agenten/Bus/bus.py", "Agenten/Handel/befehle.py",
             "Agenten/Routinen/x.ps1"],
            "bot", ECHTE_WURZEL)
        self.assertIn("eigen: 1", text)
        self.assertIn("frei: 1", text)
        self.assertIn("KONFLIKT: 1", text)
        self.assertIn("Agenten/Handel/befehle.py", text)

    def test_pfad_bleibt_in_seiner_schreibweise(self):
        """Intern wird klein geschrieben, im Bericht nicht - ein kleingeschrie-
        benes `agenten/handel/` im Befund sieht wie ein Fehler des Werkzeugs
        aus, nicht wie ein Konflikt."""
        _, grund = bg.pruefe("bot", "Agenten/Handel/befehle.py", daten(), ECHTE_WURZEL)
        self.assertTrue(grund.startswith("Agenten/Handel/befehle.py"), grund)


class FehlerfallTest(unittest.TestCase):
    """Ein Register mit Totalausfall wird abgewiesen - still durchzuwinken
    hiesse, ein totes Register als gueltig zu melden."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="bereiche_test_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_toter_ordner_ist_ein_fehler(self):
        os.makedirs(os.path.join(self.dir, "Agenten", "Handel"))
        pfad = os.path.join(self.dir, "r.json")
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump({"_regeln": ["x"], "_bereiche": [
                {"id": "handel", "besitzer": "handel",
                 "ordner": ["Agenten/Handel/", "Agenten/GibtEsNicht/"]}]}, f)
        d = bg.lade_register(pfad)
        fehler, _ = bg.pruefe_register(d, self.dir)
        self.assertTrue(any("GibtEsNicht" in f for f in fehler), fehler)

    def test_zwei_bereiche_auf_denselben_ordner_ist_ein_fehler(self):
        os.makedirs(os.path.join(self.dir, "Agenten", "Handel"))
        pfad = os.path.join(self.dir, "r.json")
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump({"_regeln": ["x"], "_bereiche": [
                {"id": "handel", "besitzer": "handel", "ordner": ["Agenten/Handel/"]},
                {"id": "bot", "besitzer": "bot", "ordner": ["Agenten/Handel/"]}]}, f)
        fehler, _ = bg.pruefe_register(bg.lade_register(pfad), self.dir)
        self.assertTrue(any("gehoert zu" in f for f in fehler), fehler)

    def test_doppelte_id_ist_ein_fehler(self):
        os.makedirs(os.path.join(self.dir, "Agenten", "Handel"))
        pfad = os.path.join(self.dir, "r.json")
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump({"_regeln": ["x"], "_bereiche": [
                {"id": "handel", "besitzer": "handel", "ordner": ["Agenten/Handel/"]},
                {"id": "handel", "besitzer": "handel", "ordner": ["Agenten/Handel/"]}]}, f)
        fehler, _ = bg.pruefe_register(bg.lade_register(pfad), self.dir)
        self.assertTrue(any("doppelt" in f for f in fehler), fehler)

    def test_kaputtes_json_ist_ein_fehler(self):
        pfad = os.path.join(self.dir, "r.json")
        with open(pfad, "w", encoding="utf-8") as f:
            f.write("{kein json")
        try:
            bg.lade_register(pfad)
        except bg.RegisterFehler as e:
            self.assertIn("JSON", str(e))
        else:
            self.fail("kaputtes JSON wurde akzeptiert")


class AufrufTest(unittest.TestCase):
    def test_cli_meldet_konflikt_als_exitcode(self):
        import contextlib
        import io
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = bg.main(["--aufrufer", "bot", "--pfad",
                            "Agenten/Handel/befehle.py", "--wurzel", ECHTE_WURZEL])
        self.assertEqual(code, 1, "ein Konflikt muss als Fehler herauskommen")

    def test_cli_meldet_erlaubten_pfad_als_exitcode_null(self):
        import contextlib
        import io
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = bg.main(["--aufrufer", "bot", "--pfad",
                            "Agenten/Bus/bus.py", "--wurzel", ECHTE_WURZEL])
        self.assertEqual(code, 0)

    def test_register_only_modus(self):
        import contextlib
        import io
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = bg.main(["--register", "--wurzel", ECHTE_WURZEL])
        ausgabe = puffer.getvalue()
        self.assertEqual(code, 0, ausgabe)
        for besitzer in ("handel", "bot", "wissen"):
            self.assertIn(besitzer, ausgabe)


class StagedTest(unittest.TestCase):
    """Pre-commit-Modus (--staged) gegen ein echtes, temporaeres Git-Repo."""

    def setUp(self):
        import subprocess
        self.sp = subprocess
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self._git("init", "-q")
        os.makedirs(os.path.join(self.tmp, "Agenten"))
        shutil.copy(_REGISTER, os.path.join(self.tmp, "Agenten", "BEREICHE.json"))
        for rel in ("Agenten/Handel/x.py", "MaxHirn/Wissen/y.md",
                    "Agenten/Routinen/z.ps1"):
            f = os.path.join(self.tmp, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(f), exist_ok=True)
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("x\n")
        self._alt_env = os.environ.pop("BRAINFILES_BEREICH", None)
        self.addCleanup(self._env_zurueck)

    def _env_zurueck(self):
        os.environ.pop("BRAINFILES_BEREICH", None)
        if self._alt_env is not None:
            os.environ["BRAINFILES_BEREICH"] = self._alt_env

    def _git(self, *a):
        self.sp.run(["git", "-C", self.tmp] + list(a), check=True,
                    capture_output=True)

    def _lauf(self, aufrufer=None):
        import contextlib
        import io
        err = io.StringIO()
        argv = ["--staged", "--wurzel", self.tmp]
        if aufrufer:
            argv += ["--aufrufer", aufrufer]
        with contextlib.redirect_stderr(err):
            code = bg.main(argv)
        return code, err.getvalue()

    def test_fremder_bereich_wird_verweigert(self):
        self._git("add", "MaxHirn/Wissen/y.md")
        code, err = self._lauf("handel")
        self.assertEqual(code, 1, err)
        self.assertIn("wissen", err)

    def test_eigener_und_freier_bereich_passiert(self):
        self._git("add", "Agenten/Handel/x.py", "Agenten/Routinen/z.ps1")
        code, err = self._lauf("handel")
        self.assertEqual(code, 0, err)

    def test_ohne_aufrufer_wird_nicht_blockiert(self):
        self._git("add", "MaxHirn/Wissen/y.md")
        code, _ = self._lauf(None)
        self.assertEqual(code, 0)

    def test_aufrufer_aus_umgebungsvariable(self):
        self._git("add", "MaxHirn/Wissen/y.md")
        os.environ["BRAINFILES_BEREICH"] = "handel"
        code, _ = self._lauf(None)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)