#!/usr/bin/env python3
"""Bereichs-Besitz pruefen: schreibt dieser Aufrufer hier (und nur hier)?

WARUM ALS WERKZEUG: die Ueberschreibungen im BrainFiles-Baum sind kein Git-
Problem, sondern ein Zuordnungsproblem. Drei Sitzungen teilen sich denselben
Arbeitsbaum; jede darf ueberall schreiben, also gewinnt der Schnellere. Der
geteilte Index ist nur das spaeteste Symptom. Die Hausloesung ist Regelwerk,
nicht Isolation (der Vorschlag, jeder Sitzung einen eigenen Git-Zweig zu geben,
wurde gemessen verworfen - er macht die Ueberschreibung WORSE, weil fremde
Aenderungen als Branch-Differenz statt als ruhende Datei wiederkommen).

Drei Bereiche, von Max am 04.10.2026 bestaetigt, mit genau einem Besitzer je
Bereich (Agenten/BEREICHE.json):
  handel   Agenten/Handel/
  bot      Agenten/Bus/, Agenten/Hermes/skills/, Agenten/Hermes/profiles/,
           Agenten/MCP-Manifest.json
  wissen   MaxHirn/Wissen/, MaxHirn/Archiv/TASKS.md
Alles andere ist FREI. Ein Bereich sperrt seinen Elternordner nicht, und die
Sperre wuerde sonst den groessten Teil des Baums stilllegen - Nutzen nil.

WAS ES TUT
  1. Register laden (JSON) und gegen das Repo pruefen: jeder Bereichsortierer
     muss wirklich existieren, jeder Bereich genau einmal vorkommen. Fehlender
     Ordner oder Doppeleintrag ist ein FEHLER, kein stiller Durchlass.
  2. `besitzer(pfad)` - welcher Bereich gilt fuer diesen Pfad? Laengster
     Ordner-Praefix gewinnt, damit ein Unterordner nicht durch seinen Eltern-
     ordner falsch zugeordnet wird.
  3. `pruefe(aufrufer, pfad)` - der eigentliche Wächter. Drei Ausgaenge:
     `erlaubt` (frei, oder Aufrufer IST der Besitzer), `gesperrt` (ein anderer
     Bereich besitzt den Pfad - das ist der Befund, den man sehen will), und
     `fremd` (der Pfad gehoert zu einem Bereich, der gar nicht existiert).
  4. Bericht/TEXT-Ausgabe fuer eine Liste von Pfaden, damit ein Lauf ueber den
     Arbeitsbaum KONFLIKTE zeigt statt still zu sein.

WAS ES NICHT TUT
  - NICHTS schreiben, NICHTS sperren, NICHTS blockieren. Es ist ein Messgeraet;
    die Sperre setzt die Regel im jeweiligen Werkzeug (siehe `MERKSATZ` im
    Skill). Ein Werkzeug, das im fremden Bereich schreibt, wird nicht blockiert
    sondern vorher gemeldet.
  - Keine Rechte, keine Geheimnisse. Das Register nennt Ordner, keine Inhalte.
  - Kein Pfad wird aufgelöst, der nicht existiert - die Frage ist der Pfad, den
    jemand schreiben WILL, nicht der, der gerade da ist.

MERKSATZ FUER DEN EINBAU (der Grund, warum es Python ist und kein Text):
EINE Regel in JEDEN Weg, der denselben Zustand schreibt. Wer den Roster nur
im Skill beschreibt, hat eine Regel, die beim naechsten Umbau wegfaellt. Der
Aufrufer soll `pruefe(aufrufer, pfad)` VOR dem Schreiben rufen und das Ergebnis
als Befund melden, nicht als Exception werfen.

Gegenprobe: derselbe Aufrufer muss denselben Pfad zweimal pruefen koennen und
beide Male dasselbe bekommen (die Antwort darf nicht vom Aufruf abhaengen), ein
Pfad ohne Bereich muss IMMER `erlaubt` sein, und ein Aufrufer, der nicht der
Besitzer ist, muss `gesperrt` bekommen - sonst waere die ganze Regel eine
Dekoration.

Aufruf:
    python Agenten/Werkzeuge/bereiche.py                       # Register pruefen
    python Agenten/Werkzeuge/bereiche.py --aufrufer handel     # Pfade von stdin pruefen
    python Agenten/Werkzeuge/bereiche.py --baum                 # ganze Repo-Sicht
    python Agenten/Werkzeuge/bereiche.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

REGISTER = os.path.join("Agenten", "BEREICHE.json")
FREI = "erlaubt"
GESPERRT = "gesperrt"
FREMDBEREICH = "fremd"
ANFANG = "### alle Bereiche unter diesem Pfad sind frei"


class RegisterFehler(RuntimeError):
    pass


def _norm(p):
    """Pfade vergleichen, nicht Zeichenketten: `git status` liefert
    Schraegstriche, `os.path.join` Backslashes, und ein Grossbuchstaben-Unterschied
    im Laufwerksbuchstaben waere sonst ein stiller Fehlbefund."""
    p = (p or "").strip().replace("\\", "/")
    while "//" in p:
        p = p.replace("//", "/")
    if len(p) > 1:
        p = p.rstrip("/")
    return p.lower()


def _pfad_nach_root(p):
    """Relativ zur Repo-Wurzel fuehren, damit ein Aufrufer aus jeder Lage
    denselben Pfad meldet. Ein absoluter Pfad unter der Wurzel wird erkannt
    und abgeschnitten; alles andere bleibt, wie es ist (und wird dann
    `_passt_zu` nicht treffen -> FREI)."""
    root = repo_wurzel()
    p = os.path.abspath(p)
    try:
        if os.path.normcase(p).startswith(os.path.normcase(root + os.sep)):
            return _norm(os.path.relpath(p, root))
    except ValueError:
        pass
    return _norm(p)


def repo_wurzel():
    """Die Repo-Wurzel: `.git` von hier aus aufwaerts. Kein Pfad geraten, kein
    absoluter Pfad im Code - das Werkzeug laeuft aus jeder Lage."""
    hier = os.path.dirname(os.path.abspath(__file__))
    for start in (hier, os.getcwd()):
        cur = os.path.abspath(start)
        for _ in range(6):
            if os.path.isdir(os.path.join(cur, ".git")):
                return cur
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    raise RegisterFehler("keine .git-Wurzel gefunden (cwd=%s)" % os.getcwd())


def _existiert(root, rel):
    """Ein Bereichseintrag kann ORDNER oder DATEI sein (TASKS.md und
    MCP-Manifest.json sind Einzeldateien). Beides ist zulaessig - `os.path.isdir`
    allein wuerde beide als 'toter Bereich' melden und damit einen korrekten
    Registerstand als Fehler ausgeben (gemessen 04.10.2026: beide wurden
    gemeldet, obwohl sie genau das sind, was sie sein sollen)."""
    return os.path.exists(os.path.join(root, rel.replace("/", os.sep)))


def lade_register(pfad=None):
    root = repo_wurzel()
    p = os.path.join(root, REGISTER) if not pfad else pfad
    if not os.path.exists(p):
        raise RegisterFehler("Register fehlt: %s" % p)
    with open(p, encoding="utf-8") as f:
        try:
            daten = json.load(f)
        except ValueError as e:
            raise RegisterFehler("Register ist kein gueltiges JSON: %s" % e)
    for pflicht in ("_bereiche", "_regeln"):
        if pflicht not in daten:
            raise RegisterFehler("Register ohne %s" % pflicht)
    return daten


def pruefe_register(daten, root=None):
    """Jeder Bereich genau einmal, jeder Ordner wirklich im Repo. Ein toter
    Bereich ist ein Fehler: er sperrt nichts und verwirrt doch jeden, der die
    Liste liest."""
    root = root or repo_wurzel()
    fehler, gesehen = [], {}
    bereiche = daten["_bereiche"]
    for i, b in enumerate(bereiche):
        for pflicht in ("id", "besitzer", "ordner"):
            if pflicht not in b:
                fehler.append("Bereich %d ohne Feld %r" % (i, pflicht))
        if "id" in b:
            if b["id"] in gesehen:
                fehler.append("Bereich %r doppelt (Index %d und %d)"
                              % (b["id"], gesehen[b["id"]], i))
            gesehen[b["id"]] = i
        for o in b.get("ordner", []):
            if not _existiert(root, o):
                fehler.append("Bereich %r: Pfad %r existiert nicht"
                              % (b.get("id"), o))
    for eig, o in _alle_ordner(daten):
        besitzer = eig["besitzer"]
        if not besitzer:
            fehler.append("Bereich %r ohne Besitzer" % eig.get("id"))
        elif not isinstance(besitzer, str) or not besitzer.strip():
            fehler.append("Bereich %r: Besitzer leer" % eig.get("id"))
    # Ein Ordner darf nicht ZWEI Bereichen gehoeren - das waere die
    # Ueberlappung, die das Register ausschliessen soll.
    besitzer_von = {}
    for eig in bereiche:
        for o in eig.get("ordner", []):
            k = _norm(o)
            alt = besitzer_von.get(k)
            if alt and alt != eig["id"]:
                fehler.append("Ordner %r gehoert zu %r UND %r" % (o, alt, eig["id"]))
            besitzer_von[k] = eig["id"]
    return fehler, besitzer_von


def _alle_ordner(daten):
    for b in daten["_bereiche"]:
        for o in b.get("ordner", []):
            yield b, o


def besitzer(pfad, daten=None, root=None):
    """Welcher Bereich gilt fuer diesen Pfad? Laengster Ordner-Praefix
    gewinnt. `None` = der Pfad ist frei (kein Bereich besitzt ihn)."""
    daten = daten or lade_register()
    root = root or repo_wurzel()
    ziel = _pfad_nach_root(pfad) if os.path.isabs(pfad) else _norm(pfad)
    treffer, laenge = None, -1
    for b in daten["_bereiche"]:
        for o in b.get("ordner", []):
            k = _norm(o)
            if ziel == k or ziel.startswith(k + "/"):
                if len(k) > laenge:
                    treffer, laenge = b, len(k)
    return treffer


def pruefe(aufrufer, pfad, daten=None, root=None):
    """DER Wächter. Gibt (urteil, begruendung) zurueck - ein Urteil, kein
    Exception: der Aufrufer soll den Befund melden koennen, nicht crashen."""
    daten = daten or lade_register()
    aufrufer = (aufrufer or "").strip().lower()
    b = besitzer(pfad, daten, root)
    # Fuer den BERICHT den Pfad so zeigen, wie er geschrieben wurde. Intern wird
    # er klein geschrieben (`_norm`), damit `Agenten/` und `agenten/` denselben
    # Bereich treffen - fuer das Auge ist eine kleingeschriebene Pfadangabe
    # aber eine Fehlanzeige des Werkzeugs, kein Befund (gemessen 04.10.2026).
    anzeige = (pfad or "").strip()
    if anzeige:
        zeige = anzeige.replace("\\", "/")
    else:
        zeige = _pfad_nach_root(pfad)
    if b is None:
        return FREI, "%s ist keinem Bereich zugewiesen" % zeige
    if aufrufer == b["besitzer"]:
        return FREI, "%s gehoert %r - %r darf" % (zeige, b["id"], aufrufer)
    return GESPERRT, ("%s gehoert Bereich %r (Besitzer %r), Aufrufer ist %r - "
                      "anderer Bereich darf hier nicht schreiben"
                      % (zeige, b["id"], b["besitzer"], aufrufer or "(nicht angegeben)"))


def text_bericht(daten, pfade, aufrufer=None, root=None):
    """Der Bericht muss die DREI Ausgaenge unterscheiden: der Pfad ist dem
    Aufrufer eigen, der Pfad ist FREI, oder der Pfad gehoert einem anderen
    Bereich. "Keine Konflikte: alle N Pfade sind frei oder gehoeren 'bot'"
    las sich bei einem freien Pfad wie eine Zusage - gehoeren hat er niemandem
    (gemessen 04.10.2026, dort war es Agenten/Routinen/). Die Zahlen stehen
    deshalb einzeln da, und ohne Aufrufer wird jeder freie Pfad als 'frei'
    gezeigt statt still weggelassen."""
    z = []
    if aufrufer:
        z.append("Aufrufer: %s" % aufrufer)
        z.append("")
    konflikte, eigen, frei = [], [], []
    for p in pfade:
        if aufrufer:
            urteil, grund = pruefe(aufrufer, p, daten, root)
            if urteil == GESPERRT:
                konflikte.append((p, grund))
            elif besitzer(p, daten, root) is None:
                frei.append(p)
            else:
                eigen.append(p)
        else:
            b = besitzer(p, daten, root)
            if b:
                z.append("  %-46s -> %s (%s)" % (p, b["id"], b["besitzer"]))
            else:
                z.append("  %-46s -> frei" % p)
    if aufrufer:
        z.append("eigen: %d | frei: %d | KONFLIKT: %d (von %d Pfaden)"
                 % (len(eigen), len(frei), len(konflikte), len(pfade)))
        for p, g in konflikte:
            z.append("  %s" % g)
    return "\n".join(z)

def _status_pfade(root, grenze=400):
    """Die Pfade, die gerade im Baum stehen - `git status --porcelain` liest
    nur die erste Spalte, damit 'MM' als 'M' und nicht als zwei Pfade
    durchgeht."""
    proc = subprocess.run(["git", "-C", root, "status", "--porcelain"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=90)
    if proc.returncode != 0:
        return []
    pfade = []
    for z in proc.stdout.splitlines():
        if len(z) < 4:
            continue
        p = z[3:].strip().strip('"')
        if " -> " in p:  # Umbenennung: nur das Ziel zaehlt
            p = p.split(" -> ", 1)[1]
        if p:
            pfade.append(p)
    return pfade[:grenze]


def _staged_pfade(root):
    """Die Pfade im Index (`git diff --cached`), ohne Loeschungen auszulassen:
    auch eine geloeschte Datei im fremden Bereich ist ein Schreibzugriff."""
    proc = subprocess.run(["git", "-C", root, "diff", "--cached", "--name-only",
                           "-z"], capture_output=True, encoding="utf-8",
                          errors="replace", timeout=90)
    if proc.returncode != 0:
        return []
    return [p for p in proc.stdout.split("\0") if p]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Pruefen, ob ein Aufrufer einen Pfad bedienen darf (Besitz-Register).")
    ap.add_argument("--aufrufer", default=None, help="handel | bot | wissen")
    ap.add_argument("--pfad", action="append", default=[],
                    help="zu pruefender Pfad (mehrfach); ohne Angabe von stdin")
    ap.add_argument("--baum", action="store_true",
                    help="alle geaenderten Pfade im Arbeitsbaum pruefen")
    ap.add_argument("--staged", action="store_true",
                    help="Pre-commit-Modus: Pfade aus dem Index, Aufrufer aus "
                         "--aufrufer oder $BRAINFILES_BEREICH; ohne Aufrufer "
                         "wird nicht geprueft (Exit 0)")
    ap.add_argument("--register", action="store_true", help="nur das Register pruefen")
    ap.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    ap.add_argument("--wurzel", default=None, help="Repo-Wurzel (Vorgabe: selbst finden)")
    args = ap.parse_args(argv)

    root = args.wurzel or repo_wurzel()
    daten = lade_register(os.path.join(root, REGISTER))
    fehler, _ = pruefe_register(daten, root)

    if args.staged:
        # Ein Commit-Hook kennt den Aufrufer nicht von selbst. Wer sich nicht
        # als Bereich ausweist (Max von Hand, Routinen wie kb-sync), wird nicht
        # blockiert - sonst stuende der ganze Baum still. Ein Register-
        # Fehler blockiert nicht: ein Hook, der wegen eines kaputten Registers
        # jeden Commit verweigert, wird nach dem ersten Mal abgeschaltet.
        args.aufrufer = args.aufrufer or os.environ.get("BRAINFILES_BEREICH")
        if not args.aufrufer:
            return 0
        pfade = _staged_pfade(root)
        konflikte = [p for p in pfade
                     if pruefe(args.aufrufer, p, daten, root)[0] == GESPERRT]
        if konflikte:
            print("bereiche: Commit verweigert - Aufrufer %r schreibt in fremde "
                  "Bereiche:" % args.aufrufer, file=sys.stderr)
            for p in konflikte:
                print("  " + pruefe(args.aufrufer, p, daten, root)[1],
                      file=sys.stderr)
            print("Fremdes aus dem Index nehmen (git restore --staged <pfad>) "
                  "oder den Besitzer arbeiten lassen.", file=sys.stderr)
            return 1
        return 0

    pfade = list(args.pfad)
    if args.baum:
        pfade = _status_pfade(root)
    elif not pfade and not sys.stdin.isatty():
        pfade = [z.strip() for z in sys.stdin.read().splitlines() if z.strip()]

    # Nur-Register-Modus: ohne Pfadliste wird das Register selbst geprueft.
    if args.register and not pfade:
        if args.json:
            print(json.dumps({"fehler": fehler, "bereiche": [
                {"id": b["id"], "besitzer": b["besitzer"], "ordner": b["ordner"]}
                for b in daten["_bereiche"]]}, ensure_ascii=False, indent=2))
            return 1 if fehler else 0
        print("Register: %s" % os.path.join(root, REGISTER))
        for b in daten["_bereiche"]:
            print("  %-9s Besitzer %-8s  %s" % (b["id"], b["besitzer"],
                                                ", ".join(b["ordner"])))
        if fehler:
            print("")
            print("FEHLER (%d):" % len(fehler))
            for f in fehler:
                print("  %s" % f)
            return 1
        print("")
        print("Register ist in Ordnung: %d Bereiche, jeder Pfad existiert, "
              "jeder Bereich genau einmal." % len(daten["_bereiche"]))
        return 0

    # Exitcode: ein Konflikt ist ein BEFUND und muss als Fehler herauskommen,
    # sonst findet ein Aufrufer (oder ein Cron) die Zeile nur im Text und
    # meldet "alles ok". 1 = mindestens ein Konflikt ODER ein Registerfehler.
    konflikte = []
    for p in pfade:
        if args.aufrufer and pruefe(args.aufrufer, p, daten, root)[0] == GESPERRT:
            konflikte.append(p)

    if args.json:
        zeilen = []
        for p in pfade:
            urteil, grund = pruefe(args.aufrufer, p, daten, root)
            zeilen.append({"pfad": p, "ergebnis": urteil, "begruendung": grund})
        print(json.dumps({"aufrufer": args.aufrufer, "register_fehler": fehler,
                          "konflikte": konflikte, "pfade": zeilen},
                         ensure_ascii=False, indent=2))
        return 1 if (fehler or konflikte) else 0

    print(text_bericht(daten, pfade, args.aufrufer, root))
    return 1 if (fehler or konflikte) else 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except RegisterFehler as e:
        print("FEHLER: %s" % e, file=sys.stderr)
        sys.exit(2)