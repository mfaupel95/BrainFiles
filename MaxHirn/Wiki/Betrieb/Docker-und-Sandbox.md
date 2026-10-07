---
id: 20260921-docker-und-sandbox
title: 'Betrieb — Docker und Sandbox'
tags: [betrieb, docker]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Lektionen/Windows-Umgebung]]', '[[Betrieb/Hermes]]']
summary: 'Der Docker-Terminal-Backend als Sandbox, seine Grenzen, und windows-mcp als Rueckfallweg fuer Host-Arbeit.'
---

# Docker und Sandbox

## Aufbau

- `terminal`, `execute_code`, `read_file`, `search_files`, `patch` laufen in einem
  **Docker-Container** auf dem Host (Container z. B. `hermes-098f5c80`).
- **Ist Docker Desktop down, scheitern ALLE** mit „Docker daemon is not responding",
  „Terminal environment unavailable" oder „could not stat".
- Nach einem Docker-Neustart ist das Terminal wieder die Linux-Sandbox (`pwd=/root`,
  kein `/c`-Mount) — Host-Pfade sind dann nicht erreichbar.
- Der hauseigene CLI-Backend (`terminal.backend: local`) laeuft unveraendert lokal.

## Rueckfallweg

Ist der Dockerweg blockiert, **Host-Arbeit ueber windows-mcp PowerShell** fahren
(MCP-Server laeuft am Host, unabhaengig vom Sandbox-Container). Ebenso fuer:

- Massenlaeufe (Repos vorspulen, Dateien zaehlen) — im Sandbox-Terminal brachen sie bei
  Speicherdruck mit `WinError 1455` ab.
- Alles, was echte Windows-Dienste, Aufgabenplanung, Registry oder Laufwerke betrifft.

## Weitergeleitete Variablen

`terminal.docker_forward_env` in `Agenten/Hermes/config.yaml` listet 43 Variablen (alle
Schluesselnamen der Hermes-`.env` plus `OLLAMA_MODELS`, `HANDEL_RISIKO`, `HERMES_HOME`).
Geheimnisse stehen NICHT in der Config — der Sandbox-Container loest sie aus der Shell-Env
bzw. der `.env` auf.

**Nachweis im Container:** `env | grep -E 'OLLAMA|HANDEL|OMNIROUTE'`.
Setzen per `hermes config set terminal.docker_forward_env [...]` — mit den bekannten
`config set`-Fallen (siehe [[Betrieb/Hermes]]).

## Container mit Daueraufgaben

- `nautilus-demo` — OKX-Demo-Quoten-Node, `--restart unless-stopped`, Dummy-Env
  (die OKX-Factory verlangt die Variablen hart; echte Schluessel verlassen den Rechner nie).
- `ollama/ollama` auf `127.0.0.1:11437` (zweite Instanz neben dem Host-Ollama auf 11434).

GUI-Fenster-Automation ist fragil, wenn Max parallel am PC arbeitet (Fokus, virtuelle
Desktops, 150 % DPI) — Docker ist die robuste Startmethode.