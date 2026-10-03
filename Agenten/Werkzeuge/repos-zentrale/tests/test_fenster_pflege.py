"""Tests fuer den Pflegereiter: Vorschlaege, Pruefung, Auftrag, Sammelbericht.

**Kein Test richtet etwas ein.** `pflege.ausfuehren` und `pflege.eintragen`
werden fuer die Auftrags-Tests durch Mitschreiber ersetzt; geprueft wird, WAS
das Fenster aufruft, nicht dass npm oder pip laufen.
"""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fenster  # noqa: E402
import pflege  # noqa: E402

try:
    import tkinter as tk

    _r = tk.Tk()
    _r.destroy()
    TK_DA = True
except Exception:  # pragma: no cover
    TK_DA = False


@unittest.skipUnless(TK_DA, "kein Fenstersystem verfuegbar")
class PflegereiterTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.bf = Path(self.t.name)
        repos = self.bf / "Werkstatt" / "Repos"
        self.node = repos / "node-projekt"
        self.leer = repos / "leeres-projekt"
        self.python = repos / "python-projekt"
        for d in (self.node, self.leer, self.python):
            (d / ".git").mkdir(parents=True)
        (self.node / "package.json").write_text(
            json.dumps({"scripts": {"build": "vite build"}}), encoding="utf-8")
        (self.node / "README.md").write_text("# x\n", encoding="utf-8")
        (self.leer / "README.md").write_text("# y\n", encoding="utf-8")
        (self.python / "requirements.txt").write_text("requests\n", encoding="utf-8")
        (self.python / "README.md").write_text("# z\n", encoding="utf-8")

        self.manifest = self.bf / "repos-zentrale.json"
        self.manifest.write_text(json.dumps({
            "stand": "x",
            "repos": [
                {"ordner": "python-projekt", "art": "python", "venv_pflicht": True},
                {"ordner": "node-projekt", "art": "node"},
                {"ordner": "leeres-projekt", "art": "d abl"},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        (self.bf / "profiles").mkdir()
        self.logs = self.bf / "logs"

    def tearDown(self):
        self.t.cleanup()

    def _bauen(self, **kwargs):
        f = fenster.Fenster(
            self.bf, self.manifest, self.bf / "profiles", self.logs,
            lauf=lambda argv: None, handel_zustand_lader=lambda: {}, **kwargs)
        f.root.withdraw()
        f.root.update()
        return f

    def _waehlen(self, f, ordner):
        for item, z in f.kinder.items():
            if z.ordner == ordner:
                f.baum.selection_set(item)
                f._auswahl_geaendert()
                f.root.update()
                return z
        raise AssertionError(f"{ordner} steht nicht im Baum")

    def _pumpen(self, f, sekunden=10):
        ende = time.time() + sekunden
        while time.time() < ende:
            f.root.update()
            time.sleep(0.02)

    def test_es_gibt_zwei_reiter(self):
        f = self._bauen()
        try:
            namen = [f.reiter.tab(i, "text") for i in range(len(f.reiter.tabs()))]
            self.assertEqual(namen, ["Handel · Testen", "Einrichten · Reparatur"])
        finally:
            f.root.destroy()

    def test_vorschlag_kommt_aus_den_dateien_des_projekts(self):
        f = self._bauen()
        try:
            self._waehlen(f, "node-projekt")
            text = f.pflege_text.get("1.0", "end")
            self.assertIn("Einrichten: 1 Schritt(e)", text)
            self.assertIn("npm install", text)
            self.assertIn("npm run build", text)
            self.assertEqual(str(f.pflege_knoepfe["einrichten"]["state"]), "normal")
            self.assertEqual(str(f.pflege_knoepfe["bauen"]["state"]), "normal")
        finally:
            f.root.destroy()

    def test_projekt_ohne_anhaltspunkt_hat_keinen_knopf(self):
        f = self._bauen()
        try:
            self._waehlen(f, "leeres-projekt")
            self.assertIn("kein Befehl", f.pflege_text.get("1.0", "end"))
            self.assertEqual(str(f.pflege_knoepfe["einrichten"]["state"]), "disabled")
            self.assertEqual(str(f.pflege_knoepfe["bauen"]["state"]), "disabled")
            self.assertEqual(str(f.pflege_knoepfe["pruefen"]["state"]), "normal")
        finally:
            f.root.destroy()

    def test_manifest_kette_schlaegt_den_vorschlag(self):
        daten = json.loads(self.manifest.read_text(encoding="utf-8"))
        daten["repos"][1]["einrichten_kette"] = [["npm", "ci"]]
        self.manifest.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
        f = self._bauen()
        try:
            z = self._waehlen(f, "node-projekt")
            schritte, quelle = f._pflege_schritte(z, "einrichten")
            self.assertEqual(schritte, [["npm", "ci"]])
            self.assertEqual(quelle, "Manifest (Kette)")
        finally:
            f.root.destroy()

    def test_pruefen_meldet_die_fehlende_venv(self):
        f = self._bauen()
        try:
            self._waehlen(f, "python-projekt")
            f.pflege_pruefen()
            self._pumpen(f)
            text = f.pflege_text.get("1.0", "end")
            self.assertIn("venv", text)
            self.assertIn("FEHLT", text)
            self.assertIn("python-projekt:", f.status["text"])
        finally:
            f.root.destroy()

    def test_auftrag_ruft_ausfuehren_und_belegt_die_kette(self):
        """Der Weg bis zum Manifest - ohne dass wirklich etwas installiert wird."""
        gerufen = {"aus": [], "ein": []}
        echt_aus, echt_ein = pflege.ausfuehren, pflege.eintragen
        pflege.ausfuehren = lambda schritte, cwd, log=None, **kw: (
            gerufen["aus"].append((schritte, str(cwd), log is not None))
            or (True, "simulierte Ausgabe\n-> Exit-Code 0"))
        pflege.eintragen = lambda *a, **kw: (gerufen["ein"].append((a, kw)) or True)
        try:
            f = self._bauen()
            try:
                self._waehlen(f, "python-projekt")
                f.pflege_einrichten()
                self._pumpen(f)
                self.assertEqual(len(gerufen["aus"]), 1)
                schritte, cwd, mit_log = gerufen["aus"][0]
                self.assertGreaterEqual(len(schritte), 2)
                self.assertTrue(cwd.endswith("python-projekt"))
                self.assertTrue(mit_log, "die Ausgabe gehoert ins Log")
                self.assertIn("simulierte Ausgabe", f.pflege_text.get("1.0", "end"))
                self.assertEqual(len(gerufen["ein"]), 1, "die Kette wird belegt")
                args = gerufen["ein"][0][0]
                self.assertEqual(args[1], "python-projekt")
                self.assertEqual(args[2], "einrichten_kette",
                                 "mehrere Schritte gehoeren in die Kette")
                self.assertIn("Manifest belegt", f.status["text"])
            finally:
                f.root.destroy()
        finally:
            pflege.ausfuehren, pflege.eintragen = echt_aus, echt_ein

    def test_auftrag_ohne_befehl_sagt_warum(self):
        f = self._bauen()
        try:
            self._waehlen(f, "leeres-projekt")
            f.pflege_einrichten()
            self.assertIn("kein einrichten-Befehl", f.status["text"])
        finally:
            f.root.destroy()

    def test_sammelbericht_schreibt_eine_datei(self):
        f = self._bauen()
        try:
            f.pflege_alle()
            self._pumpen(f, 20)
            berichte = list(self.logs.glob("pruefbericht-*.log"))
            self.assertEqual(len(berichte), 1, f"kein Bericht in {self.logs}")
            inhalt = berichte[0].read_text(encoding="utf-8")
            self.assertIn("Projekte geprueft", inhalt)
            self.assertIn("3 Projekte geprueft", inhalt)
            self.assertIn("Pruefbericht", f.status["text"])
        finally:
            f.root.destroy()

    def test_ohne_auswahl_ist_der_reiter_leer_erklaert(self):
        f = self._bauen()
        try:
            self.assertIn("Links ein Projekt waehlen", f.pflege_kopf["text"])
            self.assertEqual(str(f.pflege_knoepfe["pruefen"]["state"]), "disabled")
        finally:
            f.root.destroy()


if __name__ == "__main__":
    unittest.main()