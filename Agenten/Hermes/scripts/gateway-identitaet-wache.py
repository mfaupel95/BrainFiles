"""Gateway-Identitaets-Wache: prueft, ob `hermes update` den laufenden Gateway sieht.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster, siehe bus-waechter.py).
Der Hermes-Scheduler laeuft am Gateway vorbei und liefert direkt nach Telegram.

WARUM ES DIESE WACHE GIBT
-------------------------
Am 26.09.2026 brach JEDER Update-Lauf nach dem Pre-update-Snapshot ab:

    exit_code 1
    stop_reason: RuntimeError: Could not map Windows gateway PIDs to profiles:
                 Could not inspect gateway PID for profile default

Ursache war eine Kette aus zwei Dingen:
1. Der Gateway wurde vom Update-Restart-Watcher als `python -I -c "<bootstrap>"
   ... gateway run` gestartet. Der Identitaetsmatcher des Updaters
   (`gateway.status.looks_like_gateway_runtime_command_line`) verweigert die
   `-c`-Form absichtlich (#107002) - der laufende Gateway war fuer den Updater
   also KEIN Gateway.
2. Beim Start war zusaetzlich `gateway.pid` nicht entstanden, sodass die
   Pruefung schon vorher mit "active gateway lock has no PID metadata" abbrach.

Der Updater prueft VOR dem Pull (`find_profile_gateway_processes(strict=True)`)
und bricht bei einer unklaren Antwort ab: der Checkout blieb 153 Commits hinter
origin/main, ohne dass es jemandem auffiel. Ein Abbruch ist richtig (nie auf
einen halb erkannten Gateway losgehen) - aber er braucht eine Wache, sonst
steht das Update still, bis jemand von Hand nachsieht.

WAS ES TUT
----------
1. Lock/pid im HERMES_HOME sowie jedes Profil-Home: ist der Lock aktiv (PID
   lebt), aber `gateway.pid` fehlt -> Befund (und mit --reparieren: die Datei
   aus dem Lock rekonstruieren, danach die Identitaet beweisen).
2. Laeuft der A2A-Port 9900 und findet der Updater den Gateway trotzdem nicht
   -> Befund "Update wuerde blockieren" mit der Handlungsanweisung (Gateway
   ueber die Aufgabe starten, dann ist die Kommandozeile klassisch).
3. Dieselbe Feststellung hoechstens alle 6 h erneut senden (Zustandsdatei).
4. Nichts loeschen, kein Netz ausser localhost, kein Schreiben in den Checkout.

Aufruf:
    python Agenten/Hermes/scripts/gateway-identitaet-wache.py
    python ... --stand <pfad> --nicht-reparieren   # Alarmrichtung pruefen
"""
import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
HOME = WURZEL / "Agenten" / "Hermes"
CHECKOUT = HOME / "hermes-agent"
STAND = HOME / "cache" / "gateway-identitaet-wache.json"
PORT = 9900
WIEDERHOLUNG_H = 6                            # dieselbe Meldung hoechstens so oft

# Sicht des Updaters nachbilden: genau der Aufruf, an dem `hermes update`
# abbricht (strict=True). Laeuft im Checkout-venv - dem Interpreter des Updaters.
PROBE = (
    "import json,sys;"
    "sys.path.insert(0,%r);"
    "from hermes_cli.gateway import find_profile_gateway_processes;"
    "import io,contextlib\n"
    "try:\n"
    "    p=find_profile_gateway_processes(strict=True)\n"
    "    print(json.dumps({'ok':True,'profile':[x.profile for x in p]}))\n"
    "except Exception as e:\n"
    "    print(json.dumps({'ok':False,'fehler':type(e).__name__+': '+str(e)}))\n"
) % str(CHECKOUT)


