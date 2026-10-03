"""Tests fuer manifest.py - Manifest laden, pruefen, mit der Platte zusammenfuehren."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import manifest  # noqa: E402
import quellen  # noqa: E402
import scan  # noqa: E402


def schreibe_manifest(pfad: Path, eintraege: list[dict], stand: str = "2026-09-18") -> Path:
    pfad.write_text(
        json.dumps({"stand": stand, "repos": eintraege}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return pfad


def repo(ordner="demo", *, art="python", venv=".venv", node_modules=True) -> scan.Repo:
    return scan.Repo(
        ordner=ordner,
        pfad=Path("C:/x") / ordner,
        art=art,
        git=True,
        venv=venv,
        venv_python=(Path("C:/x") / ordner / venv / "Scripts" / "python.exe") if venv else None,
        node_modules=node_modules,
        readme="README.md",
    )


class ManifestLadenTest(unittest.TestCase):
    def test_start_als_zeichenkette_ist_ein_fehler_statt_eines_absturzes(self):
        with tempfile.TemporaryDirectory() as t:
            p = schreibe_manifest(
                Path(t) / "m.json",
                [{"ordner": "a", "start": "npm start"}],
            )
            eintraege = manifest.manifest_laden(p)
            self.assertEqual(eintraege[0].start, None)
            self.assertTrue(eintraege[0].fehler)
            self.assertIn("start", eintraege[0].fehler[0])

    def test_ordner_mit_pfadtrenner_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as t:
            p = schreibe_manifest(
                Path(t) / "m.json",
                [{"ordner": "../boese", "start": ["x"]}, {"ordner": "gut"}],
            )
            eintraege = {e.ordner: e for e in manifest.manifest_laden(p)}
            self.assertFalse(eintraege["../boese"].erlaubt)
            self.assertTrue(eintraege["gut"].erlaubt)

    def test_bot_wird_klein_geschrieben(self):
        with tempfile.TemporaryDirectory() as t:
            p = schreibe_manifest(Path(t) / "m.json", [{"ordner": "a", "bot": "Moon-Dev-Agents"}])
            self.assertEqual(manifest.manifest_laden(p)[0].bot, "moon-dev-agents")

    def test_fehlende_datei_ergibt_leere_liste_statt_fehler(self):
        self.assertEqual(manifest.manifest_laden(Path("gibt-es-nicht.json")), [])

    def test_kaputtes_json_wirft_nicht(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "m.json"
            p.write_text("{ das ist kein json", encoding="utf-8")
            self.assertEqual(manifest.manifest_laden(p), [])


class ZeilenBauenTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.basis = Path(self.t.name) / "Repos"
        self.profile = Path(self.t.name) / "profiles"
        (self.profile / "moon-dev-agents").mkdir(parents=True)
        (self.profile / "moon-dev-agents" / "config.yaml").write_text("a: 1\n", encoding="utf-8")
        (self.basis / "moon-dev-ai-agents").mkdir(parents=True)

    def tearDown(self):
        self.t.cleanup()

    def zeilen(self, repos, eintraege):
        # Die Testordner muessen auf der Platte liegen: sonst entsteht zusaetzlich
        # eine "fehlt"-Zeile fuer denselben Eintrag (gewolltes Verhalten).
        for r in repos:
            (self.basis / r.ordner).mkdir(parents=True, exist_ok=True)
        plaetze = [(quellen.wurzel_von("repos"), repos)]
        return {
            z.ordner: z
            for z in manifest.zeilen_bauen(plaetze, eintraege, self.profile)
        }

    def test_ordner_ohne_eintrag_ist_neu(self):
        z = self.zeilen([repo("frischer-klon")], [])
        self.assertEqual(z["frischer-klon"].gruppe, "neu")
        self.assertTrue(z["frischer-klon"].gruende)

    def test_eintrag_ohne_ordner_ist_fehlt(self):
        e = manifest.Eintrag(ordner="weg", start=["x"])
        z = self.zeilen([], [e])
        self.assertEqual(z["weg"].gruppe, "fehlt")

    def test_start_ohne_venv_ist_einrichten_mit_grund(self):
        e = manifest.Eintrag(ordner="demo", start=[".venv\\Scripts\\python.exe", "x.py"],
                            venv_pflicht=True)
        z = self.zeilen([repo("demo", venv=None)], [e])
        self.assertEqual(z["demo"].gruppe, "einrichten")
        self.assertIn("venv fehlt", z["demo"].gruende)

    def test_start_mit_allem_ist_startbar(self):
        e = manifest.Eintrag(ordner="demo", start=[".venv\\Scripts\\pythonw.exe", "gui.py"],
                            venv_pflicht=True, bot="moon-dev-agents")
        z = self.zeilen([repo("demo")], [e])
        self.assertEqual(z["demo"].gruppe, "startbar")
        # `gruende` traegt Blocker UND Hinweise: seit 30.09.2026 kommt hier der
        # Fremd-Hinweis dazu (der Demo-Eintrag liegt unter Werkstatt/Repos, also
        # in der Klonsammlung). Was gelten soll, ist: NICHTS blockiert den Start -
        # und das sagt die Gruppe. Auf einen leeren Liste zu pruefen hiesse, einen
        # Zustand einzufrieren statt die Regel.
        self.assertTrue(z["demo"].start_da)
        self.assertFalse([g for g in z["demo"].gruende
                          if "fehlt" in g or "kein Startbefehl" in g])
        self.assertTrue(z["demo"].bot_da)

    def test_gruppe_doku_im_manifest_bleibt_doku_trotz_start(self):
        e = manifest.Eintrag(ordner="demo", gruppe="doku", start=["x"])
        z = self.zeilen([repo("demo", art="doku")], [e])
        self.assertEqual(z["demo"].gruppe, "doku")

    def test_fehlendes_bot_profil_ist_ein_grund_aber_keine_andere_gruppe(self):
        e = manifest.Eintrag(ordner="demo", start=["x"], bot="gibt-es-nicht")
        z = self.zeilen([repo("demo")], [e])
        self.assertEqual(z["demo"].gruppe, "startbar")
        self.assertFalse(z["demo"].bot_da)
        self.assertIn("Bot-Profil fehlt: gibt-es-nicht", z["demo"].gruende)

    def test_node_modules_pflicht_ohne_node_modules(self):
        e = manifest.Eintrag(ordner="demo", start=["npm", "start"], node_modules_pflicht=True)
        z = self.zeilen([repo("demo", art="node", venv=None, node_modules=False)], [e])
        self.assertEqual(z["demo"].gruppe, "einrichten")
        self.assertIn("node_modules fehlt (npm install)", z["demo"].gruende)

    def test_pfad_pflicht_meldet_fehlende_datei(self):
        e = manifest.Eintrag(ordner="demo", start=["target\\release\\x.exe"],
                            pfad_pflicht="target\\release\\x.exe")
        z = self.zeilen([repo("demo", art="rust", venv=None)], [e])
        self.assertEqual(z["demo"].gruppe, "einrichten")
        self.assertIn("target\\release\\x.exe fehlt (bauen)", z["demo"].gruende)

    def test_manifest_fehler_landet_als_grund(self):
        e = manifest.Eintrag(ordner="demo", start=None, fehler=["start ist keine Liste"])
        z = self.zeilen([repo("demo")], [e])
        self.assertEqual(z["demo"].gruppe, "einrichten")
        self.assertIn("start ist keine Liste", z["demo"].gruende)


class EchtesManifestTest(unittest.TestCase):
    def test_das_manifest_der_zentrale_ist_lesbar_und_vollstaendig(self):
        hier = Path(__file__).resolve().parent.parent
        p = hier / "repos-zentrale.json"
        self.assertTrue(p.is_file(), "repos-zentrale.json fehlt")
        eintraege = manifest.manifest_laden(p)
        self.assertGreaterEqual(len(eintraege), 28)
        for e in eintraege:
            self.assertTrue(e.erlaubt, f"{e.ordner}: {e.fehler}")
        ordner = {e.ordner for e in eintraege}
        self.assertIn("moon-dev-ai-agents", ordner)
        self.assertNotIn("copilot-worktrees", ordner)
        for e in eintraege:
            if e.bot:
                self.assertEqual(e.bot, e.bot.lower(), "Bot-Namen sind klein")

    def test_jeder_eintrag_liegt_in_seiner_wurzel_auf_der_platte(self):
        hier = Path(__file__).resolve().parent.parent
        brainfiles = hier.parents[2]
        if not (brainfiles / "Werkstatt" / "Repos").is_dir():
            self.skipTest(f"kein Bestand unter {brainfiles / 'Werkstatt' / 'Repos'}")
        fehlend = []
        for e in manifest.manifest_laden(hier / "repos-zentrale.json"):
            w = quellen.wurzel_von(e.wurzel)
            if w is None:
                fehlend.append(f"{e.ordner}: unbekannte Wurzel {e.wurzel}")
                continue
            if not (w.pfad(brainfiles) / e.pfad).exists():
                fehlend.append(f"{e.wurzel}/{e.pfad}")
        self.assertEqual(fehlend, [])

    def test_jede_wurzel_hat_eintraege(self):
        hier = Path(__file__).resolve().parent.parent
        eintraege = manifest.manifest_laden(hier / "repos-zentrale.json")
        belegt = {e.wurzel for e in eintraege}
        for w in quellen.REIHENFOLGE:
            self.assertIn(w, belegt, f"kein Eintrag in der Wurzel {w}")

    def test_kein_schluessel_ist_doppelt(self):
        hier = Path(__file__).resolve().parent.parent
        schluessel = [
            (e.wurzel, e.pfad)
            for e in manifest.manifest_laden(hier / "repos-zentrale.json")
        ]
        doppelt = sorted({s for s in schluessel if schluessel.count(s) > 1})
        self.assertEqual(doppelt, [], "derselbe (Wurzel, Pfad) steht zweimal im Manifest")

    def test_jedes_bot_profil_des_manifests_existiert(self):
        hier = Path(__file__).resolve().parent.parent
        profile = hier.parents[1] / "Hermes" / "profiles"
        if not profile.is_dir():
            self.skipTest(f"keine Profile unter {profile}")
        fehlend = [
            e.bot
            for e in manifest.manifest_laden(hier / "repos-zentrale.json")
            if e.bot and not (profile / e.bot / "config.yaml").is_file()
        ]
        self.assertEqual(
            fehlend, [],
            "ein Bot ohne Profil ist ein Knopf ins Leere - entweder Profil anlegen "
            "oder den Namen aus dem Manifest nehmen (weggelegte Profile liegen in "
            "profiles/.deleted)",
        )


if __name__ == "__main__":
    unittest.main()
