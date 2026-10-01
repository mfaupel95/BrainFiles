---
name: gbrain-memory
description: Use when durable memory recall or saving facts is needed. Operates Max's local GBrain installation at /workspace/gbrain (WSL archlinux) via its absolute launcher; also for remember/recall/forget requests.
---

# GBrain memory

This Bot runs on Windows; the GBrain installation lives inside the WSL2
distribution `archlinux` at `C:\...`-unreachable POSIX path `/workspace/gbrain`.
The executable for every memory command is the installation's generated
absolute launcher, called THROUGH WSL so the same installation with the same
root is always selected:

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain <command> [args...]
```

Do NOT invent a different `gbrain` from PATH or a different root; this
installation owns the host brain and the source `default`. Use this same
absolute launcher path from every conversation and native routine.

## When to use

Recall relevant memory BEFORE answering personal or continuing-work questions.
Use `gbrain recall --help` through the launcher for the installed command
schema. Explicitly remember user-requested durable facts, with their source
and date.

## Rules

- Preserve uncertainty and distinguish what the user said from an inference.
- Correct or forget outdated facts when asked; verify the change through a
  fresh recall. Forgetting withdraws active memory; history, source material,
  and private backups may remain. Never promise physical erasure.
- Never import connected-service history or enable automatic capture without
  the user's instruction.
- Do not replace the agent's identity. This is one shared local installation,
  not a boundary between Bots.
- Memory calls are finite CLI processes. A busy database means another command
  is running: retry after it finishes; never remove its lock.

## Fallen beim Speichern (29.09.2026 gemessen)

- **Langtext aus einer DATEI uebergeben, nie inline.** Die Kommandozeile geht durch
  eine Huelle, in der einfache Anfuehrungszeichen NICHT schuetzen: Backticks,
  `$`-Ausdruecke und `$(...)` werden ausgewertet, bevor gbrain den Text sieht. Am
  29.09.2026 landeten dadurch vier Fakten verstuemmelt im Gehirn ("must run as ,",
  "/usr/bin/bash.ProcessId -ne "). Richtig: Text mit dem Schreibwerkzeug in eine
  Datei legen, dann
  `gbrain remember "$(cat <pfad>)" --provenance "<quelle, datum>" --entity <entitaet>`.
  **Die Ersetzung `$(cat ...)` passiert in der AEUSSEREN Shell** (der Bot laeuft auf
  Windows): dort muss der Pfad in der Form liegen, die DIESE Shell versteht - aus dem
  Windows-Terminal also `/c/Users/...` (MSYS), nicht `/mnt/c/Users/...` (WSL). Ein
  WSL-Pfad im `cat` gibt `No such file or directory`, und gbrain meldet dann nur
  `invalid_params: fact must be a non-empty string` (gemessen 01.10.2026).
- **Nach jedem remember zuruecklesen** (`gbrain recall --grep '<stichwort>'`):
  gbrain meldet beim Schreiben keinen Inhaltsverlust, nur `remembered as fact #n`.
- **`recall <wort>` sucht ZUERST eine ENTITAET.** Ist der Begriff keine, meldet es
  `no facts for entity '<wort>'; matched N fact(s) by text` und listet sie darunter -
  die Fundstelle ist also da, nur die Einleitung irrefuehrend. Textsuche erzwingen:
  `recall --grep <text>`; nach Entitaet: `recall "projects/hermes-agent"`.
- **`search`/`query` finden KEINE Fakten** (sie gehen ueber Seiten) und laufen ohne
  Embedding-Anbieter degradiert - nur Stichwortsuche, mit eigenem Hinweis.
- **`forget <fact-id> --reason <text>`** - die ID ist positionell, `--id` gibt es
  nicht. Korrektur heisst forget + neues remember; nie Loeschung zusagen.
- **`recall --grep` mit EINEM praegnanten Stichwort, nicht mit einer Phrase.** Gemessen
  30.09.2026: `--grep "lauschte wieder auf TCP"` meldete `No matching facts.`, waehrend
  `--grep 9900` denselben Fakt sofort fand. Ein Satzfragment trifft nicht — die Suche greift
  wortweise. Bei "nicht gefunden" also erst mit dem auffaelligsten Einzelwort (Zahl, Name,
  Pfad) gegentreten, bevor man den Fakt fuer verloren haelt.
