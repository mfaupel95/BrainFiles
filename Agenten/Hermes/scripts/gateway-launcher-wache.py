"""Gateway-Launcher-Wache: prueft die zwei Dinge, die `hermes update` kaputt macht.

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
gut** und es wird nichts gesendet (Watchdog-Muster, siehe bus-waechter.py).

WARUM ES DIESE WACHE GIBT
-------------------------
Am 30.09.2026 lag der Gateway stundenlang still, aus zwei Gruenden, die ein
Update-Lauf hinterlaesst:

1. `hermes update` schreibt `gateway-service/Hermes_Gateway_*.vbs` neu und
   setzt den Start auf `tools\\python-3.14.7...\\python.exe` mit Fensterstil 0.
   `WScript.Shell.Run` mit Stil 0 startet ein KONSOLENprogramm GAR NICHT - kein
   Prozess, KEINE Fehlermeldung, der Aufruf kehrt sauber zurueck (gemessen
   30.09.2026, Tabelle in Wissen/Hardware.md). Ein GUI-Programm (`pythonw.exe`)
   laeuft mit Stil 0 dagegen versteckt.
2. Demselben `tools`-Python fehlten nach dem Update vom 29.09.2026 alle
   Abhaengigkeiten (site-packages nur mit pip). Symptome: alle MCP-Server
   geparkt ("module tools.mcp_tool has no attribute StdioServerParameters"),
   `hosted_room_worker` stirbt mit "No module named pydantic_core._pydantic_core".
   Reparatur: `tools/python-3.14.7*/python.exe -m pip install -e hermes-agent`.

Beides ist von aussen unsichtbar: der Launcher meldet nichts, und der Waechter
auf den Prozess sieht nur "kein Gateway da". Diese Wache prueft die URSACHE
statt des Symptoms.

WAS ES TUT
----------
1. Launcher-VBS lesen und die `.Run`-Zeile pruefen: sie muss auf `pythonw.exe`
   zeigen. Ein `python.exe` in der Run-Zeile bei Fensterstil 0 ist ein Befund.
2. Das `tools`-Python suchen (neuestes `tools/python-3*/python.exe`) und mit
   der Umgebung des Launchers `import pydantic_core, hermes_cli.main` ausfuehren.
   Ein Fehlschlag ist ein Befund mit der Reparaturzeile.
3. Dieselbe Feststellung hoechstens alle WIEDERHOLUNG_H Stunden erneut senden.
4. Nur lesen: kein Schreiben in den Checkout, kein Start, kein Netz.

Aufruf:
    python Agenten/Hermes/scripts/gateway-launcher-wache.py
    python ... --vbs <datei> --tools <ordner> --stand <pfad>   # Alarmrichtung pruefen
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                      # Agenten/Hermes/scripts/ -> BrainFiles
HOME = WURZEL / "Agenten" / "Hermes"
DIENST = HOME / "gateway-service"
TOOLS = HOME / "tools"
CHECKOUT = HOME / "hermes-agent"
STAND = HOME / "cache" / "gateway-launcher-wache.json"
WIEDERHOLUNG_H = 6                            # dieselbe Meldung hoechstens so oft
PROBE = "import pydantic_core, hermes_cli.main; print('ok')"


def launcher_vbs(ordner):
    """Neueste Gateway-Launcher-VBS im Dienst-Ordner (oder None)."""
    ordner = Path(ordner)
    if not ordner.is_dir():
        return None
    treffer = [p for p in ordner.glob("*.vbs")
               if "gateway" in p.name.lower() or "gateway" in p.read_text(
                   encoding="utf-8", errors="replace").lower()]
    if not treffer:
        return None
    return max(treffer, key=lambda p: p.stat().st_mtime)


def run_zeile(text):
    """Die Zeile mit dem Startbefehl (`sh.Run ...`), sonst None."""
    for zeile in text.splitlines():
        blank = zeile.strip()
        if blank.startswith("'") or blank.startswith("REM "):
            continue                          # Kommentarzeilen zaehlen nicht
        if ".Run " in blank:
            return blank
    return None


def vbs_befund(text):
    """None, wenn der Launcher ein GUI-Programm versteckt startet - sonst Grund."""
    zeile = run_zeile(text)
    if zeile is None:
        return ("keine Startzeile gefunden (`sh.Run ...`) - der Launcher kann "
                "den Gateway gar nicht starten")
    if "pythonw.exe" in zeile.lower():
        return None
    if "python.exe" in zeile.lower():
        return ("die Startzeile ruft `python.exe` (Konsolenprogramm). Mit "
                "WScript.Shell.Run und Fensterstil 0 entsteht dann KEIN Prozess, "
                "ohne Fehlermeldung - der Gateway bleibt still liegen")
    return "die Startzeile nennt kein Python-Programm: %s" % zeile[:120]


def tools_python(ordner):
    """Neuestes tools/python-3*/python.exe (oder None)."""
    ordner = Path(ordner)
    if not ordner.is_dir():
        return None
    kandidaten = [p for p in ordner.glob("python-*/python.exe") if p.is_file()]
    if not kandidaten:
        return None
    return max(kandidaten, key=lambda p: p.stat().st_mtime)


def probe_import(py, timeout=180):
    """(ok, meldung): kann dieses Python den Gateway ueberhaupt laden?"""
    umgebung = {k: v for k, v in os.environ.items()
                if k not in ("PYTHONHOME", "PYTHONPATH")}
    umgebung["PYTHONPATH"] = str(CHECKOUT)          # wie im Launcher
    umgebung["VIRTUAL_ENV"] = str(TOOLS)
    umgebung["HERMES_HOME"] = str(HOME)
    umgebung["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([str(py), "-c", PROBE], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           cwd=str(HOME), env=umgebung)
    except (OSError, subprocess.SubprocessError) as e:
        return False, "nicht ausfuehrbar: %s" % e
    if r.returncode == 0:
        return True, "ok"
    fehler = ((r.stderr or "") + (r.stdout or "")).strip().splitlines()
    letzte = fehler[-1] if fehler else "ohne Meldung"
    return False, "rc=%s, %s" % (r.returncode, letzte[:200])


def melden(zeilen, stand, jetzt, erzwingen=False):
    """Dieselbe Feststellung nicht oefter als alle WIEDERHOLUNG_H Stunden senden."""
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
        json.dump({k: v for k, v in stand.items() if not k.startswith("_")},
                  f, ensure_ascii=False)
    if gesendet:
        print("\n".join(zeilen))


def _json(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser(
        description="Gateway-Launcher-Wache (lautlos, solange Launcher und tools-Python gesund sind)")
    ap.add_argument("--vbs", default=None, help="Launcher-VBS (Vorgabe: neueste in gateway-service/)")
    ap.add_argument("--tools", default=str(TOOLS), help="Ordner mit dem tools-Python")
    ap.add_argument("--stand", default=str(STAND), help="Zustandsdatei gegen Wiederholungen")
    ap.add_argument("--probe-aus", action="store_true",
                    help="nur die VBS pruefen, das tools-Python nicht laden")
    a = ap.parse_args()

    jetzt = datetime.now()
    stand = _json(a.stand)
    stand["_pfad"] = a.stand
    zeilen = []

    # 1. Launcher: startet er ein Programm, das mit Fensterstil 0 ueberhaupt entsteht?
    vbs = Path(a.vbs) if a.vbs else launcher_vbs(DIENST)
    if vbs is None or not vbs.is_file():
        zeilen.append("Launcher-VBS nicht gefunden (%s) - der Gateway hat keinen Startweg."
                      % (a.vbs or DIENST))
    else:
        grund = vbs_befund(vbs.read_text(encoding="utf-8", errors="replace"))
        if grund:
            zeilen.append("%s: %s." % (vbs.name, grund))
            zeilen.append("Behebung: in der Startzeile `python.exe` durch `pythonw.exe` ersetzen "
                          "(dieselbe Version, gleicher Ordner).")
            zeilen.append("Beleg 30.09.2026: mit `python.exe` und Stil 0 entstand kein Prozess; "
                          "`pythonw.exe` startet versteckt und laeuft.")

    # 2. tools-Python: kann es den Gateway laden?
    if not a.probe_aus:
        py = tools_python(a.tools)
        if py is None:
            zeilen.append("kein tools-Python gefunden (%s/python-*/python.exe) - "
                          "der Launcher zeigt ins Leere." % a.tools)
        elif not (py.parent / "pythonw.exe").is_file():
            zeilen.append("%s: pythonw.exe fehlt daneben - der versteckte Start "
                          "kann nicht funktionieren." % py.parent.name)
        else:
            ok, meldung = probe_import(py)
            if not ok:
                zeilen.append("%s kann den Gateway nicht laden: %s" % (py.parent.name, meldung))
                zeilen.append("Behebung: `%s -m pip install -e hermes-agent` "
                              "(installiert alle Abhaengigkeiten in dieses Python), "
                              "danach Gateway ueber die Aufgabe neu starten." % py)

    if not zeilen:
        return 0
    melden(zeilen, stand, jetzt)
    return 0


if __name__ == "__main__":
    sys.exit(main())