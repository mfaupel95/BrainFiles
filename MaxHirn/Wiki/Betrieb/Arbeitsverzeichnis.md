---
id: 20260930-arbeitsverzeichnis
title: 'Betrieb — Arbeitsverzeichnis (cwd) der Agenten'
tags: [betrieb, hermes, pfade, cwd, terminal]
created: 2026-09-30
updated: 2026-10-01
related: ['[[Archiv/TASKS]]', '[[Betrieb/Hermes]]', '[[LEITFADEN]]']
summary: 'Hermes-Sitzungen starten in Agenten/Hermes - terminal.cwd fuer Gateway/Cron, ein hermes-Wrapper im PowerShell-Profil fuer CLI und TUI; alle Pfade in Skills und Notizen sind relativ zur BrainFiles-Wurzel.'
---

# Arbeitsverzeichnis (cwd)

Max hat am 30.09.2026 entschieden (T-233): **Hermes' Werkzeuge und Sitzungen starten in
`Agenten/Hermes`, nicht in der BrainFiles-Wurzel.** Zwei Mechanismen tragen das - der erste
allein reichte nicht, das ist am 01.10.2026 gemessen worden:

| Weg | Mechanismus | Gilt fuer |
|---|---|---|
| `terminal.cwd` in `Agenten/Hermes/config.yaml` | Umgebungsvariable `TERMINAL_CWD` | Gateway, Cron, entfernte Backends |
| `hermes`-Wrapper im PowerShell-Profil | `Push-Location` vor dem Aufruf | interaktive **CLI und TUI** |

    terminal:
      backend: local
      cwd: C:\Users\faupe\documents\BrainFiles\Agenten\Hermes

Damit liegen zwei Bezugssysteme nebeneinander, und das ist die eigentliche Falle:

| Bezugssystem | Gilt fuer |
|---|---|
| **cwd = `Agenten/Hermes`** | das, was das `terminal`-Werkzeug ohne `cd` tut |
| **BrainFiles-Wurzel** | **alle** Pfade in Skills, Notizen, Wiki und in diesem Dokument |

`$HERMES_HOME` zeigt auf `Agenten/Hermes` (in jeder Sitzung gesetzt, gemessen).

## Die gemessene Falle: `terminal.cwd` gilt interaktiv nicht

Eine **interaktive** Sitzung uebernimmt das Startverzeichnis der Shell (`os.getcwd()`);
`terminal.cwd` gilt nur fuer Gateway, Cron und entfernte Backends (so steht es auch im
Hermes-Code: *"A local interactive session starts where the user launched (or in the
--worktree), the classic CLI's rule"*, `hermes_cli/main_tui_launch.py`).

Folge bis zum 01.10.2026: von der Wurzel aus gestartet, liefen CLI **und** TUI in der Wurzel,
waehrend die Desktop-App in `Agenten\Hermes` startete. Zeuge ist `state.db`:

    select id, source, cwd from sessions order by started_at desc;
    -> alle TUI-/CLI-Sitzungen: cwd = C:\Users\faupe\Documents\BrainFiles
    -> die Desktop- und Cron-Sitzungen: cwd = ...\Agenten\Hermes

Damit zeigte jede Anweisung `cd "$HERMES_HOME/../.."` (die den Anker `Agenten/Hermes`
voraussetzt) eine Ebene **ueber** die Wurzel - genau der Fehler, den T-233 beseitigen sollte.

## Der `hermes`-Wrapper

`C:\Users\faupe\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` (Sicherung
`.bak-20261001`) definiert eine Funktion `hermes`, die den echten `hermes.exe`-Aufruf in
`Agenten\Hermes` startet und die Shell selbst per `Push-Location`/`Pop-Location` **dort
laesst, wo sie war** - die Wurzel-Aufrufer (`omnitrade.cmd`, `bestand.cmd`, `jevgrep.cmd`)
greifen weiter.

| Aufruf | Sitzung startet in |
|---|---|
| `hermes` | `Agenten\Hermes` |
| `hermes -Hier ...` | dem aktuellen Verzeichnis |
| `hermes -p <bot> ...` | dem Startordner dieses Profils (`profiles\<bot>\config.yaml`, `terminal.cwd`) |

Nachweis (01.10.2026, `Agenten/Werkzeuge/anker-pruefen.ps1` - laedt das echte Profil und
haengt statt `hermes.exe` eine Attrappe vor den PATH, damit das Kind sein Arbeitsverzeichnis
meldet):

    hermes (Vorgabe)                   ok         ...\Agenten\Hermes
    hermes -Hier                       ok         ...\BrainFiles
    hermes -p gibtsnicht               ok         ...\Agenten\Hermes
    hermes -p agent-trade-kit          ok         ...\Werkstatt\Repos\agent-trade-kit
    Shell-cwd danach                   ok         ...\BrainFiles

Zweiter Zeuge: eine ueber den Wrapper gestartete Sitzung traegt in `state.db` erstmals
`cwd = ...\Agenten\Hermes`.

