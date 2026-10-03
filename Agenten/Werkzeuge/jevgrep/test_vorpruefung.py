"""Tests fuer den Vorschalter (vorpruefung.py) und den sicheren Aufruf (jg_sicher.py).

Alles ohne Netz und ohne Kosten: der Anbieter ist eine Attrappe auf 127.0.0.1, die
Anmeldung liegt in einem Temp-XDG. Geprueft werden die ENTSCHEIDUNGEN, nicht Zahlen:
Subkommandos laufen durch, ein toter Anbieter stoppt, eine zu grosse Wurzel stoppt,
--trotzdem laesst durch, und jevgrep bekommt die eigenen Schalter nicht zu sehen.

Aufruf:  python test_vorpruefung.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import vorpruefung  # noqa: E402
import jg_sicher  # noqa: E402


class Anbieter(BaseHTTPRequestHandler):
    def do_POST(self):                                          # noqa: N802
        n = int(self.headers.get("content-length", "0"))
        self.rfile.read(n)
        daten = json.dumps({"answers": {"q": {"type": "noul", "noul": 0.5}}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *a):
        pass


class VorpruefungTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vorpruefung_")
        cls.server = HTTPServer(("127.0.0.1", 0), Anbieter)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.wurzel = Path(cls.tmp) / "quelle"
        (cls.wurzel / "unter").mkdir(parents=True)
        for i in range(4):
            (cls.wurzel / ("datei%d.py" % i)).write_text("x = 1\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def anmelden(self, basis: str) -> None:
        d = Path(self.tmp) / "jevgrep"
        d.mkdir(parents=True, exist_ok=True)
        (d / "credentials.json").write_text(json.dumps(
            {"provider": "custom", "baseURL": basis, "model": "bruecke", "apiKey": "x"}),
            encoding="utf-8")

    def setUp(self):
        self.alt_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["XDG_CONFIG_HOME"] = self.tmp
        self.anmelden("http://127.0.0.1:%d/v1" % self.port)
        self.alt_max = (vorpruefung.MAX_DATEIEN, vorpruefung.MAX_MIB)

    def tearDown(self):
        vorpruefung.MAX_DATEIEN, vorpruefung.MAX_MIB = self.alt_max
        if self.alt_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.alt_xdg

    def lauf(self, *args) -> tuple[int, str]:
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            rc = vorpruefung.pruefen(list(args))
        return rc, puffer.getvalue()

    def test_01_subkommando_laeuft_ungeprueft(self):
        rc, text = self.lauf("files", str(self.wurzel))
        self.assertEqual(rc, 0)
        self.assertEqual(text, "", "ein Subkommando darf nichts pruefen")

    def test_02_ohne_anmeldung_wird_gestoppt(self):
        os.environ["XDG_CONFIG_HOME"] = str(Path(self.tmp) / "leer")
        rc, text = self.lauf("Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 1)
        self.assertIn("nicht angemeldet", text)

    def test_03_toter_anbieter_wird_gestoppt(self):
        self.anmelden("http://127.0.0.1:9/v1")
        rc, text = self.lauf("Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 1)
        self.assertIn("antwortet nicht", text)
        self.assertIn("keine Suche gestartet", text)

    def test_04_gute_suche_nennt_kosten(self):
        rc, text = self.lauf("Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 0)
        self.assertIn("antwortet", text)
        self.assertIn("US-Dollar", text)
        self.assertIn("Dateien", text)

    def test_05_grosse_wurzel_wird_gestoppt(self):
        vorpruefung.MAX_DATEIEN = 1
        rc, text = self.lauf("Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 1)
        self.assertIn("Wurzel zu gross", text)
        self.assertIn("--trotzdem", text)

    def test_06_trotzdem_laesst_durch(self):
        vorpruefung.MAX_DATEIEN = 1
        rc, text = self.lauf("--trotzdem", "Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 0)
        self.assertIn("US-Dollar", text)

    def test_07_leise_schweigt_bei_erfolg(self):
        rc, text = self.lauf("--leise", "Wie wird X entschieden?", str(self.wurzel))
        self.assertEqual(rc, 0)
        self.assertEqual(text, "")

    def test_08_eigene_schalter_erreichen_jevgrep_nicht(self):
        """--trotzdem und --leise kennt jevgrep nicht - sie muessen entfernt werden."""
        gesehen = {}

        class Attrappe:
            returncode = 0

            def __init__(self, befehl, cwd=None):
                gesehen["befehl"] = befehl

        alt_run, alt_pruefen = jg_sicher.subprocess.run, jg_sicher.vorpruefung.pruefen
        jg_sicher.subprocess.run = Attrappe
        jg_sicher.vorpruefung.pruefen = lambda argv: 0
        alt_argv = sys.argv
        try:
            sys.argv = ["jg_sicher.py", "--trotzdem", "Frage?", str(self.wurzel)]
            jg_sicher.main()
        finally:
            jg_sicher.subprocess.run = alt_run
            jg_sicher.vorpruefung.pruefen = alt_pruefen
            sys.argv = alt_argv
        self.assertIn("Frage?", gesehen["befehl"])
        self.assertNotIn("--trotzdem", gesehen["befehl"])
        self.assertTrue(str(gesehen["befehl"][0]) == "node")


if __name__ == "__main__":
    unittest.main(verbosity=2)