# Fundus-Index - Werkstatt/Repos

Erzeugt von `Agenten/Werkzeuge/fundus-suche.ps1 -Index`. Nicht von Hand pflegen.

Geklonte Fremd-Repos: **293 eindeutige Skills** in 18 Repos (356 Dateien, 63 byte-identische Kopien zusammengefasst).

Nicht in der Hermes-Bibliothek geladen; Zugriff ueber `Agenten/Werkzeuge/fundus-suche.ps1 -Begriff "<wort>"`.

## Agent-Reach (1)

- **agent-reach** - MUST USE when user wants to 调研/research/搜索/search/查/找/look up anything on the internet — e.g. 全网调研 X / 帮我调研一下 X / 查一下 X / 搜搜 X / 看看大家怎么评价 X / X 上有什么讨论 / research this topic。
  `Werkstatt\Repos\Agent-Reach\agent_reach\skill\SKILL.md`

## basic-memory (46)

- **adversarial-review** - Cross-vendor adversarial code review of the current branch. Two different model families (Claude + Codex/GPT) review the diff independently, then try to refute each other's findings; survivors are rep...
  `Werkstatt\Repos\basic-memory\.agents\skills\adversarial-review\SKILL.md`
- **basic-memory** - Use the Basic Memory knowledge graph for persistent memory across sessions. Search before answering; capture decisions, meetings, and insights as notes.
  `Werkstatt\Repos\basic-memory\integrations\hermes\skill\SKILL.md`
- **bm-checkpoint** - Create an immutable Codex handoff in Basic Memory and return an exact bm-orient resume command.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-checkpoint\SKILL.md`
- **bm-checkpoint** - Save a deliberate work checkpoint to Basic Memory with the story, changed files, verification, decisions, blockers, and the next action. Use when the user asks to checkpoint, wrap up, hand off, or rem...
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-checkpoint\SKILL.md`
- **bm-decide** - Capture a durable engineering decision in Basic Memory with rationale, alternatives, consequences, and affected work.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-decide\SKILL.md`
- **bm-decide** - Capture a durable engineering decision in Basic Memory with rationale, alternatives, consequences, and affected work. Use when the user makes or asks to record a real choice —
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-decide\SKILL.md`
- **bm-orient** - Resume from an exact Basic Memory checkpoint or orient Codex from current graph and repository evidence.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-orient\SKILL.md`
- **bm-orient** - Orient Claude from Basic Memory before substantial repo work by reading active tasks, open decisions, recent checkpoints, and repo conventions. Use when resuming old work or when the user asks where t...
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-orient\SKILL.md`
- **bm-remember** - Quickly capture a thought, fact, or reminder into Basic Memory as a lightweight note. Use when the user says
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-remember\SKILL.md`
- **bm-remember** - Quickly save a small fact, reminder, or user preference into Basic Memory from Codex without turning it into a full decision or checkpoint.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-remember\SKILL.md`
- **bm-setup** - Set up the Basic Memory plugin for this project — a short guided interview that configures the project mapping, seeds note schemas, learns or suggests placement conventions, and enables capture reflex...
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-setup\SKILL.md`
- **bm-setup** - Set up Basic Memory for Codex at user or project level by mapping a Basic Memory project and seeding schemas.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-setup\SKILL.md`
- **bm-share** - Share a personal Basic Memory note to a configured team project from Codex with attribution and explicit confirmation.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-share\SKILL.md`
- **bm-share** - Promote a note from your personal Basic Memory project to a shared team project, with attribution. Use when the user says
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-share\SKILL.md`
- **bm-status** - Show the Basic Memory plugin's current state for this project — active project, capture folders, output style, recent session checkpoints, and whether Basic Memory is reachable.
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-status\SKILL.md`
- **bm-status** - Report the Basic Memory for Codex configuration, reachability, hook expectations, recent Codex checkpoints, and active tasks.
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-status\SKILL.md`
- **bm-writing** - Apply the user-customizable writing standard for Basic Memory notes created or substantially revised by Codex. Use with bm-checkpoint, bm-decide, bm-remember, and other Basic Memory note-writing workf...
  `Werkstatt\Repos\basic-memory\plugins\codex\skills\bm-writing\SKILL.md`
- **bm-writing** - Apply the user-customizable writing standard for Basic Memory notes created or substantially revised by Claude. Use with bm-remember, the basic-memory output style's decision captures, and other Basic...
  `Werkstatt\Repos\basic-memory\plugins\claude-code\skills\bm-writing\SKILL.md`
- **cmux** - End-user control of cmux topology and routing (windows, workspaces, panes/surfaces, focus, moves, reorder, identify, trigger flash). Use when automation needs deterministic placement and navigation in...
  `Werkstatt\Repos\basic-memory\.agents\skills\cmux\SKILL.md`