- Ein Fakt ohne `--entity` ist fuer die entitaetsbezogene Erinnerung unsichtbar -
  Entitaet setzen, sobald der Fakt ein Subjekt hat.
- **Auch im DATEI-Weg wird `$NAME` im INHALT expandiert** (gemessen 01.10.2026):
  `remember "$(cat datei)"` reicht den Text zwar unversehrt durch die eigene Shell,
  aber auf dem Weg zur Installation wird `$HERMES_HOME` zu LEER - im Fakt stand
  danach `jedes cd "/../.."`. Die Anfuehrungszeichen blieben, nur die Variable
  verschwand. Deshalb im Faktentext **kein `$`** verwenden: Ersatzschreibweise
  (`<HERMES_HOME>`) nehmen und im Text erklaeren, was gemeint ist.
- **Nach dem Schreiben den zurueckgelesenen Text GEGEN DIE VORLAGE pruefen**, nicht
  nur "gefunden" zaehlen - die Verstuemmelung oben fiel erst beim Zeichenvergleich
  auf. Bei Verlust: `forget <id> --reason <was fehlte>`, Datei korrigieren, neu
  remember.
- **`The local persistence owner is unavailable. Fix: Restart the persistence owner,
  then retry.`** (gemessen 01.10.2026): Der Schreibweg geht per IPC an einen
  residenten Owner; gebunden wird dieser Socket nur von einem laufenden `gbrain
  serve` (`core/persistence/ipc.ts`, gestartet in `mcp/resolve-ipc-binding.ts`), und
  eine Socket-Datei lag nicht auf der Platte. Die Ursache ist NICHT abschliessend
  geklaert (moeglich: ein paralleler Schreibvorgang war gerade der Owner) - die
  Probe zeigt aber, dass **ein zweiter Aufruf Sekunden spaeter durchging**
  (`remembered as fact #n`). Also wiederholen statt an Locks drehen; `recall`
  funktioniert in derselben Lage (nur lesend).
- **Entscheidung Max (01.10.2026): KEIN dauerhaftes `gbrain serve`.** Bei einem
  Ausfall des Owners wird wiederholt, nicht ein Dienst gestartet - die Installation
  verbietet das ausdruecklich (`instructions/maintenance.md`: "Do not start serve,
  cron, or a daemon."). Diese Frage nicht erneut stellen; erst wenn Schreiben
  mehrfach hintereinander scheitert, ist der Dienst die richtige Antwort.

## Was ein Fakt wert ist (Handels-/Betriebsfakten, 02.10.2026)

Gemessen an einer Sitzung: GBrain ist das Brain fuer BELEGTE Aussagen, nicht
fuer Laufzeitstaende. Speichern:

- Messergebnisse mit Datum + Beleg (Commit, Cache-Pfad, Log) - z. B.
  "rollierender Backtest: 17/22 Fenster positiv, Summe -295 USD".
- Entscheidungen von Max mit seinem Wortlaut als Anker ("Hebel 7", "auto
  freigabe erlaubt").
- Offene Aufgabennummern (T-291, T-292) NUR mit einem Stichwort, nie der
  ganze Task-Text - TASKS.md ist die Quelle.

NICHT speichern: aktuelle Positions-/Guthaben-Zahlen (aus der wachen.json
nachlesbar), Zykluslogs, was eine Auswertung jederzeit neu rechnet. Ein Fakt,
dem in drei Wochen niemand den Beleg mehr zuordnen kann, ist Ballast.

## Setup evidence (2026-09-20)

- Init mode: keyless fact memory (`--pglite --no-embedding`), search mode
  `conservative` (auto-selected: no expansion-capable API key).
- Round trip verified: fact #1 "My setup test phrase is amber-orbit-f0c2c7",
  provenance "explicit setup test, 2026-09-20", entity `projects/gbrain-setup`,
  recalled by a separate process with the exact phrase.
- Fresh-conversation test VERIFIED (2026-09-20): a new conversation recalled
  the phrase via this skill and the WSL launcher without it being supplied.
- Bulk capture and paid maintenance stayed opt-in (off).
- Generated instructions: `/workspace/gbrain/instructions/gbrain-skill.md` and
  `/workspace/gbrain/instructions/maintenance.md` (Linux paths inside WSL).
- Receipt: `/workspace/gbrain/.gbrain/agent-install/receipt.json` (state
  `ready`).