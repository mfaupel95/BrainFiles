#!/usr/bin/env python3
"""Fremd-Klone in Werkstatt auf den Stand ihrer Quelle bringen.

WARUM ALS WERKZEUG: die Flotte waechst (29 Klone am 21.09.2026) und jede
Handbewegung je Repo ist eine Gelegenheit, den falschen Zweig zu ziehen. Das
Skript macht fuer alle dieselbe Rechnung und schreibt sie auf.

WAS ES TUT (je Repo, in dieser Reihenfolge)
  1. Quelle bestimmen: `upstream`, wenn vorhanden, sonst `origin`.
  2. Standardzweig der Quelle erfragen (`git ls-remote --symref <remote> HEAD`)
     - NICHT geraten: die Klone liegen auf main, master, dev, v8, github-main.
  3. `git fetch <remote> <zweig>` (shallow-Klone: mit --depth=1, sonst volle
     Historie).
  4. Zaehlen, wie viele Commits der Klon hinterher ist.
  5. Ist er hinterher UND der Arbeitsbaum sauber: `git merge --ff-only`. Nur
     vorspulen, nie zusammenfuehren - ein Fremd-Repo mit eigenem Merge ist
     spaeter nicht mehr auseinanderzuhalten.
  6. Ist der Arbeitsbaum schmutzig: NICHT anfassen, nur melden (die Klone
     tragen .env, .venv, lokale Anpassungen).
  7. Steht das Repo auf AUSGENOMMEN: nur MESSEN (fetch + Rueckstand zaehlen),
     nie vorspulen - dort laufen Prozesse, die einen Stand mitten im Betrieb
     nicht vertragen (moon-dev-ai-agents: kraken_agent laeuft).

WAS ES NICHT TUT
  - keine eigenen Commits, kein Push, kein Rebase, kein Aufloesen von Konflikten,
  - keine Datei im Arbeitsbaum aendern, die nicht Git selbst schreibt,
  - nicht `--unshallow` (das ist ein eigener, gezielter Eingriff fuer Pushes),
  - keine Datei in AUSGENOMMEN anfassen (auch nicht mit --anwenden).

Aufruf (aus der Repo-Wurzel oder von ueberall):
    python Agenten/Werkzeuge/repos-updaten.py --trocken     # nur zeigen
    python Agenten/Werkzeuge/repos-updaten.py               # vorspulen
    python Agenten/Werkzeuge/repos-updaten.py --nur ProjectAtlas OpenTerminal
    python Agenten/Werkzeuge/repos-updaten.py --ausser Winget-cli
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
REPOS = WURZEL / "Werkstatt"
STAND = WURZEL / "Agenten" / "Hermes" / "cache" / "repos-update.json"

# Nur messen, nie vorspulen: in diesen Klonen laeuft ein Prozess, der an
# verfolgten Dateien haengt (moon-dev-ai-agents: kraken_agent, Dauerlauf).
AUSGENOMMEN = {"moon-dev-ai-agents"}


def git(verz: Path, *args: str, t: int = 180):
    r = subprocess.run(["git", "-C", str(verz), *args], capture_output=True,
                       text=True, timeout=t)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def quelle(verz: Path):
    """(Remote, Zweig) der Quelle - upstream hat Vorrang vor origin."""
    _, remotes, _ = git(verz, "remote")
    remote = "upstream" if "upstream" in remotes.split() else "origin"
    rc, aus, _ = git(verz, "ls-remote", "--symref", remote, "HEAD", t=120)
    zweig = None
    if rc == 0:
        for z in aus.splitlines():
            if z.startswith("ref:") and z.endswith("HEAD"):
                zweig = z.split()[1].split("/", 2)[-1]
    if not zweig:                     # Rueckfall: lokaler Zweigname
        _, b, _ = git(verz, "rev-parse", "--abbrev-ref", "HEAD")
        zweig = b or "main"
    return remote, zweig


def eins(v: Path, trocken: bool, ausser: set[str] = frozenset()):
    name = v.name
    e = {"repo": name, "stand": ""}
    _, branch, _ = git(v, "rev-parse", "--abbrev-ref", "HEAD")
    _, dirty, _ = git(v, "status", "--porcelain")
    zeilen = [z for z in dirty.splitlines() if z.strip()]
    # Nur UNVERFOLGTE Dateien ("??") sind harmlos: ein Vorspulen laesst sie
    # liegen (die Klone tragen fast alle ein untracked .env.template). Aenderungen
    # an verfolgten Dateien sperren den Klon - ein Fremd-Repo mit eigenen
    # Aenderungen wuerde beim Vorspulen ueberschrieben.
    e["unverfolgt"] = len([z for z in zeilen if z.startswith("??")])
    e["schmutzig"] = len([z for z in zeilen if not z.startswith("??")])
    e["zweig"] = branch
    _, shallow, _ = git(v, "rev-parse", "--is-shallow-repository")
    e["shallow"] = shallow == "true"
    remote, zweig = quelle(v)
    e["quelle"] = "%s/%s" % (remote, zweig)
    if e["zweig"] != zweig:
        e["stand"] = "Zweig %s statt %s - nicht angefasst" % (e["zweig"], zweig)
        e["stand"] = "anderer Zweig"
        return e
    args = ["fetch", remote, zweig]
    if e["shallow"]:
        args += ["--depth=1"]
    rc, _, err = git(v, *args)
    if rc != 0:
        e["stand"] = "fetch fehlgeschlagen"
        e["fehler"] = err.splitlines()[-1][:160] if err else ""
        return e
    rc, hinter, _ = git(v, "rev-list", "--count", "HEAD..FETCH_HEAD")
    e["hinter"] = int(hinter or 0)
    if name.lower() in {a.lower() for a in ausser}:
        # Gemessen wird auch hier (der Rueckstand gehoert in den Bericht),
        # gespult wird nie - im Klon laeuft ein Prozess.
        e["stand"] = ("ausgenommen (laeuft), aktuell" if not e["hinter"]
                      else "ausgenommen (laeuft), %d Commits Rueckstand" % e["hinter"])
        return e
    if e["hinter"] == 0:
        e["stand"] = "aktuell"
        return e
    if e["schmutzig"]:
        e["stand"] = "uebersprungen (lokale Aenderungen)"
        return e
    if trocken:
        e["stand"] = "waere zu spulen (%d Commits)" % e["hinter"]
        return e
    rc, _, err = git(v, "merge", "--ff-only", "FETCH_HEAD")
    if rc != 0 and "unrelated histories" in err:
        # Shallow-Klon: mit --depth=1 fehlt der gemeinsame Vorfahr, das Vorspulen
        # wird abgelehnt. Erst die Historie holen, dann erneut spulen. Gemessen am
        # 21.09.2026 an OpenTerminal und santiment (beide 1-4 Commits hinterher).
        git(v, "fetch", "--unshallow", remote, zweig, t=600)
        rc, _, err = git(v, "merge", "--ff-only", "FETCH_HEAD")
    if rc != 0:
        e["stand"] = "Vorspulen fehlgeschlagen"
        e["fehler"] = err.splitlines()[-1][:160] if err else ""
        return e
    rf, vorher, _ = git(v, "rev-parse", "--short", "HEAD")
    e["stand"] = "vorgespult"
    e["neu"] = vorher
    return e


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--trocken", action="store_true", help="nur zeigen, nicht vorspulen")
    p.add_argument("--anwenden", action="store_true",
                   help="vorspulen (Standard; --trocken ist das Gegenteil)")
    p.add_argument("--nur", nargs="*", help="nur diese Repos")
    p.add_argument("--ausser", nargs="*", default=[],
                   help="diese Repos nur messen, nie vorspulen")
    a = p.parse_args()
    trocken = a.trocken and not a.anwenden
    ausser = set(AUSGENOMMEN) | {n for n in (a.ausser or [])}

    if not REPOS.is_dir():
        print("Repos-Ordner fehlt: %s" % REPOS)
        return 2
    # Seit dem Umzug 14.10.2026 liegen die Klone direkt in Werkstatt. Nicht zur
    # Flotte gehoeren Ablagen, Archive und Arbeitsbaeume - dort nichts holen.
    SKIP_NAMEN = {
        "Ausgemustert", "Worktrees", "repos-verschoben-aus-skills", "privkopie",
        "Sitzungen", "Ablage", "Austausch", "Projekte", "Logs", "Protokolle",
        "Ausgabe", "node_modules", "Altlasten", "Autostart",
    }
    ordner = sorted(
        d for d in REPOS.iterdir()
        if (d / ".git").exists()
        and d.name not in SKIP_NAMEN
        and not d.name.startswith(("Altlasten", "Sicherung-eingebettet",
                                   "zustand-sicherung", "zusammenfuehrung"))
    )
    if a.nur:
        wollen = {n.lower() for n in a.nur}
        ordner = [d for d in ordner if d.name.lower() in wollen]

    ergebnisse = [eins(d, trocken, ausser) for d in ordner]
    STAND.parent.mkdir(parents=True, exist_ok=True)
    STAND.write_text(json.dumps(ergebnisse, indent=1, ensure_ascii=False),
                     encoding="utf-8")

    zaehler = {}
    for e in ergebnisse:
        zaehler[e["stand"].split(",")[0]] = zaehler.get(e["stand"].split(",")[0], 0) + 1
    print("Geprueft: %d Klone%s" % (len(ergebnisse),
                                    "  (Trockenlauf)" if trocken else ""))
    for name, n in sorted(zaehler.items(), key=lambda kv: -kv[1]):
        print("  %-40s %d" % (name, n))
    print()
    for e in ergebnisse:
        if e["stand"] == "aktuell":
            continue
        print("%-30s %-42s %-28s %s%s" % (e["repo"], e["stand"], e.get("quelle", ""),
                                          ("Rueckstand %s" % e["hinter"]) if e.get("hinter") else "",
                                          ("  " + e.get("fehler", "")) if e.get("fehler") else ""))
    print("\nStand geschrieben: %s" % STAND.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
