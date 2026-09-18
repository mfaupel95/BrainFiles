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


if __name__ == "__main__":
    unittest.main()
