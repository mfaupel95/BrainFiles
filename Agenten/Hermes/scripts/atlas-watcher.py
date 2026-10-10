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
import os
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
# Der Prozess, den die PID-Datei NAMLICH nennen muss. Ohne diesen Namen
# zaehlt eine PID-Wiederverwendung als lebender Watcher (03.10.2026).
ERWARTETER_NAME = "projectatlas.exe"


def prozess_laeuft(pid):
    """PID UND PROGRAMMNAME pruefen - die Zahl allein reicht nicht.

    `tasklist /FI "PID eq n" /NH` beantwortet jede noch vergebene PID mit
    einer Zeile, auch wenn dort inzwischen etwas ANDERES laeuft. Gemessen
    03.10.2026: die PID-Datei nannte 69928 (ein toter Watcher), die PID
    war inzwischen an `svchost.exe` vergeben - die Zahl stand in der
    Antwort, der Waechter glaubte, der Watcher laeuft, und startete
    bei jedem Lauf einen neuen. Daraus waren 18 haengende Projektions-
    prozesse mit je ~1 MB geworden (die Leerlaeufer einer Projektion,
    die nie zurueckkommt), waehrend der ECHTE Watcher (PID 96060, 9705 s
    CPU) nebenbei Arbeit tat.

    Die Regel: eine PID gilt nur dann als der Watcher, wenn taskslist sie
    MIT dem erwarteten Prozessnamen nennt. Das ist dieselbe Lehre wie bei
    `omnitrade_lauf.pid_lebt(pid, name=...)` - Windows vergibt PIDs neu,
    und eine lebende PID ist kein Beleg fuer einen lebenden Prozess.

    errors/encoding: tasklist und powershell schreiben in der Konsolen-
    Codepage (cp1252), nicht in UTF-8 - ohne das stirbt der Lesethread an
    einem Umlaut (gemessen 15.09.2026).
    """
    if not pid:
        return False
    r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                           capture_output=True, text=True,
                           encoding="cp1252", errors="replace",
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    for zeile in (r.stdout or "").splitlines():
        teile = zeile.split()
        # Bild: <name> <pid> <sitzung> ...  /  oder KEIN TREFFER-Zeile
        if len(teile) >= 2 and teile[1] == str(pid):
            return teile[0].lower().startswith(ERWARTETER_NAME.lower())
    return False


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
