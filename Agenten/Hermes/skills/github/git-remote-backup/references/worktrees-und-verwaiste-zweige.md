# Worktrees und verwaiste Zweige aufraeumen

Ein Dispatcher, der je Karte einen Workspace im `worktree`-Modus bekommt, legt
pro Karte einen Worktree plus Zweig `wt/<karte>` an. Die Karten enden, die
Worktrees bleiben fuer immer liegen: nach einem Tag hat ein Baum 30 Eintraege,
die jeden Flaechenscan verlangsamen und jeden `git status` mit Geisterdateien
verraeuschen.

Zielzahl ist genau EINE registrierte Worktree-Zeile (die Wurzel selbst).

## 1. Inventur in einem Lauf

```bash
cd <wurzel>
git worktree list --porcelain | grep '^worktree ' | sed 's/^worktree //'
```

Je Zeile (mit Leerzeichen im Pfad!) drei Fragen, alle mit `git -C "$w"`:

```bash
git -C "$w" rev-parse --abbrev-ref HEAD          # Zweig
git -C "$w" log --oneline master..HEAD           # eigene Commits
git -C "$w" status --porcelain                   # uncommittet
```

`scripts/worktree-inventur.py` im Skill macht das ueber alle Worktrees und
druckt je Zeile die Commits und die uncommitted Dateien.

## 2. Entscheidung je ZWEIG, nie je Worktree-Alter

```bash
git rev-list --count master..<zweig>
```

- `0` → toter Zweig, Wegwerf. `git branch -D` ist erlaubt.
- `> 0` → Arbeit. Erst auf origin sichern, dann loeschen.

Ein alter Worktree mit sauberem Status kann auf einem Zweig mit drei Commits
sitzen. Umgekehrt liegt die Arbeitsleistung manchmal nur als uncommitted Datei
im Ordner. Beide Sorten kommen im selben Verzeichnis vor.

## 3. Zweige mit Arbeit zuerst auf origin

```bash
env -u GITHUB_TOKEN -u GH_TOKEN git push origin <zweig>:refs/heads/<zweig>
git ls-remote origin refs/heads/<zweig>          # muss den Hash zeigen
```

Vor dem Push `GITHUB_TOKEN`/`GH_TOKEN` aus der Umgebung nehmen: eine
Benutzervariable mit schmalerem Scope wird von git dem Credential-Manager
vorgezogen, und der Push endet mit `remote: Write access to repository not
granted` (Exit 128) — waehrend derselbe Push von Hand durchgeht.

## 4. Uncommitted Dateien bergen, DANN entfernen

1. Jede Datei aus `git status --porcelain` in einen Rueckgabe-Ordner kopieren,
   mit Worktree-Namenspraefix im Dateinamen (mehrere Worktrees teilen sich
   Dateinamen wie `TASKS.md`).
2. Erst danach `git worktree remove --force <pfad>` und `git worktree prune`.

Ein Branch-Push sichert Commits, NICHT uncommitted Dateien.

## 5. Reste, die `worktree remove` nicht wegbekommt

`worktree remove` meldet `failed to delete ...: Filen` und laesst den Ordner
stehen, wenn darin Junctions auf echte Baeume liegen (`Werkstatt` -> `O:\`,
Repo-Klone mit `.venv`). Solche Reste sind KEIN leerer Rest: sie koennen
Dateien enthalten, die es im Original nicht gibt oder die anders sind.

Vor dem Loeschen Datei fuer Datei gegen das Original vergleichen
(`sha256`, Relativpfad als Schluessel) und drei Gruppen melden: identisch,
NUR-HIER, UNTERSCHIEDLICH. Nur die letzten beiden sind ein Befund — ein Rest
mit ausschliesslich identischen Dateien ist gefahrlos loeschbar.

Beim Vergleich Junctions und Verzeichnisse mit `.venv`/`__pycache__` NICHT
verfolgen (`os.walk` mit `dirs[:]` filtern): sonst hasht man den echten
Werkstatt-Baum durch (im Haus 6.329 Dateien, Laufzeit ueber fuenf Minuten).

## 6. Tote Zweige auch auf origin aufraeumen

```bash
git fetch -q origin <zweig>
git rev-list --count master..FETCH_HEAD     # 0 → löschen
env -u GITHUB_TOKEN -u GH_TOKEN git push origin --delete <zweig>
```

Sicherungszweige (`zwischenstand` o.ae.) bleiben stehen — sie sind eine
Vereinbarung, keine Arbeitsreste.

## Fallen

- **Verwaistes `.git/index.lock` blockiert den Push** mit `fatal: Unable to
  create index.lock`. Alter UND Zahl echter `git.exe`-Prozesse pruefen (die
  `git fsmonitor--daemon`-Prozesse zaehlen nicht, sie laufen dauerhaft). Bei
  0 Prozessen und 0 Byte ist es ein Wrack: umbenennen
  (`Move-Item -Force`), nicht loeschen. Bei >0 Prozessen warten.
- **Pfade mit Leerzeichen** (`Arbeitsbereich 1`, `KI WORKTREE`) zerlegen eine
  `for`-Schleife ueber `find`/`git worktree list` still. Mit `git -C "$w"`
  und Quotes arbeiten, nicht mit `cd` in der Schleife.
- **Ein 0-Byte-`.git` ist kein Repo**, sondern ein uv-Cache-Artefakt
  (`invalid gitfile format`). Nur die Datei loeschen — der Ordner daneben
  enthaelt echte Cache-Dateien.
- **Wegwerf-Testklone im Cache** (`probe-*` unter einem `cache/`-Ordner) tragen
  ein eigenes `.git` mit voller Historie und tauchen in jedem Flaechenscan auf.
  Sie sind ignoriert und kosten Platz; loeschen ist gefahrlos, sobald
  `git ls-files` leer ist (nichts versioniert).
- **Das `.worktrees/`-Verzeichnis selbst stehen lassen**, auch wenn leer: es ist
  die Arbeitsflaeche des Dispatchers, kein Rest.