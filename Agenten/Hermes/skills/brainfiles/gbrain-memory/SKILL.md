---
name: gbrain-memory
description: Save, recall, and correct durable facts in the local brain.
version: 0.2.0
author: Hermes
platforms: [windows]
license: MIT
metadata:
  hermes:
    tags: [Memory, Facts, Knowledge, WSL, Recall]
    related_skills: [hermes-gedaechtnis-pflegen, wiki-pflege, memory-verlust-rettung]
---

# GBrain: dauerhafte Fakten speichern, finden, korrigieren

GBrain ist das lokale Wissensgehirn (Fakten mit Quelle, Datum, Entitaet), das in der
WSL2-Distribution `archlinux` unter `/workspace/gbrain` liegt. Dieser Skill ist der
Bedienweg: **jede** Speicher- und Leseoperation laeuft ueber den absoluten Launcher,
nie ueber ein `gbrain` aus dem PATH. Er beschreibt NICHT, was ein Fakt wert ist (dafuer
`references/betrieb.md`) und ersetzt die Hermes-`memory`-Eintraege nicht: GBrain ist fuer
belegte Aussagen, Hermes-Memory fuer Regeln, die in jeder Sitzung gelten muessen.

## When to Use

- "merk dir das", "remember this", "speicher den Fakt", "was weisst du ueber X"
- "erinnerst du dich an ...", "recall", "forget", "vergiss das wieder"
- vor Antworten zu Personen-, Projekt- oder Frueher-Fragen (erst erinnern, dann antworten)
- nach einer Messung oder einer Entscheidung von Max, wenn der Beleg in drei Wochen noch
  zuordenbar sein soll

## Prerequisites

- WSL2 mit der Distribution `archlinux` (Windows-Host); der Launcher ist
  `/workspace/gbrain/bin/gbrain` und wird ueber `wsl.exe` aufgerufen.
- Kein Schluessel noetig: die Installation laeuft als reine CLI (`--pglite
  --no-embedding`), Suche im Modus `conservative`.
- Kein Dienst: **`serve`, `cron` und Daemons werden NICHT gestartet** (Anweisung der
  Installation und Entscheidung Max vom 01.10.2026) - bei einem Ausfall wird
  wiederholt, nicht ein Dienst gestartet.

## How to Run

