---
id: 20261019-fremd-inventur-recherche
title: 'FREMD-Inventur: Recherche-Rolle (4 Repos)'
tags: [fremdrepos, inventur, phase-0, markt-recherche]
created: 2026-10-19
updated: 2026-10-19
area_note: Bereich wissen (MaxHirn/Wissen/) gesperrt für Schreibzugriff über Hermes-Tool; Fallback Werkstatt/
---

# FREMD-Inventur: Recherche-Rolle (4 Repos)

Inventur-Phase 0 laut Plan `Werkstatt/plan-fremdrepos-ausbau-2026-10-09.md`, Abschnitt *Phase 0 – Ergebnis Handels-Rolle*. Gelesen, nicht geändert. Ergebnis als Markdown-Tabelle.

Vier Recherche-Repos aus der Kandidatenliste (Zeile 21 im Plan):

| Repo | Stack | Lizenz | Börsen (Treffer) | Testmodus | UI | Eignung für Anschluss |
|---|---|---|---|---|---|---|
| **Scrapling** | Python 3.10+, pyproject.toml (setuptools), v0.4.15, PyPI-Paket `scrapling` | BSD 3-Clause | **Keine.** Web-Scraping-Bibliothek; kein Trading, keine Börsen-API. Fetcht Webseiten, bypass Cloudflare, kein Markt-Data-Zugang. | pytest (pytest.ini), eigenständige Benchmarks (`benchmarks.py`), kein spezifischer Trading-/Paper-Modus | CLI: `scrapling shell`, `scrapling extract`; **MCP-Server** (`scrapling-mcp` Entry im pyproject.toml); keine grafische UI | **Mittel:** Als Web-Scraping-Recherche-Tool relevant für Topic `markt-recherche`. MCP-Server einbindbar in Hermes (Abgleich mit `mcp-sync-check.ps1`). Kein Handel, aber Datenbeschaffung aus Web-Quellen. Agent-Skill vorhanden (`agent-skill/Scrapling-Skill.zip`). |
| **jevgrep** | Bun/TypeScript, package.json (Workspaces + turbo), Bun@1.3.14, Node.js 22+ | MIT | **Keine.** Semantische Code-Suche über Jev (Vercel AI Gateway / TypeSafe / OpenRouter / OpenCode Zen). Kein Trading, keine Börsen. | `bun run test` (Docker-basiert, read-only Container), `bun run test:installed`, `bun run verify`; Test-Suite in `scripts/` | Keine. CLI `jg`; keine grafische UI | **Mittel:** Als Code-Recherche-Tool für Coding-Agenten relevant; kein Handel, keine Börsen. Kein MCP-Server. Für Hermes-Skill als Codebasis-Navigation denkbar, aber kein markt-recherche-Topic im Handel-Sinne. |
| **awesome-systematic-trading** | Statische Awesome-Liste (README.md, 93 KB EN + 113 KB ZH + 82 KB JA), **keine eigene Software**, keine Abhängigkeiten, keine Build-System | **Keine Lizenzdatei.** Inhaltlich eine Ressourcen-Sammlung (Lizenzen der verlinkten Projekte variieren; keine einheitliche Lizenz) | **Keine als Software.** Listet Broker-APIs, Datenquellen, Backtesting-Bibliotheken im Inhaltsverzeichnis auf (nur Links/Inhaltsübersicht, kein eigener Code) | Kein Test, keine Software zum Testen | Keine. Nur README | **Niedrig:** Reine Referenz/Links-Sammlung; kein ausführbarer Anschluss. Als Wissenliste/Themenübersicht nutzbar, aber kein Tool, kein Code, kein Anschluss an Hermes oder Handel. |
| **Agent-Reach** | Python 3.10+, pyproject.toml (hatchling), v1.5.0, CLI-`agent-reach` | MIT | **Keine Börsen.** Plattformen: Web (Jina Reader), YouTube (yt-dlp), RSS (feedparser), GitHub (gh CLI), Twitter/X, B站 (bili-cli), Reddit, Facebook, Instagram, LinkedIn, V2EX, 雪球, 小宇宙播客; Exa semantische Suche. Kein Handel, keine Börsen-API. | `test.sh` (isoliertes venv, pytest-Repo-Tests, `agent-reach doctor --json`, `agent-reach install --dry-run`); `pytest` in `tests/` | Keine. CLI `agent-reach`; `agent-reach doctor` als Diagnose; **MCP-Server** (optional über `mcp[cli]`) | **Hoch:** Als Recherche-Tool für Web-Plattformen und Datenquellen sehr relevant für Topic `markt-recherche`. MCP-Server einbindbar. Kein Handel, aber breite Datenbeschaffung aus 10+ Plattformen. Installation über Agenten-Befehl (OpenClaw/Claude Code/Cursor). |

## Befunde

- **Börsen-Anbindung:** Keines der vier Recherche-Repos hat eine direkte Börsen- oder Trading-API-Anbindung. Sie liefern Web-/Code-/Plattform-Daten, keine Marktdaten oder Ordermöglichkeiten.
- **MCP:** Scrapling und Agent-Reach bringen jeweils einen MCP-Server mit; jevgrep und awesome-systematic-trading nicht.
- **Lizenz:** Scrapling (BSD 3-Clause), jevgrep (MIT), Agent-Reach (MIT) klar lizenziert. awesome-systematic-trading hat keine Lizenzdatei — die verlinkten Ressourcen haben eigene Lizenzen, die bei Weiterverwendung einzeln zu prüfen sind.
- **Testmodus:** Nur Agent-Reach hat einen klar dokumentierten Integrations-Test (`test.sh`, lesend, mit dry-run). Scrapling nutzt pytest; jevgrep nutzt Docker-gebundene Bun-Tests. awesome-systematic-trading ist keine Software.
- **UI:** Keines der vier hat eine grafische UI. Alle sind CLI- oder Bibliotheks-Tools. Für UI-Start wäre OpenTerminalUI oder eine Hermes-Oberfläche nötig.
- **Anschluss-Pfad:** Höchste Eignung für den Topic `markt-recherche` hat **Agent-Reach** (breiteste Plattform-Anbindung, MCP, MIT, testbar). **Scrapling** als zweiter Kandidat (Web-Scraping, MCP, BSD). jevgrep ist eher ein Code-Recherche-Tool für Coding-Agenten. awesome-systematic-trading ist eine Lesereferenz ohne Ausführung.

## Offene Fragen

- awesome-systematic-trading: Bei weiterer Nutzung als Wissenliste — welche Lizenzen haben die verlinkten Projekte einzeln? (Der Plan sagt: Lizenz-Vorbehalt prüfen vor jeder Weiterverwendung.)
- jevgrep: Benötigt einen API-Key für Jev/Vercel-AI-Gateway — im Hermes-Betrieb wer übernimmt die Key-Provision?
- Agent-Reach: MCP-Server optional über `mcp[cli]` — ist er im vorliegenden Klon installiert und getestet?
- Scrapling: Der MCP-Server (`scrapling-mcp`) ist als Entry im pyproject.toml definiert — ist er lokal startbar und kompatibel mit dem bestehenden MCP-Abgleich (`mcp-sync-check.ps1`)?

---

*Befund: Bereich `wissen` (Besitzer `wissen`, Pfad `MaxHirn/Wissen/`) — Schreibzugriff über Hermes-Tool gesperrt (HERMES_WRITE_SAFE_ROOT). Notiz daher nach Werkstatt/ geschrieben, wie in Plan als Fallback erlaubt. Lesender Inventur-Gang, keine Änderung an bestehenden Dateien.*
