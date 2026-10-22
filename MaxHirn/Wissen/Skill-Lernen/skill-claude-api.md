---
name: skill-claude-api
description: Trockenlauf des Skills claude-api — Anthropic SDK (Python/TS/Go/...) korrekt nutzen; aktuelle Modell-IDs, Thinking-Konfiguration, Tool Use, Streaming, Caching; API-Drift-Warntabelle; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** LLM-Applikationen mit der Anthropic API / dem Claude SDK bauen — Modell wählen, Code schreiben, Drift vermeiden.

**Lauf:** 2026-10-22, trockenlauf.

**Aktuelle Modell-IDs (Stand 2026-10-06):**
| Model | ID | $/1M in/out |
|---|---|---|
| Claude Opus 5.5 (Default) | `claude-opus-5-5` | $4 / $20 |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | $2 / $10 |
| Claude Haiku 5.5 | `claude-haiku-5-5` | $0.10 / $0.50 |
| Claude Fable 5.1 | `claude-fable-5-1` | $10 / $50 |

**Immer** `claude-opus-5-5` verwenden, außer User nennt explizit anderes Modell.

**Kritische API-Drift-Punkte:**
| Alt | Aktuell |
|---|---|
| `thinking: {type: "enabled", budget_tokens: N}` | `thinking: {type: "adaptive"}` (Opus 4.6+) |
| `web_search_20250305` | `web_search_20260209` (Opus 4.6+) |
| `client.beta.files.*` | `client.files.*` (kein Beta-Header) |
| `output_format` | `output_config: {format: {...}}` |
| Prefill als letzter Assistant-Turn | 400 bei Opus/Sonnet/Fable 4.6+ |
| `tool_choice: {type: "any"}` | 400 bei Opus 5.5 / Sonnet 5.5 / Fable 5.1 |

**Thinking-Kurzregel:**
- Alle aktuellen Modelle: `thinking: {type: "adaptive"}` oder weglassen
- Opus 5.5: Default `effort: "medium"` (nicht "high"!)
- Sonnet 5.5: Denken ausschalten? → `{type: "between_tools"}`, NICHT `{type: "disabled"}`
- Haiku 4.5 / alte Modelle: `{type: "enabled", budget_tokens: N}` (min 1024)

**Surfaces:**
1. Einzelner API-Call → `client.messages.create`
2. Tool Use Loop → Tool Runner (`client.beta.messages.tool_runner`)
3. Managed Agents → `client.beta.agents` + `sessions` (Anthropic hostet Loop + Container)
4. Claude Agent SDK → eigenes Produkt, NICHT dieser Skill

**Tool Use Quick Facts:**
- `strict: true` → Schema-valide Inputs, `additionalProperties: false + required`
- Parallele Tool Calls: alle Results in EINER user-Message zurückgeben
- Tool Runner: `@beta_tool` (Python) / `betaZodTool` (TS)

**Prompt Caching:**
- `cache_control: {"type": "ephemeral"}` auf `messages.create()` für auto-caching
- Stable Content ZUERST, volatile Content NACH dem letzten Breakpoint
- Prüfen: `response.usage.cache_read_input_tokens` > 0?

**Fehlerbehandlung:** most-specific-first: `NotFoundError` → `RateLimitError` → `APIStatusError` → `APIConnectionError`

**`max_tokens`-Default:** 16000 (sync), 64000 (streaming). Nie zu klein wählen.
