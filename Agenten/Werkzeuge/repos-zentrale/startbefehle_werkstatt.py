"""T-234: Startbefehle fuer die WERKSTATT-Projekte ins Manifest eintragen.

Hausregel (aus T-234 selbst): ein Befehl kommt erst ins Manifest, wenn er
EINMAL ECHT gelaufen ist. Dieses Skript belegt das nicht mit 'der Befehl
sieht richtig aus', sondern mit zwei Dingen:

1. Der Befehl laeuft jetzt wirklich (oder das Skript sagt, warum nicht).
2. Ein Beleg-Layout wird geschrieben: die Zentrale legt fuer jeden Start
   `logs/<ordner>-<zeit>.log` mit cwd und argv an und beendet sich danach.

Aufruf (aus Agenten/Werkzeuge/repos-zentrale):
    ../../scanner/.venv/Scripts/python.py -- nein:
    "C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/scanner/.venv/Scripts/python.exe" \
        startbefehle_werkstatt.py            # Vorschau (Standard)
    ... startbefehle_werkstatt.py --anwenden  # schreibt ins Manifest
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HIER = os.path.dirname(os.path.abspath(__file__))
# ACHTUNG: `Werkstatt/` ist im BrainFiles-Baum eine JUNCTION auf O:\Werkstatt.
# In einem Worktree (.worktrees/<id>) gibt es diesen Pfad nicht - dort laeuft
# dieses Skript ins Leere. Deshalb wird die Werkstatt ueber die reale
# Repo-Wurzel aufgesucht: neben der JUNCTION zeigt `O:\Werkstatt` auf
# dieselbe Ablage, und die Junction wird in quellen.py nicht gebraucht.
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", ".."))


def _werkstatt():
    """Die Werkstatt-Ablage mit INHALT - auch aus einem Worktree heraus.

    Ein Worktree bekommt ein LEERES `Werkstatt/` (der Junctions-Eintrag ist
    versioniert, der Zielordner nicht). Deshalb zählt nicht `isdir`, sondern
    `isdir` UND ein Kind mit mindestens einem Projekt - sonst gewinnt im
    Worktree das leere Verzeichnis und jedes Projekt meldet "Ordner fehlt".
    """
    kandidaten = [os.path.join(WURZEL, "Werkstatt"), "O:/Werkstatt",
                 r"O:\Werkstatt"]
    for p in kandidaten:
        if not os.path.isdir(p):
            continue
        try:
            kinder = os.listdir(p)
        except OSError:
            continue
        if "freqtrade" in kinder or "omnitrade" in kinder:
            return p
    return os.path.join(WURZEL, "Werkstatt")


WERKSTATT = _werkstatt()
MANIFEST = os.path.join(HIER, "repos-zentrale.json")


def handel_python():
    """Der Interpreter des Handels-venvs - auch aus einem Worktree.

    Die venvs sind NICHT versioniert: im Worktree existiert
    Agenten/Handel/scanner/.venv nicht. Dann greift derselbe Hausanker wie
    ueberall im Haus - die REALE Repo-Wurzel, nicht die Worktree-Wurzel.
    """
    kandidaten = [os.path.join(WURZEL, "Agenten", "Handel", "scanner", ".venv",
                               "Scripts", "python.exe"),
                  "C:/Users/faupe/Documents/BrainFiles/Agenten/Handel/scanner/"
                  ".venv/Scripts/python.exe"]
    for p in kandidaten:
        if os.path.isfile(p):
            return p
    return kandidaten[0]


def HAUS():
    """Die REALE Repo-Wurzel - nicht die Worktree-Wurzel.

    Worktree-Wurzel: <BrainFiles>/.worktrees/<id>   (hier liegen die venvs nicht)
    Haus-Wurzel:     <BrainFiles>                   (venv, Werkstatt-Junction)
    """
    echte = "C:/Users/faupe/Documents/BrainFiles"
    if os.path.isdir(os.path.join(echte, "Agenten", "Handel", "scanner",
                                  ".venv")):
        return echte
    return WURZEL


def bash():
    """Ein bash, das es gibt - portabel fuer das Manifest.

    `bash` ohne Pfad trifft unter Windows oft den WSL-Starter (dort:
    'CreateInstance/CreateVm fehlgeschlagen'), nicht den Git-Bash. Fuer das
    MANIFEST wird aber kein absoluter Hermes-Tool-Pfad eingetragen (der wird
    beim Update ungueltig) - dort steht `bash`, und die Zentrale loest selbst
    auf. Diese Funktion liefert nur den Pfad zum FAHREN in diesem Lauf.
    """
    kandidaten = []
    pfad = os.environ.get("PATH", "")
    for eintrag in pfad.split(os.pathsep):
        if eintrag and "git" in eintrag.lower():
            kandidaten.append(os.path.join(eintrag, "bash.exe"))
    kandidaten += [r"C:\Program Files\Git\bin\bash.exe",
                   r"C:\Program Files\Git\usr\bin\bash.exe"]
    for k in kandidaten:
        if os.path.isfile(k):
            return k
    return "bash"


# (Ordner, Startbefehl, Frist in Sekunden, was der Befehl belegt)
#
# WICHTIG zum Ordner `freqtrade`: es gibt ZWEI davon. `Agenten/Handel/freqtrade`
# ist der PORTIERTE, startbare Weg (drei Bots in Docker) und traegt im
# Manifest bereits Start + Befehle. `Werkstatt/freqtrade` ist der Fremd-Klon
# von upstream (docker-compose.yml, setup.sh) - der wird NICHT gestartet,
# sondern gelesen. Ein Startbefehl auf den Fremd-Klon wuerde die Zentrale auf
# einen Weg zeigen, den das Haus nicht benutzt. Deshalb steht er hier als
# eigener Fall mit Begruendung statt als Kandidat.
FREMDE_KLONEN = {"freqtrade"}

KANDIDATEN = [
    ("omnitrade", [handel_python(),
                   os.path.join(HAUS(), "Agenten", "Handel", "omnitrade",
                                "handeln.py"), "--vorschau"],
     120, "Spur omnitrade im Vorschau-Modus (liest die Rust-Laeufe, handelt nicht)"),
    ("OmniRoute", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", os.path.join(HAUS(), "Werkstatt", "Projekte",
                                         "OmniRoute",
                                         "omniroute-quell-produktion.ps1")],
     600, "Quell-Produktionsbau starten (baut und startet den Router auf 20128)"),
]


def logs_ordner():
    pfad = os.path.join(HIER, "logs")
    os.makedirs(pfad, exist_ok=True)
    return pfad


def beleg_name(ordner):
    return "%s-%s.log" % (ordner, time.strftime("%Y%m%d-%H%M%S"))


def fahre(ordner, befehl, frist_s):
    """Der Befehl laeuft wirklich. Rueckgabe: (ok, belegpfad, letzte Zeile).

    Zwei Windows-Fallen, beide hier abgefangen:
      * Ein venv-Pfad zeigt ins Leere, wenn er ueber die Repo-Wurzel gebaut
        wurde, die selbst eine Junction ist - dann startet der Prozess nicht.
      * `powershell` schreibt cp1252, `python` utf-8; `text=True` ohne
        `errors=` bricht den Lauf mit UnicodeDecodeError ab.
    """
    cwd = os.path.join(WERKSTATT, ordner)
    if not os.path.isdir(cwd):
        return False, None, "Ordner fehlt: %s" % cwd
    # Pfade im Befehl gegen den cwd pruefen - ein relativer Programmpfad wird
    # gegen das Arbeitsverzeichnis des AUFRUFERS aufgeloest, nicht gegen cwd.
    befehl = [absolutiere(x, cwd) for x in befehl]
    pfad = os.path.join(logs_ordner(), beleg_name(ordner))
    with open(pfad, "w", encoding="utf-8", newline="") as fh:
        fh.write("# %s %s cwd=%s argv=%r\n"
                 % (ordner, datetime.now().isoformat(timespec="seconds"),
                    cwd, befehl))
        fh.flush()
        try:
            p = subprocess.run(befehl, cwd=cwd, capture_output=True, text=True,
                               timeout=frist_s, errors="replace",
                               encoding="utf-8")
        except subprocess.TimeoutExpired:
            fh.write("\nZEITUEBERSCHREITUNG nach %d s - der Befehl wurde NICHT "
                     "als belegt gewertet.\n" % frist_s)
            return False, pfad, "Zeitueberschreitung nach %d s" % frist_s
        except OSError as fehler:
            fh.write("\nSTART FEHLGESCHLAGEN: %s\n" % fehler)
            return False, pfad, "Start fehlgeschlagen: %s" % fehler
        fh.write((p.stdout or "") + (p.stderr or ""))
        fh.write("\nbeendet (Code %d)\n" % p.returncode)
    zeilen = [z for z in ((p.stdout or "") + (p.stderr or "")).splitlines() if z.strip()]
    letzte = zeilen[-1][:120] if zeilen else "(keine Ausgabe)"
    return True, pfad, letzte


def absolutiere(x, cwd):
    """Einen Programmpfad im Befehl absolut machen, wenn die Datei existiert."""
    if os.path.isabs(x) or os.sep not in x:
        return x
    if os.path.isfile(x):                      # schon absolut (C:\...)
        return x
    kandidat = os.path.join(cwd, x)
    return kandidat if os.path.isfile(kandidat) else x


def manifest_form(befehl):
    """Der Befehl in der Form, die das Manifest traegt (portabel).

    Zwei Regelungen, beide gegen die Hausregel 'keine absoluten Hermes-Pfade':
      * ein bash.exe aus Agenten/Hermes/tools/<version>/... wird zu `bash`
        (der Pfad ist beim Update ungueltig);
      * ein Pfad unter der Haus-Wurzel wird RELATIV zur Wurzel notiert,
        damit der Baum umziehbar bleibt (Agenten/..., Werkstatt/...).
    """
    haus = HAUS()
    aus = []
    for x in befehl:
        if x.lower().endswith("bash.exe") and "hermes" in x.lower():
            aus.append("bash")
            continue
        # Pfade mit gemischten Trennern zuerst vereinheitlichen
        y = x.replace("\\", "/")
        if y.startswith(haus.replace("\\", "/") + "/"):
            aus.append(y[len(haus) + 1:])
            continue
        aus.append(x)
    return aus


def manifest_laden():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anwenden", action="store_true",
                    help="Startbefehle ins Manifest schreiben (Standard: "
                         "nur fahren und zeigen)")
    args = ap.parse_args()

    d = manifest_laden()
    zeilen = d["repos"]
    nach_ordner = {}
    for x in zeilen:
        nach_ordner[(x.get("wurzel"), x.get("ordner"))] = x

    print("T-234: Startbefehle der Werkstatt-Projekte - %s"
          % ("SCHREIBEN" if args.anwenden else "VORSCHAU"))
    print()
    schreiben = bool(args.anwenden)
    # Fremd-Klonen: begruenden statt starten
    for ordner in sorted(FREMDE_KLONEN):
        eintrag = nach_ordner.get(("werkstatt", ordner))
        if eintrag is None:
            continue
        if schreiben:
            eintrag["gruppe"] = "kein_start"
            eintrag.setdefault("warnungen", []).append(
                "kein eigener Start: das ist der Fremd-Klon von upstream. Der "
                "startbare Weg ist Agenten/Handel/freqtrade (drei Bots in "
                "Docker, traegt Start + Befehle im Manifest)")
            eintrag["anleitung"] = (
                "Zum Starten die Zeile 'freqtrade' unter der Wurzel HANDEL "
                "benutzen (Start: bots.py liste; Befehl 'Bots starten' = "
                "bash bots_starten.sh). Dieser Klon liefert nur die "
                "Upstream-Dokumentation (docker-compose.yml, setup.sh).")
        print("%-12s kein Start (Fremd-Klon) - Grund in 'warnungen' notiert"
              % ordner)
    geaendert = 0
    for ordner, befehl, frist, wozu in KANDIDATEN:
        eintrag = nach_ordner.get(("werkstatt", ordner))
        if eintrag is None:
            print("%-12s kein Manifest-Eintrag (wurzel=werkstatt)" % ordner)
            continue
        if eintrag.get("start"):
            print("%-12s hat schon einen Startbefehl: %r"
                  % (ordner, eintrag["start"]))
            continue
        print("%-12s belegt: %s" % (ordner, wozu))
        ok, pfad, letzte = fahre(ordner, befehl, frist)
        print("             -> %s (Beleg: %s)"
              % (letzte, os.path.basename(pfad) if pfad else "kein Log"))
        if not ok:
            print("             NICHT eingetragen - der Befehl lief nicht sauber.")
            continue
        if args.anwenden:
            eintrag["start"] = manifest_form(befehl)
            eintrag["beleg_frist_s"] = frist
            geaendert += 1
            print("             eingetragen: %r" % (eintrag["start"],))
    if args.anwenden and geaendert:
        d["stand"] = datetime.now().date().isoformat()
        # Einrueckung wie in der Datei (2 Leerzeichen) und LF - sonst zeigt
        # git diff die GANZE Datei (T-234-Hausregel: byteweise aendern).
        with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        print()
        print("Manifest geschrieben: %d Eintraege, stand=%s" % (geaendert, d["stand"]))
    elif not args.anwenden:
        print()
        print("Vorschau - mit --anwenden wird geschrieben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())