"""Dateischwund in Agenten/Handel - gezielt, nicht flaechendeckend (T-100).

Der Auftrag
-----------
`dateischwund-wache.py` hat als Vorgabe den scripts-Ordner, und der
Scheduler kann beim Wort `script` kein Argument mitschleppen. Der Handel
Ordner war also nicht abgedeckt - obwohl T-100 dort mehrfach zugeschlagen
hat: frisch per write_file geschriebene Dateien waren Minuten spaeter weg,
nur die .pyc blieb liegen.

Warum dieser Aufrufer NICHT den Kern benutzt
--------------------------------------------
Der Kern laeuft mit `rglob('*')` ueber den ganzen Baum und liest jede Datei.
Ein Lauf ueber Agenten/Handel brauchte damit ueber viereinhalb MINUTEN -
alle fuenfzehn Minuten. Das ist kein Waechter mehr, das ist Last, und ein
Waechter, der zu teuer ist, wird abgeschaltet und damit blind. Also geht
dieser Aufrufer selbst und schaut nur dorthin, wo der Schwund tatsaechlich
auftritt: den Quelltext der Spuren, der obersten Ebene und der Testsuiten.

Ausgenommen bleiben .venv, __pycache__, logs, daten, cache, state und
sonstige Ablageordner.

Was gemeldet wird
-----------------
Nur eine Datei, die im vorigen Lauf DA war und jetzt WEG ist. Eine neue
Datei ist kein Befund - die entsteht dauernd, und eine Wache, die bei jeder
meldet, wird abgeschaltet. Dieselbe Feststellung hoechstens alle 6 Stunden.
"""
import hashlib
import json
import os
import time

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.abspath(os.path.join(HIER, "..", "..", "Handel"))
MERK = os.path.abspath(os.path.join(HIER, "..", "cache",
                                    "dateischwund-wache-handel.json"))
AUS = {".venv", "__pycache__", "logs", "daten", "cache", "state", "docs",
       "node_modules", "target", "felix-claude"}
RUHE_S = 6 * 3600


def ziele():
    """Alle beobachteten .py-Dateien: relativer Pfad -> vollstaendiger Pfad."""
    gefunden = {}
    for wurzel, ordner, dateien in os.walk(HANDEL):
        teile = set(os.path.relpath(wurzel, HANDEL).split(os.sep))
        if teile & AUS:
            ordner[:] = []          # absteigend nicht weitergehen
            continue
        for name in dateien:
            if name.endswith(".py"):
                voll = os.path.join(wurzel, name)
                gefunden[os.path.relpath(voll, HANDEL).replace(os.sep, "/")] = voll
    return gefunden


def kennung(pfad):
    try:
        with open(pfad, "rb") as fh:
            roh = fh.read()
    except OSError:
        return [-1, ""]
    return [len(roh), hashlib.sha256(roh).hexdigest()[:16]]


def speichern(daten):
    try:
        os.makedirs(os.path.dirname(MERK), exist_ok=True)
        with open(MERK, "w", encoding="utf-8") as fh:
            json.dump(daten, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def main():
    if not os.path.isdir(HANDEL):
        return 0
    ist = ziele()
    stand = {rel: kennung(voll) for rel, voll in ist.items()}

    alt, gemeldet = {}, {}
    try:
        with open(MERK, encoding="utf-8") as fh:
            daten = json.load(fh)
        alt = daten.get("stand") or {}
        gemeldet = daten.get("gemeldet") or {}
    except (OSError, ValueError):
        pass

    weg = sorted(set(alt) - set(stand))
    speichern({"stand": stand, "zeit": time.strftime("%Y-%m-%dT%H:%M"),
               "gemeldet": gemeldet})

    if not weg:
        return 0
    jetzt = time.time()
    frisch = [w for w in weg
              if jetzt - float(gemeldet.get(w, 0) or 0) >= RUHE_S]
    if not frisch:
        return 0
    for w in frisch:
        gemeldet[w] = jetzt
    speichern({"stand": stand, "zeit": time.strftime("%Y-%m-%dT%H:%M"),
               "gemeldet": gemeldet})

    print("Dateischwund in Agenten/Handel - %d Datei(en) seit dem letzten "
          "Lauf verschwunden" % len(frisch))
    print("  beobachtet: %d Quelltextdateien in %d Ordnern" % (
        len(stand), len({p.split("/")[0] for p in stand})))
    for w in frisch:
        print("  - " + w)
    print("  Nichts wurde geaendert - diese Wache holt nichts zurueck und "
          "loescht nichts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())