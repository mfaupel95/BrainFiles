"""Baut das Fenster wirklich auf (ohne es zu zeigen) und prueft die Zeilen.

Ein Test, der nur die reinen Funktionen prueft, wuerde einen Tippfehler in einem
Widget-Namen nicht finden. Hier laeuft der echte Aufbau einmal durch - unsichtbar
(`withdraw`), damit keine Sitzung ein Fenster auf den Bildschirm bekommt.

Der Baum hat drei Ebenen (Bereich -> Gruppe -> Projekt). Die Helfer unten
suchen deshalb ueber den GANZEN Baum, statt sich auf eine Ebene zu verlassen -
sonst bricht jeder Test, sobald eine Ebene dazukommt.
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
        self.brainfiles = Path(self.t.name)
        self.repos = self.brainfiles / "Werkstatt"
        (self.repos / "moon-dev-ai-agents" / "src").mkdir(parents=True)
        (self.repos / "moon-dev-ai-agents" / ".git").mkdir()
        (self.repos / "moon-dev-ai-agents" / "README.md").write_text("# x\n", encoding="utf-8")
        (self.repos / "moon-dev-ai-agents" / ".venv" / "Scripts").mkdir(parents=True)
        (self.repos / "moon-dev-ai-agents" / ".venv" / "Scripts" / "python.exe").write_bytes(b"")
        (self.repos / "ein-neuer-klon" / ".git").mkdir(parents=True)

        # Ein Projekt in der zweiten Wurzel: es muss im Bereich WERKSTATT landen.
        (self.brainfiles / "Werkstatt" / "eigenes-projekt").mkdir(parents=True)
        (self.brainfiles / "Werkstatt" / "eigenes-projekt" / "README.md").write_text(
            "# y\n", encoding="utf-8"
        )

        self.profile = self.brainfiles / "profiles"
        (self.profile / "moon-dev-agents").mkdir(parents=True)
        (self.profile / "moon-dev-agents" / "config.yaml").write_text("a: 1\n", encoding="utf-8")

        self.manifest = self.brainfiles / "repos-zentrale.json"
        self.manifest.write_text(
            json.dumps({
                "stand": "2026-09-30",
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
                }, {
                    "ordner": "eigenes-projekt",
                    "wurzel": "werkstatt",
                    "rolle": "Projekt",
                    "notiz": "Hausprojekt",
                    "gruppe": "doku",
                }],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    def tearDown(self):
        self.t.cleanup()

    def _bauen(self):
        gerufen = []
        f = fenster.Fenster(
            self.brainfiles, self.manifest, self.profile, self.brainfiles / "logs",
            lauf=gerufen.append,
        )
        f.root.withdraw()
        f.root.update()
        return f, gerufen

    # ------------------------------------------------------------- Baumhelfer
    def _alle(self, f, eltern=""):
        """Alle Items unter `eltern` (rekursiv) als Liste (id, text)."""
        ergebnis = []
        for item in f.baum.get_children(eltern):
            ergebnis.append((item, f.baum.item(item)["text"]))
            ergebnis += self._alle(f, item)
        return ergebnis

    def _finde(self, f, stichwort: str, *, ebene_text=None) -> str:
        """Das erste Item, dessen Text das Stichwort enthaelt."""
        for item, text in self._alle(f):
            if stichwort in text and (ebene_text is None or ebene_text in text):
                return item
        raise AssertionError(f"kein Knoten mit '{stichwort}' im Baum")

    def _gruppe(self, f, name: str) -> str:
        return self._finde(f, name)

    def _projekt_in(self, f, gruppe: str, ordner: str) -> str:
        kopf = self._gruppe(f, gruppe)
        for item, text in self._alle(f, kopf):
            if text == ordner:
                return item
        raise AssertionError(f"{ordner} steht nicht in {gruppe}")

    def _ordner_von(self, f, item: str) -> str:
        """Der sichtbare Pfad der Zeile (aus den Spaltenwerten des Baumitems)."""
        return f.baum.item(item)["values"][1]

    def test_baum_hat_bereich_dann_gruppe_dann_projekt(self):
        f, _ = self._bauen()
        try:
            bereiche = [t for _, t in self._alle(f) if t.startswith("REPOS") or t.startswith("WERKSTATT")]
            self.assertTrue(any(t.startswith("REPOS") for t in bereiche), bereiche)
            kopf = self._finde(f, "REPOS")
            kinder = [f.baum.item(i)["text"] for i in f.baum.get_children(kopf)]
            self.assertTrue(any(t.startswith("STARTBAR") for t in kinder), kinder)
        finally:
            f.root.destroy()

    def test_neue_und_fehlende_gruppen_zeigen_ihre_zeilen(self):
        f, _ = self._bauen()
        try:
            item = self._projekt_in(f, "NEU", "ein-neuer-klon")
            self.assertTrue(f.kinder[item].gruende)
        finally:
            f.root.destroy()

    def test_hausprojekt_landet_im_bereich_werkstatt(self):
        f, _ = self._bauen()
        try:
            werkstatt = self._finde(f, "WERKSTATT")
            texte = [t for _, t in self._alle(f, werkstatt)]
            self.assertIn("eigenes-projekt", texte)
        finally:
            f.root.destroy()

    def test_bereichsfilter_blendet_andere_bereiche_aus(self):
        f, _ = self._bauen()
        try:
            f.bereich.set("WERKSTATT (1)")
            f.anzeigen()
            texte = [t for _, t in self._alle(f)]
            self.assertIn("eigenes-projekt", texte)
            self.assertNotIn("moon-dev-ai-agents", texte)
            f.bereich.set(fenster.ALLE_BEREICHE)
            f.anzeigen()
            self.assertIn("moon-dev-ai-agents", [t for _, t in self._alle(f)])
        finally:
            f.root.destroy()

    def test_startknopf_ist_nur_bei_belegtem_befehl_aktiv(self):
        f, _ = self._bauen()
        try:
            gut = self._projekt_in(f, "STARTBAR", "moon-dev-ai-agents")
            schlecht = self._projekt_in(f, "NEU", "ein-neuer-klon")
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
            self.assertTrue(len(f.baum.get_children()) >= 1)
            self.assertIsNotNone(self._finde(f, "moon-dev-ai-agents"))
        finally:
            f.root.destroy()

    def test_ordner_und_terminal_gehen_ueber_den_ersetzten_aufruf(self):
        f, gerufen = self._bauen()
        try:
            f.baum.selection_set(self._projekt_in(f, "STARTBAR", "moon-dev-ai-agents"))
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

    def test_doppelklick_startet_wenn_belegt_sonst_ordner(self):
        f, gerufen = self._bauen()
        try:
            f.baum.selection_set(self._projekt_in(f, "NEU", "ein-neuer-klon"))
            f.doppelklick()
            self.assertEqual(gerufen[-1][0], "explorer")
        finally:
            f.root.destroy()

    # --------------------------------------------------------- Detailbereich
    def _startbar_waehlen(self, f):
        item = self._projekt_in(f, "STARTBAR", "moon-dev-ai-agents")
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

    def test_anleitung_nennt_bereich_und_rolle(self):
        f, _ = self._bauen()
        try:
            item = self._projekt_in(f, "NUR DOKU", "eigenes-projekt")
            f.baum.selection_set(item)
            f._auswahl_geaendert()
            text = f.anleitung_text.get("1.0", "end")
            self.assertIn("WERKSTATT · Projekt", text)
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
        """Seit 30.09.2026: Tab im vorhandenen Fenster, `/c` schliesst ihn, die
        Ausgabe geht zusaetzlich ins Log (sonst waere sie mit dem Tab weg)."""
        f, gerufen = self._bauen()
        try:
            item = self._startbar_waehlen(f)
            pfad = f.kinder[item].repo.pfad
            self._befehl_waehlen(f, "Pruefstand zeigen")
            f.befehl_ausfuehren()
            argv = gerufen[-1]
            self.assertEqual(argv[0], "wt.exe")
            self.assertEqual(argv[argv.index("-w") + 1], "0")
            self.assertIn("cmd.exe", argv)
            self.assertIn("/c", argv)
            self.assertNotIn("/k", argv)
            self.assertIn(str(pfad), argv)
            zeile = argv[-1]
            self.assertIn(".venv\\Scripts\\python.exe", zeile)
            self.assertIn("pruefstand.py", zeile)
            self.assertIn(">", zeile, "die Ausgabe muss ins Log umgeleitet werden")
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
            item = self._projekt_in(f, "NEU", "ein-neuer-klon")
            f.baum.selection_set(item)
            f._auswahl_geaendert()
            namen = [f.befehlsbaum.item(i)["values"][0] for i in f.befehlsbaum.get_children()]
            self.assertIn("Ordner im Explorer", namen)
            self.assertNotIn("Starten", namen)
            self.assertIn("noch kein Ablauf hinterlegt", f.anleitung_text.get("1.0", "end"))
        finally:
            f.root.destroy()

    def test_zeile_ohne_ordner_bekommt_keine_handgriffe(self):
        """Gruppe FEHLT: es gibt nichts zu oeffnen - also auch keinen Knopf."""
        self.manifest.write_text(
            json.dumps({"stand": "x", "repos": [
                {"ordner": "weg", "start": ["x.exe"], "wurzel": "handel", "rolle": "Werkzeug"},
            ]}, ensure_ascii=False),
            encoding="utf-8",
        )
        f, _ = self._bauen()
        try:
            item = self._projekt_in(f, "FEHLT", "weg")
            f.baum.selection_set(item)
            f._auswahl_geaendert()
            self.assertEqual(f.befehlsbaum.get_children(), ())
            for name in ("start", "ordner", "terminal", "doku", "bot"):
                self.assertEqual(str(f.knoepfe[name]["state"]), "disabled")
        finally:
            f.root.destroy()


if __name__ == "__main__":
    unittest.main()
