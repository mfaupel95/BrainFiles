"""Tests fuer die Pflege: Vorschlaege, Pruefung, Ausfuehrung, Belegung.

Grundsatz: **kein Test richtet etwas wirklich ein.** `ausfuehren` wird nur mit
harmlosen Befehlen des laufenden Interpreters geprueft (`-c "print(1)"`), und
`eintragen` schreibt in ein Manifest in einem Temp-Ordner.
"""

import datetime as dt
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pflege  # noqa: E402

PY = sys.executable


class VorschlagTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def _datei(self, name, inhalt=""):
        (self.repo / name).write_text(inhalt, encoding="utf-8")

    def test_leerer_ordner_ergibt_keinen_vorschlag(self):
        self.assertEqual(pflege.vorschlag_einrichten(self.repo), [])
        self.assertIn("kein Anhaltspunkt", pflege.einrichten_grund(self.repo))

    def test_requirements_legt_venv_an_und_installiert(self):
        self._datei("requirements.txt", "requests\n")
        schritte = pflege.vorschlag_einrichten(self.repo)
        self.assertEqual(len(schritte), 3)          # venv, pip hochziehen, install -r
        self.assertIn("-m", schritte[0])
        self.assertIn("venv", schritte[0])
        self.assertEqual(schritte[-1][-2:], ["-r", "requirements.txt"])

    def test_vorhandene_venv_wird_nicht_neu_gebaut(self):
        self._datei("requirements.txt")
        (self.repo / ".venv" / "Scripts").mkdir(parents=True)
        (self.repo / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
        schritte = pflege.vorschlag_einrichten(self.repo)
        self.assertEqual(len(schritte), 1)
        self.assertNotIn([sys.executable, "-m", "venv", ".venv"], schritte,
                         "die vorhandene venv wird nicht neu gebaut")

    def test_pyproject_wird_editierbar_installiert(self):
        self._datei("pyproject.toml", "[project]\nname='x'\n")
        schritte = pflege.vorschlag_einrichten(self.repo)
        self.assertEqual(schritte[-1][-2:], ["-e", "."])

    @unittest.skipUnless(shutil.which("npm"), "npm fehlt auf diesem Rechner")
    def test_package_json_ergibt_npm_install(self):
        self._datei("package.json", "{}")
        schritte = pflege.vorschlag_einrichten(self.repo)
        self.assertEqual(schritte[-1], ["npm", "install"])
        self.assertIn("package.json", pflege.einrichten_grund(self.repo))

    def test_bauen_aus_den_merkmalen(self):
        self._datei("Cargo.toml", "[package]\nname='x'\n")
        self.assertEqual(pflege.vorschlag_bauen(self.repo), [["cargo", "build", "--release"]])
        (self.repo / "Cargo.toml").unlink()
        self._datei("go.mod", "module x\n")
        self.assertEqual(pflege.vorschlag_bauen(self.repo), [["go", "build", "./..."]])
        (self.repo / "go.mod").unlink()
        self._datei("package.json", json.dumps({"scripts": {"build": "vite build"}}))
        self.assertEqual(pflege.vorschlag_bauen(self.repo), [["npm", "run", "build"]])
        self._datei("package.json", json.dumps({"scripts": {"start": "node x"}}))
        self.assertEqual(pflege.vorschlag_bauen(self.repo), [])
        self.assertIn("ohne scripts.build", pflege.bauen_grund(self.repo))

    def test_kaputtes_package_json_ergibt_keinen_bau(self):
        self._datei("package.json", "{kaputt")
        self.assertEqual(pflege.vorschlag_bauen(self.repo), [])


class Zeile:
    """Minimale Zeile fuer `pruefen` - nur die Attribute, die es liest."""

    def __init__(self, pfad, **felder):
        self.ordner = Path(pfad).name
        self.art = "python"
        self.start = felder.get("start")
        self.bot = None
        self.bot_da = False
        self.gruppe = "startbar"
        self.bereich = "REPOS"
        self.pfad_pflicht = felder.get("pfad_pflicht")
        self.port = felder.get("port")
        self.venv_pflicht = felder.get("venv_pflicht", False)

        class R:
            pass

        r = R()
        r.pfad = Path(pfad)
        r.readme = felder.get("readme")
        r.venv = felder.get("venv")
        r.node_modules = felder.get("node_modules", False)
        r.git = felder.get("git", False)
        self.repo = r


class PruefenTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def _punkte(self, z, **kwargs):
        return {p.name: p for p in pflege.pruefen(z, **kwargs)}

    def test_fehlende_venv_ist_reparierbar(self):
        z = Zeile(self.repo, venv_pflicht=True)
        p = self._punkte(z)["venv"]
        self.assertEqual(p.stand, "fehlt")
        self.assertTrue(p.reparabel)

    def test_kaputte_venv_wird_benannt_statt_repariert(self):
        """Eine .venv, deren python.exe nicht startet, ist kein pip-Fall."""
        (self.repo / ".venv" / "Scripts").mkdir(parents=True)
        (self.repo / ".venv" / "Scripts" / "python.exe").write_bytes(b"kein Programm")
        p = self._punkte(Zeile(self.repo))["venv"]
        self.assertEqual(p.stand, "fehlt")
        self.assertIn("startet nicht", p.text)
        self.assertIn("--clear", " ".join(p.schritte[0]))

    def test_fehlender_pflichtpfad_nennt_den_bauschritt(self):
        (self.repo / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
        z = Zeile(self.repo, pfad_pflicht="target/release/x.exe")
        p = self._punkte(z)["target/release/x.exe"]
        self.assertEqual(p.stand, "fehlt")
        self.assertEqual(p.schritte[0], ["cargo", "build", "--release"])

    def test_vorhandener_pflichtpfad_ist_ok(self):
        (self.repo / "target" / "release").mkdir(parents=True)
        (self.repo / "target" / "release" / "x.exe").write_bytes(b"")
        z = Zeile(self.repo, pfad_pflicht="target/release/x.exe")
        self.assertEqual(self._punkte(z)["target/release/x.exe"].stand, "ok")

    def test_freier_port_ist_ok_und_belegter_ist_warnung(self):
        import socket

        frei = self._punkte(Zeile(self.repo))["Port"]
        self.assertIn("kein Port", frei.text)
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.listen(1)
        try:
            p = self._punkte(Zeile(self.repo, port=port))["Port"]
            self.assertEqual(p.stand, "warnung")
            self.assertIn("belegt", p.text)
        finally:
            s.close()

    def test_ohne_readme_ist_eine_warnung(self):
        p = self._punkte(Zeile(self.repo))["README"]
        self.assertEqual(p.stand, "warnung")

    def test_zeile_ohne_ordner_gibt_einen_punkt(self):
        z = Zeile(self.repo)
        z.repo = None
        punkte = pflege.pruefen(z)
        self.assertEqual(len(punkte), 1)
        self.assertEqual(punkte[0].stand, "fehlt")

    def test_bericht_nennt_die_offenen_punkte(self):
        z = Zeile(self.repo, venv_pflicht=True)
        text = pflege.bericht(z, pflege.pruefen(z))
        self.assertIn("FEHLT venv", text)
        self.assertIn("offen", text)

    def test_bericht_ohne_offene_punkte(self):
        z = Zeile(self.repo, readme="README.md")
        text = pflege.bericht(z, pflege.pruefen(z))
        self.assertIn("Nichts zu tun", text)

    def test_sammelbericht_zaehlt_und_nennt_nur_auffaellige(self):
        gut = self.repo / "gut"
        schlecht = self.repo / "schlecht"
        gut.mkdir()
        schlecht.mkdir()
        (gut / "README.md").write_text("# x\n", encoding="utf-8")
        zeilen = [Zeile(gut, readme="README.md"), Zeile(schlecht)]
        text, auffaellig = pflege.sammelbericht(zeilen)
        self.assertEqual(len(auffaellig), 1)
        self.assertEqual(auffaellig[0][0], "schlecht")
        self.assertIn("2 Projekte geprueft, 1 mit offenen Punkten", text)


class AusfuehrenTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.repo = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_harmloser_befehl_laeuft_und_wird_geloggt(self):
        log = self.repo / "log.txt"
        ok, text = pflege.ausfuehren([[PY, "-c", "print('hallo')"]], self.repo, log=log)
        self.assertTrue(ok)
        self.assertIn("hallo", text)
        self.assertIn("Exit-Code 0", text)
        self.assertIn("hallo", log.read_text(encoding="utf-8"))

    def test_ein_fehler_bricht_die_kette_ab(self):
        ok, text = pflege.ausfuehren(
            [[PY, "-c", "raise SystemExit(3)"], [PY, "-c", "print('danach')"]],
            self.repo)
        self.assertFalse(ok)
        self.assertIn("Exit-Code 3", text)
        self.assertNotIn("danach", text, "nach einem Fehler darf nichts mehr laufen")

    def test_fehlendes_programm_ist_ein_ergebnis(self):
        ok, text = pflege.ausfuehren([["gibtsnicht-xyz", "--help"]], self.repo)
        self.assertFalse(ok)
        self.assertIn("nicht gefunden", text)

    def test_umgebung_raeumt_die_python_vergiftung(self):
        umg = pflege.umgebung()
        self.assertNotIn("PYTHONHOME", umg)
        self.assertNotIn("PYTHONPATH", umg)
        self.assertEqual(umg["MAXHIRN_ROUTINE"], "1")


class EintragenTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.pfad = Path(self.t.name) / "repos-zentrale.json"
        self.pfad.write_text(json.dumps({
            "stand": "2026-09-30",
            "repos": [{"ordner": "probe", "art": "python", "notiz": "x"},
                      {"ordner": "probe", "wurzel": "handel", "art": "python"}],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        self.jetzt = dt.datetime(2026, 9, 30, 20, 0)

    def tearDown(self):
        self.t.cleanup()

    def _daten(self):
        return json.loads(self.pfad.read_text(encoding="utf-8"))

    def test_kette_wird_geschrieben_und_belegt(self):
        schritte = [["python", "-m", "venv", ".venv"], ["python", "-m", "pip", "install", "-r", "requirements.txt"]]
        self.assertTrue(pflege.eintragen(self.pfad, "probe", "einrichten_kette", schritte,
                                         jetzt=self.jetzt))
        daten = self._daten()
        self.assertEqual(daten["repos"][0]["einrichten_kette"], schritte)
        self.assertIn("2026-09-30", daten["repos"][0]["_einrichten_kette_belegt"])
        self.assertTrue(self.pfad.with_name("repos-zentrale.bak-20260930.json").is_file())

    def test_die_wurzel_unterscheidet_gleichnamige_eintraege(self):
        pflege.eintragen(self.pfad, "probe", "start", ["x.exe"], wurzel="handel",
                         jetzt=self.jetzt)
        daten = self._daten()
        self.assertNotIn("start", daten["repos"][0])
        self.assertEqual(daten["repos"][1]["start"], ["x.exe"])

    def test_unbekanntes_feld_wird_verweigert(self):
        vorher = self.pfad.read_bytes()
        self.assertFalse(pflege.eintragen(self.pfad, "probe", "notiz", ["x"]))
        self.assertEqual(self.pfad.read_bytes(), vorher)

    def test_unbekannter_ordner_wird_verweigert(self):
        self.assertFalse(pflege.eintragen(self.pfad, "gibtsnicht", "start", ["x"]))

    def test_leerer_befehl_wird_verweigert(self):
        self.assertFalse(pflege.eintragen(self.pfad, "probe", "start", []))

    def test_zweimal_derselbe_befehl_schreibt_nicht_nochmal(self):
        self.assertTrue(pflege.eintragen(self.pfad, "probe", "start", ["x.exe"]))
        self.assertFalse(pflege.eintragen(self.pfad, "probe", "start", ["x.exe"]))

    def test_feldreihenfolge_bleibt(self):
        pflege.eintragen(self.pfad, "probe", "start", ["x.exe"], jetzt=self.jetzt)
        eintrag = self._daten()["repos"][0]
        # Die feste Feldreihenfolge aus fuellen.FELD_REIHENFOLGE: das neue
        # Feld steht an SEINER Stelle, nicht achtlos am Ende.
        self.assertEqual(list(eintrag)[:4], ["ordner", "art", "notiz", "start"])
        self.assertEqual(list(eintrag)[-1], "_start_belegt")
        self.assertIn("_start_belegt", eintrag)


if __name__ == "__main__":
    unittest.main()