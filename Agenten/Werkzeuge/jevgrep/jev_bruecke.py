"""Ein eigener TypeSafe-kompatibler Endpunkt fuer jevgrep - mit beliebigem Modell.

Warum: jevgrep fragt kein Chat-Modell, sondern einen **Richter**: es schickt einen
Zustand (Quelltext-Kontext) und mehrere typisierte Fragen und erwartet je Frage einen
Wert zwischen 0 und 1. Der Anbieter (Jev) kann ausfallen, rate-limitiert sein oder Geld
kosten. Diese Bruecke nimmt jevgrep-Anfragen an und beantwortet sie ueber ein
**OpenAI-kompatibles** Modell der Wahl - Inception Mercury 2.5, das Nous-Portal,
OmniRoute oder ein lokales Ollama.

Vertrag (aus der jevgrep-Dokumentation):

    POST <basis>/systemone
    {"model":"...","state":"<Quelltext>","questions":{"q":{"type":"noul","instructions":"Relevant?"}}}
    -> {"answers":{"q":{"type":"noul","noul":0.9}}}

    Fuer JEDE Frage-ID muss eine endliche Zahl zwischen 0 und 1 zurueckkommen;
    `probabilities`/`confidence` sind nicht noetig, `criteria` wird nicht verlangt.

Konfiguration ueber Umgebungsvariablen:

    JEVCREP_BRUECKE_PORT       Standard 8742
    JEVCREP_BRUECKE_BASIS      Standard http://127.0.0.1:11434/v1  (lokales Ollama)
    JEVCREP_BRUECKE_MODELL     Standard qwen35-8k:latest
    JEVCREP_BRUECKE_SCHLUESSEL optional (Bearer)
    JEVCREP_BRUECKE_FRIST      Sekunden je Modellaufruf, Standard 120
    JEVCREP_BRUECKE_MITDENKEN  "1" schaltet reasoning/think ab (Standard 0 = aus)

Start:  python jev_bruecke.py            (laeuft bis Strg-C)
Probe:  curl http://127.0.0.1:8742/gesundheit
Anmelden bei jevgrep (einmalig):
    .\\jevgrep.cmd auth --provider custom --base-url http://127.0.0.1:8742/v1 --model bruecke --stdin
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HIER = Path(__file__).resolve().parent
PROTOKOLL = Path(os.environ.get(
    "JEVCREP_BRUECKE_PROTOKOLL",
    str(HIER.parents[1] / "Hermes" / "cache" / "jev-bruecke.log"),
))
PORT = int(os.environ.get("JEVCREP_BRUECKE_PORT", "8742"))
BASIS = os.environ.get("JEVCREP_BRUECKE_BASIS", "http://127.0.0.1:11434/v1").rstrip("/")
MODELL = os.environ.get("JEVCREP_BRUECKE_MODEL") or os.environ.get(
    "JEVCREP_BRUECKE_MODELL", "gemma-e4b-8k-64k:latest")
SCHLUESSEL = os.environ.get("JEVCREP_BRUECKE_SCHLUESSEL", "")
FRIST = float(os.environ.get("JEVCREP_BRUECKE_FRIST", "120"))
OHNE_DENKEN = os.environ.get("JEVCREP_BRUECKE_MITDENKEN", "0") != "1"

# Welche Windows-Variable gehoert zu welchem Anbieter? Wird gebraucht, damit ein
# frisch gesetztes `setx` auch ohne neue Anmeldung wirkt und der Wert nie in einer
# Kommandozeile steht.
SCHLUESSEL_JE_HOST = (
    ("inceptionlabs", "INCEPTION_API_KEY"),
    ("opencode.ai", "OPENCODE_API_KEY"),
)


def _aus_registry(name: str) -> str | None:
    try:
        import winreg
    except ImportError:
        return None
    for wurzel in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(wurzel, "Environment") as k:
                wert, _ = winreg.QueryValueEx(k, name)
        except OSError:
            continue
        if isinstance(wert, str) and wert.strip():
            return wert.strip()
    return None


def schluessel_fuer(basis: str) -> str:
    """Den passenden Schluessel holen: erst Prozessumgebung, dann Registry."""
    for host, name in SCHLUESSEL_JE_HOST:
        if host in basis:
            wert = os.environ.get(name) or _aus_registry(name)
            if wert:
                return wert
    return ""


SCHLUESSEL = SCHLUESSEL or schluessel_fuer(BASIS)

ANWEISUNG = (
    "Du bist ein Relevanz-Richter fuer Quelltext. Du bekommst einen ZUSTAND "
    "(Quelltextausschnitte) und mehrere FRAGEN mit Kennungen. Beantworte jede Frage "
    "einzeln: Wie wahrscheinlich ist es, dass dieser Zustand fuer die Frage relevant "
    "ist? Antworte AUSSCHLIESSLICH mit JSON in genau dieser Form, ohne Erklaerung, "
    "ohne Marken:\n"
    '{"answers": {"<kennung>": 0.0}}\n'
    "Zahlen zwischen 0.0 (nicht relevant) und 1.0 (eindeutig relevant). "
    "Jede uebergebene Kennung muss vorkommen."
)


def _zahl(wert) -> float | None:
    """Aus einem Modellwert eine Zahl zwischen 0 und 1 machen, sonst None."""
    if isinstance(wert, bool):
        return 1.0 if wert else 0.0
    if isinstance(wert, (int, float)):
        return min(1.0, max(0.0, float(wert)))
    if isinstance(wert, str):
        treffer = re.findall(r"-?\d+(?:[.,]\d+)?", wert)
        if treffer:
            z = float(treffer[0].replace(",", "."))
            if z > 1.0 and z <= 100.0:      # 0-100-Skala mitgedacht
                z = z / 100.0
            return min(1.0, max(0.0, z))
    if isinstance(wert, dict):
        for feld in ("noul", "score", "value", "answer", "relevanz", "relevance"):
            if feld in wert:
                return _zahl(wert[feld])
    return None


def aus_text(text: str, kennungen: list[str]) -> dict[str, float]:
    """Notnagel: keine JSON-Antwort, aber Kennung und Zahl stehen im Fliesstext."""
    ergebnis: dict[str, float] = {}
    for k in kennungen:
        treffer = re.search(
            re.escape(k) + r"[^\d\-]{0,60}(-?\d+(?:[.,]\d+)?)", text)
        if not treffer:
            continue
        z = float(treffer.group(1).replace(",", "."))
        if 1.0 < z <= 100.0:
            z = z / 100.0
        ergebnis[k] = min(1.0, max(0.0, z))
    return ergebnis


def antworten_lesen(text: str, kennungen: list[str]) -> dict[str, float]:
    """Die Modellantwort auswerten. Fehlende Kennungen kommen nicht zurueck."""
    roh = text.strip()
    if roh.startswith("```"):
        roh = re.sub(r"^```[a-zA-Z]*\s*", "", roh)
        roh = re.sub(r"```\s*$", "", roh).strip()
    daten = None
    for versuch in (roh, roh[roh.find("{"):roh.rfind("}") + 1] if "{" in roh else ""):
        if not versuch:
            continue
        try:
            daten = json.loads(versuch)
            break
        except ValueError:
            continue
    if daten is None:
        return aus_text(text, kennungen)
    if isinstance(daten, dict) and isinstance(daten.get("answers"), dict):
        daten = daten["answers"]
    if not isinstance(daten, dict):
        return {}
    ergebnis: dict[str, float] = {}
    for k in kennungen:
        if k in daten:
            z = _zahl(daten[k])
            if z is not None:
                ergebnis[k] = z
    return ergebnis


def modell_fragen(zustand: str, fragen: dict) -> dict[str, float]:
    """Eine Runde an das OpenAI-kompatible Modell. Rueckgabe: {kennung: zahl}."""
    kennungen = [str(k) for k in (fragen or {})]
    if not kennungen:
        return {}
    frage_text = "\n".join(
        "- %s: %s" % (k, (fragen[k] or {}).get("instructions") or "Relevant?")
        for k in kennungen
    )
    nutzer = "ZUSTAND:\n%s\n\nFRAGEN:\n%s\n\nAntworte mit JSON." % (zustand, frage_text)
    koerper = {
        "model": MODELL,
        "messages": [
            {"role": "system", "content": ANWEISUNG},
            {"role": "user", "content": nutzer},
        ],
        "temperature": 0,
        "stream": False,
    }
    if OHNE_DENKEN:
        koerper["think"] = False          # Ollama: Denken aus, sonst leerer Inhalt
        koerper["reasoning_effort"] = "none"
    kopf = {"content-type": "application/json"}
    if SCHLUESSEL:
        kopf["authorization"] = "Bearer " + SCHLUESSEL
    req = urllib.request.Request(
        BASIS + "/chat/completions", data=json.dumps(koerper).encode("utf-8"),
        headers=kopf, method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=FRIST) as r:
            antwort = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return {"_fehler": "HTTP %s %s" % (e.code, e.read().decode("utf-8", "replace")[:200])}
    except Exception as e:                                      # noqa: BLE001
        return {"_fehler": "%s: %s" % (type(e).__name__, e)}
    dauer = time.time() - t0
    try:
        inhalt = antwort["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return {"_fehler": "unerwartete Antwortform"}
    werte = antworten_lesen(inhalt, kennungen)
    werte["_dauer"] = round(dauer, 2)
    return werte


def protokoll(zeile: dict) -> None:
    try:
        PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
        with PROTOKOLL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass


class Bruecke(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _sende(self, code: int, daten: dict) -> None:
        roh = json.dumps(daten).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    def _pfad(self) -> str:
        """Der Pfad ohne Abfragezeichenkette; jevgrep haengt /systemone an die Basis an."""
        return self.path.split("?", 1)[0].rstrip("/")

    def do_GET(self):                                           # noqa: N802
        if self._pfad().endswith("/gesundheit"):
            self._sende(200, {"ok": True, "modell": MODELL, "basis": BASIS,
                              "denken_aus": OHNE_DENKEN})
        else:
            self._sende(404, {"fehler": "unbekannter Pfad", "pfad": self.path})

    def do_POST(self):                                          # noqa: N802
        if not self._pfad().endswith("/systemone"):
            self._sende(404, {"fehler": "unbekannter Pfad", "pfad": self.path})
            return
        laenge = int(self.headers.get("content-length", "0"))
        try:
            anfrage = json.loads(self.rfile.read(laenge).decode("utf-8", "replace"))
        except ValueError:
            self._sende(400, {"fehler": "kein JSON"})
            return
        zustand = str(anfrage.get("state") or "")
        fragen = anfrage.get("questions") or {}
        t0 = time.time()
        werte = modell_fragen(zustand, fragen)
        fehler = werte.pop("_fehler", None)
        dauer_modell = werte.pop("_dauer", None)

        # Fehlende Kennungen: EINMAL nachfassen, danach 0.0 (nie 5xx an jevgrep).
        fehlend = [k for k in fragen if k not in werte]
        nachgefasst = False
        if fehlend and not fehler:
            nachgefasst = True
            zweite = modell_fragen(zustand, {k: fragen[k] for k in fehlend})
            zweite.pop("_fehler", None)
            zweite.pop("_dauer", None)
            werte.update(zweite)

        # Achtung, stille Falle: ein zu kleines Kontextfenster laesst das Modell
        # NICHTS antworten - dann waeren alle Dateien "nicht relevant". Das muss
        # sichtbar sein, nicht in 0.0 verschwinden.
        if not werte and not fehler:
            fehler = "leere Modellantwort - passt der Zustand (%d Zeichen) ins Kontextfenster von %s?" % (
                len(zustand), MODELL)
            print("WARNUNG: %s" % fehler, flush=True)

        antworten = {}
        for k, frage in (fragen or {}).items():
            art = (frage or {}).get("type") or "noul"
            z = werte.get(k, 0.0)
            if art == "score":
                antworten[k] = {"type": "score", "score": z}
            elif art == "choice":
                moeglich = (frage or {}).get("choices") or (frage or {}).get("options") or []
                antworten[k] = {"type": "choice",
                                "choice": (moeglich[0] if moeglich else None),
                                "confidence": z}
            else:
                antworten[k] = {"type": "noul", "noul": z}

        protokoll({
            "zeit": time.strftime("%Y-%m-%d %H:%M:%S"),
            "zustand_zeichen": len(zustand),
            "fragen": len(fragen),
            "beantwortet": len(werte),
            "nachgefasst": nachgefasst,
            "dauer_modell_s": dauer_modell,
            "dauer_gesamt_s": round(time.time() - t0, 2),
            "fehler": fehler,
        })
        self._sende(200, {"answers": antworten})

    def log_message(self, *a):
        pass


def main() -> int:
    print("jev-Bruecke auf 127.0.0.1:%d" % PORT)
    print("  Modell: %s" % MODELL)
    print("  Basis:  %s" % BASIS)
    print("  Protokoll: %s" % PROTOKOLL)
    print("  Anmelden: .\\jevgrep.cmd auth --provider custom "
          "--base-url http://127.0.0.1:%d/v1 --model bruecke --stdin" % PORT)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Bruecke)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbeendet")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())