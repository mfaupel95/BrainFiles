# Worktrees im geteilten Baum

Der Hausbaum traegt neben dem Hauptbaum mehrere Worktrees (ein Zweig je
Arbeitspaket, Kanban-Karten legen sie an). Sie haben eigene Arbeitskopien und
teilen nur das `.git` — daraus kommen alle Fallen dieser Datei.

## Bestand messen, bevor man anfasst

    git worktree list
    git -C <wt> rev-list --count HEAD..master     # hinter
    git -C <wt> rev-list --count master..HEAD     # eigene Commits
    git -C <wt> status --porcelain | wc -l        # uncommitted

Ein Worktree mit eigenen Commits ist Arbeit, kein Abfall. Ueber „behalten oder
weg" entscheiden drei Zeugen — `git cherry` (Patch-Id = Inhalt),
`merge-base --is-ancestor` (Kopf), `rev-list --count` (Zahlen) — nie das Alter
des Ordners und nie der SHA allein: derselbe Inhalt liegt in master oft unter
einem anderen SHA.

## `.git` ist im Worktree eine DATEI

Im Worktree ist `.git` eine **Datei** (`gitdir: <pfad>`), im Hauptbaum ein
Ordner. Jedes Werkzeug, das die Repo-Wurzel mit `isdir('.git')` sucht, bricht
dort mit „keine .git-Wurzel gefunden" ab. Ordner **oder** Datei als Wurzel
akzeptieren.

`git -C <pfad>` in einem Ordner **ohne** jedes `.git` liest still vom
Eltern-Repo weiter: Log, Status und HEAD sehen gesund aus und gehoeren zu einem
anderen Repo. Vor jedem `git -C` auf unbekanntem Pfad `rev-parse --git-dir` und
`--show-toplevel` pruefen.

## Hooks: jeder Worktree haelt seine eigene Kopie

`core.hooksPath=.githooks` loest **innerhalb des Worktrees** auf. Der Worktree
traegt damit seine eigene Arbeitskopie des Hooks *und* jedes Werkzeugs, das der
Hook aufruft. Eine Korrektur im Hauptbaum erreicht ihn erst, wenn er sie merged
— deshalb wirkt ein Fix dort scheinbar nicht.

Ein Hook laedt sein Werkzeug darum aus dem HAUPTBAUM:

    GIT_COMMON=$(git rev-parse --path-format=absolute --git-common-dir) || exit 0
    ROOT=$(dirname "$GIT_COMMON")

`--show-toplevel` liefert den Worktree und damit dessen veraltete Kopie;
`--git-common-dir` ist in Hauptbaum und Worktree dasselbe geteilte `.git`, sein
Elternordner die Baumwurzel. So wirkt jede kuenftige Korrektur sofort in allen
Worktrees, ohne dass einer mergen muss.

Nach einer Hook-Aenderung mit einem **echten** Commit in einem Worktree
beweisen, **ohne** `--no-verify`. `--no-verify` verdeckt genau den Fehlschlag,
den man behebt — ein gruener Commit damit beweist nichts.

## Viele Worktrees nachziehen

Je Worktree `git -C <wt> merge master`, danach in EINER Schleife verifizieren:
`hinter=0`, `konflikte=0`, `uncommitted=0`. Einen Worktree mit uncommitteten
oder konfliktbehafteten Dateien auslassen, nicht ueberfahren — das ist laufende
Arbeit einer anderen Sitzung.

Wurde das Werkzeug oder der Hook erst im Lauf der Sitzung in master korrigiert,
braucht es einen **zweiten** Merge-Durchgang: der erste lag vor dem Fix-Commit.
Den Stand je Worktree an einem Merkmal des Fixes pruefen (`grep` auf die neue
Zeile), nicht am Merge-Erfolg.

## Einen Worktree entfernen

1. Nicht uebernommene Commits ZUERST sichern. `git bundle create` verweigert
   einen blossen SHA („Refusing to create empty bundle") — es braucht eine
   benannte Referenz: Tag setzen, Tag bundlen, `git bundle verify`.
2. Verlustfreiheit am DATEISATZ belegen, nicht am Commit-Graph:

       comm -23 <(git show <sha> --format= --name-only | sort -u) \
                <(git ls-tree -r --name-only master | sort -u)

   Leere Ausgabe = keine Datei fehlt in master. Abweichende Inhaltsstaende sind
   dann nur aeltere Staende, kein Verlust.
3. `git worktree remove --force`, `git worktree prune`, `git branch -D`.

Das Loeschen des Zweigs entfernt nur die Referenz — der Commit bleibt im
Objektspeicher. Tag und Bundle sind das, was ihn wiederfindbar haelt.
`git worktree remove` scheitert an Resten, die JUNCTIONS enthalten; einer
Junction beim Hashen eines Baums nie folgen, sonst misst man den echten
Zielbaum mit.

## Wegwerf-Commits nie auf echte Arbeit stapeln

Ein Probe-Commit ueber einem echten Commit und danach `git reset --soft HEAD~1`
nimmt **beide** zurueck — der echte ist dann nur noch im Index. Entweder in
einem Wegwerf-Worktree proben, oder direkt nach dem Reset aus dem Index neu
committen und den Zweigkopf verifizieren (`git log -1`).

## Konflikt aus einem Stash-Pop statt einem Merge

Marker `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` (statt zweier
Commit-Namen) und ein fehlendes `MERGE_HEAD` heissen: der Konflikt kommt aus
einem Stash-Pop, nicht aus einem Merge — `git merge --abort` greift nicht.
Beide Seiten sind dann meist gewollt: die eine traegt den neueren Zweig, die
andere die liegengebliebene Arbeit. Vor dem Entscheiden pruefen, ob die vom
Stash gerufenen Namen im Arbeitsbaum ueberhaupt existieren (`grep` auf die
Definition) — existieren sie, ist die Aufloesung ein **Zusammenfuehren**, kein
Auswaehlen.

Den Konfliktblock byteweise ersetzen (Zeilenenden erhalten), die Eindeutigkeit
vorher sichern und danach kompilieren:

    raw = open(p, "rb").read()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    assert raw.count(alt_b) == 1, "Konfliktblock nicht eindeutig"
    open(p, "wb").write(raw.replace(alt_b, neu_b))

Danach `grep -c '^<<<<<<<\|^>>>>>>>'` = 0, `py_compile` gruen und die Tests der
beruehrten Spur laufen lassen — ein konfliktfreier Text ist noch kein
funktionierender.
