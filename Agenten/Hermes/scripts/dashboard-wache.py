"""Dashboard-Wache: wirft das Hermes-Web-Dashboard selbst wieder an.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster, siehe bus-waechter.py).
Der Hermes-Scheduler laeuft am Gateway vorbei und liefert direkt nach Telegram.

WARUM ES DIESE WACHE GIBT
-------------------------
Am 29.09.2026 endete `hermes update` mit `outcome=partial`: der pausierte
Gateway kam nicht zurueck (dafuer gibt es `gateway-identitaet-wache`), und das
Web-Dashboard `http://127.0.0.1:9119/` blieb aus - es musste von Hand mit
`Start-ScheduledTask -TaskName 'Hermes_Dashboard'` gestartet werden. Es gab
keine Wache, die das gemerkt haette (offener Punkt T-147).

GEMESSEN AM 30.09.2026 - und der Grund fuer die Bauform:
(a) Der Dashboard-Prozess lief, der Port 9119 war offen (`Get-NetTCPConnection`
nannte PID 27864), aber **es kam keine Antwort** - 60 s ohne Statuscode,
waehrend OmniRoute (20128) und der Gateway-Webhook (8644) im selben Moment in
Millisekunden antworteten. Ein offener Port ist also KEINE Wahrheit.
(b) Der Grund lag nicht im Dashboard selbst: die von Hand gestartete Instanz
schrieb `hermes: finishing an interrupted source update...` und baute danach
VOR dem Bereitstellen alles neu - Node-Abhaengigkeiten, TUI, Web-UI, Desktop-App
(gemessen ueber 6 Minuten, die node/electron-Kinder mit wachsender CPU-Zeit),
waehrend Port 9119 noch zu war. Ein Neustart macht das NICHT besser: die neue
Instanz faengt denselben Bau an. Die Aufgabe `Hermes_Dashboard` traegt
`RestartCount 999 / 1 min`, startet also bei einem ABSTURZ von selbst neu -
bei einem HAENGER laeuft der Prozess weiter, und niemand merkt es.

WAS ES TUT
----------
1. **Bedingung messen, nicht Adresse:** gefragt wird, ob das Dashboard
   ANTWORTET (HTTP-Statuscode, Frist 10 s). Jeder Statuscode zaehlt, auch 404.
2. **Arbeit von Haengen unterscheiden.** Vor jedem Eingriff wird zweimal die
   CPU-Zeit der Dashboard-Prozesskette gemessen (12 s Abstand): steigt sie,
   laeuft ein Bau/Start und es wird NICHTS angefasst (erst nach BUILD_GRACE_MIN
   gemeldet); steht sie still (gemessener Haenger: 1 s CPU in 5 Minuten), wird
   geheilt. Ohne diese Unterscheidung riss die Wache einen laufenden Bau ab und
   hinterliesse ein halb gebautes dist.
3. Lagen: `gesund` (still), `weg` (kein Prozess), `haengt` (idle) und
   `arbeitet` (CPU steigt). Geheilt wird in den beiden kranken Lagen: Kette per
   `Stop-Process` beenden (nie `taskkill`, siehe unten) und die Aufgabe
   `Hermes_Dashboard` starten; danach bis START_FRIST_S auf eine Antwort warten
   und das Ergebnis melden.
4. **Nie waehrend eines `hermes update`** eingreifen - der Lauf stoppt das
   Dashboard absichtlich und bringt es am Ende zurueck. Erst wenn der Ausfall
   laenger als UPDATE_GRACE_MIN dauert, kommt eine Meldung (kein Eingriff).
5. **Bremse:** hoechstens ein Heilversuch je HEIL_BREMSE_MIN Minuten; dieselbe
   Feststellung hoechstens alle WIEDERHOLUNG_H Stunden (Zustand in
   `Agenten/Hermes/cache/dashboard-wache.json`, Schluessel ohne Zahlen).

Aufruf:
    python Agenten/Hermes/scripts/dashboard-wache.py
    python ... --nicht-heilen     # Alarmrichtung pruefen, ohne einzugreifen
    python ... --selbsttest       # Form der Meldung zeigen, ohne Netz/Zustand
"""
from __future__ import annotations

import argparse
import http.client
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # scripts -> Hermes -> Agenten -> BrainFiles
HOME = WURZEL / "Agenten" / "Hermes"
STAND = HOME / "cache" / "dashboard-wache.json"
AUFGABE = "Hermes_Dashboard"
PORT = 9119
URL = "http://127.0.0.1:%d/" % PORT

