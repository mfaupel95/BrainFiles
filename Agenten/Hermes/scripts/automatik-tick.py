"""Cron-Tick der Auto-Ausfuehrungs-Engine (konsolidiertes Home).

Der eine Eintrittspunkt, den die geplante Aufgabe/cron aufruft. Laeuft eine
Engine-Tick und danach den Kopplungs-Durchgang (Log lesen, reagieren, Rueckweg)
- dieselbe Reihenfolge wie im Betriebsdokument (BETRIEB.md/AUTOMATIK.md).

NICHT selbst eine Kopie der Engine halten: dieses Skript reicht die Umgebung
durch und ruft die lebende Engine/Kopplung im Home auf (automatik/ als
Subprozess). Eine Kopie ihrer Dateien waere sofort veraltet.

MASTER-SCHALTER (EIN/AUS):
  Die ganze Automatik ist damit von EINER Stelle abzuschalten. Der Cron laeuft
  einfach weiter, tut aber nichts und meldet nichts. Vorgabe ist EIN (bleibt
  der Tick installiert, laeuft er auch); abgeschaltet wird nur ausdruecklich.
    (nicht gesetzt / != 0)       Automatik eingeschaltet (Normalbetrieb)
    HERMES_AUTOMATIK_AKTIV=0     INGESAMT AUS - leerer Lauf, kein Schreiben
  Zusaetzlich laesst sich jede Regel einzeln in betrieb/registry.yaml auf
  modus: dry_run|gesperrt stellen. Der Master-Schalter ist die Kruecke davor.

Cron-Regeln in diesem Haus:
- Leere Ausgabe heisst "nichts zu melden" und wird nicht zugestellt. Nur
  schreiben, wenn wirklich etwas lief oder ein Fehler aufgetreten ist.
- Kein Modell, kein Agent. Der Tick ist ein Prozess, der prueft und endet.
- Fehler gehoeren in die Ausgabe, nicht in ein stilles Log: ein Automatiksystem,
  das seinen eigenen Ausfall verschweigt, ist schlimmer als keines.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Home der konsolidierten Automatik (Agenten/Hermes/automatik/). Nicht an eine
# Aufgabe binden: absoluter Pfad ist hier bewusst, weil der Cron-Kontext keinen
# sauberen cwd garantiert; umstellbar ueber die Variable fuer Tests.
HOME = Path(os.environ.get(
    "HERMES_AUTOMATIK_HOME",
    "C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/automatik",
))
PYTHON = os.environ.get("HERMES_AUTOMATIK_PYTHON", sys.executable)


def _aktiv() -> bool:
    # Vorgabe EIN. Ausdruecklich AB nur mit "0" (oder "aus"/"off"/"false").
    wert = os.environ.get("HERMES_AUTOMATIK_AKTIV", "").strip().lower()
    return wert not in ("", "0", "aus", "off", "false")


def _umgebung() -> dict:
    """Engine- und Kopplungspfade auf das konsolidierte Home zeigen lassen.

    Die Engine-/Kopplungs-pfade.py haben laengst Umgebungsvariablen fuer jeden
    Pfad; hier werden ihre Standards so gesetzt, dass ein Lauf NIE in den
    scratch-Workspaces landet, sondern immer im Home arbeitet.
    """
    env = dict(os.environ)
    env.setdefault("HERMES_AUTOMATIK_ENGINE", str(HOME))
    env.setdefault("HERMES_AUTOMATIK_REAKTION", str(HOME))
    env.setdefault("HERMES_AUTOMATIK_BASIS", str(HOME / "betrieb" / "arbeit"))
    env.setdefault("HERMES_AUTOMATIK_KOPPLUNG", str(HOME / "betrieb" / "arbeit"))
    env.setdefault("HERMES_AUTOMATIK_ABLAGE", str(HOME / "betrieb" / "arbeit"))
    env.setdefault("HERMES_AUTOMATIK_REGISTRY", str(HOME / "betrieb" / "registry.yaml"))
    env.setdefault("HERMES_AUTOMATIK_REAKTIONSKONFIG", str(HOME / "reaktionen.yaml"))
    env.setdefault("HERMES_AUTOMATIK_VALIDATOR",
                   str(HOME / "spez" / "scripts" / "registry_pruefen.py"))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _lauf(titel: str, kommandoteile: list[str], env: dict) -> list[str]:
    """Eine Etappe ausfuehren; Rueckgabe der meldenswerten Zeilen (Ausschuss)."""
    try:
        fertig = subprocess.run(kommandoteile, cwd=str(HOME), env=env,
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        return ["%s FEHLER: Interpreter nicht gefunden (%s)" % (titel, e)]
    if fertig.returncode != 0:
        zeilen = (fertig.stdout or "").strip().splitlines()
        zeilen += (fertig.stderr or "").strip().splitlines()
        kern = zeilen[-8:]
        return ["%s FEHLER (exit %d): %s" % (titel, fertig.returncode,
                                             " | ".join(kern))]
    # Erfolg: nur Ausgaben, die wirklich etwas sagen (keine leere Zeile,
    # "keine Ausloeser", "Kopplung: 0 neue Lauf-Zeile(n)" sind kein Befund).
    melden = []
    for zeile in (fertig.stdout or "").splitlines():
        z = zeile.rstrip()
        if not z:
            continue
        if z.startswith("keine Ausloeser"):
            continue
        if z.startswith("Kopplung: 0 neue"):
            continue
        if z.startswith("Engine-Log:") or z.startswith("Reaktionsdaten:"):
            continue
        melden.append(z)
    return melden


def main() -> int:
    if not _aktiv():
        # Master-Schalter aus: stiller Lauf. Kein Schreiben, keine Meldung.
        return 0
    if not HOME.is_dir():
        print("Automatik gestoppt - Home fehlt: %s" % HOME)
        return 1

    env = _umgebung()
    ausgabe: list[str] = []
    # ECHTE Etappen: tick abarbeiten, dann durchgang (Log lesen + Rueckweg).
    # Die Wirkung drosselt die Registry, nicht diese Aufruf-Argumente.
    ausgabe += _lauf("Engine-Tick", [PYTHON, "-m", "engine", "tick"], env)
    ausgabe += _lauf("Durchgang",
                     [PYTHON, "-m", "automatik", "durchgang"], env)

    fehler = [z for z in ausgabe
              if z.startswith(("Engine-Tick FEHLER", "Durchgang FEHLER",
                               "Automatik gestoppt"))]
    for zeile in ausgabe:
        print(zeile)
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
