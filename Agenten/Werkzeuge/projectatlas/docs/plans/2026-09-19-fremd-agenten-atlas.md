# Fremd-Agenten-Repos kartieren (Teilprojekt A) — Implementierungsplan

**Ziel:** Acht Fremd-Agenten-Repos unter `Werkstatt/Repos/` mit einer
ProjectAtlas-Karte ausstatten und sieben Repo-Bots an ihre Karte haengen.
**Architektur:** `indexieren.sh` bekommt einen Repo-Filter und eine
Ausschluss-Vorphase (`.next`/`.turbo` bedingt; `.venv`/`node_modules`/
`__pycache__`/`build`/`dist`/`target` sind bereits Standard-Ausschluss).
Dann je Repo `init --no-scan` → `ignore add` → `init` (Scan). Bots ueber
das vorhandene `bot-verdrahten.sh`.
**Tech-Stack:** bash (git-bash), `projectatlas.exe` v0.4.5, `hermes.exe`.

**Projektweite Anforderungen:**
- Globale Schalter stehen VOR dem Unterbefehl: `projectatlas --format json init`, nicht `init --format json`.
- `ignore add` schreibt nur in `.projectatlas/config.toml`, nie in die `.gitignore` des Originals (gemessen 19.09.2026).
- Standard-Ausschlussliste (v0.4.5): `.git, .projectatlas, .venv, __pycache__, node_modules, dist, build, target` — nur `.next`/`.turbo` fehlen.
- `init --no-scan` legt `.projectatlas/config.toml` an, ohne zu scannen; erst danach funktioniert `ignore add` (gemessen 19.09.2026).
- `.projectatlas/` gehoert in `.git/info/exclude` (macht `indexieren.sh`), nicht in die `.gitignore` des Originals.
- Vor jedem Commit nur eigene Pfade stagen, nie `git add -A` (Schutzregeln, Mehrere-Sitzungen).
- Werkstatt/Repos ist eine Junction nach O: — Pfade ueber `Werkstatt/Repos/<name>` ansprechen.

**Ziel-Repos (8):** Agent-Reach, agent-trade-kit, awesome-systematic-trading,
Harvard-Algorithmic-Trading-with-AI, moon-dev-ai-agents, openmontage,
santiment, Trading-View-MCP-for-AI-by-Moon-Dev.
**Ziel-Bots (7):** agent-reach, awesome-systematic-trading, harvard-trading,
moon-dev-agents, openmontage, santiment, tradingview-mcp.
**Nicht kartieren:** Moon-Dev-Code (nur PDFs), copilot-worktrees (kein .git).

---

### Aufgabe 1: `indexieren.sh` um Repo-Filter und Ausschluss-Vorphase erweitern

**Dateien:**
- Aendern: `Agenten/Werkzeuge/projectatlas/indexieren.sh`

**Interfaces:**
- Produziert: `indexieren.sh [name...]` — mit Argumenten nur die genannten
  Repos (Name = Ordnername unter `Werkstatt/Repos/`), ohne Argumente alle
  (bisheriges Verhalten). Vor jedem `init` ergaenzt das Skript die
  Ausschlussliste um `.next`/`.turbo`, falls diese Ordner im Repo existieren.

- [ ] **Schritt 1: Repo-Filter einbauen.** Die Schleife `for d in "$ROOT"/Werkstatt/Repos/*/` durch eine gefilterte Liste ersetzen. Wenn `$# -gt 0`, nur die genannten Namen aufnehmen (Pfad = `$ROOT/Werkstatt/Repos/$name`, nur wenn `.git` existiert); sonst wie bisher alle. Die zusaetzlichen Repos (Werkstatt/omnitrade usw., nautilus, hermes-agent) bleiben nur im Alles-Modus aktiv.
- [ ] **Schritt 2: Ausschluss-Vorphase.** Vor dem `init`-Aufruf je Repo:
  ```bash
  # config.toml muss existieren, sonst schlaegt ignore add fehl (gemessen 19.09.)
  ( cd "$r" && "$PA" --format json init --no-scan >/dev/null 2>&1 )
  for ign in .next .turbo; do
    [ -d "$r/$ign" ] && ( cd "$r" && "$PA" ignore add --kind dir-name "$ign" >/dev/null 2>&1 )
  done
  ```
  Danach der bestehende `init`-Aufruf (Scan). `.venv`/`node_modules`/
  `__pycache__`/`build`/`dist`/`target` sind Standard-Ausschluss — nicht
  ergaenzen.
