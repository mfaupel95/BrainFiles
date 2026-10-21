# Nach dem Merge: Zweig, Worktree und geteilte Klone aufraeumen

Ein Zweig ist gemergt, `git worktree list` zeigt noch drei Eintraege, und die
Klone stehen auf alten Staenden. Die Reihenfolge unten ist die sichere Fassung
fuer einen Baum, in dem ANDERE Sitzungen parallel arbeiten.

## 1. Je Worktree fragen, wem die Aenderung gehoert

```bash
for d in <worktree1> <worktree2>; do echo "== $d"; \
  (cd "$d" && git rev-parse --short HEAD && git status --porcelain | grep -v '^??'); done
```

- **nur `??`** (unversioniert): niemandes Arbeit, Aufraeumen erlaubt.
- **Aenderung an einer VERFOLGTEN Datei** (` M` / `M` in Spalte 1-2 von
  `git status --porcelain`): fremde Arbeit. Der Worktree wird NICHT
  entfernt und NICHT umgehaengt, auch wenn sein Zweig schon in `main` liegt — die
  Aenderung ist per Definition nicht in `main`. Entweder in einem eigenen Commit
  mit neutraler Kennung sichern oder stehen lassen und melden.

Ein Worktree ist eine `working copy`, kein Zwischenspeicher: `git worktree remove
--force` loescht die Aenderung endgueltig, und sie ist in keinem Ref zu finden.

## 2. Worktree entfernen: Abmeldung ist das Erfolgskriterium

```bash
git worktree remove <pfad> --force
git worktree list          # muss den Pfad NICHT mehr zeigen
```

Gemessen: `remove` meldet `error: failed to delete '<pfad>': Permission denied`
und der Eintrag ist trotzdem aus `git worktree list` verschwunden. Der Inhalt war
geloe­scht, nur das (leere, ~4 KB) Verzeichnis blieb — gehalten von einem eigenen
bash-Kind, das noch mit `cwd` darin stand (`Device or resource busy`).

- Nicht dagegen ankaempfen (kein `rm -rf` auf einen Pfad, der ein Junction sein
  koennte, kein Prozess-Abschiessen der eigenen Shell).
- Der leere Ordner ist harmlos; spaeter loeschen, wenn die Shell weg ist.
- Pruefen, WER haelt: `Get-CimInstance Win32_Process | Where-Object CommandLine
  -like '*<pfad>*'` — sind es die eigenen Werkzeug-Shells, ist es kein Befund.

## 3. Zweig loeschen, auch wenn HEAD detached ist

```bash
git branch -d <zweig>              # Warnung '... but not yet merged to HEAD' ist hier normal
git push origin --delete <zweig>
git fetch --prune origin
git branch -a && git ls-remote --heads origin
```

Ist `HEAD` detached (z. B. auf `origin/main`), vergleicht `-d` gegen diesen
Commit und warnt, obwohl der Zweig remote gemergt ist. Die Loeschung passiert
trotzdem. Beweis ist die anschliessende Liste, nicht die Warnung.

## 4. Einen GETEILTEN Klon nicht mit `checkout -f` nachziehen

`git checkout --detach origin/main` bricht ab mit
`untracked working tree files would be overwritten` — das ist eine Sperre, kein
Hindernis. Vor jedem `-f` die Kollisionen zaehlen und INHALTLICH vergleichen:

```bash
for p in $(git status --porcelain | grep '^??' | awk '{print $2}'); do
  git cat-file -e "origin/main:$p" 2>/dev/null || continue
  a=$(git hash-object "$p"); b=$(git rev-parse "origin/main:$p")
  [ "$a" = "$b" ] && echo "gleich: $p" || echo "ABWEICHEND: $p"
done
```

- **gleich** → identisch mit `main`, Ueberschreiben unschaedlich.
- **abweichend** → fremde Arbeit. Nicht erzwingen, Liste melden, Klon auf dem
alten Stand lassen. Ein Klon eine Handvoll Commits hinter `main` kostet nichts;
  eine ueberschriebene fremde Datei ist weg.

Merksatz: ein `checkout`-Abbruch in einem geteilten Baum ist ein Schutz, den man
liest — nicht ein Fehler, den man mit `-f` beseitigt.

## 5. Formatierer sind SCHREIBER: nur die eigenen Dateien formatieren

Ein Formatierer fasst den ganzen Baum an. `cargo fmt --all` hat in einem Zweig
zwei fremde Dateien umformatiert, die mit der Aufgabe nichts zu tun hatten —
sie standen danach als Aenderung im eigenen Commit bereit. Dasselbe gilt fuer
`black .`, `prettier --write .`, `go fmt ./...`.

Ablauf nach jedem Formatierer-Lauf:

```bash
git diff --numstat      # VOR dem Stagen: welche Dateien hat er angefasst?
git checkout -- <fremde datei> [...]
git add <nur eigene pfade>
git diff --cached --name-only   # Gegenprobe vor dem Commit
```

Zwei Ausnahmen, bewusst:

- Der Formatierer hat eine Datei angefasst, die DU in dieser Aufgabe schon
  geaendert hast → mitnehmen, das gehoert zum Ergebnis.
- Der Zweig ist dein eigener und niemand arbeitet darin → Formatierung darf
  bleiben, aber als EIGENER Commit ("fmt"), nicht in den Fachcommit gemischt.

## 6. Reihenfolge bei Platzmangel

`target/`, `.venv`, `node_modules` in alten Worktrees sind der groesste Posten.
Worktree erst entfernen, wenn 1. geklaert ist (kein ` M`), sonst ist die
Groesse egal — es wird nichts geloescht, was jemandem gehoert.
