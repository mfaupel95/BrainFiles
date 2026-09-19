# Design: Fremd-Agenten-Repos mit ProjectAtlas kartieren (Teilprojekt A)

- Datum: 2026-09-19
- Status: zur Freigabe
- Basis: Brainstorming 19.09.2026, genehmigt A1 → B1 → C1
- Abgrenzung: Teilprojekt A (Atlas + Bot-Anbindung). B (Atlas-Auskunft
  fuer Haus-Spuren) und C (Atlas-Tab im Kontrollzentrum) folgen als
  eigene Design-/Plan-/Code-Zyklen.

## Zweck

Die neun unter `Werkstatt/Repos/` liegenden Fremd-Agenten-Repos haben
keine ProjectAtlas-Karte: ein Agent (Bot oder Haus-Sitzung) findet die
richtige Datei dort nur durch breites Lesen. Ziel von A: **jedes dieser
Repos kartieren und jeden vorhandenen Repo-Bot an seine Karte haengen** —
ohne die gemessenen Fallen (18-Minuten-Scan, 2,7-GB-WAL, leere Karten)
zu wiederholen.

## Ist-Zustand (gemessen 19.09.2026)

- Laufzeit: `Agenten/Werkzeuge/projectatlas/bin/projectatlas.exe` v0.4.5,
  `runtime-info` meldet `capabilities: [cli, mcp, sqlite, toon, symbol-index,
  text-search, watch, token-telemetry]`, 43 `atlas_*`-MCP-Werkzeuge. ✓
- Kartiert: 20 von 30 Repos unter `Werkstatt/Repos/` (`.projectatlas/`
  vorhanden), groesste Karten `codex` 1,9 GB, `odysseus` 0,5 GB.
- **Nicht kartiert (9):** Agent-Reach, agent-trade-kit,
  awesome-systematic-trading, Harvard-Algorithmic-Trading-with-AI,
  moon-dev-ai-agents, Moon-Dev-Code, openmontage, santiment,
  Trading-View-MCP-for-AI-by-Moon-Dev — alle mit eigenem `.git`,
  also kartierbar (Grenze: Git-Wurzel).
- venv vorhanden (Scan-Risiko): Agent-Reach, moon-dev-ai-agents,
  openmontage, Trading-View-MCP-for-AI-by-Moon-Dev.
- Bot-Profile vorhanden (7): agent-reach, awesome-systematic-trading,
  harvard-trading, moon-dev-agents, openmontage, santiment, tradingview-mcp.
  **Kein Profil:** agent-trade-kit (nur Atlas, keine Verdrahtung).
- Werkzeug `bot-verdrahten.sh` existiert, idempotent, unsetzt
  PYTHONHOME/PYTHONPATH, init bei Bedarf, setzt MCP-Eintrag in das
  Bot-Profil (`--db` auf dessen Repo). ✓
- Werkzeug `indexieren.sh` laeuft ueber **alle** Repos mit `.git` und
  ergaenzt `.git/info/exclude` um `.projectatlas/` — aber **ohne**
  Ausschlusslisten-Logik und ohne Repo-Filter (wuerde die 20 Karten
  erneut scannen).

## Entscheidungen

1. **Nicht kartieren: `Moon-Dev-Code`** — enthaelt nur `README.md` und
   `strategy_pdfs/` (PDF-Sammlung, kein Code). Der Atlas indexiert
   Text-/Codedateien; eine Karte waere leer. Das Repo bleibt NUR DOKU in
   der repos-zentrale. `copilot-worktrees` ist keine Repo (kein `.git`),
   bleibt aussen.
2. **`indexieren.sh` bekommt einen Repo-Filter und eine Ausschluss-
   Vorphase** statt eines neuen Parallel-Skripts: Aufruf
   `indexieren.sh <name>...` kartiert nur die genannten Repos (ohne
   Argumente wie bisher alle). Vor jedem `init` ergaenzt das Skript
   idempotent die Ausschlussliste des Repos (`projectatlas ignore add
   --kind dir-name`) fuer `.venv`, `node_modules`, `__pycache__`, `.next`,
   `.turbo` — jeweils nur, wenn die Ordner existieren. Damit heilt die
   Hauptursache (fehlende Ausschlüsse) generisch, nicht nur fuer diese
   acht Repos. Zusaetzlich `--text-index-max-bytes` fuer grosse Baeume
   (siehe Massnahmen).
3. **Reihenfolge je Repo:** Vermessen (Dateizahl ueber `git ls-files`,
   nicht `du`) → Ausschlussliste → `init` (`--format json` nach
   `logs/<name>.json/.err`) → `scan.status` pruefen → `.err` lesen.
   Ein Fehlschlag je Repo ist erwartbar (bekannte Init-Fehler, siehe
   Risiken) und wird dokumentiert, nicht still geschluckt.
4. **Bot-Verdrahtung nur fuer die 7 Profile** mit passendem Repo;
   `agent-trade-kit` bekommt nur den Atlas (kein Profil, kein Eintrag).
5. **Zwecke kuratieren nur fuer Top-Level-Bounded-Contexts** der grossen
   Repos (moon-dev-ai-agents: `src/agents` u. a.; santiment,
   agent-trade-kit), nicht jede tiefe Datei. ASCII statt Umlaute.

## Umfang A

**In** (Abnahmekriterien):