- [ ] **Schritt 3: Ausfuehren und pruefen.** `bash indexieren.sh` (ohne Argumente) muss weiterhin alle Repos durchlaufen und rc 0 melden; die 20 bereits kartierten Repos duerfen nicht neu scannen (idempotent). `bash indexieren.sh moon-dev-ai-agents` muss nur dieses eine Repo ansprechen.
- [ ] **Schritt 4: Committen.** `git add Agenten/Werkzeuge/projectatlas/indexieren.sh` + Commit `feat(projectatlas): indexieren.sh mit Repo-Filter und .next/.turbo-Ausschluss`.

---

### Aufgabe 2: Die acht Repos kartieren

**Dateien:**
- Neu (Laufzeit, nicht versioniert): je Repo `.projectatlas/` (DB, config.toml)
- Neu (Logs, nicht versioniert): `Agenten/Werkzeuge/projectatlas/logs/<name>.json` + `.err`

**Interfaces:**
- Konsumiert: `indexieren.sh` aus Aufgabe 1.
- Produziert: je Repo `scan.status: verified` im Init-JSON; `.projectatlas/` in `.git/info/exclude`.

- [ ] **Schritt 1: Lauf.** `bash Agenten/Werkzeuge/projectatlas/indexieren.sh Agent-Reach agent-trade-kit awesome-systematic-trading Harvard-Algorithmic-Trading-with-AI moon-dev-ai-agents openmontage santiment Trading-View-MCP-for-AI-by-Moon-Dev`
- [ ] **Schritt 2: Status pruefen.** Fuer jedes der 8 Repos das Init-JSON lesen und `scan.status` extrahieren:
  ```bash
  for n in Agent-Reach agent-trade-kit awesome-systematic-trading Harvard-Algorithmic-Trading-with-AI moon-dev-ai-agents openmontage santiment Trading-View-MCP-for-AI-by-Moon-Dev; do
    python -c "import json,sys; d=json.load(open('Agenten/Werkzeuge/projectatlas/logs/$n.json')); print('$n', d.get('scan',{}).get('status'))"
  done
  ```
  Erwartet: `verified` je Repo. Abweichungen (Steuerzeichen, graph row limit) in die `.err`-Datei lesen und als dokumentierte Grenze in `Wissen/Projektatlas.md` eintragen — nicht still schlucken.
- [ ] **Schritt 3: Groesse und exclude pruefen.** Je Repo DB-Groesse (`stat -c %s <repo>/.projectatlas/projectatlas.db`) und `.git/info/exclude` enthaelt `.projectatlas/`. Bei >1 GB: `--text-index-max-bytes` nachziehen und rescan.
- [ ] **Schritt 4: Kein Commit** (Laufzeitstaende sind nicht versioniert). Nur die Logs liegen auf der Platte.

---

### Aufgabe 3: Sieben Bots an ihre Karte haengen

**Dateien:**
- Aendern (durch `bot-verdrahten.sh`): `Agenten/Hermes/profiles/<bot>/config.yaml` (MCP-Eintrag projectatlas)

**Interfaces:**
- Konsumiert: Karten aus Aufgabe 2.
- Produziert: je Bot `hermes -p <bot> mcp test projectatlas` → „Connected“.

- [ ] **Schritt 1: Verdrahten.** Fuer jeden der 7 Bots:
  ```bash
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh agent-reach
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh awesome-systematic-trading
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh harvard-trading
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh moon-dev-agents
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh openmontage
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh santiment
  bash Agenten/Werkzeuge/projectatlas/bot-verdrahten.sh tradingview-mcp
  ```
  Das Skript setzt PYTHONHOME/PYTHONPATH zurueck, init bei Bedarf, setzt den MCP-Eintrag mit `--db` auf das jeweilige Repo und testet die Verbindung.
