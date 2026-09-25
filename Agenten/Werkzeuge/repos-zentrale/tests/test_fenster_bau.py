"""Baut das Fenster wirklich auf (ohne es zu zeigen) und prueft die Zeilen.

Ein Test, der nur die reinen Funktionen prueft, wuerde einen Tippfehler in einem
Widget-Namen nicht finden. Hier laeuft der echte Aufbau einmal durch - unsichtbar
(`withdraw`), damit keine Sitzung ein Fenster auf den Bildschirm bekommt.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fenster  # noqa: E402

try:
    import tkinter as tk

    _root = tk.Tk()
    _root.destroy()
    TK_DA = True
except Exception:  # pragma: no cover - nur wenn kein Fenstersystem da ist
    TK_DA = False


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class FensterBauTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        basis = Path(self.t.name)
        self.repos = basis / "Repos"
        (self.repos / "moon-dev-ai-agents" / "src").mkdir(parents=True)
        (self.repos / "moon-dev-ai-agents" / ".git").mkdir()
        (self.repos / "moon-dev-ai-agents" / "README.md").write_text("# x\n", encoding="utf-8")
        (self.repos / "moon-dev-ai-agents" / ".venv" / "Scripts").mkdir(parents=True)
        (self.repos / "moon-dev-ai-agents" / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
        (self.repos / "ein-neuer-klon" / ".git").mkdir(parents=True)

        self.profile = basis / "profiles"
        (self.profile / "moon-dev-agents").mkdir(parents=True)
        (self.profile / "moon-dev-agents" / "config.yaml").write_text("a: 1\n", encoding="utf-8")

        self.manifest = basis / "repos-zentrale.json"
        self.manifest.write_text(
            json.dumps({
                "stand": "2026-09-18",
                "repos": [{
                    "ordner": "moon-dev-ai-agents",
                    "art": "python",
                    "start": [".venv\\Scripts\\pythonw.exe", "moongui.py"],
                    "venv_pflicht": True,
                    "bot": "moon-dev-agents",
                    "notiz": "Herzstueck",
                    "anleitung": "Erst X, dann Y.",
                    "befehle": [
                        {
                            "was": "Pruefstand zeigen",
                            "cmd": [".venv\\Scripts\\python.exe", "pruefstand.py"],
                            "hinweis": "zwei Sekunden",
                        },
                        {"was": "Zweiter", "cmd": ["python", "-c", "print(1)"]},
                        {"was": "Kaputt", "cmd": []},
                    ],
                }],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self):
        self.t.cleanup()

    def _bauen(self):
        gerufen = []
        f = fenster.Fenster(
            self.repos, self.manifest, self.profile, Path(self.t.name) / "logs",
            lauf=gerufen.append,
        )
        f.root.withdraw()
        f.root.update()
        return f, gerufen

    def test_fenster_baut_auf_und_zeigt_beide_gruppen(self):
        f, _ = self._bauen()
        try:
            kopf = {f.baum.item(k)["text"]: k for k in f.baum.get_children()}
            startbar = next(k for t, k in kopf.items() if "STARTBAR" in t)
            neu = next(k for t, k in kopf.items() if "NEU" in t)
            self.assertIn(
                "moon-dev-ai-agents",
                [f.baum.item(i)["text"] for i in f.baum.get_children(startbar)],
            )
            self.assertIn(
                "ein-neuer-klon",
                [f.baum.item(i)["text"] for i in f.baum.get_children(neu)],
            )
        finally:
            f.root.destroy()

    def test_startknopf_ist_nur_bei_belegtem_befehl_aktiv(self):
        f, _ = self._bauen()
        try:
            kopf_startbar, kopf_neu = f.baum.get_children()[:2]
            gut = f.baum.get_children(kopf_startbar)[0]
            schlecht = f.baum.get_children(kopf_neu)[0]
            f.baum.selection_set(gut)
            f._auswahl_geaendert()
            self.assertEqual(str(f.knoepfe["start"]["state"]), "normal")
            self.assertEqual(str(f.knoepfe["bot"]["state"]), "normal")
            f.baum.selection_set(schlecht)
            f._auswahl_geaendert()
            self.assertEqual(str(f.knoepfe["start"]["state"]), "disabled")
        finally:
            f.root.destroy()

    def test_suchfeld_blendet_aus_und_wieder_ein(self):
        f, _ = self._bauen()
        try:
            f.suchtext.set("gibtsnicht")
            f.root.update()
            self.assertEqual(f.baum.get_children(), ())
            f.suchtext.set("")
            f.root.update()
            self.assertTrue(len(f.baum.get_children()) >= 2)
        finally:
            f.root.destroy()

    def test_ordner_und_terminal_gehen_ueber_den_ersetzten_aufruf(self):
        f, gerufen = self._bauen()
        try:
            kopf = f.baum.get_children()[0]
            f.baum.selection_set(f.baum.get_children(kopf)[0])
            f.ordner()
            f.terminal()
            self.assertEqual(len(gerufen), 2)
            self.assertEqual(gerufen[0][0], "explorer")
            self.assertEqual(gerufen[1][0], "wt.exe")
        finally:
            f.root.destroy()

    def test_start_ohne_auswahl_startet_nichts(self):
        f, gerufen = self._bauen()
        try:
            f.baum.selection_remove(*f.baum.selection())
            f.starten()
            self.assertEqual(gerufen, [])
            self.assertIn("Kein Startbefehl", str(f.status["text"]))
        finally:
            f.root.destroy()

    # --------------------------------------------------------- Detailbereich
    def _startbar_waehlen(self, f):
        kopf = f.baum.get_children()[0]
        item = f.baum.get_children(kopf)[0]
        f.baum.selection_set(item)
        f._auswahl_geaendert()
        f.root.update()
        return item

    def _befehl_waehlen(self, f, was: str):
        for item in f.befehlsbaum.get_children():
            if f.befehlsbaum.item(item)["values"][0] == was:
                f.befehlsbaum.selection_set(item)
                f._befehl_gewaehlt()
                return item
        raise AssertionError(f"Befehl '{was}' steht nicht in der Liste")

    def test_detailbereich_zeigt_anleitung_und_befehle(self):
        f, _ = self._bauen()
        try:
            self._startbar_waehlen(f)
            text = f.anleitung_text.get("1.0", "end")
            self.assertIn("Wozu: Herzstueck", text)
            self.assertIn("Erst X, dann Y.", text)
            namen = [f.befehlsbaum.item(i)["values"][0] for i in f.befehlsbaum.get_children()]
            for erwartet in ("Starten", "Terminal hier oeffnen", "Ordner im Explorer",
                             "Doku (README) oeffnen", "Bot moon-dev-agents fragen",
                             "Pruefstand zeigen", "Zweiter"):
                self.assertIn(erwartet, namen)
            # Ein Befehl ohne argv (hier "Kaputt") darf keine Zeile bekommen.
            self.assertNotIn("Kaputt", namen)
        finally:
            f.root.destroy()

    def test_befehlsknoepfe_sind_ohne_auswahl_aus(self):
        f, _ = self._bauen()
        try:
            self._startbar_waehlen(f)
            f.befehlsbaum.selection_remove(*f.befehlsbaum.selection())
            f._befehl_gewaehlt()
            for name in ("ausfuehren", "kopieren"):
                self.assertEqual(str(f.befehl_knoepfe[name]["state"]), "disabled")
        finally:
            f.root.destroy()

    def test_befehl_kopieren_legt_den_text_in_die_zwischenablage(self):
        f, _ = self._bauen()
        try:
            self._startbar_waehlen(f)
            self._befehl_waehlen(f, "Pruefstand zeigen")
            f.befehl_kopieren()
            self.assertEqual(
                f.root.clipboard_get(), ".venv\\Scripts\\python.exe pruefstand.py"
            )
            self.assertTrue(str(f.status["text"]).startswith("Kopiert:"))
        finally:
            f.root.destroy()

    def test_befehl_ausfuehren_oeffnet_ein_terminal_im_repo(self):
        f, gerufen = self._bauen()
        try:
            item = self._startbar_waehlen(f)
            pfad = f.kinder[item].repo.pfad
            self._befehl_waehlen(f, "Pruefstand zeigen")
            f.befehl_ausfuehren()
            self.assertEqual(gerufen[-1][0], "wt.exe")
            self.assertIn("cmd.exe", gerufen[-1])
            self.assertIn(str(pfad), gerufen[-1])
            self.assertEqual(gerufen[-1][-2:], [".venv\\Scripts\\python.exe", "pruefstand.py"])
        finally:
            f.root.destroy()

    def test_ordnerzeile_im_detail_geht_ueber_explorer(self):
        f, gerufen = self._bauen()
        try:
            self._startbar_waehlen(f)
            self._befehl_waehlen(f, "Ordner im Explorer")
            f.befehl_ausfuehren()
            self.assertEqual(gerufen[-1][0], "explorer")
        finally:
            f.root.destroy()

    def test_bot_beauftragen_geht_nur_mit_profil(self):
        f, gerufen = self._bauen()
        try:
            self._startbar_waehlen(f)
            self._befehl_waehlen(f, "Pruefstand zeigen")
            self.assertEqual(str(f.befehl_knoepfe["bot"]["state"]), "normal")
            f.befehl_an_bot()
            argv = gerufen[-1]
            self.assertEqual(argv[0], "wt.exe")
            self.assertIn("hermes", argv)
            self.assertIn("-q", argv)
            self.assertIn("pruefstand.py", argv[-1])
        finally:
            f.root.destroy()

    def test_neue_zeile_ohne_manifest_hat_keine_eigenen_befehle(self):
        f, _ = self._bauen()
        try:
            kopf_neu = f.baum.get_children()[1]
            item = f.baum.get_children(kopf_neu)[0]
            f.baum.selection_set(item)
            f._auswahl_geaendert()
            namen = [f.befehlsbaum.item(i)["values"][0] for i in f.befehlsbaum.get_children()]
            self.assertIn("Ordner im Explorer", namen)
            self.assertNotIn("Starten", namen)
            self.assertIn("noch kein Ablauf hinterlegt", f.anleitung_text.get("1.0", "end"))
        finally:
            f.root.destroy()


if __name__ == "__main__":
    unittest.main()