def _json(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _lebt(pid):
    """PID-Lebendigkeit ohne Fremdbibliothek: tasklist auf Windows, sonst os.kill."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return False
    return str(pid) in (r.stdout or "")


def _port_offen(port=PORT, timeout=3.0):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def gateway_laeuft():
    """True, wenn ein Gateway-Prozess laeuft.

    Der A2A-Port 9900 ist seit dem Update vom 29.09.2026 KEINE Wahrheit mehr:
    die neue Fassung lauscht auf einem Named Pipe (\\\\.\\pipe\\hermes-gateway-*)
    und bedient Webhooks auf 8644. Wer den Port prueft, haelt einen gesunden
    Gateway fuer tot. Deshalb: Prozessliste und Lock-PID.
    """
    if os.name != "nt":
        return False
    ps = ("$muster = 'hermes_cli.main' + ' ' + 'gateway' + ' ' + 'run'; "
          "Get-CimInstance Win32_Process | "
          "Where-Object { $_.ProcessId -ne $PID -and $_.Name -eq 'python.exe' "
          "-and $_.CommandLine -like ('*' + $muster + '*') } | "
          "Measure-Object | Select-Object -ExpandProperty Count")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        if int((r.stdout or "0").strip() or 0) > 0:
            return True
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return _port_offen()          # alte Fassungen lauschen weiter auf 9900


def homes():
    """Haupt-Home plus jedes Profil, das eine Lock-Datei hat."""
    gefunden = [HOME]
    pdir = HOME / "profiles"
    if pdir.is_dir():
        gefunden += [p for p in sorted(pdir.iterdir()) if (p / "gateway.lock").exists()]
    return gefunden


def proben():
    """(ok, profile, fehler) aus der Sicht des Updaters (Checkout-venv)."""
    py = CHECKOUT / "venv" / "Scripts" / "python.exe"
    if not py.exists():
        return None, [], "Checkout-venv fehlt: %s" % py
    umgebung = {k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")}
    umgebung["HERMES_HOME"] = str(HOME)
    try:
        r = subprocess.run([str(py), "-c", PROBE], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120, cwd=str(CHECKOUT), env=umgebung)
    except (OSError, subprocess.SubprocessError) as e:
        return None, [], "Probe nicht ausfuehrbar: %s" % e
    zeile = ""
    for z in reversed((r.stdout or "").strip().splitlines()):
        if z.strip().startswith("{"):
            zeile = z.strip()
            break
    if not zeile:
        return None, [], "Probe ohne Antwort (rc=%s): %s" % (r.returncode, (r.stderr or "").strip()[-200:])
    try:
        d = json.loads(zeile)
    except ValueError:
        return None, [], "Probe unlesbar: %s" % zeile[:200]
    return bool(d.get("ok")), list(d.get("profile") or []), d.get("fehler")


def reparieren(pid_path, record):
    """gateway.pid aus dem Lock rekonstruieren (derselbe Record, dieselbe Instanz)."""
    try:
        pid_path.write_text(json.dumps(record), encoding="utf-8")
    except OSError as e:
        return "Reparatur fehlgeschlagen: %s" % e
    import importlib
    sys.path.insert(0, str(CHECKOUT))
    try:
        status = importlib.import_module("gateway.status")
        ident = status.get_running_pid_identity_strict(pid_path)
        return "gateway.pid aus dem Lock geschrieben, Identitaet danach: %s" % (ident,)
    except Exception as e:  # noqa: BLE001
        return ("gateway.pid aus dem Lock geschrieben, Pruefung scheitert weiter: %s: %s"
                % (type(e).__name__, e))


def update_laeuft():
    """True, solange ein `hermes update`-Prozess laeuft - dann NICHTS anfassen.

    Das Suchmuster wird aus Teilen gebaut und der eigene Prozess ausgeschlossen:
    eine Prozessabfrage, die ihren Suchtext woertlich in der Kommandozeile
    traegt, findet sich sonst SELBST und meldet immer "es laeuft ein Update".
    """
    if os.name != "nt":
        return False
    ps = ("$muster = 'hermes_cli.main' + ' ' + 'update'; "
          "Get-CimInstance Win32_Process | "
          "Where-Object { $_.ProcessId -ne $PID -and $_.Name -eq 'python.exe' "
          "-and $_.CommandLine -like ('*' + $muster + '*') } | "
          "Measure-Object | Select-Object -ExpandProperty Count")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return True                      # im Zweifel nicht eingreifen
    try:
        return int((r.stdout or "0").strip() or 0) > 0
    except ValueError:
        return True


def gateway_klassisch_neustart(port=PORT):
    """Gateway ueber die Aufgabe neu starten: der Launcher startet ihn klassisch,
    damit der Identitaetsmatcher des Updaters ihn wieder erkennt. Gibt Klartext zurueck."""
    lock = _json(HOME / "gateway.lock")
    pid = int(lock.get("pid") or 0)
    if not _lebt(pid):
        return "Neustart unterlassen: Lock-PID %d lebt nicht (das ist ein Ausfall, keine Identitaetsfrage)." % pid
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Id %d -Force" % pid],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return "Neustart fehlgeschlagen (beenden): %s" % e
    for _ in range(20):
        if not _lebt(pid):
            break
        import time as _t
        _t.sleep(1)
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Start-ScheduledTask -TaskName 'Hermes_Gateway_2ef9d0b7'"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return "Neustart fehlgeschlagen (starten): %s" % e
    import time as _t
    for _ in range(18):                  # bis 90 s hochfahren lassen
        _t.sleep(5)
        ok, profile, _f = proben()
        if ok and "default" in profile:
            neu = _json(HOME / "gateway.lock").get("pid")
            return ("Gateway klassisch neu gestartet (alte PID %d beendet), neuer Stand: "
                    "PID %s, Profile %s - der Updater findet ihn wieder."
                    % (pid, neu or "?", ", ".join(profile)))
    return ("Gateway neu gestartet, aber der Updater sieht ihn nach 90 s noch nicht - "
            "Startprotokoll pruefen: %s" % (HOME / "logs" / "gateway.log"))


def melden(zeilen, stand, jetzt, erzwingen=False):
    """Dieselbe Feststellung nicht oefter als alle WIEDERHOLUNG_H Stunden senden.

    `erzwingen` gilt fuer Meldungen mit Wirkung (durchgefuehrter Neustart): die
    will man sehen, auch wenn dieselbe Feststellung schon gemeldet wurde.
    """
    kern = zeilen[0]
    alt = stand.get("letzte_meldung") or {}
    stand["letzte_meldung"] = {"kern": kern, "wann": jetzt.isoformat()}
    gesendet = True
    if not erzwingen and alt.get("kern") == kern and alt.get("wann"):
        try:
            faellig = datetime.fromisoformat(alt["wann"]) + timedelta(hours=WIEDERHOLUNG_H)
            if jetzt < faellig:
                gesendet = False
        except ValueError:
            pass
    with open(stand["_pfad"], "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in stand.items() if not k.startswith("_")}, f, ensure_ascii=False)
    if gesendet:
        print("\n".join(zeilen))


def main():
    ap = argparse.ArgumentParser(description="Gateway-Identitaets-Wache (lautlos, solange der Updater den Gateway sieht)")
    ap.add_argument("--stand", default=str(STAND), help="Zustandsdatei gegen Wiederholungen")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--nicht-reparieren", action="store_true",
                    help="nur melden, gateway.pid nicht rekonstruieren")
    a = ap.parse_args()

    jetzt = datetime.now()
    stand = _json(a.stand)
    stand["_pfad"] = a.stand
    zeilen = []

    # 1. Aktiver Lock ohne PID-Datei.
    for home in homes():
        pid_path, lock_path = home / "gateway.pid", home / "gateway.lock"
        if not lock_path.exists() or pid_path.exists():
            continue
        record = _json(lock_path)
        pid = int(record.get("pid") or 0)
        if not _lebt(pid):
            continue                       # verwaister Lock: harmlos, raeumt sich selbst
        zeilen.append("%s: aktiver Gateway-Lock (PID %d) ohne gateway.pid - "
                      "`hermes update` bricht mit 'active gateway lock has no PID metadata' ab."
                      % (home.name, pid))
        if a.nicht_reparieren:
            zeilen.append("Reparatur unterlassen (--nicht-reparieren): Pruefung der Alarmrichtung.")
        else:
            zeilen.append(reparieren(pid_path, record))
        break

    # 2. Gateway laeuft, aber der Updater sieht ihn nicht.
    ok, profile, fehler = proben()
    laeuft = gateway_laeuft()
    blind = False
    if ok is False:
        zeilen.append("Der Updater kann den Gateway nicht zuordnen: %s" % fehler)
        blind = laeuft
    elif ok is None:
        zeilen.append("Probe nicht moeglich: %s" % fehler)
    elif laeuft and "default" not in profile:
        zeilen.append("Gateway antwortet auf Port %d, aber der Updater findet ihn nicht "
                      "(%s) - 'hermes update' wuerde blockieren." % (a.port, profile or "keine Profile"))
        blind = True

    # 3. Heilen: im Blindfall den Gateway klassisch neu starten (nur wenn kein
    #    Update laeuft - ein Neustart mitten im Lauf waere schlimmer als der Befund).
    neustart_gemacht = False
    if blind and not a.nicht_reparieren:
        heute = jetzt.strftime("%Y-%m-%d")
        if stand.get("letzter_neustart_tag") == heute:
            zeilen.append("Neustart heute schon versucht (%s) - nicht erneut."
                          % (stand.get("letzter_neustart") or "?"))
        elif update_laeuft():
            zeilen.append("Ein 'hermes update' laeuft gerade - Neustart unterlassen.")
        else:
            zeilen.append(gateway_klassisch_neustart(a.port))
            stand["letzter_neustart_tag"] = heute
            stand["letzter_neustart"] = jetzt.isoformat()
            neustart_gemacht = True

    if not zeilen:
        return 0

    zusatz = []
    if laeuft:
        zusatz.append("Behebung: Gateway ueber die Aufgabe neu starten "
                      "(Start-ScheduledTask -TaskName 'Hermes_Gateway_2ef9d0b7'), "
                      "danach laeuft er klassisch ('python -m hermes_cli.main gateway run') "
                      "und ist fuer den Updater sichtbar.")
    zusatz.append("Beleg vom 26.09.2026: 153 Commits Rueckstand, Laeufe 11:09 und 20:01 "
                  "brachen mit exit_code 1 nach dem Snapshot ab.")
    melden(zeilen + zusatz, stand, jetzt, erzwingen=neustart_gemacht)
    return 0


if __name__ == "__main__":
    sys.exit(main())