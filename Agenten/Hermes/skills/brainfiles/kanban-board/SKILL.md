---
name: kanban-board
description: Use when ein Kanban-Board oder eine Karte angelegt wird.
version: 0.1.0
author: Hermes Agent
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Kanban, Aufgaben, Profile, Dispatch, Telegram]
---

# Kanban-Board (Hermes-Taskboard)

Dauerhafte Aufgaben-Warteschlange, die ALLE Hermes-Profile teilen. Eine Karte ist
eine Zeile in SQLite, jeder Handoff ist fuer jedes Profil lesbar, und die
Ausfuehrung ist ein eigener Betriebssystemprozess mit dem Profil als Identitaet.

## When to Use

- Max sagt "schlage Kanbans vor", "leg <board> an", "als Karte eintragen"
- mehrere Profile sollen unabhaengig an derselben Sache arbeiten
- eine Aufgabe soll einen Review, einen Retry oder eine Antwort von Max abwarten
- Flottenarbeit, bei der ein Spezialist je Gegenstand laeuft (ein Bot je Repo)

## Wann ein Board, wann die Liste

- **Board:** Arbeit, die auf mehrere PROFILE verteilt parallel laufen soll, mit
  Abhaengigkeiten (Fan-out -> Fan-in), Wiederholung nach Fehlschlag, Review, oder
  wenn etwas auf einen Menschen wartet (`blocked`/`needs_input`). Auch fuer
  Flottenarbeit: ein Spezialist je Gegenstand (ein Bot je Repo).
- **`MaxHirn/Archiv/TASKS.md`** (Skill `aufgabenliste-pflegen`) bleibt fuer
  alles, was eine ENTSCHEIDUNG von Max ist, und fuer Inhalte der Schutzstufe 0.
- **Nie** ein Board fuer Zugangsdaten, Schluessel, Bescheide oder sonstige
  Stufe-0-Inhalte: Kartentexte stehen als KLARTEXT in `kanban.db`, und die DB
  liegt unter `Agenten/` und geht damit in die Sicherung (G: und ausser Haus).
- **Faustregel: hoechstens vier Boards.** Jedes weitere Board kostet Kontext -
  eine Aufgabe verteilt sich dann auf zwei Orte, und niemand weiss mehr, wo er
  nachsehen muss. Ein Board je ARBEITSART, nicht je Ordner.

## Board-Satz des Hauses

| Slug | Zweck | Zuerst zustaendig |
|---|---|---|
| `repos` | Klone in `Werkstatt/Repos`, Bots/Profile, Rueckstand, Sicherung | `default`, `hermes-wartung` |
| `wartung` | Hermes selbst: Gateway, Dashboard, MCP-Spawn-Kette, Updates, Leistung | `hermes-wartung` |
| `handel` | Spuren bauen/rechnen/pruefen, Backtest, Befunde | `default`, `markt-recherche` |
| `wissen` | Wiki, Skills, Fundus, Vault-Doku | `obsidian-skills`, `basic-memory` |

`default` ist das Alt-Board und bleibt current; die anderen werden je Befehl mit
`--board <slug>` angesprochen. Kein Board fuer Steuer, Fristen, Belege.

## Board anlegen

```bash
cd Agenten/Hermes && unset PYTHONHOME PYTHONPATH
./bin/hermes.exe kanban boards create repos \
  --name "Repo-Flotte" --description "..." --color "#8b5cf6" \
  --default-workdir "C:/Users/faupe/Documents/BrainFiles"
```

Jedes Board ist ein eigener Ordner mit eigener DB:
`Agenten/Hermes/kanban/boards/<slug>/kanban.db`. `--default-workdir` setzt den
Arbeitsordner der Karten (die BrainFiles-WURZEL, wenn Karten verschiedene
Unterordner sehen muessen). `--switch` NICHT beifuegen - sonst ist `default`
nicht mehr current und jeder spaetere Befehl ohne `--board` landet woanders.

## Karte anlegen

Das `--board` steht VOR dem Subkommando:

```bash
./bin/hermes.exe kanban --board repos create "Kurztitel" \
  --body "Auftrag, Gegenstand, Verbot, Beleg" \
  --assignee default --priority 2 \
  --workspace "dir:C:/Users/faupe/Documents/BrainFiles"
```

- `--assignee` MUSS ein existierendes Profil sein: vorher `kanban assignees`
  lesen (die Liste ist kuerzer als der Profile-Ordner - weggelegte Profile unter
  `profiles/.deleted/` fehlen darin, ein Dispatch dorthin scheitert).
- `--workspace` ist `scratch` (Vorgabe), `dir:<pfad>` (gemeinsamer Baum) oder
  `worktree` (eigener Branch; mit `--project <repo>` an ein Repo gebunden).
- `--parent <id>` erzeugt die Abhaengigkeit (Kind bleibt `todo`, bis alle Eltern
  `done` sind). `--triage` parkt die Karte zum Spezifizieren, `--skill <name>`
  zwingt Skills in den Worker.
- Ein Auftrag, der Adminrechte oder einen UAC-Prompt braucht, gehoert trotzdem
  als Karte ins Board: der Worker blockiert dann mit `needs_input`, und DAS ist
  die richtige Antwort - nicht raten und nicht die Karte weglassen.

