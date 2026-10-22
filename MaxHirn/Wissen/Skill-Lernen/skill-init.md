---
name: skill-init
description: Trockenlauf des Skills init — CLAUDE.md für neues Repository erstellen (Befehle, Architektur); was rein soll, was nicht; Import-Hinweis für fremde KI-Configs; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** CLAUDE.md für ein Repo erstellen — damit zukünftige Claude-Instanzen produktiver starten.

**Lauf:** 2026-10-22, trockenlauf.

**Was rein soll:**
1. Häufige Befehle: Build, Lint, Tests laufen lassen, einzelnen Test ausführen
2. High-level-Architektur: was mehrere Dateien braucht, um verstanden zu werden

**Was NICHT rein soll:**
- Offensichtliches ("write unit tests", "no API keys in code")
- Jede Datei/Komponente (leicht selbst entdeckbar)
- Generische Best Practices

**Quellen prüfen:**
- `.cursor/rules/`, `.cursorrules` → wichtige Teile übernehmen
- `.github/copilot-instructions.md` → wichtige Teile übernehmen
- `README.md` → wichtige Teile übernehmen

**Pflicht-Präfix:**
```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
```

**Fremde KI-Configs:** Falls `~/.codex/config.toml`, `.codex/`, `~/.gemini/settings.json`, `.gemini/`, `GEMINI.md` gefunden → Import anbieten: `/import` zum Scannen, `/import --yes=<digest>` zum Anwenden. Dateien selbst nie lesen oder schreiben.

**Bestehende CLAUDE.md:** Verbesserungen vorschlagen, nicht ersetzen.
