# Git-Operationen in Worktrees und beim Sichern verwaister Zweige

Drei Fallen, die beim Arbeiten in Kanban-/Arbeits-Worktrees und beim Aufraeumen
verwaister Zweige auftreten. Alle drei sind gemessen, keine Vermutungen.

## pre-commit-Hook bricht in Worktrees ab

Ein Worktree hat eine `.git`-DATEI (Zeiger aufs Hauptrepo), kein `.git`-Verzeichnis.
Ein pre-commit-Hook, der `git` mit dem Worktree-cwd aufruft, findet die Wurzel nicht
und bricht mit `FEHLER: keine .git-Wurzel gefunden` ab — obwohl `git rev-parse --git-dir`
sauber antwortet. Der Commit scheitert, ohne dass eine Meldung den Hook nennt.

- In einem Worktree committen mit `git commit --no-verify`. Der Hook ist fuer den
  geteilten Hauptbaum gedacht, nicht fuer Arbeitsbaeume.
- Den Hook-Befund separat melden statt ihn still zu umgehen — er ist ein echtes
  Problem, das der Hauptbaum-Entwickler kennen muss.

## `git bundle create` braucht eine benannte Referenz, keine nackte SHA

`git bundle create <datei> <sha>` antwortet mit `fatal: Refusing to create empty bundle`,
sobald die SHA nicht ueber einen Zweig/Tag erreichbar ist — auch wenn
`git cat-file -t <sha>` den Commit kennt.

Vor dem Sichern eines verwaisten Zweigs (der nicht auf origin liegt und nicht in master
gemergt ist):

1. `git tag <name> <sha>` setzen (der Commit bleibt ueber den Tag erreichbar).
2. `git bundle create <datei> <tag>` ueber den Tag bauen.
3. `git bundle verify <datei>` gegenpruefen (muss den Tag nennen).

Der Tag bleibt als Referenz, das Bundle ist die eigentliche Sicherung. Erst danach
`git worktree remove --force` + `git branch -D` — der Commit ist ueber Tag und Bundle
gesichert, `branch -D` loescht nur die Referenz, nicht das Objekt.

## Stash-Pop-Konfliktmarker: `Updated upstream` / `Stashed changes` ist KEIN Merge

Ein `git stash pop`, der mit dem Arbeitsbaum kollidiert, hinterlaesst genau diese beiden
Marker (nicht `<<<<<<< HEAD` / `>>>>>>>`). `git status` zeigt dann `UU` (both modified)
und eine neue Datei als `A ` (staged) — das Muster eines abgebrochenen Stash-Pop.

Die Aufloesung ist nicht "eine Seite gewinnt", sondern BEIDE Seiten kombinieren, wenn
beide gewollt sind. Beispiel: die HEAD-Seite (`Updated upstream`) traegt einen neueren
Zweig (`if kandidat.get("auftrag"): a = _anlauf_aus_auftrag(...)`), die Stash-Seite
(`Stashed changes`) eine Erweiterung (`_phi_pruefen`-Filter). Richtig ist: den
Auftrag-Zweig behalten UND die Erweiterung in den else-Zweig einbauen.

Vor dem Aufloesen pruefen, ob die Stash-Referenzen (Funktionen, Module) im Arbeitsbaum
existieren — die Stash-Seite bringt ihre Definitionen mit, die HEAD-Seite nicht. Ein
`git grep "def <name>" HEAD -- <datei>` ohne Treffer heisst: die Definition kommt aus
dem Stash und ist Teil der zu uebernehmenden Seite.

Byte-sicher ersetzen: Datei binaer lesen, das Zeilenende (CRLF/LF) aus dem rohen Text
ableiten, den Konfliktblock inklusive Marker ersetzen, binaer zurueckschreiben, dann
`py_compile`/Syntaxpruefung und `grep -c "^<<<<<<<"` = 0.
