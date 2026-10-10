---
name: projectatlas
description: "Use when Repos fuer Agenten kartieren (ProjectAtlas)."
category: brainfiles
---

# ProjectAtlas: Repos kartieren, damit Agenten gezielt lesen

ProjectAtlas (Rust, MIT) legt je Repository eine SQLite-Karte an und beantwortet
"welche Datei ist fuer X zustaendig?" in einem Aufruf. Laufzeit und Hintergrund:
`Wissen/Projektatlas.md` im Vault, Fork `mfaupel95/ProjectAtlas`, Klon
`Werkstatt/Repos/ProjectAtlas`.

## Wann

- ein Repo soll fuer Agenten erschlossen werden (Orientierung statt breitem Lesen)
- ein Bot/eine Sitzung "findet die Datei nicht" oder liest zu viel Kontext
- ProjectAtlas laeuft nicht, indexiert nicht oder ein Atlas ist leer

## Ablauf

1. **Laufzeit vorhanden?** `Agenten/Werkzeuge/projectatlas/bin/projectatlas.exe --format json runtime-info`
   muss `project: ProjectAtlas`, `version` und `capabilities: [..., mcp, ...]` melden.
   Fehlt sie: Release-Archiv `projectatlas-v<version>-x86_64-pc-windows-msvc.zip` von
   `styler-ai/ProjectAtlas` holen, **SHA-256 gegen `SHA256SUMS` des Release pruefen**,
   nach `Agenten/Werkzeuge/projectatlas/v<version>/` legen und dieselbe Datei nach
   `bin/` kopieren (stabiler Aufrufpfad). Den Codex-Plugin-Installer **nicht** nehmen:
   er schreibt zusaetzlich in die Codex-Marketplace-Registry und in fremde
   Projektkonfigurationen.
2. **Projektgrenze klaeren, bevor indexiert wird.** Kartierbar ist nur, was ein
   **eigenes `.git`** hat. `init` und `root set` binden sonst die naechstgelegene
   Git-Wurzel: aus `Agenten/Bus` heraus entsteht ein Atlas an `BrainFiles/`,
   und dessen Whitelist-`.gitignore` (`*`, dann Einzelfreigaben) schliesst fast
   alles aus. Also: nur echte Repos, und immer aus dem Repo heraus aufrufen.
3. **Indexieren:** `cd <repo> && "<exe>" init`. Erwartet wird im JSON `"ok": true`
   und `scan.status: verified`. Danach im Repo `.git/info/exclude` um
   `.projectatlas/` ergaenzen (nicht die `.gitignore` des Originals anfassen).
4. **Vollstaendig indexieren:** `Agenten/Werkzeuge/projectatlas/indexieren.sh`
   (idempotent, Logs je Repo in `Agenten/Werkzeuge/projectatlas/logs/`). Nach dem
   Lauf die `.err`-Dateien lesen - ein Fehlschlag je Repo ist erwartbar (siehe Fallen).
5. **An MCP anbinden (Hermes):**
   `printf 'Y\n' | hermes.exe mcp add projectatlas --command "<exe>" --args --require-version <v> --db "<repo>/.projectatlas/projectatlas.db" --config "<repo>/.projectatlas/config.toml" mcp`
   Die Rueckfrage "Enable all 43 tools?" braucht stdin; ohne `printf` endet der Aufruf
   mit `Cancelled` **ohne** zu schreiben. Danach denselben Eintrag ins
   `Agenten/MCP-Manifest.json` (Feld `agent: hermes`) - das Manifest ist die Wahrheit,
   der Pruefer vergleicht beide. Manifest vorher sichern (`.bak-JJJJJJJJ`, es ist
   gitignored), Einfuegung als gezielter Byte-Ersatz vor `\r\n  ],\r\n  "disabled": [`,
   niemals als Rewrite (CRLF und Fremdeintraege anderer Sitzungen).
6. **Belegen:** `hermes.exe mcp test projectatlas` ("✓ Connected", 43 Werkzeuge) und
   `powershell -File Agenten/mcp-sync-check.ps1` (Exit 0).

## Eine Sitzung, viele Repos

Ein Server bedient **jedes** indexierte Repo: `--db` bindet nur den Standard.
Andere Repos kommen per `project_path` (bzw. `atlas_set_project_path`), niemals
beides zugleich. Fuer einen Bot mit eigenem Arbeitsverzeichnis denselben Eintrag in
`profiles/<bot>/config.yaml` setzen, mit `--db` auf **sein** Repo.

## Fallen (gemessen)

- **Ein Projekt INNERHALB eines Repos ist nicht kartierbar.** Ein Unterordner ohne
  eigenes `.git` (Beispiel: `Agenten/Handel/nautilus-rust`) laesst sich auch mit
  ausdruecklichem `--db`/`--config` nicht binden: `ok: false`, und der Scan endet
  mit `verification_incomplete: invalid input: ProjectAtlas config '…/config.toml'
  resolves project root '…/nautilus-rust' outside selected project root '…/BrainFiles'`.
  Es entstehen trotzdem `config.toml` und `projectatlas.db` im Unterordner - beides
  danach wieder entfernen. Ausweg ist nur ein eigenes `.git` (Gitlink-Folgen beachten)
  oder gezieltes Lesen der wenigen Einstiegsdateien.