- **cmux-markdown** - Open markdown files in a formatted viewer panel with live reload. Use when you need to display plans, documentation, or notes alongside the terminal with rich rendering (headings, code blocks, tables,...
  `Werkstatt\Repos\basic-memory\.agents\skills\cmux-markdown\SKILL.md`
- **cmux-settings** - View and edit cmux settings in ~/.config/cmux/cmux.json. Use when the user wants to change cmux preferences (appearance, sidebar, notifications, automation, browser, shortcuts), set a value by JSON pa...
  `Werkstatt\Repos\basic-memory\.agents\skills\cmux-settings\SKILL.md`
- **cmux-workspace** - Work inside the current cmux workspace and terminal. Use for cmux workspace, current workspace, caller surface, panes, surfaces, socket targeting, and non-interfering cmux automation.
  `Werkstatt\Repos\basic-memory\.agents\skills\cmux-workspace\SKILL.md`
- **code-review** - Use when reviewing Basic Machines code for house style, architecture risk, pre-merge hardening, or whether a change fits basic-memory/basic-memory-cloud conventions.
  `Werkstatt\Repos\basic-memory\.agents\skills\code-review\SKILL.md`
- **fix-pr-issues** - Use when addressing Basic Memory pull request feedback, failed checks, or Codex review blockers, then re-running the latest-head review gate.
  `Werkstatt\Repos\basic-memory\.agents\skills\fix-pr-issues\SKILL.md`
- **infographics** - Use when generating Basic Memory PR, changelog, release, or weekly images from Codex.
  `Werkstatt\Repos\basic-memory\.agents\skills\infographics\SKILL.md`
- **instrumentation** - Add Pydantic Logfire observability to applications. Use this skill whenever the user asks to
  `Werkstatt\Repos\basic-memory\.agents\skills\instrumentation\SKILL.md`
- **memory-capture** - Capture the current state of a working thread or conversation into a single coherent Basic Memory note — synthesize where it landed, don't append a log. On re-capture, rewrite the same note in place i...
  `Werkstatt\Repos\basic-memory\skills\memory-capture\SKILL.md`
- **memory-ci-capture** - Synthesize GitHub delivery context into a concise Basic Memory project update. Use in CI after `bm ci collect` prepares a ProjectUpdateContext; return only structured AgentSynthesis JSON for `bm ci pu...
  `Werkstatt\Repos\basic-memory\skills\memory-ci-capture\SKILL.md`
- **memory-continue** - Resume prior work by rebuilding context from the Basic Memory knowledge graph — pick up where you left off using memory:// URLs, recent activity, and search. Use when starting a session or when the us...
  `Werkstatt\Repos\basic-memory\skills\memory-continue\SKILL.md`
- **memory-curate** - Curate the Basic Memory knowledge graph: find orphan notes and suggest links, propose typed relations, merge duplicates, audit tags and folders, and build hub notes. Use to organize, connect, and impr...
  `Werkstatt\Repos\basic-memory\skills\memory-curate\SKILL.md`
- **memory-defrag** - Defragment and reorganize agent memory files: split bloated files, merge duplicates, remove stale information, and restructure the memory hierarchy. Use when memory files have grown unwieldy, contain ...
  `Werkstatt\Repos\basic-memory\skills\memory-defrag\SKILL.md`
- **memory-ingest** - Process unstructured external input (meeting transcripts, conversation logs, pasted documents) into structured Basic Memory entities. Extracts entities, searches for existing matches, proposes new ent...
  `Werkstatt\Repos\basic-memory\skills\memory-ingest\SKILL.md`
- **memory-lifecycle** - Manage entity status transitions in Basic Memory: archive completed work, move notes between status folders, update frontmatter, and handle edge cases. Use when marking items complete, archiving old e...
  `Werkstatt\Repos\basic-memory\skills\memory-lifecycle\SKILL.md`
- **memory-literary-analysis** - Analyze a complete literary work into a structured Basic Memory knowledge graph. Covers schema design, entity seeding, chapter-by-chapter processing, cross-referencing, validation, and graph explorati...
  `Werkstatt\Repos\basic-memory\skills\memory-literary-analysis\SKILL.md`
- **memory-metadata-search** - Structured metadata search for Basic Memory: query notes by custom frontmatter fields using equality, range, array, and nested filters. Use when finding notes by status, priority, confidence, or any c...
  `Werkstatt\Repos\basic-memory\skills\memory-metadata-search\SKILL.md`
- **memory-notes** - How to write well-structured Basic Memory notes: frontmatter, observations with semantic categories, relations with wiki-links, and best practices for building a rich knowledge graph. Use when creatin...
  `Werkstatt\Repos\basic-memory\skills\memory-notes\SKILL.md`
- **memory-onboarding** - Guide someone new to Basic Memory through designing and building a complete personal knowledge system — interview them about what they want to track, propose a structure, build it with schemas and ins...
  `Werkstatt\Repos\basic-memory\skills\memory-onboarding\SKILL.md`
- **memory-reflect** - Sleep-time memory reflection: review recent conversations and daily notes, extract insights, and consolidate into long-term memory. Use when triggered by cron, heartbeat, or explicit request to reflec...
  `Werkstatt\Repos\basic-memory\skills\memory-reflect\SKILL.md`
- **memory-research** - Research an external subject using web search, synthesize findings into a structured Basic Memory entity. Use when asked to research a company, person, technology, or topic — or when a bare name or UR...
  `Werkstatt\Repos\basic-memory\skills\memory-research\SKILL.md`
- **memory-schema** - Schema lifecycle management for Basic Memory: discover unschemaed notes, infer schemas, create and edit schema definitions, validate notes, and detect drift. Use when working with structured note type...
  `Werkstatt\Repos\basic-memory\skills\memory-schema\SKILL.md`
- **memory-tasks** - Task management via Basic Memory schemas: create, track, and resume structured tasks that survive context compaction. Uses BM's schema system for uniform notes queryable through the knowledge graph.
  `Werkstatt\Repos\basic-memory\skills\memory-tasks\SKILL.md`
- **pr-create** - Use when explicitly creating or updating a Basic Memory pull request. This compatibility entry point delegates the full workflow to pull-request and the latest-head Codex gate to pr-review-loop.
  `Werkstatt\Repos\basic-memory\.agents\skills\pr-create\SKILL.md`
- **pr-description** - Use when opening or updating a GitHub PR - writes a detailed PR description that explains what changed, why it changed, how it was implemented, and how it was tested.
  `Werkstatt\Repos\basic-memory\.agents\skills\pr-description\SKILL.md`
- **pr-review-loop** - Enforce the Basic Machines GitHub PR review loop before merging. Use whenever Codex is preparing to merge, squash-merge, auto-merge, declare a PR ready, monitor Codex comments, address review feedback...
  `Werkstatt\Repos\basic-memory\.agents\skills\pr-review-loop\SKILL.md`
- **pull-request** - Drive GitHub pull request work end to end. Use when Codex is asked to open, update, describe, push to, monitor, review, address comments on, declare ready, or merge a PR. Covers branch hygiene, PR des...
  `Werkstatt\Repos\basic-memory\.agents\skills\pull-request\SKILL.md`
- **pythonic-code** - Write, refactor, and review Python for clarity, explicit behavior, local reasoning, strong types, constructive domain modeling, and minimal abstraction. Use when creating or changing nontrivial Python...
  `Werkstatt\Repos\basic-memory\.agents\skills\pythonic-code\SKILL.md`

## caveman (21)

- **cavecrew** - When to delegate to `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit) or `cavecrew-reviewer` (diff review) instead of working inline or using `Explore`. Their output is compres...
  `Werkstatt\Repos\caveman\skills\cavecrew\SKILL.md`
- **caveman** - Ultra-compressed communication mode that cuts output tokens while keeping technical accuracy. Levels: lite, full, ultra and the wenyan variants. Use for /caveman, "caveman mode", "talk like caveman", ...
  `Werkstatt\Repos\caveman\skills\caveman\SKILL.md`
- **caveman-commit** - Write a Conventional Commits message compressed to intent only. Use for "write a commit", "commit message", /commit or /caveman-commit.
  `Werkstatt\Repos\caveman\skills\caveman-commit\SKILL.md`
- **caveman-compress** - Compress a memory file such as CLAUDE.md or a todo list into caveman format to save input tokens, keeping a readable backup. Trigger: /caveman-compress.
  `Werkstatt\Repos\caveman\skills\caveman-compress\SKILL.md`
- **caveman-discover** - Find and label every LLM workflow in the repository so Caveman Cloud groups spend by workflow instead of one bucket. Use for "discover workflows" or breaking LLM spend down by workflow.
  `Werkstatt\Repos\caveman\skills\caveman-discover\SKILL.md`
- **caveman-evidence-review** - Read-only review of Caveman Cloud evidence: cost, Cave Score, workflows, traces, latency, errors, routing, savings. Use when asked what Caveman found or where LLM spend goes.
  `Werkstatt\Repos\caveman\skills\caveman-evidence-review\SKILL.md`
- **caveman-explore** - Read-only repository explorer for cold-start orientation, broad cross-file localization, or when a direct search failed. Skip it when the exact file or symbol is already named. Returns path:line citat...
  `Werkstatt\Repos\caveman\skills\caveman-explore\SKILL.md`
- **caveman-help** - Quick-reference card for caveman modes, skills and commands. Trigger: /caveman-help or "caveman help".
  `Werkstatt\Repos\caveman\skills\caveman-help\SKILL.md`
- **caveman-learn** - Act on a Caveman learn report - review the ranked token sinks, apply cost-lowering fixes with per-edit consent, and report what those fixes returned. Use when asked to lower an agent's token cost, wha...
  `Werkstatt\Repos\caveman\skills\caveman-learn\SKILL.md`
- **caveman-manage** - Inspect Caveman Cloud's experiment lifecycle and block unsafe execution. Use when asked to start, approve, cancel, promote or roll back a Caveman experiment.
  `Werkstatt\Repos\caveman\skills\caveman-manage\SKILL.md`
- **caveman-optimize** - Turn a Caveman optimization observation into an operator-chosen candidate with a paired baseline evaluation. Use when asked to inspect or evaluate a Caveman optimization report. Needs explicit approva...
  `Werkstatt\Repos\caveman\skills\caveman-optimize\SKILL.md`
- **caveman-review** - Compressed code review - one line per finding with location, problem and fix. Use for /caveman-review, "review this PR", or "review the diff".
  `Werkstatt\Repos\caveman\skills\caveman-review\SKILL.md`
- **caveman-setup** - Wire a repository through the Caveman Cloud gateway so every LLM request is measured, with no behavior change. Use for "set up caveman" or adding LLM spend observability.
  `Werkstatt\Repos\caveman\skills\caveman-setup\SKILL.md`