1. Acht Repos kartiert, je mit `scan.status: verified` im Init-JSON:
   Agent-Reach, agent-trade-kit, awesome-systematic-trading,
   Harvard-Algorithmic-Trading-with-AI, moon-dev-ai-agents, openmontage,
   santiment, Trading-View-MCP-for-AI-by-Moon-Dev.
2. `.projectatlas/` in `.git/info/exclude` jedes Repos (durch
   `indexieren.sh`), `.gitignore` des Originals unangetastet.
3. Sieben Bots verdrahtet: `hermes -p <bot> mcp test projectatlas`
   meldet „Connected“ — agent-reach, awesome-systematic-trading,
   harvard-trading, moon-dev-agents, openmontage, santiment,
   tradingview-mcp.
4. Haupt-MCP unveraendert funktionsfaehig: `mcp-sync-check.ps1` Exit 0,
   `hermes mcp test projectatlas` weiterhin „Connected“.
5. Zwecke gesetzt fuer moon-dev-ai-agents, santiment, agent-trade-kit
   (Top-Level; `purpose queue` schrumpft, `purpose_source: agent` in
   `--format json folders`).
6. `Wissen/Projektatlas.md` Stand-Abschnitt nachgezogen: Anzahl der
   Karten, nicht-kartierte Repos mit Grund, neue Fallen.

**Nicht in A** (bewusst):

- B (Atlas-Auskunft fuer Haus-Spuren) und C (Atlas-Tab in der
  repos-zentrale) — eigene Zyklen.
- Verdrahtung neuer Bot-Profile fuer agent-trade-kit (erst wenn ein
  Profil gewuenscht ist).
- Watcher fuer weitere Repos (nur Standard-Atlas omnitrade bleibt
  beobachtet; ein Watcher je Repo = Dauerprozess, hier nicht noetig).
- Zweck-Kuration tiefer Ordner.

## Massnahmen gegen gemessene Fallen

| Falle | Massnahme |
|---|---|
| 18-Min-Scan / 2,7-GB-WAL (OmniRoute: node_modules) | Ausschlussliste VOR `init`; moon-dev-ai-agents zusaetzlich `--text-index-max-bytes` (z. B. 256 MB). Abbruch → `reset-index --apply`, WAL-Reste aufraeumen. |
| Leere Karte trotz init | Init-JSON lesen, `scan.status`/`scan.error` pruefen (TOON ist ohne JSON unlesbar). |
| Steuerzeichen in Pfaden (caveman, gbrain) | `.err` lesen; betroffenes Repo gilt als dokumentiert nicht-kartierbar, kein stiller Durchlauf. |
| `document unresolved ... graph row limit` (deepseek-harness) | dito. |
| Shallow-Klon push-unfaehig | betrifft A nicht (nur init/lesen); kein `--unshallow` noetig. |
| Karten gross (codex 1,9 GB) | bei neuen Repos Groesse nach `init` pruefen; bei >1 GB `--text-index-max-bytes` nachziehen und rescan. |
| Zwecke kuratieren (Rangliste sonst stumpf) | Rezept aus Skill: Separator `|`, kein Heredoc mit Escape-Sequenzen; verifizieren ueber `folders` + `purpose queue`. |

## Nachweis (am Ende von A)

```
bash Agenten/Werkzeuge/projectatlas/indexieren.sh <8 reponamen>   # rc 0, je verified
for b in agent-reach awesome-systematic-trading harvard-trading moon-dev-agents openmontage santiment tradingview-mcp; do
  hermes -p $b mcp test projectatlas
done
powershell -File Agenten/mcp-sync-check.ps1                       # Exit 0
<exe> --format json folders  (in den 3 kuratierten Repos)          # purpose_source: agent
git status --porcelain                                            # nur eigene Pfade
```

## Risiken

- **moon-dev-ai-agents** (46 Agenten, venv mit ta-lib/torch/whisper): der
  kritischste Scan. Falls `init` trotz Ausschlussliste nicht terminiert:
  Text-Index staerker begrenzen, WAL aufraeumen, in den Stand-Abschnitt
  von Projektatlas.md als dokumentierte Grenze eintragen.
- **awesome-systematic-trading** ist eine grosse Skill-Sammlung; die Karte
  kann >1 GB werden — dann `--text-index-max-bytes` setzen.
- **Harvard-Algorithmic-Trading** enthaelt Jupyter-Notebooks (grosse
  JSON-Quellen) — Text-Index begrenzen, wenn noetig.
- Fremde Aenderungen im Arbeitsbaum: vor dem Commit nur eigene Pfade
  stagen, nie `git add -A` (Regel Mehrere-Sitzungen, Schutzregeln.md).

## Betroffene Dateien (Aenderung)

- `Agenten/Werkzeuge/projectatlas/indexieren.sh` — Repo-Filter,
  Ausschluss-Vorphase, Groessen-/Statuszeile.
- `.gitignore` — Freigabe `Agenten/Werkzeuge/projectatlas/docs/` +
  `docs/design/*.md` (fuer diese und die Folge-Spezifikationen B/C).
- `MaxHirn/Wissen/Projektatlas.md` — Stand-Abschnitt (Ergaenzung im
  Rahmen des Bestehenden).
- Neu: diese Datei unter `docs/design/2026-09-19-fremd-agenten-atlas-design.md`.