"""Bus-Waechter: lauscht der Telegram-Bus noch?

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur, wenn
der Bus nicht lauscht - dann steht der Befund in der Nachricht.

WARUM ALS CRON UND NICHT ALS BUS-ROUTINE
----------------------------------------
Eine Wache, die ihren Befund ueber den Bus meldet, schweigt genau dann, wenn
der Bus tot ist. Vom 11.09.2026 21:13 bis 15.09.2026 21:02 war der Bus aus -
vier Tage lang blieben alle `Melde-Ende`-Zeilen der Routinen im Journal liegen,
und niemand hat es gesehen, weil der einzige Meldeweg mit ausgefallen war. Der
Hermes-Scheduler laeuft am Bus vorbei und liefert direkt nach Telegram.

WAS ES TUT
----------
1. Port aus `Agenten/Bus/bus.json` lesen (nicht hart verdrahten).
2. TCP-Verbindung auf 127.0.0.1:<port> - offen: fertig, keine Ausgabe.
3. Zu: Zustand der Aufgabe holen, `Start-ScheduledTask` versuchen, nachmessen
   und den Befund ausgeben (geheilt oder nicht).
4. Nichts loeschen, nichts schreiben, kein Netz ausser localhost.

Aufruf:
    python Agenten/Hermes/scripts/bus-waechter.py            # echter Waechter
    python Agenten/Hermes/scripts/bus-waechter.py --port 9999 --nicht-starten
        -> Alarm-Richtung pruefen, ohne den echten Bus anzufassen
"""
import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts/ -> BrainFiles
BUS_JSON = WURZEL / "Agenten" / "Bus" / "bus.json"
AUFGABE = "BrainFiles-Bus"


def port_aus_config(standard=8787):
    """Der Port steht in bus.json - eine zweite Zahl hier waere eine zweite
    Wahrheit und faellt erst auf, wenn jemand den Bus umzieht."""
    try:
        with open(BUS_JSON, encoding="utf-8") as f:
            return int(json.load(f).get("port") or standard)
    except (OSError, ValueError, TypeError):
        return standard


def lauscht(port, timeout=3.0):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def aufgaben_zustand():
    """(State, LastTaskResult, LastRunTime) oder None."""
    ps = ("$t = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
          "if ($t) { $i = $t | Get-ScheduledTaskInfo; "
          "'{0}|{1}|{2}' -f $t.State, $i.LastTaskResult, "
          "$i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss') }" % AUFGABE)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return None, "Zustand nicht lesbar: %s" % e
    aus = (r.stdout or "").strip()
    if "|" not in aus:
        return None, "Aufgabe %s nicht gefunden" % AUFGABE
    state, code, zuletzt = (aus.split("|") + ["", "", ""])[:3]
    return (state, code, zuletzt), None


def starten():
    ps = "Start-ScheduledTask -TaskName '%s'" % AUFGABE
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return "Startversuch fehlgeschlagen: %s" % e
    if r.returncode != 0:
        return "Startversuch Exit %d: %s" % (r.returncode,
                                             (r.stderr or "").strip()[:160])
    return "Startversuch abgesetzt"


def main():
    ap = argparse.ArgumentParser(description="Bus-Waechter (lautlos, solange der Bus laeuft)")
    ap.add_argument("--port", type=int, default=None,
                    help="abweichender Port (nur zum Pruefen der Alarmrichtung)")
    ap.add_argument("--nicht-starten", action="store_true",
                    help="nur melden, den Bus nicht zu starten")
    ap.add_argument("--warten", type=int, default=20,
                    help="Sekunden bis zur Nachmessung nach dem Start")
    args = ap.parse_args()

    port = args.port or port_aus_config()

    if lauscht(port):
        return 0                                  # lautlos: alles gut

    # Ab hier ist der Bus nicht erreichbar -> Befund bauen
    zeilen = ["Bus-Waechter: Port %d antwortet nicht (kein Lauscher)." % port]
    zustand, fehler = aufgaben_zustand()
    if zustand:
        state, code, zuletzt = zustand
        zeilen.append("Aufgabe %s: State=%s, LastTaskResult=%s, letzter Lauf %s"
                      % (AUFGABE, state, code, zuletzt))
        if code not in ("0", ""):
            zeilen.append("  (267014/1073807364 = von aussen beendet, "
                          "0x800710E0 = laeuft schon - nicht jeder Code ist ein Fehler)")
    elif fehler:
        zeilen.append(fehler)

    if args.nicht_starten:
        zeilen.append("Start unterlassen (--nicht-starten): Pruefung der Alarmrichtung.")
        print("\n".join(zeilen))
        return 0

    zeilen.append(starten())
    zeit = time.time()
    geheilt = False
    while time.time() - zeit < args.warten:
        time.sleep(2)
        if lauscht(port):
            geheilt = True
            break
    if geheilt:
        zeilen.append("Nachgemessen nach %d s: Port %d ist offen - geheilt."
                      % (int(time.time() - zeit), port))
        zeilen.append("Der Bus holt jetzt das Journal des Tages nach; ein Schwall "
                      "alter Meldungen ist der Rueckstand, kein neuer Fehler.")
    else:
        zeilen.append("Nach %d s immer noch kein Lauscher auf Port %d - "
                      "der Bus kommt nicht hoch. Startprotokoll: "
                      "Agenten/Bus/*.log" % (args.warten, port))
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
