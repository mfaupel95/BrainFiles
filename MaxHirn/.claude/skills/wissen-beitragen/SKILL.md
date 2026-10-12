---
name: wissen-beitragen
description: Entscheidet, wohin ein Ergebnis gehört – gbrain, Wissen/, Wiki/ oder TASKS.md – und schreibt es aus Claude Code dorthin. Benutzen bei "merk dir", "pack das ins gbrain", "ins Wissen", "in die Wissensbasis", "halt das fest", "speicher den Fakt", "was weißt du über", oder am Ende einer Aufgabe, deren Ergebnis in einem Monat noch gilt.
---

# Zu gbrain und Wissen/ beitragen (aus Claude Code)

Dieser Skill legt nur den Ort fest und beschreibt den Weg aus Claude Code. Die Form der Notiz regelt der Skill `notiz`. Wie gbrain bedient wird, steht in `Agenten/Hermes/skills/brainfiles/gbrain-memory/SKILL.md`, die Fallen beim Schreiben in `.../gbrain-memory/references/speichern.md`, der Betrieb in `.../references/betrieb.md`. Alle Pfade gehen von der Wurzel `BrainFiles/` aus. Bei Handelsthemen kommt der Inhalt zusätzlich in `MaxHirn/Wissen/Omnitrade.md` bzw. `Handelsbots.md`.

## 1. Wohin – das Ergebnis entscheidet, nicht der Wunsch

| Ergebnis | Ort |
|---|---|
| Eine einzelne belegte Aussage mit Quelle und Datum (Zahl, Entscheidung, Messwert) | **gbrain**, mit `--entity` |
| Ein Zusammenhang, ein Projektstand, eine Begründung, die Max liest | **`MaxHirn/Wissen/`**, bevorzugt in eine vorhandene Notiz |
| Eine Falle oder ein Merksatz aus dem Betrieb | **`MaxHirn/Wiki/`** (Skill `wiki-pflege`) |
| Ein offener Punkt | `MaxHirn/Archiv/TASKS.md` |

Sagt Max „gbrain **und** Wissen“, landet derselbe Inhalt an beiden Orten: im Wissen ausführlich mit `**Warum:**`, in gbrain als je eine Behauptung pro `remember` (ein Fakt pro Aufruf). Ein Satz mit zwei Aussagen wird also zu zwei Fakten.

## 2. gbrain aus Claude Code aufrufen

gbrain liegt **nicht im PATH**. `which gbrain` findet nichts, und das heißt nicht, dass es fehlt. Es läuft in der WSL-Distribution `archlinux`.

```bash
MSYS_NO_PATHCONV=1 wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall --grep <einzelwort>
```

- **`MSYS_NO_PATHCONV=1` gehört dazu.** Ohne die Variable macht Git Bash aus dem Pfad `C:/Program Files/Git/workspace/...` (Exit 127; gemessen am 13.10.2026).
- Zusammengesetzte Befehle in PowerShell sperrt die Richtlinie. Deshalb gbrain über das Bash-Werkzeug aufrufen.
- **Schreiben:** Den Faktentext mit `Write` in den Scratchpad legen, ohne `$` im Text. Daneben eine `.sh`-Datei mit `TEXT="$(cat /mnt/c/...)"` und `gbrain remember "$TEXT" --provenance "<quelle, datum>" --entity <entitaet>`, Aufruf mit `MSYS_NO_PATHCONV=1 wsl.exe -d archlinux bash /mnt/c/.../fakt.sh`. Den Text nie inline übergeben.
- In der `.sh` den **vollen** Pfad `/workspace/gbrain/bin/gbrain` verwenden.
- `--provenance`: Hat Max etwas im Chat gesagt, heißt die Quelle `"Max im Chat, 13.10.2026"`. Stammt es aus einer Messung, steht dort der Skriptpfad mit Datum.
- **Gegenprobe:** `recall --grep <stichwort>`. Als Stichwort ein ASCII-Wort aus dem Fakt nehmen (`Gebuehr` statt `Gebühr`, Zahl ohne Komma). Der zurückgelesene Text muss Zeichen für Zeichen der Vorlage entsprechen, Umlaute und `€` inklusive.
- Für die Entität vorhandene Slugs wiederverwenden (erst `recall "<entitaet>"`). Neue Slugs heißen `projects/<name>`, `people/<name>` oder `tools/<name>`, kleingeschrieben und mit Bindestrich.

## 3. Wenn gbrain streikt

- `PGLite failed to initialize its WASM runtime`: zuerst `gbrain pglite-repair --dry-run` laufen lassen (nur lesend). Lautet der Befund `stale postmaster.pid`/`wal-corruption-likely` und `Lock: free`, ist das die Folge eines unsauberen Herunterfahrens (gesehen am 13.10.2026). **Reparieren nur nach Ja von Max** (`pglite-repair --yes`). **Nie `reinit-pglite`:** Das löscht alle Fakten (siehe `references/betrieb.md`).
- `The local persistence owner is unavailable`: einmal wiederholen. Keinen Dienst starten.
- Bleibt gbrain ausgefallen, trotzdem ins Wissen schreiben und Max den gbrain-Teil als offen melden. Nicht stillschweigend weglassen.

## 4. Wissen/ schreiben – die Pflichten nebenher

1. Vorher `MaxHirn/Wissen/Schutzregeln.md` lesen. `Wissen/` ist Bereich `wissen`, die Prüfung dafür: `python Agenten/Werkzeuge/bereiche.py --aufrufer wissen --pfad <pfad>`. Wer gerade in einem anderen Bereich arbeitet (z. B. `handel`), trägt dessen Namen ein und meldet den Befund.
2. Erst `MaxHirn/Wissen/INDEX.md` nach einer passenden Notiz durchsuchen, dann gezielt mit `Edit` ändern, nie die ganze Datei neu schreiben (CRLF bleibt so erhalten).
3. Eine **neue** Notiz bekommt im selben Schritt ihren Eintrag in `INDEX.md` und wird von einer Elternnotiz aus verlinkt (`[[Name]]`).
4. Zahlen brauchen das Skript, das sie erzeugt hat, als Pfad in der Notiz.
5. Wenn nur Notizen oder der Index geändert wurden, reicht ein Pflege-Commit auf `master` (laut Wurzel-`CLAUDE.md`). Steht der Hauptbaum auf einem fremden Zweig, wird nicht umgeschaltet: entweder ein eigener Arbeitsbaum unter `.worktrees/` oder Max fragen. Commit mit `BRAINFILES_BEREICH=wissen`, nicht pushen.
6. Zum Schluss Max in einem Satz melden, was wo abgelegt wurde.

## 5. Grenzen

- Ersetzt nicht die Auto-Memory von Claude (Arbeitsregeln für Claude) und nicht das Hermes-`memory`.
- Kurzlebiges wie Laufausgaben oder Zwischenstände gehört nach `Werkstatt/`, nicht hierher.
