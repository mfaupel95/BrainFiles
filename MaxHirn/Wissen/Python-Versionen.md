---
id: 20260831-python-versionen
title: 'Python-Versionen'
tags: [betrieb, hermes]
created: 2026-08-31
updated: 2026-08-31
related: [20260830-hermes, 20260830-projekte]
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

Python ist nicht relevant. **1.481 npm-Module installiert**, dist/ mit 4.097 Dateien gebaut. Keine Aktion erforderlich.

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

## Verwandt

[[Hermes]] · [[Projekte]]
