---
name: skill-update-config
description: Trockenlauf des Skills update-config — settings.json bearbeiten, Hooks anlegen/debuggen, Berechtigungen, Umgebungsvariablen; wann /config-Befehl, wann direkt bearbeiten; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Claude Code über settings.json konfigurieren — Hooks, Berechtigungen, Env-Vars, MCP, Plugins.

**Wann nutzen:** Wenn etwas automatisch bei einem Ereignis passieren soll (Hook), Berechtigungsregeln geändert werden, oder settings.json angepasst wird.

**Lauf:** 2026-10-22, trockenlauf.

**Grundregel:** Immer zuerst die Zieldatei lesen, dann gezielt mergen — nie ersetzen.

**Wann /config-Befehl:**
- Einfache Einstellungen: `theme`, `editorMode`, `verbose`, `model`, `language`, `alwaysThinkingEnabled`, `permissions.defaultMode`

**Wann direkt settings.json bearbeiten:**
- Hooks, komplexe Berechtigungen, Env-Vars, MCP-Server, Plugins

**Drei Dateien:**
| Datei | Scope | Git |
|---|---|---|
| `~/.claude/settings.json` | Global | Nein |
| `.claude/settings.json` | Projekt | Ja |
| `.claude/settings.local.json` | Projekt lokal | Gitignore |

Reihenfolge: user → project → local (späteres überschreibt früheres).

**Hooks — Grundstruktur:**
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{"type": "command", "command": "..."}]
    }]
  }
}
```

**Hook-Ereignisse:** PreToolUse, PostToolUse, PreCompact, PostCompact, Stop, Notification, SessionStart, UserPromptSubmit.

**Hook-Prüfprozess (7 Schritte):**
1. Duplikat-Check: bestehenden Hook auf demselben Ereignis+Matcher lesen
2. Befehl aufbauen: `jq -r` für stdin-Extraktion, nie `| xargs` (splittet bei Leerzeichen)
3. Rohen Befehl testen: `echo '{"tool_name":"Edit","tool_input":{"file_path":"..."}}' | <cmd>`
4. JSON schreiben und mergen
5. Syntax validieren: `jq -e '.hooks.<event>[] | select(.matcher == "<m>") | ...' <datei>`
6. Hook-Feuern beweisen (nur für Pre|PostToolUse auf Write|Edit oder Bash)
7. Übergabe: Benutzer auf `/hooks` hinweisen

**Berechtigungen — Syntax:**
- `"Bash(git *)"` — Präfix-Wildcard
- `"Read"` — alle Reads
- `"Edit(src/**)"` — Pfad-Muster

**Mergen von Arrays — wichtig:** Immer bestehende Einträge erhalten, nie ersetzen.

**Env-Vars:**
```json
{ "env": { "DEBUG": "true" } }
```

**Attribution (Commit/PR):**
```json
{ "attribution": { "commit": "Custom text", "pr": "Custom text" } }
```
Leerer String = Attribution ausblenden. Nie `"attribution": false` — bricht ältere Versionen.

**Hook-Typen:** `command` (Shell), `prompt` (LLM-Bedingung), `agent` (Agent mit Tools), `http` (HTTP POST), `mcp_tool`.

**Häufige Fehler:**
1. Ersetzen statt mergen
2. Falsche Datei (Scope klären)
3. Ungültiges JSON (bricht alle Einstellungen aus dieser Datei)
4. Nicht zuerst gelesen
