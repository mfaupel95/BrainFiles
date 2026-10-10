#!/usr/bin/env python3
"""Wache auf die drei Dauerlauf-Stufen - sie MELDET den Zustand, sie heilt nicht.

WARUM (T-193, 30.09.2026)
-------------------------
Am 30.09.2026 standen zwischen 01:52 und 02:39 alle drei Stufen still. Aufgefallen
ist das nur, weil eine Sitzung zufaellig nachsah - die Waechter-Aufgaben starten
zwar neu (alle 30 Minuten), aber NIEMAND meldet, dass ein Lauf gestorben ist. Die
Handelszentrale zeigte derweil einen Stand, der stehen blieb.

Zwei Todesarten sind belegt:
  * `Rueckgabe 143` = SIGTERM. Gemessene Herkunft: ein MSYS-/Git-Bash-`timeout N`
    (Cygwin liefert 128+15). Wer den Dienst zur Ansicht mit `timeout 60 python
    dauerlauf.py` startet, killt ihn nach Ablauf - und die Spur, die gerade lief,
    stirbt mit ihm. Windows-Werkzeuge erzeugen das NICHT (gemessen: taskkill -> 1,
    Stop-Process -> 4294967295, os.kill -> 15).
  * spurlos: kein letzter Eintrag, kein Rueckgabecode. Dazu passt der Speicherdruck
    (Ereignis 2004 "virtueller Speicher unzureichend", 30.09. 02:07:56, Spitzenreiter
    com.docker.sailor.exe mit 15,7 GB).

WAS DIESE WACHE TUT
-------------------
Je Stufe ZWEI Zeugen (Hausregel): die Prozessnummer aus der Sperrdatei und die
Frische des Protokolls. Daraus drei Befunde - tot durch SIGTERM, tot ohne Spur,
haengt (Prozess lebt, Protokoll alt) - dazu der Sperren-Churn des Waechters
("verwaiste Sperre" gehaeuft = niemand kommt hoch).

Sie startet, beendet und kopiert NICHTS. Leere Ausgabe = alles in Ordnung; nur
ein WECHSEL des Befunds wird gemeldet, hoechstens alle 6 Stunden je Befund.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python Agenten/Hermes/scripts/dauerlauf-wache.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HIER, "..", "..", ".."))

HANDEL = os.path.join(REPO, "Agenten", "Handel")
WRAPPER_LOGS = os.path.join(REPO, "Agenten", "Routinen", "logs")
MERKDATEI = os.path.join(REPO, "Agenten", "Hermes", "cache", "dauerlauf-wache.json")

# Stufen und ihr Dateinamen-Zusatz - dieselbe Regel wie risikostufe.suffix_fuer()
# und handel-dauerlauf.ps1. Hier bewusst als Tabelle: die Wache darf nicht
# davon abhaengen, dass ein Handelsmodul importierbar ist.
STUFEN = (("niedrig", ""), ("mittel", ".mittel"), ("hoch", ".hoch"))

# Ein Zyklus dauert 6-7 min (30 Spuren). 20 min heisst: DREI Zyklen ausgefallen -
# ein einzelner langsamer Zyklus (Speicherdruck) loest also keinen Fehlalarm aus.
# Wer die Grenze hoeher setzt, meldet den Ausfall vom 30.09. (47 min) wieder erst
# nach einer Stunde; wer sie auf 10 min setzt, meldet jeden schweren Zyklus.
PROTOKOLL_ALTER_MAX_S = 20 * 60

# Ab so vielen "verwaisten Sperren" in einer Stunde kommt der Waechter nicht hoch.
CHURN_GRENZE = 3
CHURN_FENSTER_S = 60 * 60

# Ein Befund wird hoechstens einmal je Fenster gemeldet - sonst kommt alle
# 15 Minuten dieselbe Nachricht, und die wird ignoriert.
MELDE_FENSTER_S = 6 * 60 * 60

# Letzte Zeile eines Protokolls, die einen Rueckgabecode traegt.
RUECKGABE = re.compile(r"Rueckgabe\s+(-?\d+)")


def jetzt() -> float:
    return dt.datetime.now().timestamp()


def _psutil():
    try:
        import psutil                                   # noqa: PLC0415
        return psutil
    except Exception:                                   # noqa: BLE001
        return None


def prozess_mit_startzeit(pid: int):
    """(lebt, name) eines Prozesses. Reines Nachfragen, KEIN Beenden."""
    if pid <= 0:
        return False, ""
    psutil = _psutil()
    if psutil is not None:
        try:
            p = psutil.Process(pid)
            return True, p.name()
        except Exception:                               # noqa: BLE001
            return False, ""
    # Rueckfall ohne psutil: tasklist fragt nur ab.
    try:
        aus = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                                     capture_output=True, text=True, timeout=30,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        text = (aus.stdout or "").strip()
        if not text or "keine Aufgaben" in text.lower() or "no tasks" in text.lower():
            return False, ""
        return True, text.split()[0]
    except Exception:                                   # noqa: BLE001
        return False, ""


def startzeit_passt(pid: int, startzeit: float) -> bool:
    """Gehoert die gespeicherte Startzeit zu DIESEM Prozess?

    Windows vergibt PIDs wieder. Traegt eine alte Nummer inzwischen ein anderer
    Prozess, gilt der Lauf als tot (dieselbe Regel wie Agenten/Handel/sperre.py).
    Ohne psutil bleibt die Nummer der einzige Zeuge - dann gilt sie.
    """
    psutil = _psutil()
    if psutil is None:
        return True
    try:
        return abs(psutil.Process(pid).create_time() - startzeit) <= 1.0
    except Exception:                                   # noqa: BLE001
        return False


def sperre_lesen(pfad: str):
    """(pid, startzeit) aus der Sperrdatei - Format wie Agenten/Handel/sperre.py."""
    try:
        with open(pfad, encoding="ascii", errors="replace") as f:
            felder = f.read().split()
    except OSError:
        return None, None
    if not felder:
        return None, None
    try:
        pid = int(felder[0])
    except ValueError:
        return None, None
    zeit = None
    if len(felder) > 1:
        try:
            zeit = float(felder[1])
        except ValueError:
            zeit = None
    return (pid if pid > 0 else None), zeit


def protokoll_stand(pfad: str):
    """(Alter in Sekunden, letzte Zeilen) des Protokolls einer Stufe."""
    if not os.path.exists(pfad):
        return None, []
    alter = jetzt() - os.path.getmtime(pfad)
    zeilen = []
    try:
        with open(pfad, "rb") as f:
            f.seek(0, os.SEEK_END)
            groesse = f.tell()
            f.seek(max(0, groesse - 8192))
            roh = f.read().decode("utf-8", errors="replace")
        zeilen = [z for z in roh.replace("\r", "").split("\n") if z.strip()]
    except OSError:
        pass
    return alter, zeilen[-12:]


def stufe_pruefen(name: str, suffix: str):
    """Befund einer Stufe: (schluessel, text) oder (None, None) wenn gesund."""
    pid_datei = os.path.join(HANDEL, "dauerlauf%s.pid" % suffix)
    log_datei = os.path.join(HANDEL, "dauerlauf%s.log" % suffix)
    pid, startzeit = sperre_lesen(pid_datei)
    lebt, pname = prozess_mit_startzeit(pid) if pid else (False, "")
    alter, zeilen = protokoll_stand(log_datei)
    letzte = zeilen[-1] if zeilen else ""

    if pid and lebt and startzeit and not startzeit_passt(pid, startzeit):
        # PID-Wiederverwendung: eine andere Startzeit heisst anderer Prozess.
        lebt = False

    if pid and not lebt:
        # Steht die letzte Zeile auf einem Rueckgabecode, starb das Kind mit -
        # der Lauf selbst endet dann unmittelbar danach.
        for z in reversed(zeilen):
            m = RUECKGABE.search(z)
            if not m:
                continue
            code = int(m.group(1))
            if code == 143:
                return ("tot-143",
                        "Stufe %s: beendet durch SIGTERM (Rueckgabe 143) - letzte "
                        "Spur: %s. Ein Handstart mit `timeout N` erzeugt genau das; "
                        "der Waechter startet neu." % (name, z.split()[2] if len(z.split()) > 2 else "?"))
            return ("tot-code",
                    "Stufe %s: beendet, Rueckgabe %d in der letzten Spurzeile (%s)."
                    % (name, code, " ".join(z.split()[:3])))
        return ("tot-spurlos",
                "Stufe %s: steht (PID %s lebt nicht mehr, letzter Protokolleintrag "
                "%s). Kein Rueckgabecode - spurlos, dazu passt Speicherdruck "
                "(Ereignis 2004)." % (name, pid, _alter_text(alter)))

    if pid and lebt and alter is not None and alter > PROTOKOLL_ALTER_MAX_S:
        return ("haengt",
                "Stufe %s: Prozess PID %s laeuft, das Protokoll ist aber %s alt - "
                "der Lauf haengt oder schreibt nicht mehr."
                % (name, pid, _alter_text(alter)))

    if not pid and alter is not None and alter > PROTOKOLL_ALTER_MAX_S:
        return ("ohne-sperre",
                "Stufe %s: keine Sperrdatei, Protokoll %s alt - kein Lauf und keine "
                "Sperre, die ihn ankuendigt." % (name, _alter_text(alter)))
    if letzte and "Traceback" in letzte:
        return ("traceback", "Stufe %s: letzte Protokollzeile ist ein Traceback: %s"
                % (name, letzte[:160]))
    return (None, None)


def _alter_text(sekunden):
    if sekunden is None:
        return "unbekannt alt"
    if sekunden < 3600:
        return "%d min" % (sekunden // 60)
    return "%.1f h" % (sekunden / 3600)


def churn_pruefen():
    """Gehaeufte 'verwaiste Sperre' im Waechter-Protokoll = niemand kommt hoch."""
    grenze = jetzt() - CHURN_FENSTER_S
    for name, suffix in STUFEN:
        pfad = os.path.join(WRAPPER_LOGS,
                            "handel-dauerlauf-letzter-lauf%s.log" % suffix)
        if not os.path.exists(pfad):
            continue
        alt = os.path.getmtime(pfad)
        if alt < grenze:
            continue
        try:
            with open(pfad, "rb") as f:
                f.seek(max(0, os.path.getsize(pfad) - 65536))
                roh = f.read().decode("utf-8", errors="replace")
        except OSError:
            continue
        treffer = []
        for zeile in roh.replace("\r", "").split("\n"):
            if "verwaiste Sperre" not in zeile:
                continue
            try:
                wann = dt.datetime.strptime(zeile[:19], "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                continue
            if wann >= grenze:
                treffer.append(zeile)
        if len(treffer) >= CHURN_GRENZE:
            return ("churn",
                    "Stufe %s: %d verwaiste Sperren in der letzten Stunde - der "
                    "Waechter startet, der Lauf kommt nicht hoch. Letzte: %s"
                    % (name, len(treffer), treffer[-1][:19]))
    return (None, None)


def merke():
    try:
        with open(MERKDATEI, encoding="utf-8") as f:
            return json.load(f)
    except Exception:                                   # noqa: BLE001
        return {}


def schreibe_merke(daten):
    try:
        os.makedirs(os.path.dirname(MERKDATEI), exist_ok=True)
        with open(MERKDATEI, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass


def neu_zu_melden(befunde, merker, jetzt_):
    """Nur Befunde melden, deren Schluessel laenger als das Fenster her ist."""
    raus = []
    for schluessel, text in befunde:
        alt = merker.get(schluessel)
        if isinstance(alt, (int, float)) and jetzt_ - alt < MELDE_FENSTER_S:
            continue
        raus.append((schluessel, text))
    return raus


def main():
    jetzt_ = jetzt()
    befunde = []
    for name, suffix in STUFEN:
        schluessel, text = stufe_pruefen(name, suffix)
        if schluessel:
            befunde.append((schluessel, text))
    schluessel, text = churn_pruefen()
    if schluessel:
        befunde.append((schluessel, text))

    merker = merke()
    zu_melden = neu_zu_melden(befunde, merker, jetzt_)
    if not zu_melden:
        return 0
    for schluessel, text in zu_melden:
        merker[schluessel] = jetzt_
    schreibe_merke(merker)
    print("Dauerlauf-Wache (%s)" % dt.datetime.now().strftime("%d.%m. %H:%M"))
    for _, text in zu_melden:
        print("  * " + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())