### Der Body ist die Arbeitsanweisung

Formuliere ihn so, dass ein Fremder ihn ohne Rueckfrage ausfuehren kann:
Gegenstand und Pfade, das Werkzeug das schon existiert (kein Nachbau), die
VERBOTE (laufende Prozesse, Live-Pfade, bestimmte Klone), und einen SATZ, der
als Beleg zaehlt ("zweiter Lauf meldet alle als aktuell").
Fuer dieses Haus gehoeren zwei Verbote in jede Karte:

- **Kein Live-Schalter, keine echte Order** aus einer Karte - Live laeuft nur
  ueber die Freigabekette (`freigabe.erfuellt`, Freigabefenster, `/ja_<spur>`).
- **Nur eigene Pfade stagen, nie `git add -A`** - die Bots arbeiten im selben
  Baum wie eine parallele Sitzung, sonst wandert Fremdarbeit in den Commit.

## Karten auf Telegram melden lassen

```bash
./bin/hermes.exe kanban --board repos notify-subscribe t_xxxx \
  --platform telegram --chat-id <id> --chat-type dm --delivery-mode notify
```

Die Chat-ID NICHT aus dem Kopf setzen: `kanban notify-list` zeigt bestehende
Abos samt Plattform und ID - die eigene Zeile dort ist die richtige Quelle.
`--delivery-mode notify` meldet nur (Vorgabe), `notify+wake`/`wake` wecken
zusaetzlich die Sitzung des Operators.

Eine TUI-Sitzung hat KEINEN Live-Kanal: eine Meldung, die nur "origin" ist,
kommt dort nie an. Darum auf `telegram` abonnieren, wenn Max es sehen soll.

## Nachweis (Pflicht, sonst ist der Erfolg nur eine Zeile)

```bash
./bin/hermes.exe kanban boards list                 # Board da, Karten gezaehlt
./bin/hermes.exe kanban --board repos list          # Status je Karte
./bin/hermes.exe kanban --board repos runs <id>     # Run aktiv? Laufzeit?
./bin/hermes.exe kanban --board repos show <id>     # Events inkl. PID, Heartbeats
./bin/hermes.exe kanban --board repos notify-list   # Abo gesetzt?
```

Dazu die Worker-Prozesse zaehlen (`python.exe`/`pythonw.exe` aus
`Agenten/Hermes/tools/python-*`) und `Agenten/Hermes/kanban/logs/<id>.log`
beobachten. `runs`/`show` belegen die Wirkung, `list` allein belegt nur den
Datenbankstand.

## Fallen

- **Eine `ready`-Karte wird SOFORT ausgefuehrt.** Der Dispatcher laeuft im
  GATEWAY, nicht in der Sitzung: binnen etwa einer Minute ist die Karte geclaimt
  und ein Profilprozess gestartet - auch nachts, auch im TUI. Karten anlegen
  heisst also Arbeit STARTEN, nicht Arbeit vorschlagen. Den Body wie eine
  Auftragskarte schreiben, und was nur VORSCHLAG sein soll, als Text liefern
  statt als Karte.
- **`ready` heisst noch nicht, dass etwas passiert.** Nach dem Anlegen `runs`
  pruefen (Laufzeit, Heartbeats) - ein Karten-Status allein sagt nichts ueber
  den Prozess. Umgekehrt: keine Karte in `running` heisst nicht, dass der
  Dispatcher steht; erst Prozessliste und `kanban/logs/` ansehen.
- **`notify-subscribe` sucht ohne `--board` im CURRENT-Board** und antwortet
  `no such task: t_xxxx`, obwohl die Karte existiert. `--board <slug>` vor das
  Subkommando setzen, auch bei `list`/`show`/`runs` und allen anderen Verben.
- **Der Dispatcher braucht das Gateway.** Laeuft es nicht, bleibt jede Karte in
  `ready` liegen - dann zuerst die Gateway-Identitaet pruefen (Skill
  `hermes-maintenance`, `Routinen/gateway-waechter.ps1`), nicht das Board.
- **Skript heisst `hermes.exe`** und liegt als `Agenten/Hermes/bin/hermes.exe`;
  vor jedem Aufruf `PYTHONHOME`/`PYTHONPATH` entfernen. Die Modell-/Werkzeugseite
  derselben Schicht sind die `kanban_*`-Werkzeuge (fuer Worker und
  Orchestrator-Profile), die CLI ist fuer Mensch und Skript - beide schreiben
  dieselbe DB.
- **Karten ersetzen TASKS.md nicht.** Was nur eine Entscheidung oder einen
  Belegsatz braucht, bleibt in der Liste; sonst stehen die offenen Punkte des
  Hauses an zwei Orten und die Liste luegt.

## Einzelkarten-Werkzeuge

Fuer den laufenden Betrieb (nicht beim Anlegen) gibt es `comment`, `attach`,
`block`/`unblock`, `schedule` (parkt auf ZEIT, nicht auf Mensch),
`request-review`/`request-changes`, `reclaim` (haengenden Claim loesen),
`reassign`, `set-model`, `promote`, `archive`, `stats` und den Ereignisstrom
mitlesen (`kanban tail`).
`complete` markiert fertig - ein Commit oder Diff allein schliesst keine Karte.
