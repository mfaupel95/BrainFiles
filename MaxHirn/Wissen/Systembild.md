---
id: 20260930-systembild
title: 'Systembild'
tags: [hardware, struktur, betrieb]
created: 2026-09-30
updated: 2026-09-30
related: [20260830-hardware, 20260830-ordnerstruktur]
summary: 'Gemessener Stand von C: und O: (Belegung, Schwergewichte, Programme) und die daraus abgeleiteten Aufraeum-Kandidaten.'
---

# Systembild (gemessen 30.09.2026)

Momentaufnahme, Junctions ausgelassen. Plan: `docs/superpowers/plans/2026-09-30-system-und-ordner-optimieren.md`. Siehe [[Hardware]], [[Ordnerstruktur]].

| Laufwerk | Belegt | Frei | Rolle |
|---|---|---|---|
| C: | 441 GB | **34 GB** | System, Programme, Nutzerprofil, BrainFiles-Repo |
| O: "Dokumente" | 439 GB | 113 GB | Modelle 180, Werkstatt 62, Documents 62, Archiv 45, Zweitkopie 41, iTunes 37 |
| G: BackUp | 2.210 GB | 541 GB | Sicherung |
| J: Extern_BackUp | 1.779 GB | 175 GB | Sicherung extern |
| H: Music Sync | 1.369 GB | 488 GB | Musik |
| Q: musik_lib (exFAT) | 1.706 GB | 157 GB | Musik, **Zustand "Warnung"** |

## C: nach Ordner (GB)

Users 256 (AppData 125, Documents 72, .cache 16, Music 10, .docker 6,5, .rustup 5, .unsloth 4,9), Windows 53, Program Files 22, Program Files (x86) 17, ProgramData 16, Hermes.alt-20260916 3,6.

AppData: Local\Packages 24, Local\Programs 9, Local\NVIDIA 5,8, Local\pnpm 4,3, Local\hermes 4,1, Roaming\Pioneer (rekordbox) 11,7, Roaming\Claude 11,2, Roaming\npm 5,3, Roaming\Cemu 4,4.

Documents: BrainFiles 38 (ohne Junctions), Windows11 16, GitHub 16.

## Verknuepfungen

`BrainFiles\Modelle` -> `O:\Modelle` (180 GB), `BrainFiles\Werkstatt` -> `O:\Werkstatt` (62 GB), `O:\Wiki` -> `BrainFiles\MaxHirn\Wiki`. Vor jedem Messen oder Loeschen `LinkType` pruefen.

## Programme

186 Registry-Eintraege. Mehrfach vorhanden: Python 3.11/3.13/3.14, drei Browser, .NET-Laufzeiten 1.0 bis 10 in x64 und x86 (ca. 5 GB), zwei .NET SDK 10.

## Kandidaten (Hypothesen, Stand der Messung)

Zweitkopie 41 GB, Ollama-Blobs gegen GGUF, Docker-Datenträger 54 GB, Klone doppelt in Documents\GitHub und Werkstatt\Repos, zwei pnpm-Speicher, 25 .bak-Dateien und `nul` in der Wurzel, "(Kopie)"-Ordner in Windows11.

## Pruefergebnisse 30.09.2026 (Task 2 und 3, nur gemessen)

- **Widerlegt:** `O:\MaxHirn-Zweitkopie` (41 GB) ist kein Doppelgaenger, sondern die taegliche Zweitkopie (`Routinen/zweitkopie.ps1`, 21:00, siehe [[Routinen]]). Bleibt.
- **Klone Documents\GitHub gegen Werkstatt\Repos:** nur `obsidian-skills` steht auf demselben Commit (Werkstatt-Klon veraendert). Alle anderen sieben Paare stehen auf verschiedenen Staenden, teils mit lokalen Aenderungen (`Dirty`). Keine sichere Loeschung ohne Einzelentscheidung. `intelligent-trading-bot` liegt in `Werkstatt` und `Werkstatt\Repos` auf demselben Stand, beide veraendert.
- **`Windows11\* (Kopie)`:** keine echten Kopien, meist Teilmengen (z. B. Maximilian 6,3 GB gegen 1,4 GB, Native Instruments 6,7 gegen 1,3 GB). Nicht als Duplikat loeschbar ohne Hash-Vergleich.
- **C:-Kandidaten, gemessen:** `.cache\huggingface` 15,1 GB (53 Dateien), `.docker\models` 6,5 GB, `Hermes.alt-20260916` 3,6 GB, `Packages\Cinebench` 4,4 GB, `Packages\PictureGuide` 2,1 GB, `Roaming\npm\node_modules` 5,3 GB, `pnpm` 4,3 GB, `Roaming\Claude\vm_bundles` 8,3 GB (von der App verwaltet, nicht anfassen).
- Docker, Hermes, Ollama und llama-server laufen; Eingriffe an deren Ordnern erst nach Beenden.