- [ ] **Schritt 2: Verbindung pruefen.** Je Bot `hermes -p <bot> mcp test projectatlas` muss „Connected“ melden. `agent-trade-kit` hat kein Profil — nur Atlas, keine Verdrahtung.
- [ ] **Schritt 3: Haupt-MCP unveraendert.** `hermes mcp test projectatlas` (default) weiterhin „Connected“ und `powershell -File Agenten/mcp-sync-check.ps1` Exit 0.
- [ ] **Schritt 4: Kein Commit** (Profil-Configs sind in `Agenten/Hermes/` freigelegt, aber die Aenderung macht das Skript; nur eigene Pfade stagen, falls doch committet wird).

---

### Aufgabe 4: Zwecke fuer die grossen Repos kuratieren

**Dateien:**
- Aendern (Laufzeit): `.projectatlas/config.toml` der drei Repos (via `purpose set`)

**Interfaces:**
- Konsumiert: Karten aus Aufgabe 2.
- Produziert: `purpose_source: agent` in `--format json folders`; `purpose queue` schrumpft.

- [ ] **Schritt 1: Queue lesen.** Je Repo `projectatlas --format json purpose queue` (aus dem Repo-Ordner) — nur Top-Level-Bounded-Contexts ansehen, nicht jede tiefe Datei.
- [ ] **Schritt 2: Zwecke setzen.** Fuer moon-dev-ai-agents (z. B. `src/agents` = „Agenten-Definitionen“, `src/nice_funcs_hl.py`-Ordner = „Datenfunktionen“), santiment, agent-trade-kit. Separator `|`, kein Heredoc mit Escape-Sequenzen:
  ```bash
  while IFS='|' read -r p u; do "$PA" purpose set "$p" "$u" || echo "FEHLER: $p"; done <<EOF
  src/agents|Agenten-Definitionen (46 Stueck)
  EOF
  ```
- [ ] **Schritt 3: Verifizieren.** `--format json folders` zeigt `purpose_source: agent`; `purpose queue` schrumpft um die gesetzte Zahl. ASCII statt Umlaute.
- [ ] **Schritt 4: Kein Commit** (Laufzeitstand).

---

### Aufgabe 5: Doku nachziehen und Gesamt-Nachweis

**Dateien:**
- Aendern: `MaxHirn/Wissen/Projektatlas.md` (Stand-Abschnitt)
- Neu: diese Datei unter `docs/plans/2026-09-19-fremd-agenten-atlas.md`

**Interfaces:**
- Konsumiert: Ergebnisse aus Aufgaben 2–4.

- [ ] **Schritt 1: Projektatlas.md Stand-Abschnitt ergaenzen.** Anzahl der Karten (20 → 28), die 8 neuen Repos, nicht-kartierte mit Grund (Moon-Dev-Code: nur PDFs; copilot-worktrees: kein .git), neue Fallen (ignore add braucht config.toml → init --no-scan zuerst; Standard-Ausschlussliste). `updated` im Frontmatter hochsetzen. Ergaenzung im Rahmen des Bestehenden — kein Widerspruch.
- [ ] **Schritt 2: Gesamt-Nachweis.**
  ```bash
  bash Agenten/Werkzeuge/projectatlas/indexieren.sh <8 reponamen>   # rc 0, je verified
  for b in agent-reach awesome-systematic-trading harvard-trading moon-dev-agents openmontage santiment tradingview-mcp; do hermes -p $b mcp test projectatlas; done
  powershell -File Agenten/mcp-sync-check.ps1                       # Exit 0
  ```
- [ ] **Schritt 3: Committen.** `git add MaxHirn/Wissen/Projektatlas.md Agenten/Werkzeuge/projectatlas/docs/plans/2026-09-19-fremd-agenten-atlas.md` + Commit `docs(projectatlas): Fremd-Agenten-Repos kartiert, Stand nachgezogen`.