- **caveman-stats** - Show real token usage and estimated savings for the current session. Reads directly from the Claude Code session log — no AI estimation. Triggers on /caveman-stats. Output is injected by the mode-trac...
  `Werkstatt\Repos\caveman\plugins\caveman\skills\caveman-stats\SKILL.md`
- **caveman-stats** - Show real token usage and estimated savings for the current session, read from the session log. Trigger: /caveman-stats.
  `Werkstatt\Repos\caveman\skills\caveman-stats\SKILL.md`
- **investigate-first** - Diagnose ambiguous failures before editing. Use for unknown causes, intermittent behavior, performance regressions, or investigations needing evidence-ranked hypotheses.
  `Werkstatt\Repos\caveman\skills\investigate-first\SKILL.md`
- **lean-build** - Build feature work with high overbuilding risk. Use for new behavior, product slices, or integrations where repository reuse, strict scope, and an explicit stop condition matter.
  `Werkstatt\Repos\caveman\skills\lean-build\SKILL.md`
- **migration** - Implement reversible compatibility-safe transitions. Use for schema, data, API, protocol, configuration, or dependency migrations requiring rollback and preservation proof.
  `Werkstatt\Repos\caveman\skills\migration\SKILL.md`
- **safe-refactor** - Restructure code while preserving behavior. Use for extraction, consolidation, ownership moves, or cleanup where verification must bracket structural edits.
  `Werkstatt\Repos\caveman\skills\safe-refactor\SKILL.md`
- **surgical-patch** - Fix bugs and small behavior changes at the narrowest responsible layer. Use when regression proof, preserved surrounding behavior, and task-relevant tests matter.
  `Werkstatt\Repos\caveman\skills\surgical-patch\SKILL.md`
- **verify-and-stop** - Prove existing work meets acceptance conditions without expanding scope. Use for validation-only tasks, completion checks, focused gate runs, and last-mile proof.
  `Werkstatt\Repos\caveman\skills\verify-and-stop\SKILL.md`

## claude-code (10)

- **Agent Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\agent-development\SKILL.md`
- **claude-opus-4-5-migration** *(auch im Fundus)* - Migrate prompts and code from Claude Sonnet 4.0, Sonnet 4.5, or Opus 4.1 to Opus 4.5. Use when the user wants to update their codebase, prompts, or API calls to use Opus 4.5. Handles model string upda...
  `Werkstatt\Repos\claude-code\plugins\claude-opus-4-5-migration\skills\claude-opus-4-5-migration\SKILL.md`
- **Command Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\command-development\SKILL.md`
- **frontend-design** *(auch im Fundus)* - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `Werkstatt\Repos\claude-code\plugins\frontend-design\skills\frontend-design\SKILL.md`
- **Hook Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\hook-development\SKILL.md`
- **MCP Integration** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\mcp-integration\SKILL.md`
- **Plugin Settings** *(auch im Fundus)* - This skill should be used when the user asks about
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\plugin-settings\SKILL.md`
- **Plugin Structure** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\plugin-structure\SKILL.md`
- **Skill Development** *(auch im Fundus)* - This skill should be used when the user wants to
  `Werkstatt\Repos\claude-code\plugins\plugin-dev\skills\skill-development\SKILL.md`
- **Writing Hookify Rules** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-code\plugins\hookify\skills\writing-rules\SKILL.md`

## claude-plugins-official (30)

- **access** *(auch im Fundus)* - Manage Discord channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the Discord channel.
  `Werkstatt\Repos\claude-plugins-official\external_plugins\discord\skills\access\SKILL.md`
- **access** - Manage Telegram channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the Telegram channel...
  `Werkstatt\Repos\claude-plugins-official\external_plugins\telegram\skills\access\SKILL.md`
- **access** *(auch im Fundus)* - Manage iMessage channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the iMessage channel...
  `Werkstatt\Repos\claude-plugins-official\external_plugins\imessage\skills\access\SKILL.md`
- **agent-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\agent-development\SKILL.md`
- **build-mcp-app** *(auch im Fundus)* - This skill should be used when the user wants to build an
  `Werkstatt\Repos\claude-plugins-official\plugins\mcp-server-dev\skills\build-mcp-app\SKILL.md`
- **build-mcpb** *(auch im Fundus)* - This skill should be used when the user wants to
  `Werkstatt\Repos\claude-plugins-official\plugins\mcp-server-dev\skills\build-mcpb\SKILL.md`
- **build-mcp-server** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\mcp-server-dev\skills\build-mcp-server\SKILL.md`
- **cardputer-buddy** *(auch im Fundus)* - Iterate on the Cardputer-Adv MicroPython app bundle (Claude Buddy, Snake, Hello) after the device is already provisioned via m5-onboard. Use when the user wants to add a new app, push a single changed...
  `Werkstatt\Repos\claude-plugins-official\plugins\cwc-makers\skills\cardputer-buddy\SKILL.md`
- **claude-automation-recommender** *(auch im Fundus)* - Analyze a codebase and recommend Claude Code automations (hooks, subagents, skills, plugins, MCP servers). Use when user asks for automation recommendations, wants to optimize their Claude Code setup,...
  `Werkstatt\Repos\claude-plugins-official\plugins\claude-code-setup\skills\claude-automation-recommender\SKILL.md`
- **claude-md-improver** *(auch im Fundus)* - Audit and improve CLAUDE.md files in repositories. Use when user asks to check, audit, update, improve, or fix CLAUDE.md files. Scans for all CLAUDE.md files, evaluates quality against templates, outp...
  `Werkstatt\Repos\claude-plugins-official\plugins\claude-md-management\skills\claude-md-improver\SKILL.md`
- **claude-security** - The Claude Security menu — pick a job: scan the codebase (the whole repository or a scoped part of it), scan changes (this branch's or a pull request's diff, or one commit), or suggest patches (findin...
  `Werkstatt\Repos\claude-plugins-official\plugins\claude-security\skills\claude-security\SKILL.md`
- **command-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\command-development\SKILL.md`
- **configure** *(auch im Fundus)* - Set up the Discord channel — save the bot token and review access policy. Use when the user pastes a Discord bot token, asks to configure Discord, asks
  `Werkstatt\Repos\claude-plugins-official\external_plugins\discord\skills\configure\SKILL.md`
- **configure** - Set up the Telegram channel — save the bot token and review access policy. Use when the user pastes a Telegram bot token, asks to configure Telegram, asks
  `Werkstatt\Repos\claude-plugins-official\external_plugins\telegram\skills\configure\SKILL.md`
- **configure** *(auch im Fundus)* - Check iMessage channel setup and review access policy. Use when the user asks to configure iMessage, asks
  `Werkstatt\Repos\claude-plugins-official\external_plugins\imessage\skills\configure\SKILL.md`
- **example-command** *(auch im Fundus)* - An example user-invoked skill that demonstrates frontmatter options and the skills/<name>/SKILL.md layout
  `Werkstatt\Repos\claude-plugins-official\plugins\example-plugin\skills\example-command\SKILL.md`
- **example-skill** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\example-plugin\skills\example-skill\SKILL.md`
- **frontend-design** - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `Werkstatt\Repos\claude-plugins-official\plugins\frontend-design\skills\frontend-design\SKILL.md`
- **hook-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\hook-development\SKILL.md`
- **m5-onboard** *(auch im Fundus)* - End-to-end onboarding for a freshly-plugged-in M5Stack ESP32 device (Cardputer, Cardputer-Adv, Core, CoreS3, Stick) — detect on USB, flash UIFlow 2.0 firmware, and install the Claude Buddy MicroPython...
  `Werkstatt\Repos\claude-plugins-official\plugins\cwc-makers\skills\m5-onboard\SKILL.md`
- **math-olympiad** *(auch im Fundus)* - Solve competition math problems (IMO, Putnam, USAMO, AIME) with adversarial
  `Werkstatt\Repos\claude-plugins-official\plugins\math-olympiad\skills\math-olympiad\SKILL.md`
