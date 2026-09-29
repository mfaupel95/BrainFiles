"""Faehrt jede Testsuite des Handel-Baums und meldet Abweichungen.

WARUM ES DIESE DATEI GIBT
    Bis zum 29.09.2026 hat im Handel-Baum nie jemand alle Tests gefahren.
    Der Workflow unter Handel/.github/workflows/ci.yml war toter Text: er
    lag nicht im Wurzelverzeichnis des Repositories (GitHub Actions liest
    nur dort), er war nicht einmal versioniert, und er horchte auf die
    Zweige "main" und "develop", die es hier nicht gibt. Folge: rund 1300
    Tests in 34 Ordnern sind nie gelaufen.

DER AUFRUFORT ENTSCHEIDET
    Eine Spur-Testdatei setzt sich ihren Suchpfad selbst, ungefaehr so:

        for p in (scanner, xperp, HANDEL, HIER):
            if p not in sys.path:
                sys.path.insert(0, p)

    Steht HIER (der Spur-Ordner) schon im Suchpfad - und das tut er, wenn
    man aus dem Spur-Ordner heraus startet, weil Python das
    Arbeitsverzeichnis voranstellt - dann ueberspringt die Bedingung ihn,
    und scanner/ landet davor. "import handeln" trifft dann das falsche
    Modul: jede Spur hat ein eigenes handeln.py.

    Deshalb startet dieser Laeufer jede Suite aus IHREM tests-Ordner
    heraus, so wie es die Docstrings der Tests seit jeher vorschreiben.
    Aus dem Spur-Ordner gestartet meldeten dieselben Tests 188 Fehler,
    die es nicht gibt. Diese Zeile ist der ganze Unterschied:

        cwd = <spur>/tests   statt   cwd = <spur>

DIE BASISLINIE
    Ein Teil der Suiten ist heute rot. Waere dieser Laeufer schlicht
    scharf, meldete er ab dem ersten Tag Fehler und man wuerde ihn
    wegklicken. Er vergleicht darum gegen testlauf_basis.json - den
    bekannten Stand - und wird nur bei VERSCHLECHTERUNG rot. Was neu
    kaputtgeht, faellt sofort auf; was schon kaputt war, steht als
    Schuld in der Datei und schrumpft Spur fuer Spur.

    Die Zahlen stehen in der JSON, nicht hier - die Regel aus AGENTS.md.

AUFRUF
    python testlauf.py                  # pruefen, Exit 1 bei Rueckschritt
    python testlauf.py --nur tests      # eine einzelne Suite
    python testlauf.py --basis-schreiben  # die Basislinie neu setzen
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
BASIS_DATEI = os.path.join(HIER, "testlauf_basis.json")

# "Ran 25 tests in 0.177s" und "FAILED (failures=2, errors=5)"
GELAUFEN = re.compile(r"^Ran (\d+) tests?", re.M)
GESCHEITERT = re.compile(r"^FAILED \((.*)\)", re.M)
ZAHL = re.compile(r"(failures|errors)=(\d+)")


def suiten():
    """Jeder tests-Ordner bis zwei Ebenen tief, alphabetisch.

    Zwei Ebenen, weil der Baum genau so gebaut ist: Handel/tests und
    Handel/<spur>/tests. Tiefer liegt nichts, und .venv-Ordner tragen
    fremde Testsammlungen, die uns nichts angehen.
    """
    gefunden = []
    for eintrag in sorted(os.listdir(HIER)):
        voll = os.path.join(HIER, eintrag)
        if eintrag == "tests" and os.path.isdir(voll):
            gefunden.append("tests")
        elif os.path.isdir(voll) and not eintrag.startswith("."):
            if eintrag in ("OpenAlice", "daten", "__pycache__"):
                continue
            unter = os.path.join(voll, "tests")
            if os.path.isdir(unter):
                gefunden.append(eintrag + "/tests")
    return sorted(gefunden)


def lies_basis():
    try:
        with open(BASIS_DATEI, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return {"zeitlimit_sekunden": 900, "stand": {}}


def fahre(suite, zeitlimit, python=None, ort="tests"):
    """Eine Suite fahren und (tests, fehler, hinweis) zurueckgeben.

    ort waehlt das Arbeitsverzeichnis: "tests" ist der Normalfall (siehe
    Modulkopf), "spur" der Spur-Ordner darueber. Beides kommt vor, weil
    die Testdateien ihren Suchpfad selbst setzen und das nicht ueberall
    gleich tun: orb und orbk laden aus dem tests-Ordner heraus nur ein
    Fuenftel ihrer Tests. Welche Suite welchen Ort braucht, steht in
    testlauf_basis.json unter "aufrufort" - gemessen, nicht geraten.

    fehler ist -1, wenn kein Ergebnis zustande kam (Zeitlimit oder
    Absturz vor der Zusammenfassung). Das ist nicht dasselbe wie null
    Fehler und darf nie als Fortschritt durchgehen.
    """
    ordner = os.path.join(HIER, suite.replace("/", os.sep))
    if ort == "spur":
        ordner = os.path.dirname(ordner)
    befehl = [python or sys.executable, "-m", "unittest",
              "discover", "-s", ".", "-p", "test_*.py"]
    try:
        ergebnis = subprocess.run(befehl, cwd=ordner, timeout=zeitlimit,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
    except subprocess.TimeoutExpired:
        return 0, -1, "Zeitlimit von %d s ueberschritten" % zeitlimit
    except OSError as fehler:
        return 0, -1, "nicht startbar: %s" % fehler

    text = ergebnis.stdout.decode("utf-8", errors="replace")
    lauf = GELAUFEN.search(text)
    if lauf is None:
        return 0, -1, "keine Zusammenfassung - Suite bricht vorher ab"
    anzahl = int(lauf.group(1))

    schlecht = GESCHEITERT.search(text)
    if schlecht is None:
        return anzahl, 0, ""
    summe = sum(int(n) for _, n in ZAHL.findall(schlecht.group(1)))
    return anzahl, summe, schlecht.group(1)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--nur", help="nur diese eine Suite fahren")
    p.add_argument("--basis-schreiben", action="store_true",
                   help="das Ergebnis als neue Basislinie ablegen")
    p.add_argument("--python", help="Abweichender Interpreter")
    a = p.parse_args()

    basis = lies_basis()
    zeitlimit = basis.get("zeitlimit_sekunden", 900)
    stand = basis.get("stand", {})

    liste = [a.nur] if a.nur else suiten()
    neu = {}
    rueckschritte = []
    fortschritte = []

    orte = basis.get("aufrufort", {})
    for suite in liste:
        tests, fehler, hinweis = fahre(suite, zeitlimit, a.python,
                                       orte.get(suite, "tests"))
        neu[suite] = {"tests": tests, "fehler": fehler}
        war = stand.get(suite)
        marke = "??"
        if fehler == 0:
            marke = "ok"
        elif fehler < 0:
            marke = "!!"
        else:
            marke = "%2d" % fehler
        print("%s  %-28s %4d Tests  %s"
              % (marke, suite, tests, hinweis))

        if war is None:
            continue
        # Ein unbekanntes Ergebnis (-1) ist immer ein Rueckschritt, auch
        # wenn die Basislinie schon Fehler kannte: wir wissen nichts.
        if fehler < 0 <= war["fehler"]:
            rueckschritte.append((suite, war["fehler"], fehler))
        elif fehler > war["fehler"] >= 0:
            rueckschritte.append((suite, war["fehler"], fehler))
        elif 0 <= fehler < war["fehler"]:
            fortschritte.append((suite, war["fehler"], fehler))

    if a.basis_schreiben:
        basis["stand"] = neu if not a.nur else dict(stand, **neu)
        with open(BASIS_DATEI, "w", encoding="utf-8", newline="\n") as f:
            json.dump(basis, f, indent=2, ensure_ascii=False,
                      sort_keys=True)
            f.write("\n")
        print("\nBasislinie geschrieben: %s" % os.path.basename(BASIS_DATEI))
        return 0

    for suite, war, ist in fortschritte:
        print("\nBESSER  %s: %d -> %d Fehler. Basislinie nachziehen mit "
              "--basis-schreiben." % (suite, war, ist))
    if not rueckschritte:
        print("\nKein Rueckschritt gegenueber der Basislinie.")
        return 0
    for suite, war, ist in rueckschritte:
        print("\nSCHLECHTER  %s: %s -> %s Fehler"
              % (suite, war, "unbekannt" if ist < 0 else ist))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
