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

- **Steuerzeichen stecken im DATEIINHALT, nicht nur im Pfad.** `scan.status: failed` mit
  `invalid graph identity text: identity text contains control characters` entsteht, wenn ein
  NUL-, ESC- oder Backspace-Byte in einer Quelldatei steht: die Projektion baut die Identitaet
  aus Signatur/Ueberschrift der Zeile und nimmt das Byte mit. Die Dateinamen sind dabei oft
  sauber - erst den Inhalt pruefen, nicht die Pfade:
  `python Agenten/Werkzeuge/projectatlas/steuerzeichen-finden.py <repo>` (nennt Datei, Byte
  und Zeile). Dann die Fundstelle ausschliessen; `ignore add` kennt nur `--kind dir-name` und
  `--kind path-prefix`, eine Datei geht als Praefix. Beleg 18.09.2026: caveman 5 Dateien,
  gbrain 7 - danach `scan.status: verified` (DB 245 MB bzw. 557 MB).
- **Ein `init` auf einem grossen Repo kann aus dem Ruder laufen.** OmniRoute: 12 Minuten,
  3,2 GB Arbeitsspeicher, WAL stand still, kein Ergebnis (am 13.09. schon einmal 2,6 GB WAL
  ohne Ende). Nur per PID beenden, nie per Prozessname. Aufraeumen: `reset-index --apply`
  (entfernt DB, WAL, SHM), danach die zurueckbleibende `repository-graph-stage.lock` von Hand
  loeschen - sie blockt den naechsten Lauf. Vor dem ersten `init` die Ausschlussliste
  erweitern; bei OmniRoute fehlte `.build` (6,5 GB) neben den schon eingetragenen `.next`
  und `.turbo`.
- **Ein MCP-Aufruf bricht nach 300 s ab, das Kind laeuft weiter.** Lange Inits abgesetzt
  starten (`Start-Process <exe> -ArgumentList '--format','json','init' -WorkingDirectory <repo>
  -RedirectStandardOutput <log> -NoNewWindow`) und den Stand im LOG lesen, nie im
  Rueckgabewert - ein abgebrochener Aufruf ist kein abgebrochener Lauf.
- **Nicht jede Grenze ist ein Steuerzeichen.** deepseek-harness lief nach dem Ausschluss der
  4 Fundstellen in `invalid graph limits: document unresolved reason batch exceeds the graph
  row ceiling`; diese Obergrenze ist eine Kompilier-Konstante (`GraphLimits::MAX_ROWS`,
  `projectatlas-cli/src/runtime/graph_projection.rs`), es gibt keinen Schalter dafuer - nur
  weiter ausschliessen oder den Fork patchen. `init --help` kennt nur `--no-scan`,
  `--force-rescan` und `--text-index-max-bytes`.

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
