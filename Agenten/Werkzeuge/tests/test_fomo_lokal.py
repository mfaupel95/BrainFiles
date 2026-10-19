"""Tests fuer Agenten/Werkzeuge/fomo_lokal.py - ohne Netz, ohne Ollama, ohne Repo-CLI.

Aufruf (der Repo-venv, weil das Werkzeug `fomo_agent` fuer Schema und Regeln liest):

    cd Agenten/Werkzeuge/tests
    ../../../Werkstatt/fomo-robinhood-radar/.venv/Scripts/python.exe -m unittest test_fomo_lokal -v

Zwei Nahten werden gehalten: `ANFRAGE` (Ollama) und `LAUF` (Repo-CLI). Kein Test
darf das echte Repo-CLI starten, Ollama fragen oder in `fomo_agent.db` schreiben.
"""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WERKZEUG = HIER.parent / "fomo_lokal.py"

_spec = importlib.util.spec_from_file_location("fomo_lokal", WERKZEUG)
fl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fl)

GUELTIG = {"score": 71, "status": "active", "style": ["sniper"],
           "red_flags": [], "summary": "Klarer Vorteil.", "confidence": 0.8}


class BasisTest(unittest.TestCase):
    def setUp(self):
        self._anfrage, self._lauf = fl.ANFRAGE, fl.LAUF
        self.aufrufe: list = []
        fl.ANFRAGE = self._anfrage_stub
        fl.LAUF = self._lauf_stub

    def tearDown(self):
        fl.ANFRAGE, fl.LAUF = self._anfrage, self._lauf

    def _anfrage_stub(self, prompt, modell, form, zeitgrenze):
        self.aufrufe.append({"prompt": prompt, "modell": modell, "format": form})
        return json.dumps(GUELTIG)

    def _lauf_stub(self, args, *, trocken=False):
        self.aufrufe.append({"args": args, "trocken": trocken})
        return {"rc": 0, "ausgabe": "{'exported': 1}"}


class RepoQuellenTest(unittest.TestCase):
    """Prompt und Schema kommen aus dem Fremd-Repo - nicht aus einer Kopie hier."""

    def test_schema_hat_die_felder_des_urteils(self):
        s = fl.schema()
        self.assertEqual({"score", "status", "style", "red_flags", "summary", "confidence"},
                         set(s["properties"]))
        self.assertIn("status", s["required"])

    def test_regeln_sind_die_des_repos(self):
        regeln = fl.system_prompt()
        self.assertIn("JSON", regeln)
        self.assertIn("fomo PnL", regeln)
        self.assertIn("open_positions", regeln)

    def test_prompt_traegt_regeln_und_marktbild(self):
        wallet = {"address": "0xabc", "last_7d": {"trades": 3}}
        p = fl.wallet_prompt(wallet, fl.system_prompt())
        self.assertIn("Score exactly ONE trader", p)
        self.assertIn('"address":"0xabc"', p)


class BewertenTest(BasisTest):
    def test_gueltiges_urteil_wird_gelesen(self):
        urteil, zustand = fl.bewerte({"address": "0x1"}, "m", "regeln", {"type": "object"})
        self.assertEqual("bewertet", zustand)
        self.assertEqual(71, urteil["score"])
        self.assertNotIn("address", urteil)          # die Adresse setzt der Aufrufer
        self.assertEqual(1, len(self.aufrufe))

    def _zaehlend(self, antwortfolge):
        """Antwortet der Reihe nach und zaehlt die Aufrufe wie der echte Stub."""
        quelle = iter(antwortfolge)

        def frage(prompt, modell, form, zeitgrenze):
            self.aufrufe.append({"prompt": prompt, "modell": modell, "format": form})
            return next(quelle)
        return frage

    def test_erste_stufe_ist_das_schema(self):
        fl.bewerte({"address": "0x1"}, "m", "regeln", {"type": "object", "title": "ScoreResult"})
        self.assertEqual({"type": "object", "title": "ScoreResult"}, self.aufrufe[0]["format"])

    def test_schemaverletzung_faellt_aus_statt_zu_raten(self):
        kaputt = dict(GUELTIG, score=150)            # 150 ist ausserhalb 0..100
        fl.ANFRAGE = self._zaehlend([json.dumps(kaputt)] * 3)
        urteil, zustand = fl.bewerte({"address": "0x1"}, "m", "regeln", {"type": "object"})
        self.assertIsNone(urteil)
        self.assertEqual("unlesbar", zustand)
        self.assertEqual(3, len(self.aufrufe))       # Schema -> json -> Text, dann Schluss

    def test_zweite_stufe_ist_json_dritte_freier_text(self):
        fl.ANFRAGE = self._zaehlend(["kein json", "auch kein json", json.dumps(GUELTIG)])
        urteil, zustand = fl.bewerte({"address": "0x1"}, "m", "regeln", {"type": "object"})
        self.assertEqual("bewertet", zustand)
        self.assertEqual([{"type": "object"}, "json", None],
                         [a["format"] for a in self.aufrufe])

    def test_ollama_tot_ist_kein_urteil(self):
        fl.ANFRAGE = lambda *a, **k: None
        urteil, zustand = fl.bewerte({"address": "0x1"}, "m", "regeln", {"type": "object"})
        self.assertIsNone(urteil)
        self.assertEqual("ollama_tot", zustand)

    def test_json_im_text_wird_herausgeschnitten(self):
        fl.ANFRAGE = lambda *a, **k: "Hier: ```json\n" + json.dumps(GUELTIG) + "\n```"
        urteil, zustand = fl.bewerte({"address": "0x1"}, "m", "regeln", None)
        self.assertEqual("bewertet", zustand)
        self.assertEqual(71, urteil["score"])


