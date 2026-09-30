"""Nachweis: jevgrep laeuft unter Windows, und der Weg ueber einen eigenen
TypeSafe-kompatiblen Endpunkt funktioniert vollstaendig (auth, doctor, Suche).

Die Attrappe laeuft auf 127.0.0.1 und beantwortet jede Frage mit noul=0.9.
XDG_CONFIG_HOME wird auf einen Tempordner gebogen, damit die ECHTE Anmeldung
in ~/.config/jevgrep NICHT angefasst wird.

Aufruf:  python test_jevgrep.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent
JG = HIER / "jg.cmd"
NODE_INDEX = HIER / "node_modules" / "@dzhng" / "jevgrep" / "dist" / "bin" / "index.js"
REPO = HIER.parents[2] / "Werkstatt" / "Repos" / "jevgrep"
SUCHWURZEL = REPO / "apps"

anfragen: list[dict] = []


class Attrappe(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length", "0"))
        try:
            a = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            a = {}
        fragen = list((a.get("questions") or {}).keys())
        anfragen.append({
            "pfad": self.path,
            "modell": a.get("model"),
            "fragen": len(fragen),
            "state_zeichen": len(str(a.get("state", ""))),
            "auth": bool(self.headers.get("authorization")),
        })
        daten = json.dumps({"answers": {k: {"type": "noul", "noul": 0.9} for k in fragen}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *a):
        pass


class JevgrepTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="jgtest_")
        cls.umgebung = dict(os.environ)
        cls.umgebung["XDG_CONFIG_HOME"] = cls.tmp
        cls.umgebung.pop("PYTHONHOME", None)
        cls.umgebung.pop("PYTHONPATH", None)
        cls.server = HTTPServer(("127.0.0.1", 0), Attrappe)
        cls.port = cls.server.server_address[1]
        cls.faden = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.faden.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lauf(self, *args, stdin: str = "", frist: int = 300):
        return subprocess.run(
            [str(JG), *args], input=stdin, capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=self.umgebung, timeout=frist,
            cwd=str(HIER),
        )

    def test_00_dateien_vorhanden(self):
        self.assertTrue(JG.exists(), "jg.cmd fehlt")
        self.assertTrue(NODE_INDEX.exists(), "Paket nicht installiert")
        self.assertTrue(SUCHWURZEL.is_dir(), "Suchwurzel fehlt: %s" % SUCHWURZEL)

    def test_01_version(self):
        r = self.lauf("--version")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout.strip(), r"^\d+\.\d+\.\d+$")

    def test_02_files_ohne_netz(self):
        r = self.lauf("files", str(SUCHWURZEL))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("eligible", r.stdout)
        self.assertEqual(len(anfragen), 0, "files darf keine Anfrage senden")

    def test_03_auth_gegen_attrappe_und_doctor(self):
        basis = "http://127.0.0.1:%d/v1" % self.port
        r = self.lauf("auth", "--provider", "custom", "--base-url", basis,
                      "--model", "stub", "--stdin", stdin="test-schluessel\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        ablage = Path(self.tmp) / "jevgrep" / "credentials.json"
        self.assertTrue(ablage.exists(), "Anmeldung wurde nicht abgelegt")
        self.assertIn("127.0.0.1", r.stdout)

        r = self.lauf("doctor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("verified", r.stdout)

    def test_04_suche_erreicht_die_attrappe(self):
        vorher = len(anfragen)
        r = self.lauf("Wie wird ein Projekt gestartet?", str(SUCHWURZEL),
                      "--concurrency", "2", frist=420)
        self.assertIn(r.returncode, (0, 2), r.stdout + r.stderr)  # 2 = unvollstaendig
        self.assertIn("Jevgrep", r.stdout)
        neu = anfragen[vorher:]
        self.assertGreater(len(neu), 0, "keine Anfrage an den Endpunkt")
        self.assertTrue(all(a["pfad"].endswith("/systemone") for a in neu))
        self.assertTrue(all(a["modell"] == "stub" for a in neu))
        self.assertTrue(all(a["auth"] for a in neu), "Bearer-Kopf fehlt")
        self.assertTrue(all(a["fragen"] >= 1 for a in neu))
        self.assertGreater(max(a["state_zeichen"] for a in neu), 1000,
                           "Zustand wird nicht mitgeschickt")

    def test_05_echte_anmeldung_unberuehrt(self):
        echt = Path(os.path.expanduser("~/.config/jevgrep/credentials.json"))
        if echt.exists():
            self.assertNotIn(str(self.tmp), echt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)