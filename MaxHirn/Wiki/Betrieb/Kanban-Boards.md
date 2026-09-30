---
id: 20260930-kanban-boards
title: 'Betrieb — Kanban-Boards'
tags: [betrieb, kanban, aufgaben, dispatch]
created: 2026-09-30
updated: 2026-09-30
related: ['[[Archiv/TASKS]]', '[[Betrieb/Wachen-und-Aufgaben]]', '[[Betrieb/Hermes]]']
summary: 'Die Boards des Hauses: welches Board welche Arbeit traegt, wie eine Karte sofort ausgefuehrt wird, und der gemessene Stand vom 30.09.2026.'
---

# Kanban-Boards

Hermes hat eine dauerhafte Aufgaben-Warteschlange in SQLite, die **alle Profile**
teilen. Eine Karte ist eine Zeile; der Dispatcher laeuft im **Gateway**, startet
binnen etwa einer Minute einen eigenen Prozess mit dem zugewiesenen Profil und
schreibt jede Bewegung in den Ereignisstrom der Karte.

## Zwei Aufgabenorte - nie derselbe Punkt an beiden

| Ort | Wofuer |
|---|---|
| **Board** | Arbeit, die mehrere Profile parallel ausfuehren, die auf Review oder Wiederholung wartet, oder die einen Betriebsprozess startet |
| **`MaxHirn/Archiv/TASKS.md`** | alles, was eine **Entscheidung von Max** ist, und Inhalte der Schutzstufe 0 |

Kartentexte stehen als **Klartext** in `kanban.db` unter `Agenten/` - die Datei geht
in die Sicherung. Also: **keine Zugangsdaten, Bescheide oder Stufe-0-Inhalte** auf
eine Karte, auch nicht als Kommentar.

## Der Board-Satz des Hauses (hoechstens vier)

Ein Board je **Arbeitsart**, nicht je Ordner - jedes weitere Board kostet
Kontext, weil eine Aufgabe sich dann auf zwei Orte verteilt.

| Slug | Zweck |
|---|---|
| `repos` | Klone in `Werkstatt/Repos`, Bots/Profile, Rueckstand, Sicherung |
| `wartung` | Hermes selbst: Gateway, Dashboard, MCP-Spawn-Kette, Updates, Leistung |
| `handel` | Spuren bauen/rechnen/pruefen, Backtest, Befunde |
| `wissen` | Wiki, Skills, Fundus, Vault-Doku |

`default` ist das Alt-Board (Proben, Erstversuche) und bleibt current. Jedes Board
ist ein eigener Ordner mit eigener DB:
`Agenten/Hermes/kanban/boards/<slug>/kanban.db`.

## Die Falle, die jede Karte zur Ausfuehrung macht

**Eine `ready`-Karte wird SOFORT ausgefuehrt** - auch nachts, auch aus dem TUI,
auch wenn sie nur als Vorschlag gemeint war. Was Vorschlag bleiben soll, ist Text
im Chat, keine Karte. Umgekehrt gilt: **`ready` ist kein Beleg fuer einen Lauf** -
`kanban --board <slug> runs <id>` und der Log unter `kanban/logs/t_*.log` zeigen,
ob wirklich ein Prozess lief.

Zwei Verbote gehoeren in **jede** Karte dieses Hauses:

- kein Live-Schalter und keine echte Order (Live laeuft nur ueber die
  Freigabekette),
- nur eigene Pfade stagen, nie `git add -A` (parallele Sitzungen im selben Baum).

Braucht eine Karte Adminrechte oder einen UAC-Prompt, gehoert sie trotzdem ins
Board: der Worker **blockiert mit `needs_input`**, und das ist die richtige
Antwort.

## Gemessener Stand 30.09.2026

```
default   Alt-Board: 9 Karten done, 1 triage (Proben, Erstversuche)
repos     Repo-Flotte: 2 done, 1 blocked
```

Drei Karten liefen in der Nacht zum 30.09.2026 durch bzw. blieben stehen:

| Karte | Ergebnis |
|---|---|
| `t_ffc3e694` Flotte nachziehen | 26 Klone vorgespult (deepseek-harness 2411, laya 887, codex 523 Commits), Gegenprobe "41 aktuell" |
| `t_585c1332` Klone ohne gesicherte `.env` | 7 Klone tragen eine `.env`, keine war gesichert -> Kopien in `Agenten/Hermes/.sicherung/` (Commit 3d78999) |
| `t_5cf6dbfd` Profile ohne `auth.json`-Verknuepfung | **blocked** (`needs_input`): `fomo-radar` und `lokal-first` brauchen einen echten NTFS-Symlink auf `Agenten/Hermes/auth.json`. `ln -s` bildet ohne `SeCreateSymbolicLinkPrivilege` **still eine Kopie** (genau das Insel-Muster, das vermieden werden soll) - das Skript wurde in der headless-Sitzung nicht bestaetigt. Naechster Schritt ist Handarbeit: `powershell -File Agenten\Hermes\scripts\auth-verknuepfen.ps1 -Anwenden` in einer erhoehten Shell. |

## Nachweis und Bedienung

```bash
cd Agenten/Hermes && unset PYTHONHOME PYTHONPATH
./bin/hermes.exe kanban boards list                 # Boards + Kartenzahl
./bin/hermes.exe kanban --board repos list          # Status je Karte
./bin/hermes.exe kanban --board repos runs <id>     # lief ein Prozess?
./bin/hermes.exe kanban --board repos show <id>     # Events inkl. PID, Heartbeats
```

Das `--board <slug>` steht **vor** dem Subkommando; ohne es arbeitet jeder Befehl
im current-Board (`default`) und meldet bei fremden Karten "no such task".

Regeln, Fallen und das Anlegen selbst: Skill `kanban-board`.