class AblaufTest(BasisTest):
    def setUp(self):
        super().setUp()
        self._modal, self._modelle = fl.modell_da, fl.modelle
        fl.modell_da = lambda name: True
        self.tmp = tempfile.TemporaryDirectory()
        self.export = Path(self.tmp.name) / "pending.json"
        self.ergebnis = Path(self.tmp.name) / "local.json"
        self.export.write_text(json.dumps({"wallets": [
            {"address": "0xaa", "fomo": {"fomo_handle": "eins"}},
            {"address": "0xbb", "fomo": {"fomo_handle": "zwei"}}]}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()
        fl.modell_da, fl.modelle = self._modal, self._modelle
        super().tearDown()

    def _main(self, *zusaetzlich):
        return fl.main(["--export-datei", str(self.export),
                        "--ergebnis-datei", str(self.ergebnis), *zusaetzlich])

    def test_lauf_exportiert_bewertet_und_importiert(self):
        rc = self._main()
        self.assertEqual(0, rc)
        dateien = json.loads(self.ergebnis.read_text(encoding="utf-8"))
        self.assertEqual(2, len(dateien["results"]))
        self.assertEqual(["0xaa", "0xbb"], [r["address"] for r in dateien["results"]])
        importe = [a for a in self.aufrufe if a.get("args", [])[:2] == ["score", "--import"]]
        self.assertEqual(1, len(importe))
        args = importe[0]["args"]
        self.assertIn("--model-label", args)
        self.assertTrue(args[args.index("--model-label") + 1].startswith("ollama-"))

    def test_trocken_importiert_nichts(self):
        rc = self._main("--trocken")
        self.assertEqual(0, rc)
        self.assertFalse([a for a in self.aufrufe if a.get("args", [])[:2] == ["score", "--import"]])

    def test_adresse_grenzt_auf_eine_wallet(self):
        rc = self._main("--adresse", "0xBB")
        self.assertEqual(0, rc)
        dateien = json.loads(self.ergebnis.read_text(encoding="utf-8"))
        self.assertEqual(["0xbb"], [r["address"] for r in dateien["results"]])

    def test_unbekannte_adresse_bricht_ab(self):
        with self.assertRaises(SystemExit):
            self._main("--adresse", "0xcc")

    def test_kein_urteil_heisst_kein_import(self):
        fl.ANFRAGE = lambda *a, **k: "kein json"
        rc = self._main()
        self.assertEqual(1, rc)
        self.assertFalse([a for a in self.aufrufe if a.get("args", [])[:2] == ["score", "--import"]])

    def test_fehlendes_modell_bricht_ab(self):
        fl.modell_da = lambda name: False
        fl.modelle = lambda: ["qwen35-8k:latest"]
        with self.assertRaises(SystemExit):
            self._main()

    def test_leere_warteschlange_ist_kein_fehler(self):
        self.export.write_text(json.dumps({"wallets": []}), encoding="utf-8")
        self.assertEqual(0, self._main())

    def test_anzahl_wird_an_den_export_gereicht(self):
        self._main("--anzahl", "5")
        exporte = [a for a in self.aufrufe if a.get("args", [])[:2] == ["score", "--export"]]
        self.assertIn("--limit", exporte[0]["args"])
        self.assertIn("5", exporte[0]["args"])

    def test_alle_erzwingt_den_export(self):
        self._main("--alle")
        exporte = [a for a in self.aufrufe if a.get("args", [])[:2] == ["score", "--export"]]
        self.assertIn("--force", exporte[0]["args"])
        self.assertNotIn("--unscored", exporte[0]["args"])


class UmgebungTest(unittest.TestCase):
    """Das Repo-CLI darf nie ueber den toten API-Weg laufen."""

    def test_sonde_setzt_scorer_manual(self):
        quelle = WERKZEUG.read_text(encoding="utf-8")
        self.assertIn('umgebung["SCORER"] = "manual"', quelle)
        self.assertIn('umgebung["PYTHONIOENCODING"] = "utf-8"', quelle)

    def test_denken_ist_abgeschaltet(self):
        quelle = WERKZEUG.read_text(encoding="utf-8")
        self.assertIn('"think": False', quelle)

    def test_repo_pfad_ist_relativ_gebaut(self):
        self.assertTrue(str(fl.REPO).endswith(os.path.join("Werkstatt", "fomo-robinhood-radar")))
        self.assertNotIn("C:\\Users", WERKZEUG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)