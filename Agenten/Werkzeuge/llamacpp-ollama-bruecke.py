#!/usr/bin/env python3
"""Ollama-Schnittstelle auf llama-server: der Adapter fuer die Moon-Dev-Agenten.

WARUM (12.10.2026)
------------------
Die Fremd-Agenten (moon-dev-ai-agents) holen ihre Sprachmodell-Antwort in
`llm_lokal()` ueber **Ollamas native API** (`POST /api/chat`, `GET /api/tags`,
`think: false`). Ollama wurde am 11.10.2026 deinstalliert; die Haus-Laufzeit ist
jetzt der verwaltete **llama-server** auf 127.0.0.1:18434.

llama-server spricht ausschliesslich **OpenAI** (`/v1/chat/completions`,
`/v1/models`) - nachgemessen am 12.10.2026: `/api/chat`, `/api/tags` und
`/api/version` antworten alle mit HTTP 404. Die Agenten wuerden also ohne
Adapter ins Leere greifen.

Dieser Adapter uebersetzt in die Gegenrichtung der alten
`ollama-openai-bruecke.py`: er stellt Ollamas native Pfade bereit und leitet sie
an llama-server weiter. Der Fremd-Repo-Code bleibt damit unangetastet.

WAS ER ANBIETET
---------------
    GET  /gesundheit      -> {"ok": true|false, "llamacpp": <basis>}
    GET  /api/tags        -> {"models": [{"name": <id>}, ...]}
    GET  /api/version     -> {"version": "llama-server"}
    POST /api/chat        -> Ollama-Form; wird auf /v1/chat/completions gemappt

`think` wird angenommen und ignoriert - llama-server kennt keinen
Denk-Schalter; bei Denk-Modellen steht der Text im content-Feld (gemessen).

SCHLUESSEL
----------
llama-server verlangt `Authorization: Bearer <key>`. Der Schluessel wird aus
`Agenten/Hermes/runtimes/llamacpp/.api_key` gelesen und NIE ausgegeben oder
geloggt. Er steht nicht in dieser Datei.

AUFRUF
------
    python Agenten/Werkzeuge/llamacpp-ollama-bruecke.py            # Port 11498
    python ... --port 11498 --basis http://127.0.0.1:18434
    python ... --pruefen                                          # Selbsttest

Umgebungsvariablen: BRUECKE_PORT, LLAMACPP_BASIS (Vorgaben s. u.).
Nur stdlib. Nur localhost.
"""

from __future__ import annotations

import argparse
import json
import os
import socketserver
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent                     # Agenten/Werkzeuge
HAUS = HIER.parent.parent                                  # BrainFiles
SCHLUESSEL_DATEI = (HIER / ".." / "Hermes" / "runtimes" / "llamacpp" / ".api_key").resolve()
LOG_DATEI = (HIER / ".." / "Hermes" / "cache" / "llamacpp-ollama-bruecke.log").resolve()

VORGABE_PORT = 11498
VORGABE_BASIS = "http://127.0.0.1:18434"
FRIST_S = 180


