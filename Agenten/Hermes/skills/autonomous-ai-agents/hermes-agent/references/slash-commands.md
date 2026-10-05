# Slash Commands (In-Session)

Registry of record: `hermes_cli/commands.py` (`COMMAND_REGISTRY`) — every
consumer (autocomplete, `/help`, Telegram menu, Slack mapping) derives from
it. New commands land often; `/help` in-session is always authoritative.
(CLI) = interactive CLI/TUI only. (GW) = gateway platforms only.

### Session
```
/new (/reset) [name]     Fresh session
/clear                   Clear screen + new session (CLI)
/retry                   Resend last message
/undo [N]                Back up N user turns and re-prompt
/title [name]            Name the session
/prompt (/compose)       Compose next prompt in $EDITOR (CLI)
/compress (/compact)     Compress context ('here [N]' keeps N turns; --preview)
/stop                    Kill background processes
/rollback [N]            List/restore filesystem checkpoints
/diff [mode] [--stat]    Git changes in cwd (staged|all|session modes)
/snapshot [sub]          Create/restore Hermes config+state snapshots (CLI)
/bg <prompt>              Run a prompt in a separate background session
/btw <question>           Ask a side question about the current conversation without interrupting it
/queue (/q) <prompt>     Queue prompt for next turn
/steer <prompt>          Inject a message after the next tool call
/agents (/tasks)         Show active agents and running tasks
/goal [text|sub]         Standing goal across turns (status|pause|resume|clear)
/subgoal [text]          Add/manage criteria on the active goal
/branch (/fork) [name]   Branch the session
/resume [name]           Resume a named session
/sessions                Browse and resume previous sessions
/handoff <platform>      Hand live session off to a messaging platform (CLI)
/status                  Session, model, token, and context info
/redraw                  Force full UI repaint (CLI)
```

### Configuration
```
/config                  Show config (CLI)
/model [name] [--global] Switch model (session-scoped by default)
/personality [name]      Set a personality
/reasoning [level|show|hide] Reasoning effort/display (none..xhigh|max|ultra)
/fast [normal|fast]      Priority/fast processing tier
/verbose                 Cycle tool progress: off → new → all → verbose → log (CLI)
/voice [on|off|tts]      Voice mode
/yolo                    Toggle approval bypass
/busy [queue|steer|interrupt] How messages behave while working (CLI + gateway)
/indicator [style]       TUI busy indicator: kaomoji|emoji|unicode|ascii (CLI)
/footer [on|off]         Gateway runtime-metadata footer on replies
/skin [name]             Change theme (CLI)
/statusbar (/sb)         Toggle status bar (CLI)
/battery [on|off]        Battery indicator in status bar (CLI)
/timestamps (/ts) [on|off] Message timestamps (CLI)
/codex-runtime [auto|codex_app_server] Codex runtime toggle
```

### Tools & Skills
```
/tools [list|enable|disable] Manage tools (CLI)
/toolsets                List toolsets (CLI)
/skills                  Search/install/manage skills (CLI)
/bundles                 List skill bundles (/<name> loads several skills)
/learn <source>          Learn a reusable skill from dirs/URLs/this chat
/memory [pending|approve|reject] Review pending memory writes / approval gate
/pet [toggle|list|<slug>] Petdex mascot control (CLI)
/hatch [description]     Generate a new pet from a description (CLI)
/cron [sub]              Manage scheduled tasks (CLI)
/suggestions (/suggest)  Review suggested automations
/blueprint (/bp) [name]  Set up an automation from a blueprint
/curator [sub]           Skill maintenance (status, run, pin, archive, …)
/kanban [sub]            Multi-profile collaboration board
/moa <prompt>            One prompt through the Mixture-of-Agents preset
/reload                  Reload .env into the running session (CLI)
/reload-mcp              Reload MCP servers
/reload-skills           Re-scan skills directory
/browser [connect|status] CDP connection to your live browser (CLI)
/plugins                 List plugins (CLI)
```

### Gateway
```
/approve [session|always]  Approve a pending dangerous command (GW)
/deny [all] [reason]       Deny a pending dangerous command (GW)
/restart                   Restart gateway after draining active runs (GW)
/sethome                   Set current chat as home channel (GW)
/topic [off|help]          Telegram DM topic sessions (GW)
/platform <pause|resume|list> Pause/resume a failing platform (GW)
/commands [page]           Browse all commands, paginated (GW)
```

