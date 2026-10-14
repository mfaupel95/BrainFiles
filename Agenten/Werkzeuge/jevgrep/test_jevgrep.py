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
REPO = HIER.parents[2] / "Werkstatt" / "jevgrep"
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


class AnmeldungAusOpenCodeTest(unittest.TestCase):
    """Das Anmeldewerkzeug: liest die OpenCode-Anmeldung, zeigt den Wert nie an."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="jgoauth_")
        cls.umgebung = dict(os.environ)
        cls.umgebung["XDG_CONFIG_HOME"] = cls.tmp
        cls.server = HTTPServer(("127.0.0.1", 0), Attrappe)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.schluessel = "zen-testwert-1234567890"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def lauf(self, *args, frist: int = 240):
        return subprocess.run(
            [sys.executable, str(HIER / "von_opencode_anmelden.py"), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=self.umgebung, cwd=str(HIER), timeout=frist,
        )

    def test_01_ohne_anmeldung_kommt_anleitung(self):
        fehlt = Path(self.tmp) / "gibtsnicht.json"
        r = self.lauf("--quelle", "datei", "--datei", str(fehlt))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("OPENCODE_API_KEY", r.stdout)
        self.assertIn("--provider custom", r.stdout)

    def test_02_trockenlauf_schreibt_nichts(self):
        datei = Path(self.tmp) / "auth.json"
        datei.write_text(json.dumps({"opencode": {"type": "api", "key": self.schluessel}}),
                         encoding="utf-8")
        r = self.lauf("--quelle", "datei", "--datei", str(datei))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Trockenlauf", r.stdout)
        self.assertIn(str(len(self.schluessel)), r.stdout)
        self.assertNotIn(self.schluessel, r.stdout)
        self.assertFalse((Path(self.tmp) / "jevgrep" / "credentials.json").exists())

    def test_03_anwenden_meldet_gegen_den_endpunkt_an(self):
        datei = Path(self.tmp) / "auth.json"
        basis = "http://127.0.0.1:%d/v1" % self.port
        r = self.lauf("--quelle", "datei", "--datei", str(datei), "--anwenden",
                      "--basis", basis, "--modell", "jev-1.13-free")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("127.0.0.1", r.stdout)
        self.assertNotIn(self.schluessel, r.stdout)
        ablage = Path(self.tmp) / "jevgrep" / "credentials.json"
        self.assertTrue(ablage.exists(), "jg auth hat nichts abgelegt")
        inhalt = ablage.read_text(encoding="utf-8")
        self.assertIn("jev-1.13-free", inhalt)
        self.assertIn(self.schluessel, inhalt)   # angekommen, nur nicht ausgegeben

    def test_04_umgebung_hat_vorrang_und_wird_nicht_ausgegeben(self):
        """Eine gesetzte OPENCODE_API_KEY gewinnt - und der Wert bleibt unsichtbar."""
        umg = dict(self.umgebung)
        umg["OPENCODE_API_KEY"] = "env-testwert-0987654321"
        basis = "http://127.0.0.1:%d/v1" % self.port
        r = subprocess.run(
            [sys.executable, str(HIER / "von_opencode_anmelden.py"),
             "--quelle", "umgebung", "--anwenden", "--basis", basis,
             "--modell", "jev-1.13-free"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=umg, cwd=str(HIER), timeout=240,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Prozessumgebung OPENCODE_API_KEY", r.stdout)
        self.assertNotIn("env-testwert-0987654321", r.stdout)

    def test_05_echte_anmeldung_unberuehrt(self):
        echt = Path(os.path.expanduser("~/.config/jevgrep/credentials.json"))
        if echt.exists():
            self.assertNotIn(str(self.tmp), echt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)