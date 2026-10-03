"""Die Befehlsliste eines Repos - reine Logik, kein Fenster.

Geprueft wird die REGEL, nicht ein Datenbestand: dass die Grundkommandos nur
erscheinen, wenn sie etwas ausloesen koennen, dass Manifest-Befehle ohne argv
wegfallen und dass die Anleitung den Zustand des Repos nennt (venv da/fehlt).
"""

import sys
import unittest
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import befehle  # noqa: E402


@dataclass
class FakeRepo:
    pfad: Path = Path("C:/x/Projekt")
    venv: str | None = ".venv"
    readme: str | None = "README.md"


@dataclass
class FakeZeile:
    ordner: str = "Projekt"
    notiz: str = "macht etwas"
    gruende: list[str] = field(default_factory=list)
    anleitung: str = ""
    befehle: list[dict] = field(default_factory=list)
    start: list[str] | None = None
    bot: str | None = None
    bot_da: bool = False
    repo: FakeRepo | None = field(default_factory=FakeRepo)


class GrundkommandosTest(unittest.TestCase):
    def test_starten_steht_nur_da_wenn_ein_befehl_belegt_ist(self):
        ohne = befehle.grundkommandos(FakeZeile())
        mit = befehle.grundkommandos(FakeZeile(start=[".venv\\Scripts\\python.exe", "x.py"]))
        self.assertNotIn("Starten", [k.was for k in ohne])
        self.assertEqual(mit[0].was, "Starten")
        self.assertEqual(mit[0].art, "start")
        self.assertEqual(mit[0].cmd, [".venv\\Scripts\\python.exe", "x.py"])

    def test_ordner_und_terminal_gibt_es_immer(self):
        namen = [k.was for k in befehle.grundkommandos(FakeZeile())]
        self.assertIn("Terminal hier oeffnen", namen)
        self.assertIn("Ordner im Explorer", namen)

    def test_doku_nur_mit_readme(self):
        ohne = befehle.grundkommandos(FakeZeile(repo=FakeRepo(readme=None)))
        self.assertEqual([k for k in ohne if k.art == "doku"], [])
        mit = befehle.grundkommandos(FakeZeile())
        self.assertEqual([k.hinweis for k in mit if k.art == "doku"], ["README.md"])

    def test_bot_nur_mit_vorhandenem_profil(self):
        ohne = befehle.grundkommandos(FakeZeile(bot="x", bot_da=False))
        self.assertEqual([k for k in ohne if k.art == "bot"], [])
        mit = befehle.grundkommandos(FakeZeile(bot="x", bot_da=True))
        self.assertEqual([k.was for k in mit if k.art == "bot"], ["Bot x fragen"])

    def test_ohne_repo_gibt_es_keine_handgriffe(self):
        """Ein Eintrag ohne Ordner auf der Platte (Gruppe FEHLT) hat nichts zu oeffnen."""
        liste = befehle.grundkommandos(FakeZeile(repo=None))
        self.assertEqual(liste, [])
        self.assertEqual([k for k in liste if k.art == "doku"], [])


class ManifestkommandosTest(unittest.TestCase):
    def test_befehl_ohne_argv_faellt_weg(self):
        z = FakeZeile(befehle=[{"was": "kaputt", "cmd": []}, {"was": "gut", "cmd": ["a", "b"]}])
        liste = befehle.manifestkommandos(z)
        self.assertEqual([k.was for k in liste], ["gut"])

    def test_titel_faellt_auf_den_befehl_zurueck(self):
        z = FakeZeile(befehle=[{"cmd": ["python", "-m", "x"]}])
        self.assertEqual(befehle.manifestkommandos(z)[0].was, "python -m x")

    def test_start_markierung_wird_uebernommen(self):
        z = FakeZeile(befehle=[{"was": "Los", "cmd": ["a"], "start": True}])
        self.assertEqual(befehle.manifestkommandos(z)[0].art, "start")

    def test_reihenfolge_grund_dann_manifest(self):
        z = FakeZeile(start=["a"], befehle=[{"was": "Eigenes", "cmd": ["b"]}])
        namen = [k.was for k in befehle.kommandos(z)]
        self.assertEqual(namen[0], "Starten")
        self.assertEqual(namen[-1], "Eigenes")


class BefehlTextTest(unittest.TestCase):
    def test_leerzeichen_werden_gequotet(self):
        self.assertEqual(
            befehle.befehl_text([".venv\\Scripts\\python.exe", "-m", "scripts.download"]),
            ".venv\\Scripts\\python.exe -m scripts.download",
        )
        self.assertEqual(
            befehle.befehl_text(["cmd.exe", "/c", "C:\\mit leer\\x.py"]),
            'cmd.exe /c "C:\\mit leer\\x.py"',
        )

    def test_leere_liste_ist_leerer_text(self):
        self.assertEqual(befehle.befehl_text(None), "")
        self.assertEqual(befehle.befehl_text([]), "")


class AnleitungTest(unittest.TestCase):
    def test_nennt_zweck_ordner_und_venv(self):
        text = befehle.anleitung(FakeZeile())
        self.assertIn("Wozu: macht etwas", text)
        self.assertIn("Projekt", text)
        self.assertIn("Venv: vorhanden", text)

    def test_fehlendes_venv_wird_gesagt(self):
        text = befehle.anleitung(FakeZeile(repo=FakeRepo(venv=None)))
        self.assertIn("Venv: fehlt", text)

    def test_gruende_stehen_als_zu_tun_da(self):
        text = befehle.anleitung(FakeZeile(gruende=["venv fehlt"]))
        self.assertIn("Zu tun: venv fehlt", text)

    def test_eigene_anleitung_hat_vorrang_vor_dem_hinweis(self):
        mit = befehle.anleitung(FakeZeile(anleitung="Erst X, dann Y."))
        ohne = befehle.anleitung(FakeZeile())
        self.assertIn("Erst X, dann Y.", mit)
        self.assertNotIn("noch kein Ablauf hinterlegt", mit)
        self.assertIn("noch kein Ablauf hinterlegt", ohne)


if __name__ == "__main__":
    unittest.main()