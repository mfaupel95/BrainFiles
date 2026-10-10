"""Gateway-Ausfall-Wache: meldet, wenn der A2A-Gateway laenger weg war.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster, siehe bus-waechter.py).
Der Hermes-Scheduler laeuft am Gateway vorbei und liefert direkt nach Telegram.

WARUM ES DIESE WACHE GIBT
-------------------------
Am 19.09.2026 startete der Gateway 126-mal neu (Neustart-Schleife, rund 90 s
Ausfall je Mal). Die Luecken fielen nur als fehlgeschlagene Auftraege auf
("(Aufgabe FAILED)" im SkillsBot) - niemand sah, WIE LANGE der Dienst weg war.
Der Windows-Waechter (Aufgabe MaxHirn-Gateway-Waechter, alle 2 min) startet den
Gateway neu; DIESE Wache misst die DAUER und meldet sie. Sie ist bewusst ein
zweiter Zutritt: stirbt der Windows-Waechter selbst, merkt es hier trotzdem
jemand - die Aufgabe wird im Befund mitgenannt.

WAS ES TUT
----------
1. TCP-Verbindung auf 127.0.0.1:9900 - der A2A-Port ist die Wahrheit.
2. Offen: lief eine Ausfallzeit? Dauer rechnen, ab der Schwelle melden
   (Erholung samt Dauer), darunter lautlos. Zustand danach loeschen.
3. Zu: Ausfallbeginn merken; ab der Schwelle einmal melden (kein Spam).
4. Nichts loeschen ausser dem eigenen Zustand, kein Netz ausser localhost.

Aufruf:
    python Agenten/Hermes/scripts/gateway-ausfall-wache.py
    python Agenten/Hermes/scripts/gateway-ausfall-wache.py --port 9999 \
        --stand <pfad> --schwelle 1
        -> Alarmrichtung pruefen, ohne den echten Gateway zu beruehren
"""
import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts/ -> BrainFiles
STAND = WURZEL / "Agenten" / "Hermes" / "cache" / "gateway-wache-stand.json"
AUFGABE = "MaxHirn-Gateway-Waechter"
PORT = 9900
SCHWELLE_S = 300                            # 5 Minuten


def lauscht(port, timeout=3.0):
    """Eine TCP-Verbindung genuegt: offen heisst der Dienst lebt."""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def zustand_lesen(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def zustand_schreiben(pfad, d):
    try:
        pfad = Path(pfad)          # --stand kommt als String, STAND als Path
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except OSError:
        pass


def zustand_loeschen(pfad):
    try:
        Path(pfad).unlink()
    except OSError:
        pass


def waechter_zustand():
    """(State, LastTaskResult, letzter Lauf) der Windows-Aufgabe - oder None.

    Nur fuer den Befund aufgerufen, nicht im Normalfall: ein PowerShell-Aufruf
    kostet Sekunden, und der lautlose Weg soll schnell bleiben.
    """
    ps = ("$t = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
          "if ($t) { $i = $t | Get-ScheduledTaskInfo; "
          "'{0}|{1}|{2}' -f $t.State, $i.LastTaskResult, "
          "$i.LastRunTime.ToString('yyyy-MM-dd HH:mm:ss') }" % AUFGABE)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    aus = (r.stdout or "").strip()
    return aus.split("|") if "|" in aus else None


def dauer_minuten(seit_iso, jetzt):
    try:
        return (jetzt - datetime.fromisoformat(seit_iso)).total_seconds() / 60.0
    except (TypeError, ValueError):
        return None


def befunde_zusatz(zeilen):
    """Was im Befund nicht fehlen darf: lebt der Windows-Waechter noch?"""
    z = waechter_zustand()
    if z:
        zeilen.append("Windows-Aufgabe %s: State=%s, LastTaskResult=%s, "
                      "letzter Lauf %s" % (AUFGABE, z[0], z[1], z[2]))
    else:
        zeilen.append("Windows-Aufgabe %s nicht lesbar - wer startet den "
                      "Gateway dann neu?" % AUFGABE)


def main():
    ap = argparse.ArgumentParser(
        description="Gateway-Ausfall-Wache (lautlos, solange der Gateway laeuft)")
    ap.add_argument("--port", type=int, default=PORT,
                    help="A2A-Port (Standard 9900)")
    ap.add_argument("--stand", default=str(STAND),
                    help="Zustandsdatei fuer den Ausfallbeginn")
    ap.add_argument("--schwelle", type=int, default=SCHWELLE_S,
                    help="Sekunden Ausfall, ab denen gemeldet wird")
    a = ap.parse_args()

    jetzt = datetime.now()
    z = zustand_lesen(a.stand)
    if lauscht(a.port):
        # Lief ein Ausfall? Nur ab der Schwelle ist er eine Meldung wert -
        # ein Neustart von zwei Minuten ist Betrieb, kein Befund.
        seit = z.get("seit")
        if seit:
            dauer = dauer_minuten(seit, jetzt)
            zustand_loeschen(a.stand)
            if dauer is not None and dauer * 60 >= a.schwelle:
                zeilen = ["Gateway war %.1f min weg (Port %d), jetzt wieder offen."
                          % (dauer, a.port)]
                befunde_zusatz(zeilen)
                print("\n".join(zeilen))
        return 0

    # Port zu: Ausfallbeginn merken, ab der Schwelle einmal melden.
    if not z.get("seit"):
        zustand_schreiben(a.stand, {"seit": jetzt.isoformat(), "gemeldet": False})
        return 0
    dauer = dauer_minuten(z["seit"], jetzt)
    if dauer is None:
        zustand_schreiben(a.stand, {"seit": jetzt.isoformat(), "gemeldet": False})
        return 0
    if dauer * 60 >= a.schwelle and not z.get("gemeldet"):
        z["gemeldet"] = True
        zustand_schreiben(a.stand, z)
        zeilen = ["Gateway-Ausfall: Port %d antwortet seit %.1f min nicht "
                  "(seit %s)." % (a.port, dauer, z["seit"])]
        befunde_zusatz(zeilen)
        zeilen.append("Der Windows-Waechter startet ihn alle 2 min neu; bleibt "
                      "der Port zu, kommt der Gateway nicht hoch - Startprotokoll "
                      "pruefen: Agenten/Hermes/logs/gateway.log")
        print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())