- **Der Projektstamm kommt aus dem NAECHSTEN `.projectatlas` aufwaerts.** Liegt unter
  der Wurzel ein Streu-Atlas aus einem alten Lauf, traegt er seinen eigenen Stamm und
  jeder Aufruf aus einem anderen Verzeichnis endet mit `project_mismatch: selected
  project root '…' does not match index root '…'`. Vor „ProjectAtlas ist kaputt"
  also `root show` im Zielverzeichnis pruefen - dort stehen `config_path` und
  `db_project_root` im Klartext.
- **Cargo-Nebenzielordner fehlen in der Standard-Ausschlussliste.** `exclude_dir_names`
  kennt `target`, aber nicht `target-live` (o.ae.): der Scan laeuft dann in
  `verification_incomplete` an `target-live/release/.cargo-build-lock`
  („anderer Prozess haelt einen Teil der Datei gesperrt", os error 33) - auch wenn
  gar kein Build mehr laeuft, denn die 0-Byte-Sperrdatei bleibt liegen.
  Fix: `projectatlas ignore add --kind dir-name target-live`.
- **Der Watcher loggt Erfolg NICHT.** Eine Logdatei, die seit Stunden unveraendert
  ist, heisst „nichts hat sich geaendert" - nicht „Prozess tot". Zwei Zeugen: der
  Prozess (`Get-CimInstance Win32_Process` mit `CommandLine -like '*watch*'`) und die
  mtime der `.projectatlas/projectatlas.db` nach einem `touch` an einer Quelldatei.
  Nach einer Config-Aenderung (Ignore/Zwecke) muss der Watcher neu starten -
  `Agenten/Werkzeuge/projectatlas/watch-start.ps1` sieht einen laufenden Prozess
  ueber die PID-Datei und tut dann nichts.
- **Globale Schalter stehen vor dem Unterbefehl.** `projectatlas init --format json`
  scheitert mit "unexpected argument"; richtig ist `projectatlas --format json init`.
- **Verwaiste Git-Worktrees brechen den Scan.** Meldung:
  `repository boundary could not be validated ... .git/worktrees/<name>/gitdir` —
  es wird **nichts** indexiert. Abhilfe `git worktree prune` im Repo. Ein
  **locked** Worktree stoert nicht.
- **Steuerzeichen in Pfaden** lassen die Graph-Projektion scheitern
  (`identity text contains control characters`); der Atlas bleibt leer.
- **Leerer Atlas trotz "init" heisst: `scan.status: failed` nachlesen.** Die
  Init-Ausgabe ist TOON; mit `--format json` in eine Datei je Repo schreiben und
  `scan.status`/`scan.error` herausziehen.
- **Karten werden gross** (18 MB bis 2 GB je Repo) und aendern sich bei jedem Scan:
  `.projectatlas/` gehoert weder ins Git noch in die Sicherung (in
  `Agenten/sichern*.ps1` in die `/XD`-Liste).
- **Riesige generierte Baeume kosten Scanzeit:** Ein Next.js-Repo lief 18 Minuten
  und schrieb 2,7 GB WAL, ohne fertig zu werden. Vor dem ersten `init` die
  Ausschlussliste erweitern (`projectatlas ignore add --kind dir-name .next`,
  ebenso `.turbo`); einen abgebrochenen Lauf mit `reset-index --apply` aufraeumen,
  sonst bleiben WAL-Reste liegen.
- **Shallow-Klon kann nicht pushen.** Fuer einen Arbeitsklon, aus dem committet
  wird, erst `git fetch --unshallow`.
- **Zwecke kuratiert niemand von allein** — Rezept im Abschnitt
  "Zwecke kuratieren" oben; ohne sie bleibt die Rangliste stumpf.

## Zwecke kuratieren (Rangliste schaerfen)

`purpose queue` listet Ordner ohne Zweck; zuerst die Top-Level-Bounded-Contexts
setzen (Crates, src, Hauptordner), nicht jede tiefe Datei. Batch-Rezept —
Separator `|` verwenden, **Heredocs expandieren keine Escape-Sequenzen**
(`\t` bleibt Backslash-t und der Eintrag schlaegt fehl):

```bash
while IFS='|' read -r p u; do "$PA" purpose set "$p" "$u" || echo "FEHLER: $p"; done <<EOF
omnitrade-core|Kern-Crate: Typen, Indikatoren, Ringpuffer
EOF
```

- Leere Ordner (z. B. `exchange/src/keystore` ohne Dateien) sind **nicht** im
  Index: `purpose set` verweigert zu Recht den Eintrag.
- Verifizieren: in `--format json folders` erscheinen die gesetzten Zwecke als
  `purpose_source: agent`, `purpose_agent_reviewed: true`; die `purpose queue`
  schrumpft um exakt die gesetzte Zahl.
- ASCII statt Umlaute haelt den Index schlank; ein deutscher Einzeiler mit
  Komma grenzt schon gut ab.

## Nachweis

- `runtime-info` nennt Version und `mcp`.
- `scan.status: verified` je Repo im Init-JSON.
- `hermes mcp test projectatlas` verbindet und zaehlt die Werkzeuge.
- `mcp-sync-check.ps1` endet mit Exit 0 (Warnungen zu fremden Eintraegen sind kein Fehler).

## Abgrenzung

- MCP-Manifest und Pruefer: `mcp-sync`, Hermes-Config: `hermes-config-ops`
- Fremd-Repos klonen und Bots je Repo: `repo-flotte`
- Platz und Umzuege: `laufwerk-platz-schaffen`
