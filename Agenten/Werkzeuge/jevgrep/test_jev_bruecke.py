"""Nachweis: die jev-Bruecke beantwortet jevgrep-Anfragen ueber ein beliebiges
OpenAI-kompatibles Modell - inklusive echtem Durchlauf jevgrep -> Bruecke -> Modell.

Der Modell-Dienst ist eine Attrappe auf 127.0.0.1, die drei Verhaltensweisen kennt:
sauberes JSON, Fliesstext mit Zahlen, und Unsinn. Damit ist die Bruecke ohne
Schluessel, ohne Netz und ohne Kosten pruefbar.

Aufruf:  python test_jev_bruecke.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent
JG = HIER / "jg.cmd"
BRUECKE = HIER / "jev_bruecke.py"
REPO = HIER.parents[2] / "Werkstatt" / "jevgrep"
SUCHWURZEL = REPO / "apps"

modus = {"art": "json"}
gesehen: list[dict] = []


class ModellAttrappe(BaseHTTPRequestHandler):
    def do_POST(self):                                          # noqa: N802
        n = int(self.headers.get("content-length", "0"))
        try:
            a = json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            a = {}
        text = ""
        for m in (a.get("messages") or []):
            text += str(m.get("content") or "")
        ids = re.findall(r"^- ([^:]+):", text, flags=re.M)
        gesehen.append({"ids": ids, "zeichen": len(text), "modell": a.get("model"),
                        "denken": a.get("think")})
        art = modus["art"]
        if art == "json":
            inhalt = json.dumps({"answers": {i: 0.9 for i in ids}})
        elif art == "fliesstext":
            inhalt = "Ich denke: " + ", ".join("%s ist zu 0,85 relevant" % i for i in ids)
        elif art == "leer":
            inhalt = ""          # so antwortet ein Modell, dessen Kontext zu klein ist
        else:
            inhalt = "keine Ahnung, vielleicht?"
        daten = json.dumps({"choices": [{"message": {"content": inhalt}}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *a):
        pass


def freier_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def warte_auf(url: str, frist: float = 30.0) -> bool:
    ende = time.time() + frist
    while time.time() < ende:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:                                       # noqa: BLE001
            time.sleep(0.2)
    return False


class BrueckeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="jevbruecke_")
        cls.modell = HTTPServer(("127.0.0.1", 0), ModellAttrappe)
        cls.modell_port = cls.modell.server_address[1]
        threading.Thread(target=cls.modell.serve_forever, daemon=True).start()

        cls.port = freier_port()
        umg = dict(os.environ)
        umg.update({
            "JEVCREP_BRUECKE_PORT": str(cls.port),
            "JEVCREP_BRUECKE_BASIS": "http://127.0.0.1:%d/v1" % cls.modell_port,
            "JEVCREP_BRUECKE_MODELL": "attrappe",
            "JEVCREP_BRUECKE_FRIST": "20",
            "JEVCREP_BRUECKE_PROTOKOLL": str(Path(cls.tmp) / "protokoll.log"),
            "PYTHONIOENCODING": "utf-8",
        })
        umg.pop("PYTHONHOME", None)
        umg.pop("PYTHONPATH", None)
        cls.umg = umg
        cls.bruecke = subprocess.Popen(
            [sys.executable, str(BRUECKE)], env=umg,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace",
        )
        cls.basis = "http://127.0.0.1:%d" % cls.port
        if not warte_auf(cls.basis + "/gesundheit"):
            cls.tearDownClass()
            raise unittest.SkipTest("Bruecke ist nicht gestartet")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.bruecke.terminate()
            cls.bruecke.wait(timeout=10)
        except Exception:                                       # noqa: BLE001
            cls.bruecke.kill()
        cls.modell.shutdown()
        cls.modell.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def systemone(self, fragen, zustand="Zustand: handeln.py schliesst Positionen."):
        koerper = json.dumps({"model": "attrappe", "state": zustand,
                              "questions": fragen}).encode()
        req = urllib.request.Request(self.basis + "/v1/systemone", data=koerper,
                                     headers={"content-type": "application/json",
                                              "authorization": "Bearer egal"},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def test_01_gesundheit(self):
        with urllib.request.urlopen(self.basis + "/gesundheit", timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        self.assertTrue(d["ok"])
        self.assertEqual(d["modell"], "attrappe")

    def test_02_noul_fragen_werden_beantwortet(self):
        modus["art"] = "json"
        fragen = {"a": {"type": "noul", "instructions": "Relevant?"},
                  "b": {"type": "noul", "instructions": "Auch?"},
                  "c": {"type": "noul", "instructions": "Und?"}}
        code, d = self.systemone(fragen)
        self.assertEqual(code, 200)
        self.assertEqual(set(d["answers"]), {"a", "b", "c"})
        for k, v in d["answers"].items():
            self.assertEqual(v["type"], "noul")
            self.assertIsInstance(v["noul"], float)
            self.assertGreaterEqual(v["noul"], 0.0)
            self.assertLessEqual(v["noul"], 1.0)
        self.assertEqual(gesehen[-1]["denken"], False, "Denken muss abgeschaltet sein")

    def test_03_fliesslext_mit_zahlen_wird_gelesen(self):
        modus["art"] = "fliesstext"
        code, d = self.systemone({"x": {"type": "noul", "instructions": "Relevant?"}})
        self.assertEqual(code, 200)
        self.assertAlmostEqual(d["answers"]["x"]["noul"], 0.85, places=2)

    def test_04_unsinn_ergibt_null_statt_fehler(self):
        modus["art"] = "unsinn"
        code, d = self.systemone({"y": {"type": "noul", "instructions": "Relevant?"}})
        self.assertEqual(code, 200, "die Bruecke darf jevgrep nie mit 5xx abweisen")
        self.assertEqual(d["answers"]["y"]["noul"], 0.0)

    def test_05_score_und_choice_werden_bedient(self):
        modus["art"] = "json"
        code, d = self.systemone({
            "s": {"type": "score", "instructions": "Wie gut?"},
            "c": {"type": "choice", "instructions": "Welche?", "choices": ["a", "b"]},
        })
        self.assertEqual(code, 200)
        self.assertIn("score", d["answers"]["s"])
        self.assertEqual(d["answers"]["c"]["choice"], "a")

    def test_06_protokoll_wird_geschrieben(self):
        modus["art"] = "json"
        self.systemone({"z": {"type": "noul", "instructions": "Relevant?"}})
        p = Path(self.tmp) / "protokoll.log"
        self.assertTrue(p.is_file(), "kein Protokoll")
        letzte = json.loads(p.read_text(encoding="utf-8").strip().splitlines()[-1])
        self.assertIn("zustand_zeichen", letzte)
        self.assertIn("dauer_gesamt_s", letzte)

    def test_07_leere_modellantwort_wird_gemeldet(self):
        """Die stille Falle: zu kleines Kontextfenster -> das Modell antwortet NICHTS.

        Dann waeren alle Dateien 'nicht relevant'. Die Bruecke darf das nicht in
        0.0 verschwinden lassen, sondern muss es protokollieren.
        """
        modus["art"] = "leer"
        protokoll = Path(self.tmp) / "protokoll.log"
        vorher = protokoll.read_text(encoding="utf-8").count("\n") if protokoll.is_file() else 0
        code, d = self.systemone({"k": {"type": "noul", "instructions": "Relevant?"}})
        self.assertEqual(code, 200)
        self.assertEqual(d["answers"]["k"]["noul"], 0.0)
        zeilen = protokoll.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreater(len(zeilen), vorher)
        letzte = json.loads(zeilen[-1])
        self.assertIsNotNone(letzte.get("fehler"), "leere Antwort wurde nicht gemeldet")
        self.assertIn("leere Modellantwort", letzte["fehler"])
        modus["art"] = "json"

    def test_08_jevgrep_laeuft_ueber_die_bruecke(self):
        """Der ganze Weg: jevgrep -> Bruecke -> Modell -> Trefferliste."""
        if not (JG.is_file() and SUCHWURZEL.is_dir()):
            self.skipTest("jevgrep oder Suchwurzel fehlt")
        modus["art"] = "json"
        umg = dict(self.umg)
        umg["XDG_CONFIG_HOME"] = self.tmp
        r = subprocess.run(
            [str(JG), "auth", "--provider", "custom",
             "--base-url", self.basis + "/v1", "--model", "attrappe", "--stdin"],
            input="egal\n", capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=umg, timeout=120,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run(
            [str(JG), "Wie wird ein Projekt gestartet?", str(SUCHWURZEL),
             "--concurrency", "2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=umg, timeout=420,
        )
        self.assertIn(r.returncode, (0, 2), r.stdout + r.stderr)
        self.assertIn("Jevgrep", r.stdout)
        self.assertIn("relevant", r.stdout)
        self.assertTrue(any("apps" in g or "cli" in g for g in [r.stdout]),
                        "keine Datei in der Ausgabe:\n" + r.stdout[:500])


if __name__ == "__main__":
    unittest.main(verbosity=2)