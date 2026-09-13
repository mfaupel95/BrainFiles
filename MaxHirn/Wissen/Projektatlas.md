---
id: 20260913-projektatlas
title: 'ProjectAtlas'
tags: [mcp, betrieb, ki-agenten]
created: 2026-09-13
updated: 2026-09-13
related: [20260830-verbindungen, 20260830-hermes, 20260830-werkzeuge]
summary: 'ProjectAtlas: Rust-Werkzeug, das je Repo eine SQLite-Karte der Struktur anlegt, damit Agenten die richtige Datei finden statt breit zu lesen. Fork, Laufzeit, MCP-Eintrag, Rezept je Repo und die vier gemessenen Grenzen.'
---

# ProjectAtlas

Ein Werkzeug, das **vor** dem Lesen greift: Es legt je Repository eine
SQLite-Karte der Struktur an — Ordnerzwecke, Dateizusammenfassungen,
Symbolgraph, Volltextsuche, Token-Telemetrie — und beantwortet die Frage
„welche Datei ist für X zuständig?" in einem Aufruf. Ein Agent liest danach
**eine** Stelle statt zwanzig. Alles läuft lokal, ohne Dienst, Konto oder
Schlüssel.

Herkunft: [styler-ai/ProjectAtlas](https://github.com/styler-ai/ProjectAtlas),
MIT, Rust, Fassung **v0.4.5** (20.08.2026).

## Wo es liegt

| Was | Wo |
|---|---|
| Fork (außer Haus) | `mfaupel95/ProjectAtlas`, öffentlich, Fork von `styler-ai/ProjectAtlas` (13.09.2026) |
| Arbeitsklon | `Werkstatt/Repos/ProjectAtlas` — `origin` = Fork, `upstream` = Original, volle Historie |
| Laufzeit | `Agenten/Werkzeuge/projectatlas/v0.4.5/projectatlas.exe` samt Kopie in `bin/` |
| Atlas je Repo | `<repo>/.projectatlas/` — Laufzeitzustand, nicht im Git |
| Indexier-Lauf | `Agenten/Werkzeuge/projectatlas/indexieren.sh` (idempotent, Logs daneben) |
| Bot | `hermes -p projectatlas chat`, Arbeitsverzeichnis `Werkstatt/Repos/ProjectAtlas` |

Die Laufzeit stammt aus dem Release-Archiv `projectatlas-v0.4.5-x86_64-pc-windows-msvc.zip`,
geprüft gegen `SHA256SUMS` des Release
(`30a0dadd9bc18f5026a0cebf5a2f742cec54988599dff92401e73276a7adcec8`). Bewusst **nicht**
der Codex-Plugin-Weg: Dessen Installer schreibt zusätzlich in die
Codex-Marketplace-Registry und in fremde Projektkonfigurationen — hier soll ein
Eintrag an einer Stelle stehen, im [[Verbindungen|MCP-Manifest]].

## Bedienung

CLI — **globale Schalter stehen vor dem Unterbefehl**, sonst bricht der Aufruf ab:

```
projectatlas --format json overview          # Zahlen zur Karte
projectatlas --format json files "suchbegriff"
projectatlas --format json slice <datei> --start-line <n> --end-line <m>
projectatlas health-check --source-only --limit 50
projectatlas token                           # geschätzte Token-Ersparnis
projectatlas scan                            # Karte neu aufbauen
```

MCP bei Hermes: **43 `atlas_*`-Werkzeuge** (Eintrag `projectatlas`, nur Hermes).
Einstieg ist `atlas_session_brief` mit `query` und `compact: true`; es antwortet
mit Rangliste und dem nächsten Aufruf. `atlas_overview`, `atlas_folders`,
`atlas_files` sind der Rückfallweg, `atlas_slice` liefert die exakte Quellstelle.

**Ein** Server bedient **jedes** indexierte Repository: Der im Eintrag gebundene
Atlas ist der Standard (`Werkstatt/omnitrade`), ein anderes Repo kommt über
`project_path` (bzw. dauerhaft `atlas_set_project_path`) dazu. Beides zugleich
zu senden ist ein Fehler.

## Rezept: Repo kartieren

```
cd <repo> && "<exe>" init          # legt .projectatlas/ an, indexiert, schreibt Host-Configs
```

Danach liegt im Repo auch `.projectatlas/projectatlas.mcp.json` (für
`.mcp.json`-Hosts), `...claude.mcp.json` (Claude Code) und
`...opencode.json` — jeweils mit absolutem Pfad zur Laufzeit, `--require-version`
und festem `--db`/`--config`. Diese Dateien sind die **Vorlage**; der Hermes-Eintrag
wurde daraus gebaut. Damit `.projectatlas/` einen Fremd-Klon nicht beschmutzt,
steht der Ordner in `.git/info/exclude` (nicht in der `.gitignore` des Originals).

## Rezept: Bot an seinen Atlas hängen

Jeder Repo-Bot hat ein eigenes Profil mit eigenem Arbeitsverzeichnis; damit er
seinen eigenen Atlas hat, bekommt sein Profil denselben Eintrag mit `--db` auf
**sein** Repo. Der Eintrag ist idempotent zu setzen:

```
hermes.exe -p <bot> mcp add projectatlas --command "<exe>" ^
  --args --require-version 0.4.5 --db "<pfad>/.projectatlas/projectatlas.db" --config "<pfad>/.projectatlas/config.toml" mcp
```

Rückfrage „Enable all 43 tools?": `hermes mcp add` **hängt ohne Terminal** —
aus einer Werkzeugsitzung mit `printf 'Y\n' | …` aufrufen, sonst bricht es mit
`Cancelled` ab, ohne etwas zu schreiben.

## Grenzen und Fallen (gemessen 13.09.2026)

1. **Projektgrenze ist die Git-Wurzel.** Ordner ohne eigenes `.git` unterhalb
   von `BrainFiles/` — `Agenten/Bus`, `Agenten/Handel`, `Werkstatt/Repos`
   selbst — lassen sich **nicht** einzeln kartieren: `init` und `root set .`
   binden die nächstgelegene Wurzel, hier `BrainFiles`. Zusätzlich würde dort die
   Whitelist-`.gitignore` (`*`, dann Einzelfreigaben) bis auf die freigegebenen
   Textdateien alles ausschließen. Deshalb: **nur echte Repos** kartieren.
   (Ein versehentlich an der Wurzel angelegter Atlas wurde am 13.09.2026 mit
   `reset-index --apply` wieder entfernt.)
2. **Verwaiste Git-Worktrees brechen den Scan.** Der Scan prüft die
   Repository-Grenze; zeigt `.git/worktrees/<name>/gitdir` ins Leere, endet er mit
   `repository boundary could not be validated` und **nichts** wird indexiert
   (getroffen: `Werkstatt/omnitrade`). Abhilfe: `git worktree prune` im Repo.
   Ein **gesperrter** (locked) Worktree stört nicht.
3. **Steuerzeichen in Pfaden** lassen die Graph-Projektion scheitern
   (`identity text contains control characters`, getroffen: `caveman`); der Atlas
   bleibt dann leer.
4. **Globale Schalter nur vor dem Unterbefehl** — `init --format json` ist ein
   Fehlschlag mit unbrauchbarer Meldung.
5. **Die Karte kann groß werden:** gemessen 18 MB (superpowers), 414 MB
   (basic-memory), 2,0 GB (codex). Beim `init` lässt sich die Volltextablage
   begrenzen: `--text-index-max-bytes <n>`.
6. **`.projectatlas` ist Laufzeitzustand** — nicht ins Git, nicht in die
   Sicherung (SQLite-Hauptdatei plus `-wal`/`-shm` ändern sich bei jedem Scan).
7. **Ein Shallow-Klon lässt sich nicht pushen.** Der Arbeitsklon hat deshalb
   volle Historie (`git fetch --unshallow`), wie bei der übrigen Flotte.

## Nachweis

```
"<exe>" --format json runtime-info | head            # Laufzeit und Fähigkeiten
hermes.exe mcp test projectatlas                     # Verbindung + 43 Werkzeuge
powershell -File Agenten\mcp-sync-check.ps1          # Manifest gegen beide Agenten
python -c "import json;print(len(json.load(open('Agenten/MCP-Manifest.json'))['servers']))"
```

## Stand 2026-09-13

Eingebaut: Fork, Arbeitsklon, Laufzeit (geprüft), MCP-Eintrag bei Hermes
(`✓ Connected, 43 Tools`), Manifest-Eintrag (`agent: hermes`),
`mcp-sync-check.ps1` ohne Fehler, Bot `projectatlas`, Karten für die
Arbeits-Repos.

Noch offen:

- **Claude Desktop** hat den Server nicht (Manifest `agent: hermes`) — der
  Eintrag ist eine Zeile Arbeit, sinnvoll erst mit einem eigenen Standard-Atlas
  für Claudes Arbeitsweise. **Claude Code** bekommt ihn projektweise über
  `.projectatlas/projectatlas.claude.mcp.json`.
- **Zwecke** (`purpose`) sind noch nicht kuratiert: ProjectAtlas führt die
  Ordnerzwecke als Vorschlagsliste (`projectatlas purpose queue`), erst gepflegte
  Zwecke machen die Rangliste scharf.
- Beim Einbau gepflegt: `Werkstatt/omnitrade` (verwaister Worktree entfernt).

Siehe auch: [[Verbindungen]] (Serverübersicht), [[Hermes]] (Profilpflege).