- **mcp-integration** - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\mcp-integration\SKILL.md`
- **playground** *(auch im Fundus)* - Creates interactive HTML playgrounds — self-contained single-file explorers that let users configure something visually through controls, see a live preview, and copy out a prompt. Use when the user a...
  `Werkstatt\Repos\claude-plugins-official\plugins\playground\skills\playground\SKILL.md`
- **plugin-settings** *(auch im Fundus)* - This skill should be used when the user asks about
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\plugin-settings\SKILL.md`
- **plugin-structure** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\plugin-structure\SKILL.md`
- **project-artifact** - Generate and publish a project status artifact — an opinionated, tabbed status page for a project too big for one update (overview & success criteria, the workstream sequence, next steps, plus backgro...
  `Werkstatt\Repos\claude-plugins-official\plugins\project-artifact\skills\project-artifact\SKILL.md`
- **receipts** *(auch im Fundus)* - Generate a personal Claude Code usage & impact report (
  `Werkstatt\Repos\claude-plugins-official\plugins\receipts\skills\receipts\SKILL.md`
- **session-report** *(auch im Fundus)* - Generate an explorable HTML report of Claude Code session usage (tokens, cache, subagents, skills, expensive prompts) from ~/.claude/projects transcripts.
  `Werkstatt\Repos\claude-plugins-official\plugins\session-report\skills\session-report\SKILL.md`
- **skill-development** *(auch im Fundus)* - This skill should be used when the user wants to
  `Werkstatt\Repos\claude-plugins-official\plugins\plugin-dev\skills\skill-development\SKILL.md`
- **writing-hookify-rules** *(auch im Fundus)* - This skill should be used when the user asks to
  `Werkstatt\Repos\claude-plugins-official\plugins\hookify\skills\writing-rules\SKILL.md`

## codex (17)

- **babysit-pr** - Babysit a GitHub pull request after creation by continuously polling review comments, CI checks/workflow runs, and mergeability state until the PR is merged/closed or user help is required. Diagnose f...
  `Werkstatt\Repos\codex\.codex\skills\babysit-pr\SKILL.md`
- **code-breaking-changes** - Breaking changes
  `Werkstatt\Repos\codex\.codex\skills\code-review-breaking-changes\SKILL.md`
- **code-review** - Run a final code review on a pull request
  `Werkstatt\Repos\codex\.codex\skills\code-review\SKILL.md`
- **code-review-change-size** - Change size guidance (800 lines)
  `Werkstatt\Repos\codex\.codex\skills\code-review-change-size\SKILL.md`
- **code-review-context** - Model visible context
  `Werkstatt\Repos\codex\.codex\skills\code-review-context\SKILL.md`
- **code-review-testing** - Test authoring guidance
  `Werkstatt\Repos\codex\.codex\skills\code-review-testing\SKILL.md`
- **codex-pr-body** - Update the title and body of one or more pull requests.
  `Werkstatt\Repos\codex\.codex\skills\codex-pr-body\SKILL.md`
- **imagegen** - Generate or edit raster images when the task benefits from AI-created bitmap visuals such as photos, illustrations, textures, sprites, mockups, or transparent-background cutouts. Use when Codex should...
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\imagegen\SKILL.md`
- **openai-docs** - Use for Codex models/pricing, scheduled tasks, skills, settings, setup, troubleshooting, customization, automations, and self-knowledge—including 'you,' 'your,' 'this app,' or 'this coding agent' when...
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\openai-docs\SKILL.md`
- **path-types** - Choose Rust types for operating system paths across the Codex repository. Use when defining new path-bearing types or explicitly migrating existing ones.
  `Werkstatt\Repos\codex\.codex\skills\path-types\SKILL.md`
- **plugin-creator** - Create and scaffold plugin directories for Codex with a required `.codex-plugin/plugin.json`, optional plugin folders/files, valid manifest defaults, and personal-marketplace entries by default. Use w...
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\plugin-creator\SKILL.md`
- **remote-tests** - Testing against remote executors in integration tests.
  `Werkstatt\Repos\codex\.codex\skills\remote-tests\SKILL.md`