ANTWORT_FRIST_S = 10        # so lange darf die Antwort auf sich warten lassen
START_FRIST_S = 90          # so lange wird nach dem Start auf die Antwort gewartet
CPU_WARTE_S = 12            # Abstand der beiden CPU-Messungen
CPU_SCHWELLE_S = 0.5        # so viel CPU-Zeit muss in dieser Zeit dazukommen
HEIL_BREMSE_MIN = 30        # hoechstens ein Heilversuch je so vielen Minuten
BUILD_GRACE_MIN = 25        # ein laufender Bau darf so lange still sein
UPDATE_GRACE_MIN = 20       # waehrend eines Updates erst ab hier melden
WIEDERHOLUNG_H = 6          # dieselbe Feststellung hoechstens so oft
ROTATION_BYTE_FRIST = 4 * 1024 * 1024   # ab wie vielen Bytes
                                        # dashboard-restart.log wandert
                                        # nach <name>.1 (T-196). Der Wert
                                        # stand nie in der Datei, obwohl
                                        # _rotieren() ihn als Vorgabe las -
                                        # die Wache brach beim LADEN ab und
                                        # meldete seitdem nur noch den
                                        # SyntaxError weiter.


# ---------------------------------------------------------------- Zustand

def _laden(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _schreiben(pfad, stand):
    try:
        Path(pfad).parent.mkdir(parents=True, exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as f:
            json.dump(stand, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def _rotieren(pfad: Path, *, byte_frist: int = ROTATION_BYTE_FRIST, behalten: int = 1) -> None:
    """dashboard-restart.log ist ein reines Anhaenge-Protokoll (Schreiber:
    ``hermes_cli/main_dashboard.py::_respawn_dashboard_processes``, Appends nur,
    keine Rotation dort - T-196). Damit die Datei nicht unbegrenzt waechst,
    rotiert die Wache sie hier am eigenen Seam: ueber der Frist wandert die
    alte Fassung nach ``<name>.1`` (fruehere Generationen fallen weg - die
    Heilung im Log betrifft nur die Zyklen der letzten Stunden, die CPU-Bremse
    und die Fristen decken den Rest ab). Still bei Schreibfehlern: die Wache
    darf nie an einem Protokoll scheitern (z. B. WinError am offenen Handle
    eines gerade respawnten Backends - dann rotiert der naechste Lauf).
    """
    if not pfad.is_file():
        return
    try:
        if pfad.stat().st_size <= byte_frist:
            return
    except OSError:
        return
    # Eine Generation: die aktuelle Fassung wird <name>.1; eine bereits
    # liegende <name>.1 wird von Path.replace ueberschrieben (auf diesem
    # Windows so atomar wie ein Posix-rename). Hohere Staende gibt es nicht -
    # die Heilung im Log betrifft nur die Zyklen der letzten Stunden.
    try:
        pfad.replace(pfad.with_name(pfad.name + ".1"))
    except OSError:
        return


# ---------------------------------------------------------------- Messen

def antwortet(url=URL, frist=ANTWORT_FRIST_S):
    """Die Bedingung: der Dienst ANTWORTET. Jeder Statuscode zaehlt."""
    rest = url.split("//", 1)[-1]
    host_teil, _, pfad_teil = rest.partition("/")
    host, _, port = host_teil.partition(":")
    try:
        c = http.client.HTTPConnection(host, int(port or 80), timeout=frist)
        c.request("GET", "/" + pfad_teil)
        r = c.getresponse()
        r.read(64)
        c.close()
        return True
    except Exception:                       # noqa: BLE001 - jede Stoerung = keine Antwort
        return False


def _ps(skript, frist=60):
    """PowerShell auf dem Host. Leere Rueckgabe heisst: nicht messbar."""
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", skript],
            capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=frist)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (p.stdout or "").strip()


def port_halter(port=PORT):
    """PIDs, die auf dem Port lauschen. Leer = niemand hoert zu."""
    roh = _ps("(Get-NetTCPConnection -LocalPort %d -State Listen -ErrorAction "
              "SilentlyContinue | Select-Object -ExpandProperty OwningProcess) -join ','" % port)
    if not roh:
        # Rueckfall: netstat, Spalte LISTENING, letzte Spalte ist die PID
        roh2 = _ps("netstat -ano -p tcp | Select-String ':%d\\s' | "
                   "Select-String 'LISTENING' | ForEach-Object { ($_.Line -split '\\s+')[-1] }" % port)
        roh = ",".join(z for z in (roh2 or "").split() if z.isdigit())
    pids = []
    for stueck in (roh or "").split(","):
        stueck = stueck.strip()
        if stueck.isdigit() and int(stueck) > 0:
            pids.append(int(stueck))
    return sorted(set(pids))


def dashboard_pids():
    """Dashboard-Prozesse ueber die Kommandozeile.

    Das Suchmuster wird aus Teilen gebaut und der eigene Prozess ausgeschlossen:
    eine Abfrage, die ihren Suchtext woertlich in der Kommandozeile traegt,
    findet sich sonst SELBST. Gefordert sind zwei Merkmale zusammen
    (`hermes_cli.main` UND `dashboard`) - der Pfad dieses Skripts allein
    ('dashboard-wache.py') darf nicht als Treffer zaehlen.
    """
    teile = ("'hermes_' + 'cli.main'", "'dash' + 'board'")
    ps = ("$m1 = %s; $m2 = %s; "
          "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and "
          "($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and "
          "$_.CommandLine -like ('*' + $m1 + '*') -and $_.CommandLine -like ('*' + $m2 + '*') } | "
          "Select-Object -ExpandProperty ProcessId" % teile)
    pids = []
    for z in (_ps(ps) or "").splitlines():
        z = z.strip()
        if z.isdigit() and int(z) > 0:
            pids.append(int(z))
    return sorted(set(pids))


def update_laeuft():
    """True, solange ein `hermes update` laeuft - dann NICHTS anfassen."""
    teile = "'hermes_' + 'cli.main'"
    ps = ("$m = %s; $m2 = 'upd' + 'ate'; "
          "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and "
          "($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and "
          "$_.CommandLine -like ('*' + $m + '*') -and $_.CommandLine -like ('*' + $m2 + '*') } | "
          "Measure-Object | Select-Object -ExpandProperty Count" % teile)
    roh = _ps(ps)
    try:
        return int(roh or 0) > 0
    except ValueError:
        return True                          # im Zweifel nicht eingreifen


def prozessliste():
    """Alle Prozesse als (eltern, cpu_sekunden) - Grundlage fuer den Baum."""
    ps = ("Get-CimInstance Win32_Process | ForEach-Object { "
          "'{0}|{1}|{2}' -f $_.ProcessId, $_.ParentProcessId, "
          "[math]::Round(($_.KernelModeTime + $_.UserModeTime) / 10000000, 2) }")
    eltern, cpu = {}, {}
    for zeile in (_ps(ps, frist=90) or "").splitlines():
        teile = zeile.strip().split("|")
        if len(teile) != 3 or not teile[0].isdigit():
            continue
        pid = int(teile[0])
        eltern[pid] = int(teile[1]) if teile[1].isdigit() else 0
        try:
            cpu[pid] = float(teile[2].replace(",", "."))
        except ValueError:
            cpu[pid] = 0.0
    return eltern, cpu


def kette(pids, eltern):
    """Die Prozesse UND alles, was sie gestartet haben (der Bau laeuft in
    Kindern: cmd -> node -> node). Ohne die Kinder wird die falsche CPU gemessen."""
    kette_pids = set(pids)
    geaendert = True
    while geaendert:
        geaendert = False
        for pid, vater in eltern.items():
            if vater in kette_pids and pid not in kette_pids:
                kette_pids.add(pid)
                geaendert = True
    return kette_pids


def arbeitet(pids, warte=CPU_WARTE_S, schwelle=CPU_SCHWELLE_S):
    """Steigt die CPU-Zeit der Kette? Dann laeuft ein Bau/Start - nicht anfassen.

    Gemessener Unterschied: der HAENGER stand 5 Minuten mit 1 s CPU still,
    ein laufender Bau liess die node-Kinder in Sekunden um Sekunden wachsen.
    """
    if not pids:
        return False                         # nichts laeuft, nichts baut
    e1, c1 = prozessliste()
    vorher = sum(c1.get(p, 0.0) for p in kette(pids, e1))
    time.sleep(warte)
    e2, c2 = prozessliste()
    nachher = sum(c2.get(p, 0.0) for p in kette(pids, e2))
    return (nachher - vorher) >= schwelle


def warten(url=URL, frist=START_FRIST_S, schritt=5):
    """Nach dem Start auf die Antwort warten. Gibt True zurueck, sobald sie kommt."""
    ende = time.time() + frist
    while time.time() < ende:
        if antwortet(url):
            return True
        time.sleep(schritt)
    return antwortet(url)


# ---------------------------------------------------------------- Handeln

def beenden(pids):
    """Prozesskette per Stop-Process beenden (nativ; `taskkill` tut auf diesem
    Windows aus einer Sitzung still nichts). Liefert (beendet, uebrig)."""
    pids = [p for p in pids if p and p > 0]
    if not pids:
        return [], []
    body = ";".join("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % p for p in pids)
    _ps(body)
    time.sleep(2)
    uebrig = [p for p in pids if _ps("if(Get-Process -Id %d -ErrorAction SilentlyContinue){'ja'}" % p) == "ja"]
    return [p for p in pids if p not in uebrig], uebrig


def starten():
    """Die Aufgabe starten. Gibt Klartext zurueck (fuer die Meldung)."""
    _ps("Start-ScheduledTask -TaskName '%s'" % AUFGABE)
    return "Aufgabe '%s' gestartet" % AUFGABE


# ---------------------------------------------------------------- Melden

def _kern(zeilen):
    """Schluessel der Feststellung OHNE Zahlen: die Dauer waechst sonst jeden
    Lauf, und dieselbe Lage kaeme als 'neue' Meldung wieder."""
    return re.sub(r"\d+", "#", zeilen[0])[:120]


def melden(zeilen, stand, pfad, jetzt, erzwingen=False):
    """Zustand schreiben und - wenn die Feststellung neu ist - ausgeben.

    `erzwingen` gilt fuer Meldungen mit Wirkung (durchgefuehrte Heilung): die
    will man sehen, auch wenn dieselbe Feststellung schon gemeldet wurde.
    """
    kern = _kern(zeilen)
    alt = stand.get("letzte_meldung") or {}
    stand["letzte_meldung"] = {"kern": kern, "wann": jetzt.isoformat()}
    _schreiben(pfad, stand)
    if not erzwingen and alt.get("kern") == kern and alt.get("wann"):
        try:
            if jetzt < datetime.fromisoformat(alt["wann"]) + timedelta(hours=WIEDERHOLUNG_H):
                return 0
        except ValueError:
            pass
    print("\n".join(zeilen))
    return 0


def _minuten_seit(iso, jetzt):
    try:
        return max(0, int((jetzt - datetime.fromisoformat(iso)).total_seconds() // 60))
    except (TypeError, ValueError):
        return 0


def _bremse_aktiv(stand, jetzt):
    """Ein Heilversuch je HEIL_BREMSE_MIN - sonst startet die Wache im eigenen
    Takt neu (dieselbe Falle wie beim Gateway: 128 Neustarts an einem Tag)."""
    versuch = stand.get("letzter_versuch")
    if not versuch:
        return False
    try:
        return jetzt < datetime.fromisoformat(versuch) + timedelta(minutes=HEIL_BREMSE_MIN)
    except ValueError:
        return False


# ---------------------------------------------------------------- Lauf

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Dashboard-Wache (lautlos, solange das Dashboard antwortet)")
    ap.add_argument("--stand", default=str(STAND), help="Zustandsdatei")
    ap.add_argument("--url", default=URL)
    ap.add_argument("--nicht-heilen", action="store_true",
                    help="nur melden, nicht neu starten (Pruefung der Alarmrichtung)")
    ap.add_argument("--selbsttest", action="store_true",
                    help="Form der Meldung zeigen, ohne zu messen und ohne Zustand zu schreiben")
    a = ap.parse_args(argv)

    # Protokollgrenze erhalten, bevor irgendetwas gelesen/gemeldet wird
    # (T-196): dashboard-restart.log waechst nur durch den Writer in
    # ``hermes_cli.main_dashboard._respawn_dashboard_processes``, ueber der
    # Frist wandert die alte Fassung nach <name>.1. Still bei Schreibfehlern.
    try:
        _rotieren(HOME / "logs" / "dashboard-restart.log")
    except OSError:
        pass

    jetzt = datetime.now()

    if a.selbsttest:
        print("Dashboard-Wache Selbsttest (nur die FORM, keine Lage):")
        print("Dashboard haengt (Prozess da, keine Antwort) seit 42 min - "
              "Kette beendet (3 PID(s)), Aufgabe 'Hermes_Dashboard' gestartet, "
              "antwortet wieder auf %s." % a.url)
        return 0

    stand = _laden(a.stand)

    if antwortet(a.url):
        stand.pop("ausgefallen_seit", None)
        stand.pop("letzter_versuch", None)
        stand["letzter_gesund"] = jetzt.isoformat()
        _schreiben(a.stand, stand)
        return 0

    halter = port_halter()
    pids = sorted(set(halter) | set(dashboard_pids()))
    seit = stand.get("ausgefallen_seit") or jetzt.isoformat()
    stand["ausgefallen_seit"] = seit
    stand["pids"] = pids
    dauer = _minuten_seit(seit, jetzt)

    # Laeuft ein Bau/Start? Dann ist die fehlende Antwort kein Befund.
    stand["arbeitet"] = arbeitet(pids) if pids else False
    lage = "haengt (Prozess da, keine Antwort)" if pids else "laeuft nicht"
    stand["grund"] = lage

    zeilen = []
    eingriff = None

    if a.nicht_heilen:
        eingriff = "kein Eingriff (--nicht-heilen, Pruefung der Alarmrichtung)"
    elif update_laeuft():
        # Der Lauf stoppt das Dashboard absichtlich und bringt es zurueck.
        if dauer >= UPDATE_GRACE_MIN:
            eingriff = "kein Eingriff (ein 'hermes update' laeuft)"
        else:
            _schreiben(a.stand, stand)
            return 0                          # innerhalb der Gnadenfrist still
    elif stand["arbeitet"]:
        # Ein laufender Bau darf still sein - erst nach der Frist wird gemeldet.
        stand["grund"] = "arbeitet (Bau/Start laeuft)"
        if dauer < BUILD_GRACE_MIN:
            _schreiben(a.stand, stand)
            return 0
        eingriff = "kein Eingriff (Bau/Start laeuft seit %d min)" % dauer
    elif _bremse_aktiv(stand, jetzt):
        # Ein Versuch laeuft schon in der Bremse: nichts Neues, also still.
        # (Der fehlgeschlagene Versuch selbst wurde bereits gemeldet.)
        stand["grund"] = "Heilversuch vor weniger als %d min - Bremse" % HEIL_BREMSE_MIN
        _schreiben(a.stand, stand)
        return 0
    else:
        teile = []
        if pids:
            beendet, uebrig = beenden(pids)
            teile.append("Kette beendet (%d von %d PID(s)%s)"
                         % (len(beendet), len(pids),
                            ", uebrig: %s" % uebrig if uebrig else ""))
        teile.append(starten())
        stand["letzter_versuch"] = jetzt.isoformat()
        if warten(a.url):
            stand.pop("ausgefallen_seit", None)
            stand["letzter_erfolg"] = jetzt.isoformat()
            stand["grund"] = "geheilt"
            zeilen.append("Dashboard %s seit %d min - %s, antwortet wieder auf %s."
                          % (lage, dauer, ", ".join(teile), a.url))
            return melden(zeilen, stand, a.stand, jetzt, erzwingen=True)
        # Keine Antwort, aber die frische Instanz baut: kein Fehlschlag, sondern
        # derselbe Bau wie beim Start - die Antwort kommt spaeter.
        neu = sorted(set(port_halter()) | set(dashboard_pids()))
        if neu and arbeitet(neu):
            stand["grund"] = "gestartet, baut/startet noch"
            _schreiben(a.stand, stand)
            return 0
        zeilen.append("Dashboard %s seit %d min - %s, aber nach %d s keine Antwort: "
                      "Heilversuch fehlgeschlagen." % (lage, dauer, ", ".join(teile), START_FRIST_S))
        zeilen.append("Nachsehen: %s und %s" % (HOME / "logs" / "dashboard-restart.log",
                                                HOME / "logs" / "agent.log"))
        return melden(zeilen, stand, a.stand, jetzt)

    zeilen.append("Dashboard %s seit %d min - %s." % (lage, dauer, eingriff))
    if pids:
        zeilen.append("Prozesskette %s, keine Antwort auf %s (HTTP-Frist %d s)."
                      % (", ".join(str(p) for p in pids), a.url, ANTWORT_FRIST_S))
    zeilen.append("Protokoll: %s | Von Hand starten: Start-ScheduledTask -TaskName '%s'"
                  % (HOME / "logs" / "dashboard-restart.log", AUFGABE))
    return melden(zeilen, stand, a.stand, jetzt)


if __name__ == "__main__":
    sys.exit(main())