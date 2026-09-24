"""Tests fuer die Wache der Ollama-Bruecke (Agenten/Hermes/scripts/ollama-bruecke-wache.py).

Geprueft wird die REGEL, nicht ein Text:
- laeuft die Bruecke -> LEERE Ausgabe (Watchdog-Muster: nichts senden),
- laeuft sie nicht und --nicht-starten -> ein Befund mit Port,
- fehlt das Werkzeug -> ein Befund, kein Absturz,
- und der Startweg heilt einen toten Port wirklich (eigener Port, damit die
  laufende Bruecke auf 11499 unberuehrt bleibt).

Start:  python -m unittest test_ollama_bruecke_wache  (aus diesem Ordner)
"""
from __future__ import annotations

import importlib.util
import io
import contextlib
import sys
import unittest
import urllib.error
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE_PFAD = HIER / "ollama-bruecke-wache.py"

_spec = importlib.util.spec_from_file_location("ollama_bruecke_wache", WACHE_PFAD)
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)

TOTER_PORT = 11497          # hier lauscht nichts (die echte Bruecke liegt auf 11499)


def lauf(*argumente):
    """main() mit Argumenten aufrufen und die Ausgabe abfangen."""
    puffer = io.StringIO()
    alt = sys.argv
    sys.argv = ["ollama-bruecke-wache.py"] + list(argumente)
    try:
        with contextlib.redirect_stdout(puffer):
            code = wache.main()
    finally:
        sys.argv = alt
    return code, puffer.getvalue()


class GesundTest(unittest.TestCase):

    def test_laufende_bruecke_ist_still(self):
        """Die echte Bruecke laeuft auf dem Standardport - darf keine Zeile ausgeben."""
        if not wache.gesund(11499, frist=3.0)[0]:
            self.skipTest("Bruecke auf 11499 laeuft gerade nicht")
        code, ausgabe = lauf("--port", "11499")
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "")


class BefundTest(unittest.TestCase):

    def test_toter_port_mit_nicht_starten_meldet_port(self):
        code, ausgabe = lauf("--port", str(TOTER_PORT), "--nicht-starten")
        self.assertEqual(code, 0)
        self.assertIn(str(TOTER_PORT), ausgabe)
        self.assertIn("nicht", ausgabe.lower())

    def test_fehlendes_werkzeug_wird_gemeldet(self):
        alt = wache.WERKZEUG
        wache.WERKZEUG = Path("C:/gibt/es/nicht/ollama-openai-bruecke.py")
        try:
            code, ausgabe = lauf("--port", str(TOTER_PORT))
        finally:
            wache.WERKZEUG = alt
        self.assertEqual(code, 1)
        self.assertIn("Werkzeug fehlt", ausgabe)


class StartTest(unittest.TestCase):
    """Der Startweg: toter Port -> Bruecke hoch -> geheilt gemeldet."""

    def test_start_heilt_den_toten_port(self):
        if wache.gesund(TOTER_PORT, frist=1.0)[0]:
            self.skipTest("Port %d ist schon belegt" % TOTER_PORT)
        code, ausgabe = lauf("--port", str(TOTER_PORT), "--warten", "25")
        try:
            self.assertEqual(code, 0)
            self.assertIn("geheilt", ausgabe)
            self.assertTrue(wache.gesund(TOTER_PORT, frist=5.0)[0],
                            "Bruecke antwortet nach dem Start nicht")
        finally:
            # Aufraeumen: den gestarteten Dienst auf dem Testport beenden
            self._beende_port(TOTER_PORT)

    @staticmethod
    def _beende_port(port):
        import json
        import os
        import subprocess
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
              "Where-Object { $_.CommandLine -like '*--port %d*' } | "
              "ForEach-Object { $_.ProcessId }" % port)
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, text=True, timeout=60)
        except Exception:
            return
        for zeile in (r.stdout or "").split():
            if zeile.strip().isdigit():
                try:
                    subprocess.run(["taskkill", "/T", "/F", "/PID", zeile.strip()],
                                   capture_output=True, timeout=30)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)