Jeden Aufruf ueber das `terminal`-Werkzeug, immer mit demselben absoluten Pfad:

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain <command> [args...]
```

## Quick Reference

```
gbrain recall --grep <einzelwort>           Fakten per Stichwort (wortweise Suche)
gbrain recall "<entitaet>"                  Fakten einer Entitaet, z. B. projects/hermes-agent
gbrain remember "<fakt>" --provenance "<quelle, datum>" --entity <entitaet> [--kind fact]
gbrain forget <fact-id> --reason "<grund>"   ID POSITIONELL, kein --id
gbrain doctor --fast --json                 Health; "warnings" ist bei CLI-Betrieb normal
gbrain stats | gbrain health                Umfang, Zustand
```

`gbrain recall --help` und `gbrain forget --help` geben nur einen Stub aus ("run gbrain
--help") - die Optionen stehen im Haupt-Hilfetext und in
`references/lesen-und-korrigieren.md`.

## Procedure

1. **Erinnern.** `wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall --grep <wort>`
   mit EINEM praegnanten Wort (Zahl, Name, Pfad). Trifft nichts, mit dem auffaelligsten
   Einzelwort gegentreten, bevor der Fakt als verloren gilt.
2. **Schreiben.** Faktentext mit `write_file` in eine Datei legen (nie inline) und dann
   `gbrain remember "$(cat <pfad>)" --provenance "<quelle, datum>" --entity <entitaet>`.
   Der `cat`-Pfad muss in der Form der AUFRUFENDEN Shell liegen (aus dem Windows-Terminal
   `/c/Users/...`, nicht `/mnt/c/...`) - das gilt fuer den INLINE-Aufruf aus bash. Aus
   PowerShell gibt es keinen Inline-Weg; dort das `.sh`-Skript nehmen (siehe Pitfalls).
   Der `cat` gehoert zum wortgetreuen Aufruf: den Pfad
   INNERHALB von WSL kann `read_file` nicht lesen. Den Faktentext selbst legt man mit
   `write_file` auf der Windows-Seite ab.
3. **Zuruecklesen und zeichengenau vergleichen** (`recall --grep <stichwort>`) - nicht nur
   "gefunden" zaehlen. Bei Verlust: `forget <id> --reason ...`, Datei korrigieren, neu
   `remember`.
4. **Korrigieren.** Es gibt kein Update: `forget` + neues `remember`. Nie eine Loeschung
   zusagen - vergessen nimmt nur die aktive Erinnerung zurueck.
5. **Nachpruefen bei Zweifeln.** `gbrain doctor --fast --json` (Status `ok` oder
   `warnings`); die Haus-Wache faehrt das ohnehin taeglich um 06:00 (Hermes-Cron
   `gbrain-maintenance`).

## Pitfalls

- **Langtext nie inline.** Die Kommandozeile geht durch eine Huelle, in der einfache
  Anfuehrungszeichen NICHT schuetzen: Backticks, `$`-Ausdruecke und `$(...)` werden
  ausgewertet, bevor gbrain den Text sieht (29.09.2026: vier verstuemmelte Fakten).
- **Der `$(cat ...)`-Aufruf gehoert in ein Skript, nicht in die Kommandozeile.** Aus
  PowerShell (`mcp__windows_mcp__PowerShell`) bricht
  `-Command "... $(cat $f) ..."` mit `Unerwartetes Token "$"` ab - die aeussere Huelle
  wertet aus, bevor gbrain den Text sieht. Richtiger Weg: eine kleine `.sh` neben die
  Faktdatei legen und mit `wsl.exe -d archlinux bash <skript.sh>` aufrufen:

      F=/mnt/c/Users/<...>/cache/scratch/fakt.txt
      TEXT="$(cat "$F")"
      /workspace/gbrain/bin/gbrain remember "$TEXT" --provenance "<quelle, datum>" \
        --entity projects/<name> --kind fact

  Der Pfad IM Skript ist die WSL-Form (`/mnt/c/...`), weil das Skript in WSL laeuft -
  die Form der aufrufenden Shell gilt nur fuer den INLINE-Aufruf aus bash. Beide Wege
  vorher einmal mit `--help` trocken fahren, wenn der Fakt lang ist.
- **Auch im Dateiweg wird `$NAME` im Inhalt expandiert** (01.10.2026: `$HERMES_HOME`
  wurde zu LEER). Im Faktentext **kein `$`** verwenden - Ersatzschreibweise wie
  `<HERMES_HOME>` nehmen und im Text erklaeren.
- **`recall <wort>` sucht zuerst eine ENTITAET.** Ist der Begriff keine, meldet es
  `no facts for entity '<wort>'; matched N fact(s) by text` - die Fundstelle steht
  darunter, nur die Einleitung ist irrefuehrend.
- **`search`/`query` finden keine Fakten** (sie gehen ueber Seiten) und laufen ohne
  Embedding-Anbieter nur als Stichwortsuche.
- **Ein Fakt ohne `--entity`** ist fuer die entitaetsbezogene Erinnerung unsichtbar.
- **Ein gespeicherter Fakt ist eine Momentaufnahme, kein Dauerzustand.** Bevor du
  auf einen Fakt HANDELST ("klaere diese Faelle", "was ist mit X"), miss den
  Live-Zustand neu (Prozess, Aufgabe, Datei) - ein Befund vom selben Tag kann schon
  ueberholt sein (gemessen 13.10.2026: 3 von 5 Fakten waren abends falsch, weil
  Waechter reaktiviert und die Mittel-Stufe neu gestartet worden war). Ist der Fakt
  ueberholt, korrigiere ihn (forget + neues remember mit dem IST-Zustand) statt den
  alten stehen zu lassen - ein veralteter Fakt wird sonst zur Grundlage einer falschen
  Aktion.
- **`The local persistence owner is unavailable.`** (01.10.2026): ein zweiter Aufruf
  Sekunden spaeter ging durch. Nicht an Locks drehen, keinen Dienst starten.
- Details, Wortlaute und Belege: `references/speichern.md` (Schreiben),
  `references/lesen-und-korrigieren.md` (Lesen/Korrigieren), `references/betrieb.md`
  (Wartung, Sicherung, was ein Fakt wert ist, Kommandokarte).

## Verification

```
wsl.exe -d archlinux /workspace/gbrain/bin/gbrain recall --grep <stichwort-des-neuen-fakts>
```

Der zurueckgelesene Text muss dem geschriebenen **zeichengenau** entsprechen; die Ausgabe
nennt `id=<n>`, die Entitaet in eckigen Klammern und `(fact, conf ...)`.

## References (bei Bedarf laden)

- `references/speichern.md` - Schreiben: exakte Aufrufe, gemessene Verstuemmelungen,
  Statuswerte (inserted/duplicate/superseded), TTL, visibility. Laden, wenn ein Fakt
  geschrieben oder ein Verlust repariert wird.
- `references/lesen-und-korrigieren.md` - Erinnern und Vergessen: Entitaet gegen Text,
  Suchverhalten, `forget`-Semantik, Korrekturweg. Laden bei recall-/forget-Fragen.
- `references/betrieb.md` - Wartung (`doctor`, taegliche Wache), Sicherung und
  Wiederherstellung, was ein Fakt wert ist, und die Kommandokarte der Installation.
  Laden bei Betriebsfragen - **und immer, wenn `stats`/`list` 0 zeigen oder der
  Doctor `reinit-pglite` empfiehlt** (beides sieht wie Datenverlust aus, ist keiner,
  und der Befehl waere einer).