**Was der Wrapper nicht deckt:** `cmd.exe` und andere Shells (dort bleibt es beim
Startverzeichnis der Shell - die Windows-Terminal-Profile "Eingabeaufforderung" und
"BRAINFILES" starten in der Wurzel, absichtlich), und `hermes --resume`/`-c`: eine
wiederaufgenommene Sitzung kehrt in **ihr aufgezeichnetes** Verzeichnis zurueck
(`--no-restore-cwd` bzw. `--in DIR` heben das auf). Fuer eine Repo-Bot-Sitzung ist das
erwuenscht.

## Der Anker - und die gemessene Falle

    cd "$HERMES_HOME/../.."      # = BrainFiles-Wurzel  <- RICHTIG

**`cd "$HERMES_HOME/.."` ist falsch** und tut trotzdem etwas: es landet in `Agenten`, eine
Ebene zu hoch. Ein Befehl wie `Agenten/Routinen/systempruefung.ps1` findet von dort aus nichts
und meldet nur `No such file or directory`. Am 30.09.2026 genau so passiert - der erste
Reparaturlauf dokumentierte den falschen Anker, weil die Verkettung `cd ... && <befehl>` den
Fehlschlag verschluckt und der naechste Befehl scheinbar grundlos scheitert.

## Befehle fuer Max: PowerShell, nicht bash

**Die Werkzeug-Shell der Agenten ist bash (git-bash/MSYS), Max' Shell ist PowerShell.**
Kopiert Max einen Befehl aus dem Werkzeugprotokoll, scheitert er an Woertern, die es nur
in bash gibt — gemessen am 01.10.2026: `export : Der Begriff "export" wird nicht als Name
eines Cmdlets ... erkannt`.

| bash (Werkzeuge) | PowerShell (Max) |
|---|---|
| `export NAME=WERT` | `$env:NAME = "WERT"` |
| `rm -f datei` | `Remove-Item datei -Force` |
| `$VAR` | `$env:VAR` |
| `head -20`, `wc -l`, `grep` | `Select-Object -First 20`, `Measure-Object`, `Select-String` |
| `/c/Users/faupe/...` | `C:\Users\faupe\...` |
| `python x.py` (im Wurzelverzeichnis) | `.\x.cmd` oder `& 'C:\...\x.cmd'` |

Regeln daraus:

1. **Ein Befehl fuer Max wird als PowerShell-Zeile geschrieben und als solche markiert**
   („zum Einfuegen"), nie als Kopie eines Werkzeugaufrufs.
2. **Relative Programme brauchen in PowerShell `.\`** — ohne das sucht PowerShell ein
   Modul und meldet „Der Begriff ... ist nicht als Name eines Cmdlets ... erkannt".
3. **Wurzel-Aufrufer (`.cmd`) sind der beste Weg**: `.\jevgrep.cmd`, `.\omnitrade.cmd`,
   `.\bestand.cmd` laufen aus jedem Verzeichnis und in jeder Shell.
4. `git`-Befehle ohne Pfadangabe (`git status`) sind in beiden Shells gleich — dort ist
   nur das Arbeitsverzeichnis zu beachten.

## Was davon unberuehrt bleibt (gemessen)

- **`Agenten/Routinen/*.ps1`** - 51 von 53 Skripten lokalisieren sich ueber `$PSScriptRoot`
  (die zwei Ausnahmen sind Einmal-Skripte vom 02.09.2026). Geplante Aufgaben haben kein
  Startverzeichnis (`Starten in: Nicht zutreffend`) - genau deshalb ist das richtig.
- **Cron-Wachen** (`Agenten/Hermes/scripts/*.py`) - `Path(__file__).resolve().parent`, danach
  drei `dirname()`-Stufen bis zur Wurzel. Aus jedem Verzeichnis lauffaehig.
- **Wurzel-Aufrufer** `omnitrade.cmd` und `omnitrade-auswertung.cmd` - arbeiten mit `%~dp0`.
- **`git -C <repo>`** - Argumente wie `Agenten/Handel/spiegel` loest git gegen den Repo-Root auf,
  nicht gegen das cwd.
- **Max' eigene Shell** - ihr Startverzeichnis bleibt die Wurzel (Windows-Terminal-Profil
  "BRAINFILES" und die Profilzeile `Set-Location $BrainFiles`); nur der `hermes`-Aufruf wird
  durch den Wrapper umgelenkt.

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

## Befehle fuer Max sind PowerShell (01.10.2026)

Max' Shell ist PowerShell - `grep`, `ls`, `cat` und bash-`for`-Schleifen gibt es dort
nicht ("Der Begriff \"grep\" wird nicht als Name eines Cmdlets ... erkannt"). Daraus zwei
Regeln: einzeilige Nachweise SELBST fahren und nur das Ergebnis zeigen; muss er selbst
laufen, `Select-String` / `Get-ChildItem` / `Get-Content` verwenden und den Befehl vorher
einmal echt in PowerShell ausprobieren. Arbeitsregel im Skill `brainfiles-auftrag`.
