---
id: 20261023-sitzungen-und-worktrees
title: 'Sessions und Worktrees - Bestand 23.10.2026'
tags: [betrieb, ki-agenten, system]
created: 2026-10-23
updated: 2026-10-23
related: ['20260830-ki-ablagen-benutzerordner', '20260830-hermes', '20261020-sitzungs-konsolidierung', '20260830-schutzregeln']
summary: 'Gezielte Bestandsaufnahme bekannter Session-Speicher, Codex-App-Threads und sichtbarer Worktrees mit offenem Abdeckungsrand und Prüfplänen.'
---

# Sessions und Worktrees - Bestand 23.10.2026

## Umfang und Grenzen

Erfasst wurden die bekannten lokalen Speicherorte für Codex, Claude Code und
Hermes sowie die Codex-App-Threadliste und die bekannten
`Werkstatt/Worktrees`. Das ist **keine vollständige Dateisuche über jedes
Laufwerk oder jedes installierte Programm**. Die Codex-App lieferte höchstens
50 Threads; mindestens 50 waren in der Antwort enthalten. Der Codex-Sitzungsindex
und die Hermes-/Claude-Ordner wurden read-only gezählt. Sessioninhalte wurden
nicht ausgewertet.

## Gemessener Bestand

| Quelle | Stand am 23.10.2026 | Befund |
|---|---:|---|
| Codex `~/.codex/sessions` | 387 Dateien, 87.738.092 Byte; jüngste Datei 04:20:47 | Lokale Codex-Sessionablage |
| Codex `~/.codex/session_index.jsonl` | 39 Zeilen | Indexeinträge; nicht als Zahl aller archivierten Threads interpretieren |
| Codex `~/.codex/archived_sessions` | 14 Dateien, 1.308.877 Byte | Separater Archivordner; jüngste Datei 28.08.2026 |
| Codex-App | 50 Threads geliefert, davon 2 mit Status `active` | Limit der App-Abfrage erreicht; dies ist kein Gesamtzähler |
| Claude Code `~/.claude/projects` | 47 direkte Unterordner, 1.612 Dateien, 1.105.930.105 Byte | Session-/Projektablage laut vorhandenem Pfadwissen |
| Hermes `Agenten/Hermes/sessions` | 83 direkte Einträge, 85 Dateien, 47.703.435 Byte | Jüngste Datei 04:21:22; direkter Unterordner `saved` ist vorhanden |
| Codex `~/.codex/worktrees` | nicht vorhanden | Kein Codex-eigener Worktree-Ordner an diesem bekannten Pfad |
| `Werkstatt/Worktrees` | 5 direkte Ordner | Namen: `Arbeitsbereich`, `KI WORKTREE`, `maks.sound`, `omnitrade-live-testnet-verify`, `PC` |

Die zwei in der App als aktiv angezeigten Threads waren `Sessions und Worktrees
erfassen` und `Set up PolyStrata` (Abruf am 23.10.2026). Die Threadliste ist
keine vollständige Sessionhistorie.

## Sichtbare Worktree-Befunde

- `omnitrade-live-testnet-verify` ist ein Git-Checkout unter `O:\Werkstatt\Worktrees`,
  Branch `mainnet-gate`, HEAD `8fd1f314fe8ab89620e972750f3f1fe5004028ae`.
- `KI WORKTREE` enthält einen `.git`-Verweis auf
  `C:/Users/faupe/Documents/GitHub/onchainos-skills/.git/worktrees/KI-WORKTREE`;
  Git meldet `fatal: not a git repository: (NULL)`. Ursache und Nutzungsstatus
  sind ungeklärt. Nicht löschen oder reparieren, bevor Repo-Pfad und Besitzer
  geprüft sind.
- `Arbeitsbereich`, `maks.sound` und `PC` sind im untersuchten Ordnerbestand
  keine normalen Git-Worktrees mit `.git`-Marker. Das sagt nichts darüber aus,
  ob sie andere Arbeitsdaten enthalten.
- Der aufrufende BrainFiles-Git-Root meldet nur sich selbst in
  `git worktree list`; das erfasst keine unabhängigen Repositories unter
  `Werkstatt` oder anderen Laufwerken.

## Vorschläge mit Prüfplan

### 1. Gesamtinventar der Codex-App vervollständigen

**Vorschlag:** App-Threads seitenweise bzw. über die native Codex-Datenbank
erfassen, damit das 50-Thread-Limit nicht als Vollständigkeit missverstanden
wird.

**Prüfplan:** (a) Quelle und Schema der nativen Threaddatenbank bestimmen,
read-only; (b) Zahl der eindeutigen Thread-IDs gegen `session_index.jsonl`
und die App-Liste abgleichen; (c) aktive Threads anhand des App-Status separat
bestätigen; (d) Differenzen samt Abrufzeit festhalten. Keine Sessioninhalte
kopieren, bis der Nutzer das ausdrücklich möchte.

### 2. PC-weite Worktree-Suche abschließen

**Vorschlag:** Git-Worktree-Metadaten über die übrigen lokalen Volumes und
bekannten Projektwurzeln ermitteln.

**Prüfplan:** (a) vorhandene Laufwerksbuchstaben und bekannte Repo-Wurzeln
listen; (b) ausschließlich `.git`-Dateien bzw. `git worktree list --porcelain`
für gefundene Repositories lesen; (c) dieselben Checkout-Pfade deduplizieren,
Junctions berücksichtigen und Existenz/Branch/HEAD erfassen; (d) keine
Ordnerinhalte rekursiv inventarisieren und keine Worktrees verändern.

### 3. Verwaisten Verweis `KI WORKTREE` klären

**Vorschlag:** Repo-Root `onchainos-skills` und Besitzer des Worktrees finden.

**Prüfplan:** (a) den eingetragenen Git-Common-Dir-Pfad mit `Test-Path`
prüfen; (b) nur falls vorhanden, `git worktree list --porcelain` im Repo
lesen; (c) Branch, HEAD und Änderungen erfassen; (d) bei fehlendem Repo den
Worktree-Eintrag unverändert lassen und den ursprünglichen Pfad aus
Git-Metadaten suchen; (e) erst nach eindeutiger Zuordnung einen separaten
Vorschlag zur Reparatur oder Bereinigung erstellen.

### 4. Session-Sicherungsstrategie verifizieren

**Vorschlag:** Prüfen, ob Codex-, Claude- und Hermes-Sessions absichtlich
außerhalb der regulären BrainFiles-Sicherung bleiben oder gesichert werden
sollen.

**Prüfplan:** (a) Sicherungsskript und Ausschlusslisten read-only prüfen;
(b) Zielmedien und verfügbare Kapazität feststellen; (c) einzelne
repräsentative Dateien per Hash gegen eine vorhandene Sicherung vergleichen;
(d) Ergebnis und Umfang vor jeder Änderung vorlegen. Keine Sessiondaten
verschieben oder kopieren, bevor Ziel und Datenschutzumfang geklärt sind.

## Wiederholbare Erhebung

Die Zahlen oben sind ein Snapshot, kein automatisch aktueller Zustand. Bei
einer Wiederholung dieselben Pfade messen, Zeitstempel und Bytezahlen sichern
und die App-Abfragegrenze separat notieren. Die alte Erhebung in
[[KI-Ablagen-im-Benutzerordner]] bleibt als historischer Stand vom 30.08.2026
erhalten.
