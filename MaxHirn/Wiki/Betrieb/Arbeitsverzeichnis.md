---
id: 20260930-arbeitsverzeichnis
title: 'Betrieb — Arbeitsverzeichnis (cwd) der Agenten'
tags: [betrieb, hermes, pfade, cwd, terminal]
created: 2026-09-30
updated: 2026-09-30
related: ['[[Archiv/TASKS]]', '[[Betrieb/Hermes]]', '[[LEITFADEN]]']
summary: 'Hermes-Werkzeuge starten in Agenten/Hermes, alle Pfade in Skills und Notizen sind relativ zur BrainFiles-Wurzel - der Anker, die gemessene Falle und was davon unberuehrt bleibt.'
---

# Arbeitsverzeichnis (cwd)

Max hat am 30.09.2026 entschieden (T-233): **Hermes' Werkzeuge und Sitzungen starten in
`Agenten/Hermes`, nicht in der BrainFiles-Wurzel.** Gesetzt ist das in
`Agenten/Hermes/config.yaml` als `terminal.cwd`.

    terminal:
      backend: local
      cwd: C:\Users\faupe\documents\BrainFiles\Agenten\Hermes

Damit liegen zwei Bezugssysteme nebeneinander, und das ist die eigentliche Falle:

| Bezugssystem | Gilt fuer |
|---|---|
| **cwd = `Agenten/Hermes`** | das, was das `terminal`-Werkzeug ohne `cd` tut |
| **BrainFiles-Wurzel** | **alle** Pfade in Skills, Notizen, Wiki und in diesem Dokument |

`$HERMES_HOME` zeigt auf `Agenten/Hermes` (in jeder Sitzung gesetzt, gemessen).

## Der Anker - und die gemessene Falle

    cd "$HERMES_HOME/../.."      # = BrainFiles-Wurzel  <- RICHTIG

**`cd "$HERMES_HOME/.."` ist falsch** und tut trotzdem etwas: es landet in `Agenten`, eine
Ebene zu hoch. Ein Befehl wie `Agenten/Routinen/systempruefung.ps1` findet von dort aus nichts
und meldet nur `No such file or directory`. Am 30.09.2026 genau so passiert - der erste
Reparaturlauf dokumentierte den falschen Anker, weil die Verkettung `cd ... && <befehl>` den
Fehlschlag verschluckt und der naechste Befehl scheinbar grundlos scheitert.

## Was davon unberuehrt bleibt (gemessen)

- **`Agenten/Routinen/*.ps1`** - 51 von 53 Skripten lokalisieren sich ueber `$PSScriptRoot`
  (die zwei Ausnahmen sind Einmal-Skripte vom 02.09.2026). Geplante Aufgaben haben kein
  Startverzeichnis (`Starten in: Nicht zutreffend`) - genau deshalb ist das richtig.
- **Cron-Wachen** (`Agenten/Hermes/scripts/*.py`) - `Path(__file__).resolve().parent`, danach
  drei `dirname()`-Stufen bis zur Wurzel. Aus jedem Verzeichnis lauffaehig.
- **Wurzel-Aufrufer** `omnitrade.cmd` und `omnitrade-auswertung.cmd` - arbeiten mit `%~dp0`.
- **`git -C <repo>`** - Argumente wie `Agenten/Handel/spiegel` loest git gegen den Repo-Root auf,
  nicht gegen das cwd.
- **Max' eigene Shell** - sein Startverzeichnis ist die Wurzel; `terminal.cwd` betrifft nur die
  Werkzeuge der Agenten.

## Was repariert wurde

Root-relative **Befehle** in den Anleitungen wurden cwd-fest gemacht (Praefix
`cd "$HERMES_HOME/../.." &&`), ohne die Pfadangaben selbst zu aendern:

- `skills/journal-spiegelung`, `skills/claude-code-imports/verbindungen` (auch die Vault-Kopie
  `MaxHirn/.claude/skills/verbindungen`), `skills/claude-code-imports/rueckschau`,
  `skills/brainfiles/systempruefung-abarbeiten`, `skills/brainfiles/betriebsrunde`,
  `skills/brainfiles/wirkung-nachweisen`, `skills/aufgabenliste-pflegen`, `Agenten/Bus/README.md`.
- `Agenten/Werkzeuge/projectatlas/tasks-anpassen.py` - der einzige Code mit einem relativen
  Pfad-Literal; jetzt `Path(__file__).resolve().parents[3] / "MaxHirn/Archiv/TASKS.md"`.
- Regel fuer neue Skills und Skripte: **selbstlokalisierend** (`Path(__file__)`,
  `$PSScriptRoot`) oder ausdruecklicher `cd "$HERMES_HOME/../.."` — nie ein blosses
  `Agenten/...` als Aufruf.

## Nachweis (30.09.2026, aus `Agenten/Hermes` heraus)

    cd "$HERMES_HOME/../.." && Agenten/Handel/scanner/.venv/Scripts/python.exe Agenten/Handel/spiegelstand.py
    -> Ergebnis: 29 von 29 Spuren byte-gleich (Q:)

    cd "$HERMES_HOME/../.." && python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py --ruhig
    -> OK: jede Nummer genau einmal, beide Abschnitte vorhanden