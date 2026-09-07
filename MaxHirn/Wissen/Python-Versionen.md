---
id: 20260831-python-versionen
title: 'Python-Versionen'
tags: [betrieb, ki-agenten]
created: 2026-08-31
updated: 2026-09-07
related: [20260830-hermes, 20260830-projekte, 20260901-globale-npm-tools-path]
summary: 'Installierte Python-Versionen und venv-Konfigurationen nach dem Upgrade auf 3.13.'
---

# Python-Versionen

## Systemüberblick (31.08.2026)

| Komponente | Python | Ort | Status |
|---|---|---|---|
| **Global installiert** | 3.13.15 | `C:\Users\faupe\AppData\Local\Programs\Python\Python313\` | aktiv |
| **Hermes venv** | 3.13.15 | `../Agenten/Hermes/hermes-agent/venv/` | aktuell, funktionsfähig |
| **OmniRoute** | Node.js v24.19.0 | `../Werkstatt/OmniRoute/` | npm-Module installiert |

## Upgrade auf Python 3.13 — 31.08.2026

Durchgeführt, um Max' persönliche Anforderung zu erfüllen. **Datum kritisch:** Upgrade-Skript lief als Background-Task, venvs wurden neu gebaut.

### Was wurde gemacht

1. Alte venvs gesichert (Timestamps):
   - `C:\Hermes\venv.backup-20260831-224134` (Python 3.11.16 vom 24.08.)
   - `../Agenten/Hermes/hermes-agent/venv.backup-20260831-224134` (Python 3.11.15 vom 31.08.)

2. Neue venvs mit Python 3.13.15 gebaut
   - `../Agenten/Hermes/hermes-agent/venv/` neu erstellt
   - 60+ Dependencies neu installiert (`setuptools`, `wheel`, alle Hermes-Abhängigkeiten)
   - Hermes als editable install: `pip install -e C:\Hermes`

3. CLI-Funktionalität verifiziert:
   ```
   hermes --version
   → Hermes Agent v0.21.0 (2026.8.31)
   → Python: 3.13.15 ✓
   ```

### Bekannte Eigenheit

Der editable install `hermes_agent` ist per direktem Python-Import nicht verfügbar (`import hermes_agent` schlägt fehl). **Das ist nicht kritisch** — Hermes funktioniert über CLI-Entry-Points (`hermes.exe`, `hermes.cmd`) und Python-Modulaufruf (`python -m hermes_cli.main`), beide funktionieren.

**Warum:** Das `pyproject.toml` definiert keine `packages`-Konfiguration. Der editable install funktioniert über `__editable__.hermes_agent-0.21.0.pth`, kann aber das Modul nicht automatisch mappen.

**Workaround falls nötig:** `export PYTHONPATH=C:\Hermes` setzt, dann `import agent` (ohne `hermes_` prefix) funktioniert.

## OmniRoute (Node.js)

Python ist nicht relevant. Quell-Klon in `Werkstatt/OmniRoute/` (Branch
`release/v3.8.51`). **From-Source-Installation am 07.09.2026 abgeschlossen:**
`npm install` (2518 Pakete, ~5 min), `.env` automatisch aus `.env.example`
erzeugt (47 Keys, 0 Secrets), native Module verifiziert (`libxmljs2`,
`onnxruntime-node` laden; node-gyp/MSVC war als Voraussetzung installiert).
Smoke-Test: `npm run dev` lief auf übersteuerten Ports (PORT=20138) und
beantwortete `/v1/models` mit 200 inkl. `auto/best-coding`.

**Betriebshinweise:**
- Der laufende Produktions-Router ist die globale npm-Installation
  (`omniroute serve`, Port 20128). Quell-Instanz und globale teilen sich
  `~/.omniroute/storage.sqlite` — nie zwei Instanzen gleichzeitig auf derselben
  DB starten.
- `npm run dev` braucht Schreibplatz für `.build/` (Turbopack-Cache); bei
  Datenträger voll bricht er mit os error 112 ab.
- 5 Install-Skripte sind durch `allow-scripts` noch nicht freigegeben
  (playwright, bun, libxmljs2, onnxruntime-node, opencode-ai) — die beiden
  nativen laden auch ohne; die übrigen sind optionale Pakete.

## Backups

Können nach 24–48 h gelöscht werden. Die neuen venvs mit 3.13.15 sind stabil und werden verwendet.

```powershell
# Zum Löschen (falls nicht mehr nötig):
Remove-Item -Path "C:\Hermes\venv.backup-20260831-224134" -Recurse -Force
Remove-Item -Path "../Agenten/Hermes/hermes-agent/venv.backup-20260831-224134" -Recurse -Force
```

## Python 3.14 Readiness

Das `pyproject.toml` von Hermes sagt:
```
requires-python = ">=3.11,<3.14"
```

Python 3.14 ist **nicht freigegeben** (obere Grenze `<3.14`). Das ist bewusst — Rust-basierte Transitive (z. B. `pydantic-core`) haben keine `cp314` Wheels und würden per Maturin kompiliert. Sobald diese Packages 3.14 unterstützen, wird die Grenze hochgezogen.

## Der Neubau blieb unvollständig — Stromausfall mitten im Lauf

**Nachtrag 31.08.2026, 23:30.** Der Umbau auf 3.13.15 wurde um **22:56:23**
von einem harten Stromausfall unterbrochen (`Kernel-Power 41`, `BugcheckCode=0`,
dazu `EventLog 6008` — dasselbe Hardwarebild wie in [[Hardware]]). Das venv war
zuletzt um 22:52 geschrieben worden, die Installation lief also mitten hinein.

**Ergebnis: 70 statt 146 Pakete.** Es fehlten unter anderem `anthropic` und
`mcp` — also der Anthropic-SDK und der MCP-Client. Hermes hätte damit weder mit
`claude-opus-5` sprechen noch einen einzigen der 11 MCP-Server nutzen können.

**Warum das keiner merkt:** `hermes --version` und `hermes status` laufen
trotzdem sauber durch und melden Modell, Provider und Token als erkannt — sie
lesen nur die Konfiguration. Der Defekt fällt erst bei der ersten echten
Aufgabe auf.

> **Prüfung nach jedem venv-Neubau** — Versionsabfrage genügt nicht:
> ```
> venv\Scripts\python.exe -c "import anthropic, mcp, aiohttp, numpy; print('ok')"
> ```
> und die Paketzahl gegen den Vorstand halten:
> `ls -d venv/Lib/site-packages/*.dist-info | wc -l`

Behoben am 31.08. um 23:20: die 77 fehlenden Pakete mit `uv pip install -r`
nachgezogen, alle unter 3.13.15 ohne Konflikt auflösbar. **Jetzt 150 Pakete**,
`anthropic`, `mcp`, `aiohttp`, `numpy`, `sounddevice`, `playwright` und
`faster_whisper` sämtlich importierbar, `hermes status` meldet
`Model: claude-opus-5`. Protokoll:
`../Agenten/Hermes/.sicherung/nachinstallation-20260831.log`.

Die oben notierte Eigenheit bleibt richtig: `import hermes_agent` schlägt auch
nach der Reparatur fehl — der Modulname ist `hermes_cli`, `hermes_agent` ist nur
der Name der Distribution. Das ist kein Defekt.

## Verwandt

[[Hermes]] · [[Projekte]] · [[Globale-npm-Tools-PATH]]
