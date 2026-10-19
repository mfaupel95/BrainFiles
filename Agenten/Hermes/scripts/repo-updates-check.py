"""Repo-Updates-Check: sind die Werkstatt-Klone hinter ihrem upstream?

Laeuft als Hermes-Cron OHNE Modell (`no_agent`): **leere Ausgabe heisst alles
aktuell** und es wird nichts gesendet (Watchdog-Muster). Ausgabe gibt es nur,
wenn mindestens ein Klon hinter dem Original herhinkt - dann steht je Repo
der Rueckstand in der Nachricht.

WARUM
-----
Die Fremd-Repos unter Werkstatt (je Repo ein Hermes-Bot-Profil) sind
die Quelle fuer den Skill-Fundus und die Repo-Flotte. Ein Klon, der Monate
hinter upstream liegt (gemessen 16.09.2026: superpowers zwei Monate), haelt
alte Skills, alte Bugs und alte Doku vor. Der woechentliche Check holt die
upstream-Refs und meldet nur die Repos MIT Rueckstand - nichts weiter.

WAS ES TUT (nur lesend fuer den Arbeitsbaum)
--------------------------------------------
1. Fuer jedes Repo mit .git unter Werkstatt:
   `git fetch upstream --quiet` (holt nur Refs, veraendert den Arbeitsbaum nicht).
2. Vorsprung zaehlen: `git rev-list --count HEAD..<upstream-Standardzweig>`.
   Bei SHALLOW-Klonen kann die Zahl kleiner als die Wahrheit sein - die
   Richtung (0 oder >0) stimmt immer.
3. Repos ohne upstream-Remote oder ohne Zweig ueberspringen (kein Fehler).
4. Nichts loeschen, nichts committen, kein Schreiben in den Arbeitsbaum.

Aufruf:
    python Agenten/Hermes/scripts/repo-updates-check.py     # echter Lauf
    python Agenten/Hermes/scripts/repo-updates-check.py --ohne-fetch
        -> nur lokale Refs vergleichen (fuer Tests, kein Netz)
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = Path(__file__).resolve()
WURZEL = HIER.parents[3]                    # Agenten/Hermes/scripts/ -> BrainFiles
REPOS = WURZEL / "Werkstatt"


def git(repo: Path, *args: str, zeit: int = 90):
    """git-Aufruf in einem Repo; (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=zeit,
                           errors="replace")
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", str(e)


def main():
    ap = argparse.ArgumentParser(description="Repo-Updates-Check (lautlos, solange alles aktuell ist)")
    ap.add_argument("--ohne-fetch", action="store_true",
                    help="kein git fetch (nur lokale Refs vergleichen)")
    args = ap.parse_args()

    if not REPOS.is_dir():
        print("Werkstatt nicht gefunden: %s" % REPOS)
        return 0

    meldungen = []
    geprueft = 0
    for repo in sorted(REPOS.iterdir()):
        if not repo.is_dir() or not (repo / ".git").exists():
            continue
        _, remotes, _ = git(repo, "remote")
        if "upstream" not in remotes.split():
            continue                       # kein upstream-Remote: nicht unser Fall
        # Standardzweig des upstream OHNE lokale Refs bestimmen (ls-remote
        # --symref nennt die HEAD-Referenz des Originals; vor dem ersten
        # fetch existieren refs/remotes/upstream/* noch nicht).
        code, aus, _ = git(repo, "ls-remote", "--symref", "upstream", "HEAD")
        zweig = None
        for zeile in (aus or "").splitlines():
            if zeile.startswith("ref:"):
                zweig = zeile.split()[1].replace("refs/heads/", "")
                break
        if not zweig:
            continue
        if not args.ohne_fetch:
            git(repo, "fetch", "upstream", "--quiet", zeit=180)
        code, aus, _ = git(repo, "rev-list", "--count", "HEAD..refs/remotes/upstream/" + zweig)
        if code != 0 or not aus:
            continue
        try:
            vorsprung = int(aus)
        except ValueError:
            continue
        geprueft += 1
        if vorsprung > 0:
            _, lokal, _ = git(repo, "log", "-1", "--format=%ci", "HEAD")
            # ACHTUNG: `zweig` ist der Name des UPSTREAM-Standardzweigs
            # ("main"). `git log ... main` liest aber den LOKALEN Zweig
            # gleichen Namens - beide Zeilen der Meldung zeigten damit
            # denselben Zeitstempel, und der Rueckstand sah wie "aktuell"
            # aus (gemessen 04.10.2026 an jevgrep: lokal 29.09., upstream
            # 02.10., gemeldet zweimal der 29.09.). Der volle Ref ist
            # refs/remotes/upstream/<zweig>.
            _, fern, _ = git(repo, "log", "-1", "--format=%ci",
                              "refs/remotes/upstream/" + zweig)
            meldungen.append("%s: %d Commit(s) hinter upstream\n"
                             "    lokal %s | upstream %s"
                             % (repo.name, vorsprung,
                                (lokal or "?").strip(), (fern or "?").strip()))

    if not meldungen:
        return 0                           # lautlos: alles aktuell

    print("Repo-Updates (%d Repos geprueft):" % geprueft)
    for m in meldungen:
        print("- " + m)
    print("Auffrischen:  git -C Werkstatt/<repo> pull upstream <zweig>")
    print("Danach:       Agenten/Werkzeuge/fundus-suche.ps1 -Index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
