---
name: skill-schedule
description: Trockenlauf des Skills schedule — Cloud-Routinen (CCR) erstellen/aktualisieren/listen/ausführen per RemoteTrigger-Tool; Cron-Ausdrücke, Environments, MCP-Konnektoren; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** Cloud-Agenten (CCR) als wiederkehrende Routinen oder Einmal-Läufe planen.

**Lauf:** 2026-10-22, trockenlauf.

**Wichtig:** Cloud-Agents laufen in Anthropics Cloud-Infrastruktur — kein Zugriff auf lokale Dateien, lokale Dienste oder lokale Env-Variablen.

**Tool:** `RemoteTrigger` (via `ToolSearch select:RemoteTrigger` laden)

**Actions:**
| Action | Zweck |
|---|---|
| `list` | Alle Routinen auflisten |
| `get` | Eine Routine abrufen |
| `create` | Neue Routine erstellen |
| `update` | Routine aktualisieren (partial) |
| `run` | Routine sofort ausführen |
| `list_runs` | Letzte Läufe einer Routine |
| `get_run_log` | Kondensiertes Log eines Laufs |

**Environments (Max' Setup):**
- `MaksPC420:C:\Users\faupe\Documents\BrainFiles:2c31` → id: `env_01WmoeRXXZZ1SpwApQPksaEb` (bridge)
- `MaxPC` → id: `env_01QL5722PAcQAyy48Y47tB2i` (anthropic_cloud)

**Cron-Regeln:**
- Minimum-Intervall: **1 Stunde** (`*/30 * * * *` wird abgelehnt)
- Immer UTC; Max' Zeitzone: Europe/Berlin (UTC+1/+2)
- Einmal-Lauf: `run_once_at: "YYYY-MM-DDTHH:MM:SSZ"` statt `cron_expression`
- Vor jedem `run_once_at`-Wert: `date -u` via Bash!

**Create-Body:**
```json
{
  "name": "...",
  "cron_expression": "0 8 * * *",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "env_...",
      "session_context": {
        "model": "claude-sonnet-5-5",
        "sources": [{"git_repository": {"url": "https://github.com/mfaupel95/BrainFiles"}}],
        "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
      },
      "events": [{"data": {
        "uuid": "<fresh-lowercase-v4-uuid>",
        "session_id": "",
        "type": "user",
        "parent_tool_use_id": null,
        "message": {"role": "user", "content": "PROMPT_HERE"}
      }}]
    }
  }
}
```

**Verfügbare MCP-Konnektoren für Routinen:**
Claude-Docs, Etherscan, Figma, TEXT-TO-QUANT, DEBYKO, Superhuman-Docs, UseMyContext-ai, ChangeThisFile, Google-Calendar, Gmail

**Löschen:** Nicht per API möglich → https://claude.ai/code/routines

**Debugging:** `list_runs` → `get_run_log` für Session-ID. Kein Lauf in der Liste = Routine selbst prüfen (Pause, Fehler vor Session-Erstellung).

**Link nach Erstellen:** `https://claude.ai/code/routines/{ROUTINE_ID}`
