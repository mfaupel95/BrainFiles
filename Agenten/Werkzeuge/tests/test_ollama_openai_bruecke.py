"""Tests fuer die OpenAI-Bruecke auf Ollama (Agenten/Werkzeuge/ollama-openai-bruecke.py).

Ohne Netz und ohne Ollama: ein Attrappen-Ollama auf 127.0.0.1 beantwortet
/api/tags und /api/chat. Geprueft wird, was die Bruecke zusichert:
- der Aufruf geht NATIV raus, mit think=false (das ist ihr Zweck),
- der vom Agenten genannte Modellname wird auf ein lokales Modell abgebildet,
- die Antwort hat die Form, die das OpenAI-SDK erwartet,
- ein stummer Ollama wird als 5xx gemeldet, nicht als leere Antwort.

Start:  python -m unittest discover -s Agenten/Werkzeuge/tests -t Agenten/Werkzeuge/tests
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent
BRUECKE_PFAD = HIER.parent / "ollama-openai-bruecke.py"

_spec = importlib.util.spec_from_file_location("ollama_openai_bruecke", BRUECKE_PFAD)
bruecke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bruecke)


# --------------------------------------------------------------------------
# Attrappen-Ollama
# --------------------------------------------------------------------------

class AttrappenOllama:
    """Mini-Server, der nur mitschreibt, was die Bruecke schickt.

    ``kontext_grenze`` bildet Ollamas haerteste Eigenschaft nach: ist die
    Anfrage groesser als das angeforderte Fenster (num_ctx), antwortet der
    Server mit 400 "exceeds the available context size" - genau das, was einen
    Agenten sonst als "Bruecke tot" erscheint.
    """

    def __init__(self, leere_antwort=False, kontext_grenze=None, token_faktor=2.5):
        self.aufrufe = []
        self.leere_antwort = leere_antwort
        self.kontext_grenze = kontext_grenze
        # Wie viele Zeichen der Attrappen-Ollama je Token rechnet. 2.5 ist die
        # Schaetzung der Bruecke; ein KLEINERER Wert macht den Server strenger
        # als die Bruecke - so laesst sich der Nachbesserungsweg provozieren.
        self.token_faktor = token_faktor
        aussen = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _sende(self, code, koerper):
                daten = json.dumps(koerper).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(daten)))
                self.end_headers()
                self.wfile.write(daten)

            def do_GET(self):
                if self.path.startswith("/api/tags"):
                    self._sende(200, {"models": [{"name": "qwen35-8k:latest"},
                                                 {"name": "gemma-e4b-8k:latest"}]})
                else:
                    self._sende(404, {})

            def do_POST(self):
                laenge = int(self.headers.get("Content-Length") or 0)
                koerper = json.loads(self.rfile.read(laenge).decode("utf-8"))
                aussen.aufrufe.append(koerper)
                if aussen.kontext_grenze:
                    fenster = (koerper.get("options") or {}).get(
                        "num_ctx", aussen.kontext_grenze)
                    bedarf = sum(len(str(m.get("content") or ""))
                                 for m in koerper.get("messages") or []) / aussen.token_faktor
                    if bedarf > fenster:
                        self._sende(400, {"error": (
                            "request (%d tokens) exceeds the available context "
                            "size (%d tokens), try increasing num_ctx"
                            % (int(bedarf), int(fenster)))})
                        return
                text = "" if aussen.leere_antwort else "Attrappen-Antwort"
                self._sende(200, {
                    "message": {"role": "assistant", "content": text},
                    "prompt_eval_count": 11, "eval_count": 7,
                })

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.server.shutdown()
        self.server.server_close()

    @property
    def basis(self):
        return "http://127.0.0.1:%d" % self.port


class BrueckenDienst:
    """Die Bruecke selbst, auf freiem Port, gegen den Attrappen-Ollama."""

    def __init__(self, ollama_basis):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), bruecke.Bruecke)
        self.server.ollama = ollama_basis
        self.server.standard = "qwen35-8k:latest"
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *a):
        self.server.shutdown()
        self.server.server_close()

    def anfrage(self, pfad, koerper=None):
        url = "http://127.0.0.1:%d%s" % (self.port, pfad)
        daten = None if koerper is None else json.dumps(koerper).encode("utf-8")
        anfrage = urllib.request.Request(url, data=daten, method="POST" if daten else "GET",
                                         headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(anfrage, timeout=20)


# --------------------------------------------------------------------------
# Reine Funktionen
# --------------------------------------------------------------------------

class ModellabbildungTest(unittest.TestCase):

    def test_bekannter_name_wird_abgebildet(self):
        self.assertEqual(bruecke.lokales_modell("deepseek-chat", "x"), "qwen35-8k:latest")
        self.assertEqual(bruecke.lokales_modell("deepseek-reasoner", "x"), "qwen36-35b-a3b:8k")

    def test_grossschreibung_und_leerzeichen(self):
        self.assertEqual(bruecke.lokales_modell("  DeepSeek-Chat ", "x"), "qwen35-8k:latest")

    def test_unbekannter_name_mit_tag_bleibt(self):
        self.assertEqual(bruecke.lokales_modell("smollm2:latest", "qwen35-8k:latest"), "smollm2:latest")

    def test_unbekannter_name_ohne_tag_faellt_auf_standard(self):
        self.assertEqual(bruecke.lokales_modell("irgendein-modell", "qwen35-8k:latest"),
                         "qwen35-8k:latest")

    def test_leerer_name_nimmt_standard(self):
        self.assertEqual(bruecke.lokales_modell("", "qwen35-8k:latest"), "qwen35-8k:latest")


class OllamaBasisTest(unittest.TestCase):

    def setUp(self):
        self.alt = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.alt)

    def test_entfernt_v1_und_api(self):
        os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434/v1"
        self.assertEqual(bruecke.ollama_basis(), "http://127.0.0.1:11434")
        os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434/api"
        self.assertEqual(bruecke.ollama_basis(), "http://127.0.0.1:11434")

    def test_ergaenzt_fehlendes_schema(self):
        os.environ["OLLAMA_BASE_URL"] = "127.0.0.1:11434"
        self.assertEqual(bruecke.ollama_basis(), "http://127.0.0.1:11434")

    def test_standard_ohne_variable(self):
        os.environ.pop("OLLAMA_BASE_URL", None)
        os.environ.pop("OLLAMA_HOST", None)
        self.assertEqual(bruecke.ollama_basis(), "http://127.0.0.1:11434")


# --------------------------------------------------------------------------
# Der Dienst
# --------------------------------------------------------------------------

class BrueckenDienstTest(unittest.TestCase):

    def test_denken_ist_abgeschaltet_und_modell_abgebildet(self):
        with AttrappenOllama() as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                antwort = dienst.anfrage("/v1/chat/completions", {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 50, "temperature": 0,
                })
                daten = json.loads(antwort.read().decode("utf-8"))
        self.assertEqual(len(ollama.aufrufe), 1)
        gesendet = ollama.aufrufe[0]
        self.assertIs(gesendet["think"], False)              # der Zweck der Bruecke
        self.assertFalse(gesendet["stream"])
        self.assertEqual(gesendet["model"], "qwen35-8k:latest")
        self.assertEqual(gesendet["options"]["num_predict"], 50)
        # OpenAI-Form
        self.assertEqual(daten["object"], "chat.completion")
        self.assertEqual(daten["choices"][0]["message"]["content"], "Attrappen-Antwort")
        self.assertEqual(daten["choices"][0]["finish_reason"], "stop")
        self.assertEqual(daten["usage"]["total_tokens"], 18)

    def test_modelle_liste_kennt_die_zuordnung(self):
        with AttrappenOllama() as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                daten = json.loads(dienst.anfrage("/v1/models").read().decode("utf-8"))
        namen = [e["id"] for e in daten["data"]]
        self.assertIn("qwen35-8k:latest", namen)
        self.assertIn("deepseek-chat", namen)

    def test_leere_messages_ergeben_400(self):
        with AttrappenOllama() as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                with self.assertRaises(urllib.error.HTTPError) as fehler:
                    dienst.anfrage("/v1/chat/completions", {"model": "deepseek-chat", "messages": []})
        self.assertEqual(fehler.exception.code, 400)

    def test_stummer_ollama_wird_5xx_nicht_leer(self):
        # Ollama-Basis auf einem geschlossenen Port: die Bruecke darf keine
        # leere Antwort liefern, sondern muss 5xx MELDEN. Der Dienst selbst
        # laeuft normal (sonst haengt shutdown() in __exit__).
        with BrueckenDienst("http://127.0.0.1:1") as dienst:
            with self.assertRaises(urllib.error.HTTPError) as fehler:
                dienst.anfrage("/v1/chat/completions",
                               {"model": "deepseek-chat",
                                "messages": [{"role": "user", "content": "Test"}]})
            self.assertGreaterEqual(fehler.exception.code, 500)
            meldung = json.loads(fehler.exception.read().decode("utf-8"))
            self.assertIn("Ollama nicht erreichbar", meldung["error"]["message"])

    def test_unbekannter_weg_ist_404(self):
        with AttrappenOllama() as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                with self.assertRaises(urllib.error.HTTPError) as fehler:
                    dienst.anfrage("/v1/etwas-anderes")
        self.assertEqual(fehler.exception.code, 404)


# --------------------------------------------------------------------------
# Kontextfenster: die Bruecke darf einen Agenten nicht stumm auflaufen lassen
# --------------------------------------------------------------------------

class KontextrechnungTest(unittest.TestCase):
    """Die reinen Rechenfunktionen - ohne Server."""

    def test_schaetzung_ist_ueberschaetzend(self):
        # 2500 Zeichen duerfen NICHT als 1000 Token gelten (2,5 Zeichen/Token),
        # sonst hebt die Bruecke das Fenster zu knapp an.
        nachrichten = [{"role": "user", "content": "x" * 2500}]
        self.assertGreater(bruecke.geschaetzte_token(nachrichten), 1000)

    def test_schaetzung_kennt_die_openai_textform(self):
        nachrichten = [{"role": "user",
                        "content": [{"type": "text", "text": "y" * 500}]}]
        self.assertGreater(bruecke.geschaetzte_token(nachrichten), 190)

    def test_naechste_potenz_waechst_und_deckelt(self):
        self.assertEqual(bruecke.naechste_potenz(5000), 8192)
        self.assertEqual(bruecke.naechste_potenz(9000), 16384)
        self.assertEqual(bruecke.naechste_potenz(999999), bruecke.KONTEXT_MAX)

    def test_mitte_kuerzen_behaelt_kopf_und_ende(self):
        text = "ANFANG" + "m" * 40000 + "ENDE"
        neu, ersetzt = bruecke.mitte_kuerzen([{"role": "user", "content": text}], 2000)
        inhalt = neu[0]["content"]
        self.assertTrue(inhalt.startswith("ANFANG"))
        self.assertTrue(inhalt.endswith("ENDE"))
        self.assertGreater(ersetzt, 30000)
        self.assertLess(len(inhalt), len(text))

    def test_mitte_kuerzen_laesst_kurzes_unberuehrt(self):
        neu, ersetzt = bruecke.mitte_kuerzen([{"role": "user", "content": "kurz"}], 2000)
        self.assertEqual(neu[0]["content"], "kurz")
        self.assertEqual(ersetzt, 0)


class KontextfensterTest(unittest.TestCase):
    """Die Bruecke gegen Ollamas harte Kontextgrenze."""

    def setUp(self):
        # Protokoll in eine Wegwerfdatei: ein Test darf nie ins echte Log schreiben.
        self.alt_log = os.environ.get("BRUECKE_LOG")
        self.log = Path(os.environ["TMPDIR"]) / "bruecke-test.log"
        self.log.unlink(missing_ok=True)
        os.environ["BRUECKE_LOG"] = str(self.log)

    def tearDown(self):
        if self.alt_log is None:
            os.environ.pop("BRUECKE_LOG", None)
        else:
            os.environ["BRUECKE_LOG"] = self.alt_log

    def test_kleiner_text_laesst_num_ctx_weg(self):
        # Standardverhalten unveraendert: ohne Bedarf kein num_ctx im Aufruf.
        with AttrappenOllama() as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                dienst.anfrage("/v1/chat/completions",
                               {"model": "deepseek-chat",
                                "messages": [{"role": "user", "content": "Hallo"}]})
        self.assertNotIn("num_ctx", ollama.aufrufe[0]["options"])

    def test_grosser_text_hebt_das_fenster_an(self):
        # 120.000 Zeichen = ~48.000 Token: ohne Anhebung wuerde die Attrappe mit
        # 400 abbrechen. Die Bruecke muss 32768 anfordern - und dann durchkommen.
        with AttrappenOllama(kontext_grenze=8192) as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                antwort = dienst.anfrage("/v1/chat/completions", {
                    "model": "deepseek-chat", "max_tokens": 50,
                    "messages": [{"role": "user", "content": "z" * 120000}]})
                self.assertEqual(json.loads(antwort.read())["choices"][0]["message"]["role"],
                                 "assistant")
        self.assertEqual(ollama.aufrufe[0]["options"]["num_ctx"], 32768)
        self.assertLessEqual(ollama.aufrufe[0]["options"]["num_ctx"], bruecke.KONTEXT_MAX)

    def test_zu_grosser_text_wird_nachgebessert_statt_zu_scheitern(self):
        # Der Attrappen-Ollama rechnet STRENGER als die Bruecke (1,2 statt 2,5
        # Zeichen je Token) und ist damit der harte Fall. Die Bruecke darf die
        # 400 nicht weiterreichen, sondern kuerzt die Mitte und sendet erneut -
        # der Agent sieht am Ende eine Antwort, keinen 503.
        with AttrappenOllama(kontext_grenze=8192, token_faktor=1.2) as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                antwort = dienst.anfrage("/v1/chat/completions", {
                    "model": "deepseek-chat", "max_tokens": 50,
                    "messages": [{"role": "user", "content": "s" * 120000}]})
                self.assertEqual(json.loads(antwort.read())["choices"][0]["message"]["role"],
                                 "assistant")
        # Die REGEL pruefen, nicht eine feste Versuchszahl: mehr als ein Aufruf
        # (also wurde nachgebessert), jeder Versuch kuerzer als der vorige,
        # hoechstens drei Versuche.
        groessen = [len(a["messages"][0]["content"]) for a in ollama.aufrufe]
        self.assertGreater(len(groessen), 1, "ohne Nachbesserung waere der Lauf gescheitert")
        self.assertLessEqual(len(groessen), 3)
        for vorher, nachher in zip(groessen, groessen[1:]):
            self.assertLess(nachher, vorher * 0.7)

    def test_ende_der_nachbesserungen_ist_ein_fehler_keine_leere_antwort(self):
        # Ein Server, der IMMER "zu gross" sagt, darf die Bruecke nicht in eine
        # Endlosschleife ziehen: nach drei Versuchen kommt ein Fehler.
        with AttrappenOllama(kontext_grenze=8192, token_faktor=0.02) as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                with self.assertRaises(urllib.error.HTTPError) as fehler:
                    dienst.anfrage("/v1/chat/completions", {
                        "model": "deepseek-chat", "max_tokens": 50,
                        "messages": [{"role": "user", "content": "s" * 120000}]})
        self.assertGreaterEqual(fehler.exception.code, 400)
        self.assertEqual(len(ollama.aufrufe), 3, "hoechstens drei Versuche")

    def test_nachbesserung_wird_protokolliert(self):
        # Ein stilles Kuerzen waere schlimmer als ein Fehler: es gehoert ins Log.
        with AttrappenOllama(kontext_grenze=6000, token_faktor=1.2) as ollama:
            with BrueckenDienst(ollama.basis) as dienst:
                dienst.anfrage("/v1/chat/completions", {
                    "model": "deepseek-chat", "max_tokens": 50,
                    "messages": [{"role": "user", "content": "k" * 90000}]})
        inhalt = self.log.read_text(encoding="utf-8")
        self.assertIn("KONTEXT", inhalt)
        # Kein Nutzinhalt im Protokoll - nur Zahlen und der Modellname.
        self.assertNotIn("kkkk", inhalt)


if __name__ == "__main__":
    unittest.main(verbosity=2)