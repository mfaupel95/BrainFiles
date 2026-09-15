"""Atlas-Waechter: haelt den ProjectAtlas-Watcher am Leben.

WARUM ES IHN GIBT
-----------------
`projectatlas watch` ist ein Dauerprozess: er beobachtet ein Repository und
zieht dessen Atlas nach, wenn sich Dateien aendern (gemessen: eine neue Datei
war nach 40 s im Index). Stirbt er, merkt das niemand - die Karte veraltet
still, und ein Agent liest danach eine Datei, die es nicht mehr gibt.
Ein Autostart-Traegt nur die Anmeldung; er heilt keinen toten Prozess. Die
Windows-Aufgabenplanung waere der naheliegende Ort, verlangt aber
Administratorrechte (`Register-ScheduledTask` -> Zugriff verweigert) - der
Scheduler laeuft ohne.

MELDUNG
-------
Leere Ausgabe heisst: es laeuft alles, es wird nichts gesendet (Waechter-Muster
wie bus-waechter.py). Ausgabe gibt es nur, wenn gestartet wurde oder etwas
klemmt.

Aufruf (aus der Repo-Wurzel):
    python Agenten/Hermes/scripts/atlas-watcher.py
    python Agenten/Hermes/scripts/atlas-watcher.py --zeige   # Zustand immer ausgeben
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts -> BrainFiles
ATLAS = WURZEL / "Agenten" / "Werkzeuge" / "projectatlas"
START = ATLAS / "watch-start.ps1"
REPO = "O:/Werkstatt/omnitrade"
PID_DATEI = ATLAS / "logs" / "watch-omnitrade.pid"


def prozess_laeuft(pid):
    """tasklist statt psutil: das Hermes-Python hat psutil nicht zwingend.

    errors/encoding: tasklist und powershell schreiben in der Konsolen-
    Codepage (cp1252), nicht in UTF-8 - ohne das stirbt der Lesethread an
    einem Umlaut (gemessen 15.09.2026).
    """
    if not pid:
        return False
    r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                       capture_output=True, text=True,
                       encoding="cp1252", errors="replace")
    return str(pid) in (r.stdout or "")


def pid_aus_datei():
    try:
        return int(PID_DATEI.read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        return None


def main():
    p = argparse.ArgumentParser(description="ProjectAtlas-Watcher bewachen")
    p.add_argument("--zeige", action="store_true",
                   help="Zustand auch dann ausgeben, wenn alles laeuft")
    a = p.parse_args()

    pid = pid_aus_datei()
    if prozess_laeuft(pid):
        if a.zeige:
            print("Atlas-Watcher laeuft: PID %d auf %s" % (pid, REPO))
        return 0

    zustand = "keine PID-Datei" if pid is None else "PID %d laeuft nicht" % pid
    if not START.exists():
        print("Atlas-Waechter: Skript fehlt - %s" % START)
        return 1

    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy",
                        "Bypass", "-File", str(START)],
                       capture_output=True, text=True,
                       encoding="cp1252", errors="replace", timeout=120)
    aus = (r.stdout or "").strip() or (r.stderr or "").strip()

    neu = pid_aus_datei()
    if prozess_laeuft(neu):
        print("Atlas-Watcher war weg (%s) - neu gestartet: PID %d auf %s"
              % (zustand, neu, REPO))
        print("Die Karte wird ab jetzt wieder nachgezogen. Kommt diese Meldung "
              "haeufig, stirbt der Prozess regelmaessig - dann die Logs unter "
              "Agenten/Werkzeuge/projectatlas/logs/watch-*.err ansehen.")
        return 0

    print("Atlas-Watcher ist weg (%s) und kam NICHT hoch." % zustand)
    print(aus or "(keine Ausgabe des Startskripts)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