### Info
```
/help                    Show commands
/usage [reset]           Token usage and rate limits
/insights [days]         Usage analytics
/whoami                  Slash-command access level (admin/user)
/profile                 Active profile info
/platforms (/gateway)    Platform connection status (CLI)
/journey (/learning)     Learned skills + memories timeline (CLI)
/subscription (/upgrade) Nous plan info (CLI)
/topup                   Nous balance / billing
/copy [N]                Copy last response to clipboard (CLI)
/paste                   Attach clipboard image (CLI)
/image <path>            Attach a local image file (CLI)
/update                  Update Hermes to latest
/version (/v)            Show version
/debug [nous|local]      Upload debug report, get shareable links
```

### Exit
```
/quit (/exit) [--delete] Exit CLI; --delete also removes session history
```

## /queue im Detail (Routing, Verben, Inline-Dispatch)

Quelle: `hermes_cli/cli_loops_mixin.py:320-452` (`_cmd_queue` und die
`_queue_*`-Handler). Ein einziger Befehl, zwei Bedeutungen - die Unterscheidung
ist eine **Argument-Routing-Regel**, kein zweiter Befehl:

- **Enqueuen (Vorgabe):** `/queue <beliebiger Text>` stellt den Text als Prompt
  fuer den naechsten Turn an. Auch `add` davor erzwingt explizites Enqueuen.
- **Verwalten:** ein fuehrendes Verb, dessen Argumente passen. Verb-Tabelle
  `_QUEUE_VERBS` (Zeile 48): `list|ls|show` (ohne Argument), `clear` (ohne
  Argument), `edit|set N <text>`, `rm|remove|delete|del|pop N`, `move A B`.
- **Die Falle:** passt das Argument NICHT zur Verb-Semantik, ist es ein Prompt.
  `/queue clear the logs` enqueut "clear the logs" als Prompt - es leert NICHT.
  `/queue rm` OHNE Nummer druckt nur die Usage-Zeile (Verb allein = Management-
  Fall, Handler fragt Argument). Ein Index wird mit
  `_parse_queue_index` (1-basiert, weiße-zeichenfreies Token) geparst;
  `str.isdigit()` allein reicht nicht (akzeptiert `²`, `②`).

**Inline-Dispatch waehrend der Agent laeuft** (`cli_info_mixin.py:470-476`):
`/queue` und `/steer` werden SOFORT verarbeitet, wenn die Agent-Schleife gerade
laeuft (`_should_handle_steer_command_inline`), statt roh in die Warteschlange
gelegt zu werden. Grund: roh eingereiht haette sich `/queue <prompt>` nach dem
Turn selbst nochmal enqueued, und `/queue list|rm|edit` haette die Schlange erst
nach dem Leeren zu sehen bekommen (beide beobachteten Fehlerbilder). Die
1-basierte Nummerierung erscheint im `list`-Ausdruck, `[voice]` markiert
Sprachaufnahmen, `_preview` kuerzt auf 80 Zeichen.

**Weitere semantische Punkte:**
- Enqueuen waehrend der Agent laeuft ist NICHT unterbrechend: der Text kommt als
  naechster Turn, die laufende Antwort bleibt unberuehrt (anders als
  `/steer`, das nach dem naechsten Werkzeugaufruf injiziert).
- `_queue_enqueue` streckt zuerst Paste-Referenzen
  (`_expand_paste_references`); ein eingefuegter Dateiinhalt wird aufgeloest,
  bevor er in die Schlange kommt.
- Ein Sprachaufnahme-Eintrag behaelt seinen Sentinel beim `edit`
  (`_VoiceInputMessage` bleibt `_VoiceInputMessage`, damit die knappe
  Sprachantwort-Praefix weiter gilt; #65827).
- Reihenfolge der Verwaltung ist FIFO in `_pending_input` (eine
  `queue.Queue`); `move A B` ordnet um.
- `/queue` ist (CLI): die Messaging-Gateway-Plattformen (Telegram-Bot,
  SkillsBot-Bruecke) haben KEINEN queue-Handler — dort angekommen, wird die
  Nachricht als Freitext/Bot-Auftrag behandelt statt enqueued.
