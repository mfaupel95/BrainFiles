---
id: 20260921-hermes
title: 'Betrieb — Hermes'
tags: [betrieb, hermes]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Betrieb/Wachen-und-Aufgaben]]', '[[Werkzeuge/Fundus-Skills-Bots]]', '[[Wissen/Hermes]]']
summary: 'Installation, Pfade, Profile, die wiederkehrenden config.yaml-Fallen, Gateway, Kompression und Delegation.'
---

# Hermes

## Orte

| Was | Wo |
|---|---|
| Programmcode (aktiv) | `Agenten/Hermes/hermes-agent` |
| Projekt-Config (**aktiv**) | `Agenten/Hermes/config.yaml` — `hermes config path` zeigt cwd-unabhaengig hierher |
| AppData-Config | `C:\Users\faupe\AppData\Local\hermes\config.yaml` — existiert, ist NICHT mehr aktiv |
| `hermes.exe` | `Agenten/Hermes/bin/hermes.exe` (vor Aufruf `PYTHONHOME`/`PYTHONPATH` entfernen) |
| Profile | `Agenten/Hermes/profiles/<name>/` |
| Bibliothek | `Agenten/Hermes/skills/` (Archiv: `skills/.archive/` — wird nicht geladen) |
| Cron | `hermes`-Scheduler (nicht die Windows-Aufgabenplanung) |

`C:\Hermes` ist stillgelegt (Altanlage, `C:\Hermes.alt-20260916`). Wenn dort noch etwas
Prozesse startet: `Hermes_Gateway.vbs` / `Hermes_Dashboard.vbs` pruefen — die zeigten
Anfang September noch auf die Altanlage.

## Die wiederkehrenden `config.yaml`-Fallen

1. **`hermes config set` schneidet den Kommentar-Schluss ab** (37 Zeilen Security-/Fallback-Doku
   waren weg) **und schreibt LF in eine CRLF-Datei** (2477 statt 2 geaenderte Zeilen).
   → Vorher kopieren, danach byte-genau zurueckholen, `git diff --numstat` pruefen.
2. **Beide Apps ueberschreiben ihre Config aus eigenem Speicher** — am 10.09.2026 verschwand
   so `mcp-memory` aus beiden Configs. Nach `hermes mcp add/remove` gegentesten.
3. **MCP-Wahrheit** ist `Agenten/MCP-Manifest.json`; Abgleich ueber
   `Agenten/mcp-sync-check.ps1` (steht in `systempruefung.ps1`).
4. **`${env:NAME}`** loest Hermes nur aus der **Prozessumgebung** auf, nicht aus `.env`.
   Provider-Zugangsdaten kommen dagegen aus Credential-Pool (`auth.json`) und `.env` —
   dafuer ist KEIN Gateway-Neustart noetig, fuer `${env:…}`-Aenderungen schon.
5. **Profile sind Inseln:** sie lesen NUR ihr eigenes `auth.json`; ein Root-`auth.json`
   wird nie geerbt. Loesung ist ein **Symlink** `profiles/<bot>/auth.json` → `Agenten/Hermes/auth.json`
   (Hermes unterstuetzt das ausdruecklich: „ein Symlink auf den Root-Store ist kein Klon").
   Werkzeug: `Agenten/Hermes/scripts/auth-verknuepfen.ps1` (braucht Adminrechte).
6. **`hermes profile create <name>` ohne `--clone`** erzeugt nur eine 45-Zeilen-Config:
   kein `providers`-, kein `terminal`-Block, `profile.yaml` fehlt ganz. Nacharbeiten:
   `providers.omniroute` kopieren, `model.provider`/`model.default` setzen, `terminal.cwd`,
   Router-Schluesselnamen in die eigene `.env`, Beschreibung per `hermes profile describe`.

## Gateway

- Der A2A-Gateway ist `python.exe -m hermes_cli.main gateway run` (Launcher-venv → Kind
  `.hermes-runtime-python`), bindet **Port 9900**. `python -m tui_gateway.entry` ist das
  Desktop-JSON-RPC-Backend, lauscht NICHT auf 9900 und ist NICHT der Gateway.
- **Falle (19.09.2026), zweimal schiefgegangen:** Das Waechter-Muster `hermes_cli.main gateway`
  war zu eng (startete alle ~16 min neu, 90 s Ausfall), das „breitere" `tui_gateway` zu
  breit (hielt Desktop-Backends fuer den Gateway, ~12 h echter Ausfall blieb UNERKANNT).
  **Richtig:** Port 9900 ist die erste Wahrheit; nur `hermes_cli.main gateway` zaehlt als
  Prozess; 120 s Boot-Gnadenfrist gegen Churn.
- `Test-NetConnection 127.0.0.1 -Port 9900` als Schnellprobe.

## Kompression

`compression.threshold` steht auf **0.19**, weil das Kompressionsmodell
(`auto/coding:free`) nur 200k Kontext traegt und die Schwelle darauf deckelt — das
Hauptmodell traegt 786k. Mit einem groesseren Kompressionsmodell darf die Schwelle wieder hoch.

## Delegation (Subagenten)

- Haus-Delegation: `provider=nous`, `model=deepseek/deepseek-v4-flash-0731`;
  `claude-opus-5` bleibt erster Fallback.
- **Kritisch:** Subagenten mit `provider=omniroute` haengen am lokalen Router
  (Port 20128). Ohne Router scheitern ALLE `delegate_task`.
- `max_concurrent_children: 3`.
- **`delegate_task`-JSON-Falle:** `context`/`goal` als EINZEILIGE Strings formulieren;
  Literal-Zeilenumbrueche und lange verschachtelte `output_schema` kippen das Parsing
  („Expecting ',' delimiter"). Absolute Pfade mitgeben — der Subagent sucht sonst relativ
  zu seinem eigenen Arbeitsordner.
- Subagenten-Selbstberichte sind Selbstauskuenfte, kein Beweis: externe Wirkungen
  (Upload, Remote-Schreibvorgang) immer selbst nachpruefen.