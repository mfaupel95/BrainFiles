"""Wache fuer die OpenAI-Bruecke auf Ollama (Agenten/Werkzeuge/ollama-openai-bruecke.py).

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur, wenn
die Bruecke nicht antwortet - dann wird sie gestartet, nachgemessen und der
Befund gemeldet.

WARUM UEBERHAUPT EINE WACHE
---------------------------
Fremd-Agenten (moon-dev-ai-agents) holen ihre Sprachmodell-Antwort ueber diese
Bruecke, wenn kein bezahlter Schluessel da ist. Faellt sie aus, antwortet kein
Agent mehr - und zwar STILL: die Agenten schreiben dann Fehlertexte statt
Urteilen in ihre Logs. Ein Dienst ohne Wache faellt genau dann aus, wenn ihn
niemand braucht (Lehre vom Bus, 11.-15.09.2026: vier Tage aus, kein Alarm).

WAS ES TUT
----------
1. GET /gesundheit auf 127.0.0.1:<port> - antwortet sie mit ok:true: fertig.
2. Sonst: Prozess abgesetzt starten (DETACHED, eigener Prozessgruppe), Log nach
   Agenten/Hermes/cache/ollama-openai-bruecke.out.
3. Nachmessen bis 30 s. Ergebnis melden (geheilt oder nicht).
4. Nichts loeschen, nichts ueberschreiben, kein Netz ausser localhost.

Aufruf:
    python Agenten/Hermes/scripts/ollama-bruecke-wache.py
    python ... --port 11498 --nicht-starten     # Alarmrichtung pruefen
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                                   # BrainFiles
WERKZEUG = WURZEL / "Agenten" / "Werkzeuge" / "ollama-openai-bruecke.py"
LOG = WURZEL / "Agenten" / "Hermes" / "cache" / "ollama-openai-bruecke.out"
STANDARD_PORT = 11499


def gesund(port, frist=6.0):
    """(ok, text) - ok ist True nur bei ok:true von der Bruecke."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/gesundheit" % port, timeout=frist) as a:
            daten = json.loads(a.read().decode("utf-8", "replace"))
        return bool(daten.get("ok")), json.dumps(daten, ensure_ascii=False)
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code
    except Exception as e:
        return False, str(e)


def starten(port):
    """Bruecke abgesetzt starten; gibt eine Meldung zurueck."""
    umgebung = {k: v for k, v in os.environ.items()
                if k not in ("PYTHONHOME", "PYTHONPATH")}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | \
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    try:
        with LOG.open("ab") as log:
            log.write(("\n--- Start durch Wache %s ---\n"
                       % time.strftime("%Y-%m-%d %H:%M:%S")).encode("utf-8"))
            prozess = subprocess.Popen(
                [sys.executable, str(WERKZEUG), "--port", str(port)],
                stdout=log, stderr=subprocess.STDOUT,
                cwd=str(WURZEL), env=umgebung, creationflags=flags, close_fds=True)
        return "Startversuch abgesetzt (PID %d)" % prozess.pid
    except Exception as e:
        return "Startversuch fehlgeschlagen: %s" % e


def main():
    ap = argparse.ArgumentParser(description="Wache fuer die Ollama-Bruecke (lautlos, solange sie laeuft)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("BRUECKE_PORT") or STANDARD_PORT))
    ap.add_argument("--nicht-starten", action="store_true",
                    help="nur melden, die Bruecke nicht starten")
    ap.add_argument("--warten", type=int, default=30, help="Sekunden bis zur Nachmessung")
    args = ap.parse_args()

    ok, text = gesund(args.port)
    if ok:
        return 0                                   # lautlos: alles gut

    zeilen = ["Ollama-Bruecke antwortet nicht auf Port %d (%s)." % (args.port, text[:200])]
    if args.nicht_starten:
        zeilen.append("Start unterlassen (--nicht-starten): Pruefung der Alarmrichtung.")
        print("\n".join(zeilen))
        return 0

    if not WERKZEUG.exists():
        zeilen.append("Werkzeug fehlt: %s" % WERKZEUG)
        print("\n".join(zeilen))
        return 1

    zeilen.append(starten(args.port))
    start = time.time()
    geheilt = False
    while time.time() - start < args.warten:
        time.sleep(3)
        ok, _ = gesund(args.port, frist=4.0)
        if ok:
            geheilt = True
            break
    if geheilt:
        zeilen.append("Nachgemessen nach %d s: Port %d antwortet - geheilt."
                      % (int(time.time() - start), args.port))
        zeilen.append("Sprachmodell-Aufrufe der Fremd-Agenten laufen wieder lokal "
                      "ueber die Bruecke (think:false).")
    else:
        zeilen.append("Nach %d s antwortet Port %d immer noch nicht - die Fremd-Agenten "
                      "bekommen keine Urteile. Protokoll: %s"
                      % (args.warten, args.port, LOG))
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())