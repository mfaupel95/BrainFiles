---
name: skill-plugin-authoring
description: Trockenlauf des Skills plugin-authoring — Claude Code Mods/Plugins erstellen (Panes, Bands, Hooks, Status); Dateistruktur, API, Validierung; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Claude Code-Mods (Plugins) erstellen — Panes, Bands, Status-Line-Einträge, Tool-Hooks.

**Lauf:** 2026-10-22, trockenlauf.

**Ordner:** `~/.claude/dev-mods/<session-id>/<mod-name>/`

**Drei Pflichtdateien:**
```
.claude-plugin/plugin.json  → { "name", "version": "0.1.0", "description" }
hooks/hooks.json             → { "modules": ["./register.tsx"] }
hooks/register.tsx           → export const register: Register = (on, options) => { ... }
```
Optional: `types/index.d.ts` für `$.state`-Werte (in plugin.json als `"types"`).

**Hauptkonzepte:**
- `on(event, matcher?, hook)` — Hook registrieren; `($, e, next)` als Signatur
- `next(e)` weiterleiten; ohne next = eigene Antwort; `next({ ...e, x })` = Rewrite
- JSX kompiliert gegen globales `h`; Elemente per `$.ui.resolve(e)`: `{ Box, Text, Button }`

**Was womit:**
| Anfrage | Werkzeug |
|---|---|
| Pane/Panel/Sidebar | `$.ui.open({ id, title })` + `ui.render`-Hook auf `Pane` |
| Band über Prompt | `ui.render`-Hook auf `AbovePrompt` |
| Status-Line | `$.ui.status(text)` aus beliebigem Hook |
| Toast | `$.ui.toast(text)` |
| Tool-Call abfangen | `on('tool.call', { tool }, hook)` → `{ deny }` oder `next` |
| Slash-Befehl | `$.command.register(...)` in `session.start` + `command.run`-Hook |

**Typ-Dateien:** Beim ersten Schreiben unter `claude-code.d.ts` im Skill-Ordner; nach Engine-Load unter `<mod>/.claude-plugin/types/`. `tsc -p <mod folder>` zum Type-Check.

**Validierung:** `claude plugin validate <mod folder>` — prüft Manifest + Modul.

**Aktivierung:** Engine fragt einmalig „Turn on the mods?" → Bestätigen; sonst beim nächsten Start.

**Sharing:** `.claude-plugin/marketplace.json` + GitHub → `/plugin install <mod> --marketplace <owner>/<repo>`.
