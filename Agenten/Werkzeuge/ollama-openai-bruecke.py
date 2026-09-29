#!/usr/bin/env python
"""OpenAI-kompatible Bruecke auf Ollama - mit abgeschaltetem Denken.

Warum: Fremd-Agenten (moon-dev-ai-agents und Verwandte) waehlen ihren
Sprachmodell-Anbieter nach ANWESENHEIT eines Schluessels und sprechen ihn
ueber das OpenAI-SDK an (`openai.OpenAI(api_key=..., base_url=...)`). Der
lokale Ollama-Server bietet zwar selbst einen /v1-Adapter, liefert dort aber
fuer Denk-Modelle (qwen35, gemma-e4b) einen LEEREN content: das Denken
verbraucht das Token-Budget, finish_reason ist "length", der Text steht im
Feld "reasoning" - gemessen am 24.09.2026 in dieser Umgebung. Der OpenAI-
Adapter von Ollama reicht "think": false NICHT durch.

Diese Bruecke ist der eine Weg, der traegt: sie nimmt den OpenAI-Aufruf
entgegen und ruft Ollama NATIV (/api/chat) mit "think": false auf. Damit
laeuft jeder Agent, der einen "deepseek"-Zweig hat, ohne bezahlten
Schluessel und ohne eine Zeile Aenderung am Fremd-Repo.

Aufruf (Dienst, gebunden auf 127.0.0.1):
    python Agenten/Werkzeuge/ollama-openai-bruecke.py
    python ... --port 11499 --modell qwen35-8k:latest
    python ... --pruefen          # Selbsttest: ein echter Aufruf, Dauer, Antwort
    python ... --trocken          # nur die Zuordnung zeigen, nichts starten

Sie spricht BEIDE Formen: OpenAI (/v1/chat/completions) und die native
Ollama-Form (/api/chat, /api/tags) - Agenten, die die native API nutzen
(OllamaModel der moon-dev-Agenten), laufen damit ebenso.

Danach in die .env des Agenten:
    DEEPSEEK_KEY=lokal-ollama
    DEEPSEEK_BASE_URL=http://127.0.0.1:11499/v1

Nur Standardbibliothek. Keine Schluessel, keine Kosten, keine Inhalte im Log
(je Aufruf eine Zeile: Modell, Dauer, Zeichenzahl).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------

STANDARD_PORT = 11499
# STANDARD und die Zuordnung zeigen auf Modelle, die im Ollama-Store WIRKLICH
# liegen. Am 29.09.2026 war das nicht mehr `qwen35-8k:latest` (der Store wurde
# umbenannt: qwen3.5:9b, deepseek-chat:latest = qwen35 4,3B, deepseek-reasoner
# = 35B-A3B) - die Bruecke antwortete danach auf JEDEN Aufruf mit 503.
# Vor jeder Namensaenderung im Store: `lokal_routing.py --pruefen`.
#
# WARUM DAS KLEINE MODELL DER STANDARD IST (gemessen 29.09.2026, RTX 3060 Ti
# 8 GB): qwen3.5:9b belegt mit 8k-Fenster 6,4 GB VRAM (7,36 GB gesamt, 667 MB
# frei) - es passt nur, solange der Schreibtisch nichts belegt, und JEDES
# zweite Modell daneben scheitert mit cudaMalloc OOM (HTTP 500, kein 503 -
# die Hermes-Fallbackkette greift darauf NICHT). deepseek-chat:latest (qwen35
# 4,3B) belegt 3,1 GB, laeuft mit 88 T/s auch nebenher und ist damit der
# richtige Weg fuer Massenaufrufer (Fremd-Agenten, Schleifen). Das 9B bleibt
# ueber seinen echten Namen oder 'deepseek-reasoner' erreichbar.
STANDARD_MODELL = "deepseek-chat:latest"

SCHNELL = "deepseek-chat:latest"     # qwen35 4,3B, 3,1 GB, ~88 T/s
QUALITAET = "qwen3.5:9b"             # 9,7B Q4_K_M, 262k, 6,4 GB, ~59 T/s @8k

# Namen, die die Fremd-Agenten im Aufruf nennen -> lokales Modell.
# Warum eine Zuordnung und kein Umbenennen: `ollama cp` legt eine Kopie an,
# die bei jedem Modellwechsel mitgezogen werden muesste. Die Zuordnung hier
# wirkt sofort und steht an EINER Stelle.
MODELL_ABBILDUNG = {
    "deepseek-chat": SCHNELL,
    "deepseek-chat-schnell": SCHNELL,
    "deepseek-coder": SCHNELL,
    "gpt-4o": SCHNELL,
    "gpt-4o-mini": SCHNELL,
    "gpt-3.5-turbo": SCHNELL,
    # Wo es auf Textverstaendnis ankommt: das 9B (Denken wird hier ohnehin
    # abgeschaltet - ohne diese Bruecke kaeme ein LEERER content zurueck).
    "deepseek-reasoner": QUALITAET,
    "deepseek-9b": QUALITAET,
    # Ausdruecklicher Wunsch nach dem grossen Modell: 22,7 GB, laeuft nur mit
    # RAM-Auslagerung (gemessen 2-5 T/s) - NICHT der Standardweg.
    "deepseek-reasoner-35b": "deepseek-reasoner:latest",
}

HIER = Path(__file__).resolve().parent
HAUS = HIER.parent.parent  # BrainFiles-Wurzel
STANDARD_LOG = HAUS / "Agenten" / "Hermes" / "cache" / "ollama-openai-bruecke.log"

# Kontextfenster der lokalen Modelle (qwen35-8k/qwen36-35b-a3b sind auf 8192
# gebaut). Reicht das Modellfenster fuer eine Anfrage nicht, hebt die Bruecke
# num_ctx bis KONTEXT_MAX an; darueber wird die Mitte des Textes gekuerzt.
KONTEXT_STANDARD = 8192
KONTEXT_MAX = 32768
RESERVE_AUSGABE = 1024       # Platz fuer die Antwort, wird vom Fenster abgezogen
ZEICHEN_JE_TOKEN = 2.5       # konservativ: gemessen ~2,6 Zeichen/Token (deutsch)


def geschaetzte_token(nachrichten: list) -> int:
    """Grobe, absichtlich UEBERschaetzende Tokenzahl der Nachrichten."""
    zeichen = 0
    for nachricht in nachrichten or []:
        inhalt = nachricht.get("content")
        if isinstance(inhalt, list):      # OpenAI-Form mit Textteilen
            inhalt = " ".join(str(t.get("text") or t) for t in inhalt)
        zeichen += len(str(inhalt or ""))
    return int(zeichen / ZEICHEN_JE_TOKEN) + 8 * len(nachrichten or [])


def naechste_potenz(bedarf: int) -> int:
    """Kleinste Zweierpotenz >= bedarf (num_ctx verlangt feste Groessen)."""
    wert = 1024
    while wert < bedarf and wert < KONTEXT_MAX:
        wert *= 2
    return wert


def mitte_kuerzen(nachrichten: list, budget: int):
    """Die MITTE langer Nachrichten ersetzen, Kopf und Ende behalten.

    Der Kopf traegt die Anweisung, das Ende die frischesten Daten - die Mitte
    ist der entbehrlichste Teil. Rueckgabe: (neue Nachrichten, ersetzte Zeichen).
    """
    erlaubt = int(max(budget, 512) * ZEICHEN_JE_TOKEN)
    neu, ersetzt = [], 0
    for nachricht in nachrichten:
        inhalt = nachricht.get("content")
        if isinstance(inhalt, list):
            inhalt = " ".join(str(t.get("text") or t) for t in inhalt)
        inhalt = str(inhalt or "")
        if len(inhalt) > erlaubt:
            kopf, ende = erlaubt // 2, erlaubt // 2
            weg = len(inhalt) - kopf - ende
            inhalt = ("%s\n\n[... %d Zeichen gekuerzt: Kontextfenster des lokalen "
                      "Modells ...]\n\n%s" % (inhalt[:kopf], weg, inhalt[-ende:]))
            ersetzt += weg
        neu.append(dict(nachricht, content=inhalt))
    return neu, ersetzt


def protokoll(zeile: str):
    """Eine Zeile ins Bruecken-Protokoll (nur Zahlen/Metadaten, kein Inhalt)."""
    pfad = Path(os.environ.get("BRUECKE_LOG") or STANDARD_LOG)
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a", encoding="utf-8") as fh:
            fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), zeile))
    except OSError:
        pass


def ollama_basis() -> str:
    """Basis-URL des Ollama-Servers, ohne /v1 (native API)."""
    wert = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
    wert = wert.strip().rstrip("/")
    for ende in ("/v1", "/api"):
        if wert.endswith(ende):
            wert = wert[: -len(ende)]
    if not wert.startswith("http"):
        wert = "http://" + wert
    return wert


def lokales_modell(name: str, standard: str) -> str:
    """Den vom Agenten genannten Modellnamen auf ein lokales Modell abbilden."""
    if not name:
        return standard
    klein = name.strip().lower()
    if klein in MODELL_ABBILDUNG:
        return MODELL_ABBILDUNG[klein]
    # Namen, die es lokal wirklich gibt (inkl. Tag), unveraendert durchlassen.
    if ":" in name:
        return name
    for kandidat in MODELL_ABBILDUNG.values():
        if kandidat.split(":")[0] == klein:
            return kandidat
    return standard


def ollama_nativ(basis: str, modell: str, nachrichten: list, temperature=None,
                 max_tokens=None, top_p=None, frist=600):
    """EIN Aufruf an die native Ollama-API mit think: false.

    Rueckgabe: (content, denk_zeichen, usage) - content ist der sichtbare Text.

    KONTEXT-GRENZE (gemessen 24.09.2026): Ollama antwortet hart mit HTTP 400
    ("request (25219 tokens) exceeds the available context size (8192 tokens)"),
    sobald die Anfrage groesser ist als das Modellfenster - der Fremd-Agent
    sieht dann nur "503 Ollama nicht erreichbar" und haelt die Bruecke fuer tot.
    Deshalb: num_ctx hochsetzen, so weit der Bedarf reicht, und erst wenn auch
    die harte Obergrenze nicht reicht, die MITTE des Textes kuerzen (Kopf und
    Ende bleiben - Anweisung vorn, frische Daten hinten).
    """
    optionen = {}
    if temperature is not None:
        optionen["temperature"] = temperature
    if max_tokens:
        optionen["num_predict"] = int(max_tokens)
    if top_p is not None:
        optionen["top_p"] = top_p

    reserve = int(os.environ.get("BRUECKE_RESERVE") or RESERVE_AUSGABE)
    obergrenze = int(os.environ.get("BRUECKE_KONTEXT_MAX") or KONTEXT_MAX)
    bedarf = geschaetzte_token(nachrichten) + reserve
    if bedarf > KONTEXT_STANDARD:
        optionen["num_ctx"] = min(obergrenze, naechste_potenz(bedarf))
    if bedarf > obergrenze:
        vorher = geschaetzte_token(nachrichten)
        nachrichten, rest = mitte_kuerzen(nachrichten, obergrenze - reserve)
        optionen["num_ctx"] = obergrenze
        gekuerzt = "gekuerzt: %d -> %d geschaetzte Token, %d Zeichen Mitte ersetzt" % (
            vorher, geschaetzte_token(nachrichten), rest)
    else:
        gekuerzt = ""
    if gekuerzt:
        protokoll("KONTEXT %s %s" % (modell, gekuerzt))

    koerper = {
        "model": modell,
        "messages": nachrichten,
        "stream": False,
        "think": False,          # der eigentliche Zweck dieser Bruecke
        "options": optionen or {"temperature": 0},
    }
    daten = json.dumps(koerper).encode("utf-8")
    anfrage = urllib.request.Request(
        basis + "/api/chat", data=daten,
        headers={"Content-Type": "application/json"}, method="POST")
    # Zwei Nachbesserungen, falls die Schaetzung zu knapp war: Ollama sagt im
    # Rumpf genau, um wie viel es zu gross war ("exceeds the available context
    # size") - dann Mitte kuerzen und dieselbe Anfrage erneut senden, statt den
    # Aufrufer mit einer 503 stehen zu lassen.
    for versuch in range(3):
        try:
            with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
                roh = json.loads(antwort.read().decode("utf-8", "replace"))
            break
        except urllib.error.HTTPError as fehler:
            try:
                rumpf = fehler.read().decode("utf-8", "replace")
            except Exception:
                rumpf = ""
            zu_gross = ("exceeds the available context size" in rumpf
                        or "exceed_context_size_error" in rumpf)
            if zu_gross and versuch < 2:
                nachrichten, rest = mitte_kuerzen(nachrichten, int(
                    geschaetzte_token(nachrichten) * 0.6))
                koerper["messages"] = nachrichten
                protokoll("KONTEXT %s nachgebessert (%d. Versuch): %d Zeichen "
                          "Mitte ersetzt, Fenster %s"
                          % (modell, versuch + 1, rest, koerper["options"].get("num_ctx")))
                anfrage = urllib.request.Request(
                    basis + "/api/chat",
                    data=json.dumps(koerper).encode("utf-8"),
                    headers={"Content-Type": "application/json"}, method="POST")
                continue
            # Ollama nennt im Rumpf den Grund (z. B. "does not support tools").
            # Ohne ihn bleibt nur "HTTP Error 400" und man raet - deshalb den
            # Rumpf mitgeben, gekuerzt und ohne Nutzinhalt.
            zeilen = len(koerper.get("messages") or [])
            zeichen = sum(len(str(m.get("content") or "")) for m in koerper.get("messages") or [])
            raise urllib.error.HTTPError(
                fehler.url, fehler.code,
                "%s | Ollama-Rumpf: %s | Nachrichten: %d, Zeichen: %d, options: %s"
                % (fehler.reason, rumpf[:300], zeilen, zeichen, koerper.get("options")),
                fehler.headers, fehler.fp)
    nachricht = roh.get("message") or {}
    content = nachricht.get("content") or ""
    denk = nachricht.get("thinking") or ""
    usage = {
        "prompt_tokens": roh.get("prompt_eval_count") or 0,
        "completion_tokens": roh.get("eval_count") or 0,
        "total_tokens": (roh.get("prompt_eval_count") or 0) + (roh.get("eval_count") or 0),
    }
    return content, denk, usage


def modelle(basis: str, frist=10) -> list:
    with urllib.request.urlopen(basis + "/api/tags", timeout=frist) as antwort:
        roh = json.loads(antwort.read().decode("utf-8", "replace"))
    return [m.get("name") for m in roh.get("models", []) if m.get("name")]


# ---------------------------------------------------------------------------
# HTTP-Dienst
# ---------------------------------------------------------------------------

class Bruecke(BaseHTTPRequestHandler):
    server_version = "OllamaOpenAIBruecke/1.0"
    protokoll_version = "HTTP/1.1"

    # -- Hilfen ------------------------------------------------------------
    def _antwort(self, code: int, koerper: dict | str, typ="application/json"):
        if isinstance(koerper, dict):
            koerper = json.dumps(koerper)
        daten = koerper.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def _fehler(self, code: int, text: str):
        # OpenAI-Form, damit die SDKs eine lesbare Meldung zeigen
        self._antwort(code, {"error": {"message": text, "type": "bruecke",
                                       "code": code}})

    def _log(self, zeile: str):
        pfad = Path(os.environ.get("BRUECKE_LOG") or STANDARD_LOG)
        try:
            pfad.parent.mkdir(parents=True, exist_ok=True)
            with pfad.open("a", encoding="utf-8") as fh:
                fh.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), zeile))
        except OSError:
            pass

    def log_message(self, fmt, *args):  # kein Zugriffslog auf stderr
        pass

    # -- Wege --------------------------------------------------------------
    def do_GET(self):
        basis = self.server.ollama
        if self.path.split("?")[0] in ("/v1/models", "/models"):
            try:
                namen = modelle(basis)
            except Exception as fehler:
                self._fehler(503, "Ollama nicht erreichbar (%s): %s" % (basis, fehler))
                return
            liste = [{"id": n, "object": "model", "owned_by": "ollama"} for n in namen]
            liste += [{"id": k, "object": "model", "owned_by": "bruecke"}
                      for k in MODELL_ABBILDUNG]
            self._antwort(200, {"object": "list", "data": liste})
            return
        if self.path.split("?")[0] == "/api/tags":
            # Native Ollama-Sicht: manche Fremd-Agenten pruefen ihre
            # Verbindung ueber /api/tags (so macht es das OllamaModel der
            # moon-dev-Agenten). Ohne diesen Weg halten sie die Bruecke fuer
            # tot und der Modellaufbau scheitert.
            try:
                with urllib.request.urlopen(basis + "/api/tags", timeout=10) as antwort:
                    roh = antwort.read().decode("utf-8", "replace")
            except Exception as fehler:
                self._fehler(503, "Ollama nicht erreichbar (%s): %s" % (basis, fehler))
                return
            self._antwort(200, roh)
            return
        if self.path.split("?")[0] in ("/gesundheit", "/health"):
            try:
                namen = modelle(basis)
                self._antwort(200, {"ok": True, "ollama": basis,
                                    "standard": self.server.standard, "modelle": len(namen)})
            except Exception as fehler:
                self._antwort(503, {"ok": False, "ollama": basis, "fehler": str(fehler)})
            return
        self._fehler(404, "unbekannter Weg: %s" % self.path)

    def _nativ_chat(self):
        """Die NATIVE Ollama-Antwortform - fuer Agenten, die /api/chat sprechen.

        Sie bekommen dieselbe Abschaltung des Denkens, aber die Antwortfelder,
        die sie erwarten (message.content, done, eval_count).
        """
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8", "replace") or "{}")
        except Exception as fehler:
            self._fehler(400, "Anfrage nicht lesbar: %s" % fehler)
            return
        gewuenscht = anfrage.get("model") or ""
        modell = lokales_modell(gewuenscht, self.server.standard)
        nachrichten = anfrage.get("messages") or []
        if not nachrichten:
            self._fehler(400, "keine messages")
            return
        optionen = anfrage.get("options") or {}
        start = time.time()
        try:
            content, denk, usage = ollama_nativ(
                self.server.ollama, modell, nachrichten,
                temperature=optionen.get("temperature"),
                max_tokens=optionen.get("num_predict"),
                top_p=optionen.get("top_p"))
        except urllib.error.URLError as fehler:
            self._log("FEHLER (nativ) %s -> %s (%s)" % (modell, self.server.ollama, fehler))
            self._fehler(503, "Ollama nicht erreichbar (%s): %s" % (self.server.ollama, fehler))
            return
        except Exception as fehler:
            self._log("FEHLER (nativ) %s: %s" % (modell, fehler))
            self._fehler(500, "Aufruf gescheitert: %s" % fehler)
            return
        dauer = time.time() - start
        self._log("nativ %s -> %s  %.1fs  %d Zeichen%s" % (
            gewuenscht or "-", modell, dauer, len(content),
            "  ACHTUNG leer" if not content else ""))
        nachricht = {"role": "assistant", "content": content}
        if denk:
            nachricht["thinking"] = denk
        self._antwort(200, {
            "model": modell,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000000000Z", time.gmtime()),
            "message": nachricht,
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": usage.get("prompt_tokens", 0),
            "eval_count": usage.get("completion_tokens", 0),
        })

    def do_POST(self):
        weg = self.path.split("?")[0]
        if weg == "/api/chat":
            self._nativ_chat()
            return
        if weg not in ("/v1/chat/completions", "/chat/completions"):
            self._fehler(404, "unbekannter Weg: %s" % weg)
            return
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8", "replace") or "{}")
        except Exception as fehler:
            self._fehler(400, "Anfrage nicht lesbar: %s" % fehler)
            return

        gewuenscht = anfrage.get("model") or ""
        modell = lokales_modell(gewuenscht, self.server.standard)
        nachrichten = anfrage.get("messages") or []
        if not nachrichten:
            self._fehler(400, "keine messages")
            return

        start = time.time()
        try:
            content, denk, usage = ollama_nativ(
                self.server.ollama, modell, nachrichten,
                temperature=anfrage.get("temperature"),
                max_tokens=anfrage.get("max_tokens"),
                top_p=anfrage.get("top_p"))
        except urllib.error.URLError as fehler:
            self._log("FEHLER %s -> %s (%s)" % (modell, self.server.ollama, fehler))
            self._fehler(503, "Ollama nicht erreichbar (%s): %s" % (self.server.ollama, fehler))
            return
        except Exception as fehler:
            self._log("FEHLER %s: %s" % (modell, fehler))
            self._fehler(500, "Aufruf gescheitert: %s" % fehler)
            return

        dauer = time.time() - start
        self._log("%s -> %s  %.1fs  %d Zeichen%s" % (
            gewuenscht or "-", modell, dauer, len(content),
            "  ACHTUNG leer" if not content else ""))

        antwort = {
            "id": "bruecke-%d" % int(start * 1000),
            "object": "chat.completion",
            "created": int(start),
            "model": modell,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": usage,
        }
        if denk:
            antwort["choices"][0]["message"]["reasoning"] = denk
        self._antwort(200, antwort)


# ---------------------------------------------------------------------------
# Start / Selbsttest
# ---------------------------------------------------------------------------

def selbsttest(modell: str) -> int:
    basis = ollama_basis()
    print("Ollama   :", basis)
    print("Modell   :", modell)
    try:
        namen = modelle(basis)
    except Exception as fehler:
        print("FEHLER: Ollama nicht erreichbar:", fehler)
        return 1
    print("Modelle  :", ", ".join(namen) or "(keine)")
    if modell not in namen:
        print("WARNUNG: '%s' liegt nicht im Ollama-Store." % modell)
    nachrichten = [
        {"role": "system", "content": "Antworte in EINER Zeile."},
        {"role": "user", "content": "Liquidationspreis eines 10x Long ab 100 USD? Eine Zeile."},
    ]
    start = time.time()
    content, _, usage = ollama_nativ(basis, modell, nachrichten, temperature=0, max_tokens=120)
    print("Dauer    : %.1f s" % (time.time() - start))
    print("Antwort  :", (content or "<< LEER - Denken nicht abgeschaltet? >>")[:300])
    print("Tokens   :", usage)
    return 0 if content else 2


def dienst(port: int, modell: str) -> int:
    basis = ollama_basis()
    server = ThreadingHTTPServer(("127.0.0.1", port), Bruecke)
    server.ollama = basis
    server.standard = modell
    print("Bruecke auf http://127.0.0.1:%d/v1  ->  %s (think: false)" % (port, basis), flush=True)
    print("Test: curl -s http://127.0.0.1:%d/gesundheit" % port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("beendet", flush=True)
    return 0


def main(argv=None) -> int:
    zerleger = argparse.ArgumentParser(description="OpenAI-kompatible Bruecke auf Ollama (think:false)")
    zerleger.add_argument("--port", type=int, default=int(os.environ.get("BRUECKE_PORT") or STANDARD_PORT))
    zerleger.add_argument("--modell", default=os.environ.get("BRUECKE_MODELL") or STANDARD_MODELL)
    zerleger.add_argument("--pruefen", action="store_true", help="Selbsttest, dann Ende")
    zerleger.add_argument("--trocken", action="store_true", help="nur Zuordnung zeigen")
    args = zerleger.parse_args(argv)

    if args.trocken:
        print("Ollama-Basis :", ollama_basis())
        print("Standardmodell:", args.modell)
        print("Zuordnung    :")
        for k, v in MODELL_ABBILDUNG.items():
            print("  %-22s -> %s" % (k, v))
        print("Adresse in die .env des Agenten: http://127.0.0.1:%d/v1" % args.port)
        return 0
    if args.pruefen:
        return selbsttest(args.modell)
    return dienst(args.port, args.modell)


if __name__ == "__main__":
    sys.exit(main())