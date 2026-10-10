"""OmniRoute-Waechter: lauscht der Router noch auf seinem Port?

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur, wenn
der Router nicht lauscht - dann steht der Befund in der Nachricht.

WARUM UEBERHAUPT
----------------
Am 16.09.2026 lag der Router von 10:39 bis 16:04 still - 5,5 Stunden, ohne dass
es jemandem auffiel. Der Start-Eintrag der Aufgabe sah dabei harmlos aus (Code
267014 = von aussen beendet). Festgestellt hat es erst eine Sitzung, die den
Port zufaellig antippte. An OmniRoute haengen die Agenten-Delegationen; faellt er
aus, scheitern sie still.

WARUM ALS CRON UND NICHT ALS BUS-ROUTINE
----------------------------------------
Dieselbe Bauart wie bei der Bus-Wache: der Meldeweg darf nicht der ueberwachte
Weg sein. Der Hermes-Scheduler laeuft am Router vorbei und liefert direkt.

WAS ES TUT
----------
1. Port aus dem Wrapper `Agenten/Routinen/omniroute-start.ps1` lesen (nicht hart
   verdrahten - eine zweite Zahl waere eine zweite Wahrheit und faellt erst auf,
   wenn jemand den Port umzieht).
2. TCP-Verbindung auf 127.0.0.1:<port> - offen: fertig, keine Ausgabe.
3. Zu: Zustand der Aufgabe holen, den Wrapper starten (er startet losgeloest und
   wartet selbst auf den Port), nachmessen und den Befund ausgeben.
4. Nichts loeschen, nichts schreiben ausser ueber den Wrapper, kein Netz ausser
   localhost.

Aufruf:
    python Agenten/Hermes/scripts/omniroute-waechter.py            # echter Waechter
    python Agenten/Hermes/scripts/omniroute-waechter.py --port 9999 --nicht-starten
        -> Alarm-Richtung pruefen, ohne den echten Router anzufassen
"""
import argparse
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts/ -> BrainFiles
WRAPPER = WURZEL / "Agenten" / "Routinen" / "omniroute-start.ps1"
PROTOKOLL = WURZEL / "Agenten" / "Routinen" / "logs" / "omniroute-letzter-lauf.log"
AUFGABE = "MaxHirn-OmniRoute"


def port_aus_wrapper(standard=20128):
    """Der Port steht im Wrapper - dort, wo auch der Start ihn hernimmt."""
    try:
        text = WRAPPER.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return standard
    m = re.search(r"^\s*\$port\s*=\s*(\d+)", text, re.M)
    return int(m.group(1)) if m else standard


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
    """(State, LastTaskResult, LastRunTime) oder (None, Begruendung)."""
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


def starten(frist=660):
    """Den Wrapper aufrufen. Er startet den Router losgeloest und wartet selbst
    auf den Port - hier darf deshalb gewartet werden (Rueckkehr = Befund)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", str(WRAPPER)],
                           capture_output=True, text=True, timeout=frist, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        return "Startversuch nach %d s abgebrochen (Wrapper antwortet nicht)." % frist
    except (OSError, subprocess.SubprocessError) as e:
        return "Startversuch fehlgeschlagen: %s" % e
    if r.returncode == 0:
        return "Startversuch: Wrapper meldet Erfolg (Exit 0)."
    return "Startversuch Exit %d: %s" % (r.returncode, (r.stderr or "").strip()[:200])


def protokoll_ende(zeilen=8):
    try:
        text = PROTOKOLL.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return ["Protokoll: " + z for z in text.strip().splitlines()[-zeilen:]]


def main():
    ap = argparse.ArgumentParser(
        description="OmniRoute-Waechter (lautlos, solange der Router laeuft)")
    ap.add_argument("--port", type=int, default=None,
                    help="abweichender Port (nur zum Pruefen der Alarmrichtung)")
    ap.add_argument("--nicht-starten", action="store_true",
                    help="nur melden, den Router nicht starten")
    ap.add_argument("--warten", type=int, default=30,
                    help="Sekunden bis zur Nachmessung nach dem Start")
    args = ap.parse_args()

    port = args.port or port_aus_wrapper()

    if lauscht(port):
        return 0                                  # lautlos: alles gut

    zeilen = ["OmniRoute-Waechter: Port %d antwortet nicht (kein Lauscher)." % port]
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
        zeilen.append("Nachgemessen: Port %d ist offen - geheilt." % port)
        zeilen.extend(protokoll_ende())
    else:
        zeilen.append("Nach %d s immer noch kein Lauscher auf Port %d - der Router "
                      "kommt nicht hoch." % (args.warten, port))
        zeilen.extend(protokoll_ende(15))
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