def protokoll(text: str) -> None:
    """Zeile ins Adapterlog; ein nicht schreibbares Log darf nie stoeren."""
    try:
        LOG_DATEI.parent.mkdir(parents=True, exist_ok=True)
        with LOG_DATEI.open("a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except Exception:                                          # noqa: BLE001
        pass


def schluessel_lesen() -> str:
    return SCHLUESSEL_DATEI.read_text(encoding="utf-8").strip()


def llamacpp(basis: str, pfad: str, daten=None, frist: int = FRIST_S):
    """Aufruf am llama-server. Gibt (status, koerper) zurueck, wirft nie."""
    kopf = {"Authorization": "Bearer " + schluessel_lesen(),
            "Content-Type": "application/json"}
    anfrage = urllib.request.Request(
        basis.rstrip("/") + pfad, headers=kopf,
        data=json.dumps(daten).encode("utf-8") if daten is not None else None,
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=frist) as a:
            return a.status, json.loads(a.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rumpf = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(rumpf)
        except ValueError:
            return e.code, {"error": rumpf[:400]}
    except Exception as e:                                     # noqa: BLE001
        return 0, {"error": "%s: %s" % (type(e).__name__, e)}


def modelle(basis: str) -> list:
    status, koerper = llamacpp(basis, "/v1/models", frist=20)
    if status != 200:
        return []
    return [m.get("id") for m in (koerper.get("data") or []) if m.get("id")]


def auf_openai(koerper: dict) -> dict:
    """Ollama-Chat-Rumpf -> OpenAI-Chat-Rumpf."""
    optionen = koerper.get("options") or {}
    neu = {
        "model": koerper.get("model"),
        "messages": koerper.get("messages") or [],
    }
    if isinstance(optionen.get("temperature"), (int, float)):
        neu["temperature"] = optionen["temperature"]
    if isinstance(optionen.get("num_predict"), int) and optionen["num_predict"] > 0:
        neu["max_tokens"] = optionen["num_predict"]
    if isinstance(koerper.get("max_tokens"), int):
        neu["max_tokens"] = koerper["max_tokens"]
    # `think` gibt es bei llama-server nicht - bewusst nicht uebersetzt.
    return neu


class SchnellServer(ThreadingHTTPServer):
    """ThreadingHTTPServer ohne die umgekehrte DNS-Abfrage beim Binden.

    HTTPServer.server_bind() ruft socket.getfqdn(host). Auf diesem Rechner
    dauert das fuer 127.0.0.1 GEMESSEN 8,03 s (12.10.2026), weil Docker
    Desktop den Namen 'kubernetes.docker.internal' auf 127.0.0.1 zeigt.
    In diesen acht Sekunden ist der Socket zwar gebunden, aber noch NICHT im
    Zustand LISTEN: jeder weitere Aufrufer haelt den Port fuer frei und
    startet einen weiteren Adapter. Im Protokoll standen sechs "Start auf
    Port 11498" in derselben Sekunde, fuenf davon starben am Binden. Der Name
    wird hier nirgends gebraucht (er landet nur im Fehlertext), also wird er
    gesetzt statt erfragt. Wer einen Dienst an 127.0.0.1 bindet, sollte
    getfqdn nie im Startweg haben.
    """

    daemon_threads = True

    # WINDOWS-FALLE, der eigentliche Grund der Prozessschwemme: HTTPServer
    # setzt von Haus aus SO_REUSEADDR (allow_reuse_address = 1). Unter Unix
    # laesst das nur das Wiederverwenden eines Sockets im TIME_WAIT zu, unter
    # WINDOWS darf ein ZWEITER Prozess damit denselben Port binden - ohne
    # Fehler. Der zweite Adapter glaubte also, er sei der einzige, blieb am
    # Leben und teilte sich den Port: sechs Prozesse, alle "erfolgreich",
    # keiner beendete sich. Mit False schlaegt das Binden mit WinError 10048
    # fehl, main() faengt es und endet still - der Port bekommt genau einen
    # Besitzer. Gemessen 12.10.2026: vorher 6 Prozesse auf 11498, nachher 1.
    allow_reuse_address = False

    def server_bind(self):                                     # noqa: D102
        socketserver.TCPServer.server_bind(self)               # bindet wirklich
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    server_version = "llamacpp-ollama-bruecke/1.0"
    protokoll_version = "HTTP/1.1"

    def log_message(self, fmt, *args):                         # noqa: A003
        pass                                    # eigenes Log, kein stderr-Rauschen

    # -- Hilfen -------------------------------------------------------------
    def _sende(self, status: int, koerper: dict) -> None:
        roh = json.dumps(koerper).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    def _sende_ndjson(self, zeilen: list) -> None:
        roh = "".join(json.dumps(z) + "\n" for z in zeilen).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    def _rumpf(self) -> dict:
        laenge = int(self.headers.get("Content-Length") or 0)
        if not laenge:
            return {}
        try:
            return json.loads(self.rfile.read(laenge).decode("utf-8", "replace"))
        except ValueError:
            return {}

    @property
    def basis(self) -> str:
        return self.server.basis                            # type: ignore[attr-defined]

    # -- Wege ---------------------------------------------------------------
    def do_GET(self):                                          # noqa: N802
        pfad = self.path.split("?")[0].rstrip("/") or "/"
        if pfad == "/gesundheit":
            namen = modelle(self.basis)
            self._sende(200 if namen else 503,
                        {"ok": bool(namen), "llamacpp": self.basis,
                         "modelle": len(namen)})
            return
        if pfad == "/api/tags":
            namen = modelle(self.basis)
            if not namen:
                self._sende(503, {"error": "llama-server nicht erreichbar (%s)" % self.basis})
                return
            self._sende(200, {"models": [{"name": n, "model": n} for n in namen]})
            return
        if pfad == "/api/version":
            self._sende(200, {"version": "llama-server"})
            return
        # OpenAI-Durchlass: Verbraucher, die das OpenAI-SDK benutzen
        # (DEEPSEEK_BASE_URL), brauchen keinen eigenen Schluessel - der
        # Adapter setzt ihn. Sonst muesste das Geheimnis in jeder Agenten-
        # Umgebung stehen.
        if pfad == "/v1/models":
            namen = modelle(self.basis)
            self._sende(200, {"object": "list",
                              "data": [{"id": n, "object": "model"} for n in namen]})
            return
        self._sende(404, {"error": "unbekannter Pfad %s" % pfad})

    def do_POST(self):                                         # noqa: N802
        pfad = self.path.split("?")[0].rstrip("/") or "/"
        if pfad == "/v1/chat/completions":
            # Durchlass: unveraendert weiterreichen, nur den Schluessel setzen.
            koerper = self._rumpf()
            status, antwort = llamacpp(self.basis, "/v1/chat/completions", koerper)
            self._sende(status or 503, antwort)
            return
        if pfad != "/api/chat":
            self._sende(404, {"error": "unbekannter Pfad %s" % pfad})
            return
        koerper = self._rumpf()
        modell = koerper.get("model")
        daten = auf_openai(koerper)
        status, antwort = llamacpp(self.basis, "/v1/chat/completions", daten)

        if status != 200:
            meldung = (antwort.get("error") or {})
            if isinstance(meldung, dict):
                meldung = meldung.get("message") or json.dumps(meldung)
            protokoll("FEHLER %s (Modell %s): %s" % (status, modell, str(meldung)[:200]))
            self._sende(status or 503,
                        {"error": "llama-server: %s" % str(meldung)[:300]})
            return

        wahl = (antwort.get("choices") or [{}])[0]
        inhalt = (wahl.get("message") or {}).get("content") or ""
        ziel = wahl.get("finish_reason")
        nutzung = antwort.get("usage") or {}

        if koerper.get("stream"):
            # Ollama-Streamform als NDJSON - in einem Stueck, weil die Agenten
            # ohne stream arbeiten und nur die Endform brauchen.
            self._sende_ndjson([
                {"model": modell, "message": {"role": "assistant", "content": inhalt},
                 "done": False},
                {"model": modell, "done": True, "done_reason": ziel,
                 "prompt_eval_count": nutzung.get("prompt_tokens", 0),
                 "eval_count": nutzung.get("completion_tokens", 0)},
            ])
            return

        self._sende(200, {
            "model": modell,
            "message": {"role": "assistant", "content": inhalt},
            "done": True, "done_reason": ziel,
            "prompt_eval_count": nutzung.get("prompt_tokens", 0),
            "eval_count": nutzung.get("completion_tokens", 0),
        })


def selbsttest(basis: str) -> int:
    print("=== Selbsttest gegen %s ===" % basis)
    try:
        k = schluessel_lesen()
        print("  Schluessel gelesen: %d Zeichen (Wert nicht ausgegeben)" % len(k))
    except Exception as e:                                     # noqa: BLE001
        print("  SCHLUESSEL FEHLT: %s -> %s" % (SCHLUESSEL_DATEI, e))
        return 1
    namen = modelle(basis)
    print("  Modelle: %d" % len(namen))
    for n in namen[:5]:
        print("    %s" % n)
    if not namen:
        print("  llama-server nicht erreichbar - laeuft er auf %s?" % basis)
        return 1
    ziel = namen[0]
    status, antwort = llamacpp(basis, "/v1/chat/completions", {
        "model": ziel,
        "messages": [{"role": "user", "content": "Antworte mit genau: OK"}],
        "max_tokens": 200,
    })
    inhalt = ((antwort.get("choices") or [{}])[0].get("message") or {}).get("content")
    print("  Chat mit %s: HTTP %s  content=%r" % (ziel, status, inhalt))
    return 0 if status == 200 and inhalt else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("BRUECKE_PORT") or VORGABE_PORT))
    ap.add_argument("--basis",
                    default=os.environ.get("LLAMACPP_BASIS") or VORGABE_BASIS)
    ap.add_argument("--pruefen", action="store_true",
                    help="nur Selbsttest, keinen Server starten")
    args = ap.parse_args(argv)

    if args.pruefen:
        return selbsttest(args.basis)

    try:
        schluessel_lesen()
    except Exception as e:                                     # noqa: BLE001
        print("ABBRUCH: Schluessel nicht lesbar (%s): %s" % (SCHLUESSEL_DATEI, e),
              file=sys.stderr)
        return 2

    # ERST binden, dann die Gegenstelle fragen. Umgekehrt (Fassung vom
    # 12.10.2026, vormittags) lag zwischen dem Start und dem Binden ein
    # Fenster, in dem modelle() auf llama-server wartete: jeder weitere
    # Aufrufer sah den Port als FREI und startete einen weiteren Adapter.
    # Im Log standen sechs "Start auf Port 11498" in derselben Sekunde,
    # fuenf davon starben am Binden. Wer zuerst bindet, ist der Einzige.
    try:
        server = SchnellServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        # Belegt = es laeuft schon einer. Das ist kein Fehler, sondern der
        # Normalfall bei mehreren Aufrufern; still und mit 0 enden, damit
        # keine Wache einen "Fehlschlag" meldet und neu startet.
        print("Port %d ist belegt (%s) - es laeuft schon ein Adapter. Ende."
              % (args.port, e), file=sys.stderr)
        return 0
    server.basis = args.basis                                  # type: ignore[attr-defined]

    namen = modelle(args.basis)
    protokoll("Start auf Port %d -> %s (%d Modelle)"
              % (args.port, args.basis, len(namen)))
    if not namen:
        # NICHT beenden: eine tote Gegenstelle ist kein Grund, den Dienst
        # abzuschalten. Wer sich hier beendet, gibt den Port frei und laesst
        # jeden Aufrufer einen neuen Prozess starten - die Schwemme.
        print("WARNUNG: llama-server auf %s antwortet nicht - der Adapter "
              "laeuft weiter und meldet /gesundheit als false." % args.basis,
              file=sys.stderr)
    print("Ollama-Schnittstelle auf http://127.0.0.1:%d  ->  %s"
          % (args.port, args.basis))
    print("  /gesundheit  /api/tags  /api/version  POST /api/chat")
    print("  Log: %s" % LOG_DATEI)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        protokoll("beendet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
