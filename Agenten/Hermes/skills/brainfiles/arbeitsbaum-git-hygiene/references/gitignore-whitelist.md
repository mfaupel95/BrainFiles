# .gitignore-Whitelist: Freigabe scopen, verschachtelte Sperren

Ergaenzt die SKILL.md-Regeln (die ist am Zeichenlimit). Zwei Fallen beim
FREIGEBEN neuer Pfade in der BrainFiles-Whitelist (`*` ignoriert alles, unten
wird einzeln freigegeben).

## Eine pauschale Freigabe zuerst MESSEN, dann scopen

Eine breite Freigabe (`!…/skills/**/*.md`) kann 88,5 MB / 10512 Dateien ziehen,
wenn die Absicht "ein paar gepflegte Lehren" war. Vor der Freigabe die
tatsaechliche Treffermenge messen (Dateizahl + Groesse):

```bash
find <ordner> -name '*.md' -printf '%s\n' | awk '{s+=$1} END {printf "%.1f MB, %d Dateien\n", s/1048576, NR}'
```

Dann auf den beabsichtigten Dateityp scopen (`**/SKILL.md` statt `**/*.md`) und
ausgemusterte/Archiv-Ordner ausschliessen. Eine Freigabe, die mehr zieht als
beabsichtigt, blaeht das Repo auf und verlangsamt jede Wache, die `git ls-files`
liest.

## Verschachtelte Cache-/Sicherungs-Ordner brauchen `**/` im Sperrmuster

Liegt ein auszuschliessender Ordner unter variabler Tiefe, matcht ein Muster mit
nur dem Namen auf oberster Ebene nichts:

- `skills/.sicherung-junctions/` matcht NICHTS, wenn die Ordner unter
  `skills/<skill>/.sicherung-junctions/` liegen.
- Richtig: `skills/**/.sicherung-junctions/` (und analog `.hub/`,
  `.curator_backups/`, `.archive/`).

## Gegenprobe nach jeder Freigabe

`git status --porcelain -uall` zaehlen und die Nicht-Ziel-Dateien ansehen —
Cache-/Archiv-Treffer sind der Befund. `git status --porcelain` (ohne `-uall`)
fasst untracked Ordner zu EINEM Eintrag zusammen und versteckt die Dateien;
`-uall` listet jede Datei einzeln.

## Freigabe-Reihenfolge (spaetere Regel gewinnt)

Die `!`-Freigabe muss NACH der allgemeinen Sperre stehen, die sie aufheben soll
— eine bestehende `…/skills/**`-Sperre weiter oben macht eine spaeter
platzierte Freigabe wirkungslos. Und fuer verschachtelte Ziele: erst das
Verzeichnis freigeben (`!…/skills/`), dann die Unterverzeichnisse
(`!…/skills/**/`), dann die Dateien (`!…/skills/**/SKILL.md`) — eine Datei wird
nicht freigegeben, solange ein darueber liegendes Verzeichnis gesperrt ist.