- **review-agent** - Perform a read-only, defect-first review of a specified code change and return every actionable finding. Use when another agent delegates review of uncommitted changes, a base-branch diff, a commit, o...
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\review-agent\SKILL.md`
- **skill-creator** - Create or update a Codex skill with appropriately scoped instructions and any needed supporting resources.
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\skill-creator\SKILL.md`
- **skill-installer** - Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (...
  `Werkstatt\Repos\codex\codex-rs\skills\src\assets\samples\skill-installer\SKILL.md`
- **test-tui** - Guide for testing Codex TUI interactively
  `Werkstatt\Repos\codex\.codex\skills\test-tui\SKILL.md`
- **update-v8-version** - Update Codex's pinned `v8` / `rusty_v8` versions, validate the release-candidate path, and investigate failed V8 canary or artifact builds. Use when asked to bump V8, update `rusty_v8` artifacts, prep...
  `Werkstatt\Repos\codex\.codex\skills\update-v8-version\SKILL.md`

## copilot-worktrees (1)

- **frontend-design** - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `Werkstatt\Repos\copilot-worktrees\claude-code\mfaupel95-silver-bassoon\plugins\frontend-design\skills\frontend-design\SKILL.md`

## deepseek-harness (17)

- **cordis-plugin-development** - Create, modify, debug, or extend dynamic Cordis Plugins, including Host Services and Events, Client Slot and theme UI, Package-private Client-to-Host calls, dynamic Tools, version updates, approval fa...
  `Werkstatt\Repos\deepseek-harness\packages\preset\agent-presets\presets\cordis\skills\cordis-plugin-development\SKILL.md`
- **dsh-archive-agent-notes** - Use when adding, auditing, pruning, archiving, restoring, or reviewing Agent Notes in deepseek-harness; checks every new note for superseded active records, classifies implemented notes by future deci...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-archive-agent-notes\SKILL.md`
- **dsh-ci-test-reliability** - Design, review, and diagnose DeepSeek Harness tests and fixtures that can fail nondeterministically under CI concurrency, shared host resources, clocks, process-global state, subprocesses, network lis...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-ci-test-reliability\SKILL.md`
- **dsh-code-review** - Use when reviewing a pull request in the deepseek-harness repo — orients the reviewer to this codebase's standards (AGENTS.md conventions, defensive patterns, ADRs, quality gates) and the review-speci...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-code-review\SKILL.md`
- **dsh-doc** - Create, restructure, review, audit, or migrate DeepSeek Harness Markdown documentation, package READMEs, and the documentation website using audience-first hierarchy, kind-mapped YAML metadata, biling...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-doc\SKILL.md`
- **dsh-find-simplifications** - 'Use when working in the deepseek-harness repo to find non-obvious simplification candidates, remove redundant comments or implementation-heavy documentation, write proposed Agent Notes or inline TODO...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-find-simplifications\SKILL.md`
- **dsh-merging-stacked-prs** - Use when landing a stack of dependent GitHub PRs (A ← B ← C, where each bases on the one below) onto master, merging a PR whose base is another open PR's branch, or whenever a request mentions
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-merging-stacked-prs\SKILL.md`
- **dsh-pre-push-checks** - Use before pushing, force-pushing, marking ready for review, or claiming checks pass on a deepseek-harness branch, and immediately after gh stack sync publishes rewritten branches, to select the small...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-pre-push-checks\SKILL.md`
- **dsh-prose-standard** - Use when writing, reviewing, restoring, trimming, or auditing prose in the deepseek-harness repo, including deciding where documentation or comments are required across Markdown, JSDoc, code and test ...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-prose-standard\SKILL.md`
- **dsh-translate-docs** - Manually run the extended DeepSeek Harness bilingual-document workflow, including generated briefings, delegated prose translation, whole-document translation, and scoped pairing verification.
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-translate-docs\SKILL.md`
- **dsh-trim-cot-leakage** - Use when auditing or fixing prose that reads like a leaked reasoning transcript — dead design-session citations such as (decision N), audit item codes, or §N of uncommitted drafts; change narration su...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\dsh-trim-cot-leakage\SKILL.md`
- **editing-cordis-compositions** - Use when creating, changing, or validating a Cordis composition for this harness — writing or editing an agent preset, adding or removing a plugin row, deciding whether something belongs to the host c...
  `Werkstatt\Repos\deepseek-harness\packages\preset\agent-presets\presets\cordis\skills\editing-cordis-compositions\SKILL.md`
- **model-only-skill** - Prove user-disabled skills remain available to the model.
  `Werkstatt\Repos\deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\model-only-skill\SKILL.md`
- **preview-tour** - Inspect the bundled Preview workspace and its deterministic Session examples.
  `Werkstatt\Repos\deepseek-harness\packages\experimental\webworker-runtime\tests\fixtures\vfs-example\workspace\.agents\skills\preview-tour\SKILL.md`
- **record-browser-gif** - Record browser or Web UI interaction demos as optimized GIFs using the available built-in browser, state-based frame capture, and deterministic encoding, then attach the GIF to a pull request with `gh...
  `Werkstatt\Repos\deepseek-harness\.agents\skills\record-browser-gif\SKILL.md`
- **snapshot-skill** - Exercise project skill discovery and loading in snapshot tests.
  `Werkstatt\Repos\deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\snapshot-skill\SKILL.md`
- **user-only-skill** - Prove model-disabled skills stay outside the model catalog.
  `Werkstatt\Repos\deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\user-only-skill\SKILL.md`

## everything-claude-code (11)

- **backend-patterns** - Backend architecture patterns, API design, database optimization, and server-side best practices for Node.js, Express, and Next.js API routes.
  `Werkstatt\Repos\everything-claude-code\skills\backend-patterns\SKILL.md`
- **clickhouse-io** - ClickHouse database patterns, query optimization, analytics, and data engineering best practices for high-performance analytical workloads.
  `Werkstatt\Repos\everything-claude-code\skills\clickhouse-io\SKILL.md`
- **coding-standards** - Universal coding standards, best practices, and patterns for TypeScript, JavaScript, React, and Node.js development.
  `Werkstatt\Repos\everything-claude-code\skills\coding-standards\SKILL.md`
- **continuous-learning** - Automatically extract reusable patterns from Claude Code sessions and save them as learned skills for future use.
  `Werkstatt\Repos\everything-claude-code\skills\continuous-learning\SKILL.md`
- **eval-harness**
  `Werkstatt\Repos\everything-claude-code\skills\eval-harness\SKILL.md`
- **frontend-patterns** - Frontend development patterns for React, Next.js, state management, performance optimization, and UI best practices.
  `Werkstatt\Repos\everything-claude-code\skills\frontend-patterns\SKILL.md`
- **project-guidelines-example**
  `Werkstatt\Repos\everything-claude-code\skills\project-guidelines-example\SKILL.md`
- **security-review** - Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive features. Provides comprehensive security checklist and ...
  `Werkstatt\Repos\everything-claude-code\skills\security-review\SKILL.md`
- **strategic-compact** - Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction.
  `Werkstatt\Repos\everything-claude-code\skills\strategic-compact\SKILL.md`
- **tdd-workflow** - Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with 80%+ coverage including unit, integration, and E2E tests.
  `Werkstatt\Repos\everything-claude-code\skills\tdd-workflow\SKILL.md`
- **verification-loop**
  `Werkstatt\Repos\everything-claude-code\skills\verification-loop\SKILL.md`

## gbrain (93)

- **academic-verify** - Verify a research claim or academic citation by tracing it through publication → methodology → raw data → independent replication. Routes through perplexity-research for the actual web lookup, then fo...
  `Werkstatt\Repos\gbrain\skills\academic-verify\SKILL.md`
- **adversary-tracking**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\adversary-tracking\SKILL.md`
- **archive-crawler** - Universal archivist for personal file archives (Dropbox/B2/Gmail-takeout/local-mount/hard-drive-dump). Filters for high-value content (the user's own writing, ideas, relationships) and surfaces it int...
  `Werkstatt\Repos\gbrain\skills\archive-crawler\SKILL.md`
- **article-enrichment** - Transform raw article text dumps in the brain into structured pages with executive summary, verbatim quotes, key insights, why-it-matters, and cross-references. Replaces walls-of-text with quotable, a...
  `Werkstatt\Repos\gbrain\skills\article-enrichment\SKILL.md`
- **ask-user** - Reusable pattern for presenting the user with explicit choices and gating execution until they respond. Used by other skills when a decision point requires human input before proceeding. Platform-agno...
  `Werkstatt\Repos\gbrain\skills\ask-user\SKILL.md`
- **book-mirror** - Take any book (EPUB/PDF), produce a personalized chapter-by-chapter analysis with two-column tables. Left column preserves the chapter content; right column maps every idea to the reader's actual life...
  `Werkstatt\Repos\gbrain\skills\book-mirror\SKILL.md`
- **book-mirror**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\book-mirror\SKILL.md`
- **brain-ops** - Core read/write cycle for the OpenClaw reference fixture.
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-reference-minimal\skills\brain-ops\SKILL.md`
- **brain-ops** - Brain knowledge base operations. The core read/write cycle: brain-first lookup, read-enrich-write loop, source attribution, ambient enrichment, back-linking. Read this before any brain interaction.
  `Werkstatt\Repos\gbrain\skills\brain-ops\SKILL.md`
- **brain-ops** - Read, enrich, and write brain pages with source attribution.
  `Werkstatt\Repos\gbrain\test\fixtures\skill-catalog\skills\brain-ops\SKILL.md`
- **brain-pdf** - Generate a publication-quality PDF from any brain page via the gstack make-pdf binary. Strips YAML frontmatter, sanitizes emoji, applies running headers and page numbers. Brain page is always the sour...
  `Werkstatt\Repos\gbrain\skills\brain-pdf\SKILL.md`
- **brain-search**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\brain-search\SKILL.md`
- **brain-taxonomist** - Filing gate for ALL brain writes. Consulted before creating any new brain page to determine the correct path. Reads the ACTIVE schema pack via `gbrain schema show --json` — no hardcoded directory tabl...
  `Werkstatt\Repos\gbrain\skills\brain-taxonomist\SKILL.md`
- **briefing** - Compile daily briefing with meeting context, active deals, and citation tracking
  `Werkstatt\Repos\gbrain\skills\briefing\SKILL.md`
- **briefing**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\briefing\SKILL.md`
- **broken**
  `Werkstatt\Repos\gbrain\test\fixtures\skill-catalog\skills\broken\SKILL.md`
- **calendar-prep**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\calendar-prep\SKILL.md`
- **capture** - Save any thought or content into the brain via one CLI command. The single human-facing entrypoint that replaces
  `Werkstatt\Repos\gbrain\skills\capture\SKILL.md`
- **citation-fixer** - Audit and fix citation formatting across brain pages. Ensures every fact has an inline [Source: ...] citation matching the standard format. Extended in v0.25.1: scans for broken tweet/post references ...
  `Werkstatt\Repos\gbrain\skills\citation-fixer\SKILL.md`
- **civic-intelligence**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\civic-intelligence\SKILL.md`
- **cold-start** - Day-one data bootstrapping for a new brain. Sequences the highest-leverage data sources to go from empty brain to useful brain in one session. Uses ClawVisor for safe credential handling — the agent n...
  `Werkstatt\Repos\gbrain\skills\cold-start\SKILL.md`
- **compliant-callout** - External-lookup skill with canonical Convention callout
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\compliant-callout\SKILL.md`
- **compliant-phase** - External-lookup skill with explicit Phase 1 brain heading
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\compliant-phase\SKILL.md`
- **compliant-position** - Skill that runs gbrain search before external lookup
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\compliant-position\SKILL.md`
- **concept-synthesis** - Deduplicate and synthesize raw concept stubs into a tiered intellectual map (T1 Canon to T4 Riff), tracing idea evolution across sources over time. Transforms thousands of raw concept pages into a cur...
  `Werkstatt\Repos\gbrain\skills\concept-synthesis\SKILL.md`
- **content-creation**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\content-creation\SKILL.md`
- **context-now** - ALWAYS-ON time-sensitivity discipline for the OpenClaw reference fixture.
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-reference-minimal\skills\context-now\SKILL.md`
- **cron-scheduler** - Schedule management with staggering, quiet hours, and wake-up override. Validates schedules, prevents collisions, and gates delivery during quiet hours.
  `Werkstatt\Repos\gbrain\skills\cron-scheduler\SKILL.md`
- **cross-modal-review** - Quality gate via second model. Spawn a different AI model to review work before committing. Includes refusal routing: if one model refuses, switch silently to the next. Extended in v0.25.1 with struct...
  `Werkstatt\Repos\gbrain\skills\cross-modal-review\SKILL.md`
- **daily-digest**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\daily-digest\SKILL.md`
- **daily-task-manager** - Task lifecycle management. Add, complete, defer, remove, and review tasks. Maintains a running task list as a brain page.
  `Werkstatt\Repos\gbrain\skills\daily-task-manager\SKILL.md`
- **daily-task-prep** - Morning preparation. Calendar lookahead, meeting context loading, open threads from yesterday, active task review. Extends briefing with actionable prep.
  `Werkstatt\Repos\gbrain\skills\daily-task-prep\SKILL.md`
- **data-research** - Structured data research: search sources, extract structured data, archive raw sources, maintain canonical tracker pages, deduplicate. Parameterized via YAML recipes for investor updates, donations, c...
  `Werkstatt\Repos\gbrain\skills\data-research\SKILL.md`
- **eiirp** - Everything In Its Right Place. The universal post-work organizer. After any significant work session, EIIRP runs a 7-phase audit: (1) inventory every output, (2) walk taxonomy to decide where each lan...
  `Werkstatt\Repos\gbrain\skills\eiirp\SKILL.md`
- **email-triage**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\email-triage\SKILL.md`
- **enrich**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\enrich\SKILL.md`
- **enrich** - Enrich brain pages with tiered enrichment protocol. Creates and updates person/company pages with compiled truth, timeline, and cross-links. Use when a new entity is mentioned or an existing page need...
  `Werkstatt\Repos\gbrain\skills\enrich\SKILL.md`
- **executive-assistant**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\executive-assistant\SKILL.md`
- **exempt-frontmatter** - Pure-infra skill that opts out via frontmatter
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\exempt-frontmatter\SKILL.md`
- **flight-tracker**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\flight-tracker\SKILL.md`
- **frontmatter-guard** - Validate and auto-repair YAML frontmatter on brain pages. Catches malformed pages before they enter the brain (missing closing ---, nested quotes, slug mismatches, null bytes, empty frontmatter, YAML ...
  `Werkstatt\Repos\gbrain\skills\frontmatter-guard\SKILL.md`
- **functional-area-resolver** - Compress an agent's routing file (RESOLVER.md or AGENTS.md) by converting granular skill-per-row tables into functional-area dispatchers. Each area lists sub-skills in a "(dispatcher for: ...)" clause...
  `Werkstatt\Repos\gbrain\skills\functional-area-resolver\SKILL.md`
- **gbrain** - Search and write the company knowledge brain. Use for any question about the org, people, projects, decisions, or history, and to persist durable knowledge beyond this scope's notebook.
  `Werkstatt\Repos\gbrain\docs\integrations\qm-harness-snippets\SKILL.md`
- **gbrain-advisor** - Proactive "make the most of gbrain" coaching. Runs `gbrain advisor` on a cadence and pings the user with the top high-leverage actions for their brain: version drift, pending migrations, stalled jobs,...
  `Werkstatt\Repos\gbrain\skills\gbrain-advisor\SKILL.md`
- **gbrain-upgrade** - Keep gbrain current. When a `gbrain` invocation prints an `UPGRADE_AVAILABLE <old> <new>` marker (or `gbrain self-upgrade --check-only` reports an update), apply it per the configured self_upgrade.mod...
  `Werkstatt\Repos\gbrain\skills\gbrain-upgrade\SKILL.md`
- **gift-advisor**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\gift-advisor\SKILL.md`
- **idea-ingest** - Ingest links, articles, tweets, and ideas into the brain. Fetch content, save to brain with analysis, create author people page, and cross-link. Use when the user shares a link or says "read this", "s...
  `Werkstatt\Repos\gbrain\skills\idea-ingest\SKILL.md`
- **idea-lineage** - Trace one idea's evolution through the brain: first mention, best articulation, related concepts, reversals, contradictions, abandoned branches, and the current live version. Use for single-idea conce...
  `Werkstatt\Repos\gbrain\skills\idea-lineage\SKILL.md`
- **ingest** - Route content to specialized ingestion skills. Detects input type and delegates.
  `Werkstatt\Repos\gbrain\skills\ingest\SKILL.md`
- **install**
  `Werkstatt\Repos\gbrain\skills\install\SKILL.md`
- **investor-update-ingest**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\investor-update-ingest\SKILL.md`
- **maintain** - Brain health checks: back-link enforcement, citation audit, filing validation, stale info detection, orphan pages, and benchmarks. Use when asked to check brain health, run maintenance, or audit quali...
  `Werkstatt\Repos\gbrain\skills\maintain\SKILL.md`
- **media-ingest** - Ingest video, audio, PDF, book, screenshot, and GitHub repo content into the brain. Multi-format handling with entity extraction and backlink propagation. Covers video-ingest, youtube-ingest, and book...
  `Werkstatt\Repos\gbrain\skills\media-ingest\SKILL.md`
- **meeting-ingestion** - Ingest meeting transcripts into brain pages with attendee enrichment, entity propagation, and timeline merge. A meeting is NOT fully ingested until the enrich skill has processed every entity.
  `Werkstatt\Repos\gbrain\skills\meeting-ingestion\SKILL.md`
- **meeting-prep**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-compact-resolver\skills\meeting-prep\SKILL.md`
- **migrate**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\migrate\SKILL.md`
- **migrate** - Universal migration from Obsidian, Notion, Logseq, markdown, CSV, JSON, Roam
  `Werkstatt\Repos\gbrain\skills\migrate\SKILL.md`
- **minion-orchestrator** - Unified Minions skill for both deterministic shell jobs and LLM subagent orchestration. Replaces the older `gbrain-jobs` routing intent. Use when: submitting gbrain jobs, shell/background tasks, spawn...
  `Werkstatt\Repos\gbrain\skills\minion-orchestrator\SKILL.md`
- **missing-brain-first** - External-lookup skill with NO brain-first compliance
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\missing-brain-first\SKILL.md`
- **multi-pattern** - Skill that uses multiple external tools without compliance
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\multi-pattern\SKILL.md`
- **negation-prose** - Skill where brain reference precedes a negation-prose mention
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\negation-prose\SKILL.md`
- **no-external** - Skill that operates purely on local state
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\no-external\SKILL.md`
- **perplexity-research** - Brain-augmented web research. Sends brain context about a topic to Perplexity, which searches the web with citations and returns what is NEW vs what the brain already knows. Use for entity enrichment,...
  `Werkstatt\Repos\gbrain\skills\perplexity-research\SKILL.md`
- **publish** - Share brain pages as beautiful password-protected HTML with zero LLM calls
  `Werkstatt\Repos\gbrain\skills\publish\SKILL.md`
- **query** - Answer questions using the brain's knowledge with 3-layer search, synthesis, and citation propagation. Use when the user asks a question, wants a lookup, or needs information from the brain.
  `Werkstatt\Repos\gbrain\skills\query\SKILL.md`
- **query** - Look up brain pages in the OpenClaw reference fixture.
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-reference-minimal\skills\query\SKILL.md`
- **query**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\query\SKILL.md`
- **query-helper**
  `Werkstatt\Repos\gbrain\test\fixtures\skill-catalog\skills\query-helper\SKILL.md`
- **reference-pack** - Reference skill demonstrating the 10/10 skillpack contract. Adds a
  `Werkstatt\Repos\gbrain\examples\skillpack-reference\skills\reference-pack\SKILL.md`
- **repo-architecture** - Where new brain files go. Decision protocol for filing brain pages by primary subject, not by format or source. Reference for all brain-writing skills.
  `Werkstatt\Repos\gbrain\skills\repo-architecture\SKILL.md`
- **reports** - Save and load timestamped reports. Keyword routing for fast lookup. Cron jobs save output as reports; the agent or user queries them by keyword.
  `Werkstatt\Repos\gbrain\skills\reports\SKILL.md`
- **retrieval-reflex** - When/what to retrieve — open the brain page for a salient entity before answering from memory.
  `Werkstatt\Repos\gbrain\recipes\retrieval-reflex\skills\retrieval-reflex\SKILL.md`
- **schema-author** - Evolve your brain's schema pack. Add page types, propose new ones from corpus scans, backfill page.type on existing pages, audit pack health. Triggers when an agent notices untyped pages, custom domai...
  `Werkstatt\Repos\gbrain\skills\schema-author\SKILL.md`
- **schema-unify** - Migrate a brain from gbrain-base (or any pack) to gbrain-base-v2's 14-canonical-type taxonomy via gbrain onboard --check + the unify-types Minion handler. Collapses 94 noisy types to 15 canonical with...
  `Werkstatt\Repos\gbrain\skills\schema-unify\SKILL.md`
- **setup**
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-mixed-merge\skills\setup\SKILL.md`
- **setup** - Set up GBrain with auto-provision Supabase or PGLite, AGENTS.md injection, first import
  `Werkstatt\Repos\gbrain\skills\setup\SKILL.md`
- **signal-detector** - Always-on ambient signal capture for the OpenClaw reference fixture.
  `Werkstatt\Repos\gbrain\test\fixtures\openclaw-reference-minimal\skills\signal-detector\SKILL.md`
- **signal-detector** - Always-on ambient signal capture. Fires on every inbound message to detect original thinking and entity mentions. Spawn as a cheap sub-agent in parallel, never block the main response.
  `Werkstatt\Repos\gbrain\skills\signal-detector\SKILL.md`
- **skill-creator** - Create new skills following the GBrain conformance standard. Generates SKILL.md with frontmatter, Contract, Phases, Output Format, and Anti-Patterns. Checks MECE against existing skills. Updates manif...
  `Werkstatt\Repos\gbrain\skills\skill-creator\SKILL.md`
- **skillify** - The meta skill. Turn any raw feature into a properly-skilled, tested, resolvable unit of agent capability. Cross-modal eval is the recommended Phase 3 quality gate: 3 frontier models from different pr...
  `Werkstatt\Repos\gbrain\skills\skillify\SKILL.md`
- **skill-optimizer** - Self-evolving skill optimization via SkillOpt-paper-grounded text-space optimizer.
  `Werkstatt\Repos\gbrain\skills\skill-optimizer\SKILL.md`
- **skillpack-check** - Run `gbrain skillpack-check` to produce an agent-readable JSON health report for the gbrain install. Wraps `gbrain doctor` + `gbrain apply-migrations --list` so a host agent (your OpenClaw's morning-b...
  `Werkstatt\Repos\gbrain\skills\skillpack-check\SKILL.md`
- **skillpack-harvest** - Lift a proven skill from a host repo (e.g. your OpenClaw fork) back into gbrain's bundle so other clients can scaffold it. Editorial workflow: the CLI does the file copy + privacy lint; this skill dri...
  `Werkstatt\Repos\gbrain\skills\skillpack-harvest\SKILL.md`
- **smoke-test** - Post-restart smoke tests + auto-fix for gbrain and OpenClaw environments. Tests critical services, auto-fixes known issues, extensible via user-defined test scripts in ~/.gbrain/smoke-tests.d/*.sh.
  `Werkstatt\Repos\gbrain\skills\smoke-test\SKILL.md`
- **soul-audit** - 6-phase interactive interview that generates the agent's identity (SOUL.md), user profile (USER.md), access control (ACCESS_POLICY.md), and operational cadence (HEARTBEAT.md). Re-runnable anytime to u...
  `Werkstatt\Repos\gbrain\skills\soul-audit\SKILL.md`
- **strategic-reading** - Read a book, article, transcript, or case study through the lens of a specific strategic problem you're facing. Produces an applied playbook that maps the source onto the problem and gives short/mediu...
  `Werkstatt\Repos\gbrain\skills\strategic-reading\SKILL.md`
- **testing** - Skill validation framework PLUS daily test-suite health and regression intelligence. Validates skill conformance (frontmatter, manifest coverage, resolver coverage). Runs the project test suite in tie...
  `Werkstatt\Repos\gbrain\skills\testing\SKILL.md`
- **typo-frontmatter** - Skill with typo in brain_first declaration
  `Werkstatt\Repos\gbrain\test\fixtures\brain-first-skills\typo-frontmatter\SKILL.md`
- **voice-note-ingest** - Ingest a voice note with exact-phrasing preservation (never paraphrased). Routes content to originals/, concepts/, people/, companies/, ideas/, personal/, or voice-notes/ based on a decision tree. The...
  `Werkstatt\Repos\gbrain\skills\voice-note-ingest\SKILL.md`
- **voice-persona-mars** - Route to Mars (introspective thought partner / demo showman voice persona). Used when the operator wants depth, meaning, or impressive social demos rather than logistics. Mars handles SOLO mode (philo...
  `Werkstatt\Repos\gbrain\recipes\agent-voice\skills\voice-persona-mars\SKILL.md`
- **voice-persona-venus** - Route to Venus (sharp executive-assistant voice persona). Used for logistics — calendar, tasks, recent messages, brain lookups — at sub-second phone-call latency. The default voice persona unless DEFA...
  `Werkstatt\Repos\gbrain\recipes\agent-voice\skills\voice-persona-venus\SKILL.md`
- **voice-post-call** - Post-call handling for a voice session — turn the transcript into a brain page, post the summary to the operator's messaging surface, archive the audio. Belt-and-suspenders: fires both from a tool the...
  `Werkstatt\Repos\gbrain\recipes\agent-voice\skills\voice-post-call\SKILL.md`
- **webhook-transforms** - Generic framework for converting external events (SMS, meetings, social mentions) into brain-ingestible signals. Define a transform function, register a webhook URL, and incoming events get processed ...
  `Werkstatt\Repos\gbrain\skills\webhook-transforms\SKILL.md`

## graphify (1)

- **graphify** - Use for any question about a codebase, its architecture, file relationships, or project content — especially when graphify-out/ exists, where the question should be treated as a graphify query first. ...
  `Werkstatt\Repos\graphify\graphify\skill.md`

## obsidian-skills (5)

- **defuddle** - Extract clean markdown content from web pages using Defuddle CLI, removing clutter and navigation to save tokens. Use instead of WebFetch when the user provides a URL to read or analyze, for online do...
  `Werkstatt\Repos\obsidian-skills\skills\defuddle\SKILL.md`
- **json-canvas** - Create and edit JSON Canvas files (.canvas) with nodes, edges, groups, and connections. Use when working with .canvas files, creating visual canvases, mind maps, flowcharts, or when the user mentions ...
  `Werkstatt\Repos\obsidian-skills\skills\json-canvas\SKILL.md`
- **obsidian-bases** - Create and edit Obsidian Bases (.base files) with views, filters, formulas, and summaries. Use when working with .base files, creating database-like views of notes, or when the user mentions Bases, ta...
  `Werkstatt\Repos\obsidian-skills\skills\obsidian-bases\SKILL.md`
- **obsidian-cli** - Interact with Obsidian vaults using the Obsidian CLI to read, create, search, and manage notes, tasks, properties, and more. Also supports plugin and theme development with commands to reload plugins,...
  `Werkstatt\Repos\obsidian-skills\skills\obsidian-cli\SKILL.md`
- **obsidian-markdown** - Create and edit Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, and other Obsidian-specific syntax. Use when working with .md files in Obsidian, or when the user mentions wiki...
  `Werkstatt\Repos\obsidian-skills\skills\obsidian-markdown\SKILL.md`

## odysseus (2)

- **odysseus** - Use when the user asks Claude Code to read or write Odysseus data (todos, email, calendar, memory, documents) or to launch/monitor/stop a Cookbook model-serve task through the scoped Claude Agent API....
  `Werkstatt\Repos\odysseus\integrations\claude\skills\odysseus\SKILL.md`
- **odysseus** - Use when the user asks Codex to read or write Odysseus data (todos, email, calendar, memory, documents) or to launch/monitor/stop a Cookbook model-serve task through the scoped Codex Agent API. Requir...
  `Werkstatt\Repos\odysseus\integrations\codex\skills\odysseus\SKILL.md`

## one-skill-to-rule-them-all (1)

- **task-observer** *(auch im Fundus)* - Monitors task execution for skill improvement opportunities. Use during ANY multi-step task, agentic workflow, or work session where the agent uses tools and produces deliverables. Captures patterns, ...
  `Werkstatt\Repos\one-skill-to-rule-them-all\SKILL.md`

## ProjectAtlas (2)

- **codex-coding-plugin** - Build, review, or fix ProjectAtlas plugin/runtime installer integration for Codex, Claude Code, and OpenCode, especially version convergence, stale ProjectAtlas cache repair, MCP config generation, sk...
  `Werkstatt\Repos\ProjectAtlas\skills\codex-coding-plugin\SKILL.md`
- **projectatlas** - Use ProjectAtlas as the atlas-first orientation layer before broad source reads, with MCP-first task startup, short-alias worktree registration and routing, safe targeted initialization, ranked naviga...
  `Werkstatt\Repos\ProjectAtlas\plugins\projectatlas\skills\projectatlas\SKILL.md`

## Scrapling (1)

- **scrapling-official** - Scrape web pages using Scrapling with anti-bot bypass (like Cloudflare Turnstile), stealth headless browsing, spiders framework, adaptive scraping, and JavaScript rendering. Use when asked to scrape, ...
  `Werkstatt\Repos\Scrapling\agent-skill\Scrapling-Skill\SKILL.md`

## skills (20)

- **academy-guide** - Stop and check this skill before finishing any reply to a question about how to use Claude or a Claude product — it recommends matching courses, tutorials, and use cases from Claude Academy (academy.c...
  `Werkstatt\Repos\skills\skills\academy-guide\SKILL.md`
- **algorithmic-art** - Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or...
  `Werkstatt\Repos\skills\skills\algorithmic-art\SKILL.md`
- **brand-guidelines** - Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting...
  `Werkstatt\Repos\skills\skills\brand-guidelines\SKILL.md`
- **canvas-design** - Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create ori...
  `Werkstatt\Repos\skills\skills\canvas-design\SKILL.md`
- **claude-api** - Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration. TRIGGER — read BEFORE opening the target file; do...
  `Werkstatt\Repos\skills\skills\claude-api\SKILL.md`
- **discernment-nudge** - After you give a substantive answer or draft that the user may act on — advice or recommendations, drafted artifacts such as goals, plans, pitches, proposals, or emails, estimates or projections, anal...
  `Werkstatt\Repos\skills\skills\discernment-nudge\SKILL.md`
- **doc-coauthoring** - Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This wor...
  `Werkstatt\Repos\skills\skills\doc-coauthoring\SKILL.md`
- **docx** - Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) or Word templates (.dotx files). Triggers include: any mention of 'Word doc', 'word document', ...
  `Werkstatt\Repos\skills\skills\docx\SKILL.md`
- **frontend-design** *(auch im Fundus)* - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `Werkstatt\Repos\skills\skills\frontend-design\SKILL.md`
- **internal-comms** - A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal com...
  `Werkstatt\Repos\skills\skills\internal-comms\SKILL.md`
- **mcp-builder** - Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate externa...
  `Werkstatt\Repos\skills\skills\mcp-builder\SKILL.md`
- **pdf** - Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rota...
  `Werkstatt\Repos\skills\skills\pdf\SKILL.md`
- **pptx** - Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting te...
  `Werkstatt\Repos\skills\skills\pptx\SKILL.md`
- **skill-creator** *(auch im Fundus)* - Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill...
  `Werkstatt\Repos\skills\skills\skill-creator\SKILL.md`
- **slack-gif-creator** - Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like
  `Werkstatt\Repos\skills\skills\slack-gif-creator\SKILL.md`
- **template-skill** - Replace with description of the skill and when Claude should use it.
  `Werkstatt\Repos\skills\template\SKILL.md`
- **theme-factory** - Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact t...
  `Werkstatt\Repos\skills\skills\theme-factory\SKILL.md`
- **webapp-testing** - Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser l...
  `Werkstatt\Repos\skills\skills\webapp-testing\SKILL.md`
- **web-artifacts-builder** - Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state manag...
  `Werkstatt\Repos\skills\skills\web-artifacts-builder\SKILL.md`
- **xlsx** - Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .xltx, .csv, or .tsv file (e....
  `Werkstatt\Repos\skills\skills\xlsx\SKILL.md`

## superpowers (14)

- **brainstorming** - You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.
  `Werkstatt\Repos\superpowers\skills\brainstorming\SKILL.md`
- **dispatching-parallel-agents** - Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
  `Werkstatt\Repos\superpowers\skills\dispatching-parallel-agents\SKILL.md`
- **executing-plans** - Use when you have a written implementation plan to execute in a separate session with review checkpoints
  `Werkstatt\Repos\superpowers\skills\executing-plans\SKILL.md`
- **finishing-a-development-branch** - Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
  `Werkstatt\Repos\superpowers\skills\finishing-a-development-branch\SKILL.md`
- **receiving-code-review** - Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative...
  `Werkstatt\Repos\superpowers\skills\receiving-code-review\SKILL.md`
- **requesting-code-review** - Use when completing tasks, implementing major features, or before merging to verify work meets requirements
  `Werkstatt\Repos\superpowers\skills\requesting-code-review\SKILL.md`
- **subagent-driven-development** - Use when executing implementation plans with independent tasks in the current session
  `Werkstatt\Repos\superpowers\skills\subagent-driven-development\SKILL.md`
- **systematic-debugging** - Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
  `Werkstatt\Repos\superpowers\skills\systematic-debugging\SKILL.md`
- **test-driven-development** - Use when implementing any feature or bugfix, before writing implementation code
  `Werkstatt\Repos\superpowers\skills\test-driven-development\SKILL.md`
- **using-git-worktrees** - Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
  `Werkstatt\Repos\superpowers\skills\using-git-worktrees\SKILL.md`
- **using-superpowers** - Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
  `Werkstatt\Repos\superpowers\skills\using-superpowers\SKILL.md`
- **verification-before-completion** - Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence...
  `Werkstatt\Repos\superpowers\skills\verification-before-completion\SKILL.md`
- **writing-plans** - Use when you have a spec or requirements for a multi-step task, before touching code
  `Werkstatt\Repos\superpowers\skills\writing-plans\SKILL.md`
- **writing-skills** - Use when creating new skills, editing existing skills, or verifying skills work before deployment
  `Werkstatt\Repos\superpowers\skills\writing-skills\SKILL.md`
