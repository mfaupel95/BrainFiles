# Fundus-Index - Werkstatt/Repos

Erzeugt von `Agenten/Werkzeuge/fundus-suche.ps1 -Index`. Nicht von Hand pflegen.

Geklonte Fremd-Repos: **505 eindeutige Skills** in 22 Repos (705 Dateien, 200 byte-identische Kopien zusammengefasst).

Nicht in der Hermes-Bibliothek geladen; Zugriff ueber `Agenten/Werkzeuge/fundus-suche.ps1 -Begriff "<wort>"`.

## Agent-Reach (1)

- **agent-reach** - MUST USE when user wants to 调研/research/搜索/search/查/找/look up anything on the internet — e.g. 全网调研 X / 帮我调研一下 X / 查一下 X / 搜搜 X / 看看大家怎么评价 X / X 上有什么讨论 / research this topic。
  `Agent-Reach\agent_reach\skill\SKILL.md`

## agent-trade-kit (10)

- **earn-hunter** - Automatically monitors OKX Flash Earn, Fixed Earn and Flexible Earn opportunities, sends push notifications, and guides subscription. 自动监控 OKX 闪赚、定期和活期赚币机会，推送通知并引导申购。Use when user says: 有闪赚通知我, 监控赚币, ...
  `agent-trade-kit\skills\earn-hunter\SKILL.md`
- **okx-cex-auth** - Use this skill when the user wants to 'login/log in/sign in', 'authenticate', 'authorize', 'connect OKX account', 'set up credentials', 'first time setup', 'configure okx', '登录', '授权', '认证', '连接账户', '...
  `agent-trade-kit\skills\okx-cex-auth\SKILL.md`
- **okx-cex-bot** - Manage Grid bots (spot/contract/coin-margined) and DCA Martingale bots (Spot DCA 现货马丁 / Contract DCA 合约马丁) on OKX. Covers create, stop, amend, monitor P&L, TP/SL, margin/investment adjustment, and AI-...
  `agent-trade-kit\skills\okx-cex-bot\SKILL.md`
- **okx-cex-earn** - Manages OKX Simple Earn (flexible savings/lending), Flash Earn, On-chain Earn (staking/DeFi), Dual Investment (DCD/双币赢), and AutoEarn (自动赚币) via the okx CLI. Use this skill whenever the user wants to ...
  `agent-trade-kit\skills\okx-cex-earn\SKILL.md`
- **okx-cex-market** - Use this skill when the user asks for: price of any asset, ticker, order book, candles, OHLCV, funding rate, open interest, OI change scanner, market screener (top movers, high-volume, newly listed), ...
  `agent-trade-kit\skills\okx-cex-market\SKILL.md`
- **okx-cex-portfolio** - This skill should be used when the user asks about 'account balance', 'how much USDT do I have', 'my funding account', 'show my positions', 'open positions', 'position P&L', 'unrealized PnL', 'closed ...
  `agent-trade-kit\skills\okx-cex-portfolio\SKILL.md`
- **okx-cex-skill-mp** - Use this skill when the user asks to: 'find a trading skill', 'search for skills', 'install a skill', 'add a skill', 'download a skill', 'browse skill marketplace', 'what skills are available', 'updat...
  `agent-trade-kit\skills\okx-cex-skill-mp\SKILL.md`
- **okx-cex-smartmoney** - Smart Money analytics on OKX: leaderboard traders, position tracking, trade records, closed-position history, aggregated consensus signals, and signal history. Use this skill when the user asks about ...
  `agent-trade-kit\skills\okx-cex-smartmoney\SKILL.md`
- **okx-cex-trade** - Use when the user asks to 'buy BTC', 'sell ETH', 'place a limit order', 'place a market order', 'cancel my order', 'amend my order', 'long BTC perp', 'short ETH swap', 'open a position', 'close a posi...
  `agent-trade-kit\skills\okx-cex-trade\SKILL.md`
- **okx-sentiment-tracker** - Use this skill when the user asks about: 'any crypto news', 'latest news', 'market update', 'daily briefing', 'BTC news', 'ETH news', 'news on SOL', 'search SEC ETF', 'regulation news', 'Bitcoin halvi...
  `agent-trade-kit\skills\okx-sentiment-tracker\SKILL.md`

## basic-memory (49)

- **adversarial-review** - Cross-vendor adversarial code review of the current branch. Two different model families (Claude + Codex/GPT) review the diff independently, then try to refute each other's findings; survivors are rep...
  `basic-memory\.agents\skills\adversarial-review\SKILL.md`
- **basic-memory** - Use the Basic Memory knowledge graph for persistent memory across sessions. Search before answering; capture decisions, meetings, and insights as notes.
  `basic-memory\integrations\hermes\skill\SKILL.md`
- **basic-memory-pi** - Use Basic Memory from Pi for durable continuity. Capture checkpoints with bm_capture, recall prior Pi checkpoints with bm_recall, and consult bundled Basic Memory skill references for note/task struct...
  `basic-memory\integrations\pi\skills\basic-memory-pi\SKILL.md`
- **basic-memory-pi-setup** - Set up Basic Memory for a Pi workspace. Use when Basic Memory is not configured, /bm-status shows no project, recall returns setup guidance, or the user asks to enable durable memory, choose CLI vs MC...
  `basic-memory\integrations\pi\skills\basic-memory-pi-setup\SKILL.md`
- **basic-memory-setup** - Guide Basic Memory setup in Tau. Use when a user wants to install or configure the Tau memory extension, choose a memory destination or capture policy, verify connectivity, or troubleshoot setup. Chec...
  `basic-memory\integrations\tau\skills\basic-memory-setup\SKILL.md`
- **bm-checkpoint** - Create an immutable Codex handoff in Basic Memory and return an exact bm-orient resume command.
  `basic-memory\plugins\codex\skills\bm-checkpoint\SKILL.md`
- **bm-checkpoint** - Save a deliberate work checkpoint to Basic Memory with the story, changed files, verification, decisions, blockers, and the next action. Use when the user asks to checkpoint, wrap up, hand off, or rem...
  `basic-memory\plugins\claude-code\skills\bm-checkpoint\SKILL.md`
- **bm-decide** - Capture a durable engineering decision in Basic Memory with rationale, alternatives, consequences, and affected work.
  `basic-memory\plugins\codex\skills\bm-decide\SKILL.md`
- **bm-decide** - Capture a durable engineering decision in Basic Memory with rationale, alternatives, consequences, and affected work. Use when the user makes or asks to record a real choice —
  `basic-memory\plugins\claude-code\skills\bm-decide\SKILL.md`
- **bm-orient** - Resume from an exact Basic Memory checkpoint or orient Codex from current graph and repository evidence.
  `basic-memory\plugins\codex\skills\bm-orient\SKILL.md`
- **bm-orient** - Orient Claude from Basic Memory before substantial repo work by reading active tasks, open decisions, recent checkpoints, and repo conventions. Use when resuming old work or when the user asks where t...
  `basic-memory\plugins\claude-code\skills\bm-orient\SKILL.md`
- **bm-remember** - Quickly capture a thought, fact, or reminder into Basic Memory as a lightweight note. Use when the user says
  `basic-memory\plugins\claude-code\skills\bm-remember\SKILL.md`
- **bm-remember** - Quickly save a small fact, reminder, or user preference into Basic Memory from Codex without turning it into a full decision or checkpoint.
  `basic-memory\plugins\codex\skills\bm-remember\SKILL.md`
- **bm-setup** - Set up the Basic Memory plugin for this project — a short guided interview that configures the project mapping, seeds note schemas, learns or suggests placement conventions, and enables capture reflex...
  `basic-memory\plugins\claude-code\skills\bm-setup\SKILL.md`
- **bm-setup** - Set up Basic Memory for Codex at user or project level by mapping a Basic Memory project and seeding schemas.
  `basic-memory\plugins\codex\skills\bm-setup\SKILL.md`
- **bm-share** - Share a personal Basic Memory note to a configured team project from Codex with attribution and explicit confirmation.
  `basic-memory\plugins\codex\skills\bm-share\SKILL.md`
- **bm-share** - Promote a note from your personal Basic Memory project to a shared team project, with attribution. Use when the user says
  `basic-memory\plugins\claude-code\skills\bm-share\SKILL.md`
- **bm-status** - Report the Basic Memory for Codex configuration, reachability, hook expectations, recent Codex checkpoints, and active tasks.
  `basic-memory\plugins\codex\skills\bm-status\SKILL.md`
- **bm-status** - Show the Basic Memory plugin's current state for this project — active project, capture folders, output style, recent session checkpoints, and whether Basic Memory is reachable.
  `basic-memory\plugins\claude-code\skills\bm-status\SKILL.md`
- **bm-writing** - Apply the user-customizable writing standard for Basic Memory notes created or substantially revised by Claude. Use with bm-remember, the basic-memory output style's decision captures, and other Basic...
  `basic-memory\plugins\claude-code\skills\bm-writing\SKILL.md`
- **bm-writing** - Apply the user-customizable writing standard for Basic Memory notes created or substantially revised by Codex. Use with bm-checkpoint, bm-decide, bm-remember, and other Basic Memory note-writing workf...
  `basic-memory\plugins\codex\skills\bm-writing\SKILL.md`
- **cmux** - End-user control of cmux topology and routing (windows, workspaces, panes/surfaces, focus, moves, reorder, identify, trigger flash). Use when automation needs deterministic placement and navigation in...
  `basic-memory\.agents\skills\cmux\SKILL.md`
- **cmux-markdown** - Open markdown files in a formatted viewer panel with live reload. Use when you need to display plans, documentation, or notes alongside the terminal with rich rendering (headings, code blocks, tables,...
  `basic-memory\.agents\skills\cmux-markdown\SKILL.md`
- **cmux-settings** - View and edit cmux settings in ~/.config/cmux/cmux.json. Use when the user wants to change cmux preferences (appearance, sidebar, notifications, automation, browser, shortcuts), set a value by JSON pa...
  `basic-memory\.agents\skills\cmux-settings\SKILL.md`
- **cmux-workspace** - Work inside the current cmux workspace and terminal. Use for cmux workspace, current workspace, caller surface, panes, surfaces, socket targeting, and non-interfering cmux automation.
  `basic-memory\.agents\skills\cmux-workspace\SKILL.md`
- **code-review** - Use when reviewing Basic Machines code for house style, architecture risk, pre-merge hardening, or whether a change fits basic-memory/basic-memory-cloud conventions.
  `basic-memory\.agents\skills\code-review\SKILL.md`
- **fix-pr-issues** - Use when addressing Basic Memory pull request feedback, failed checks, or Codex review blockers, then re-running the latest-head review gate.
  `basic-memory\.agents\skills\fix-pr-issues\SKILL.md`
- **infographics** - Use when generating Basic Memory PR, changelog, release, or weekly images from Codex.
  `basic-memory\.agents\skills\infographics\SKILL.md`
- **instrumentation** - Add Pydantic Logfire observability to applications. Use this skill whenever the user asks to
  `basic-memory\.agents\skills\instrumentation\SKILL.md`
- **memory-capture** - Capture the current state of a working thread or conversation into a single coherent Basic Memory note — synthesize where it landed, don't append a log. On re-capture, rewrite the same note in place i...
  `basic-memory\skills\memory-capture\SKILL.md`
- **memory-ci-capture** - Synthesize GitHub delivery context into a concise Basic Memory project update. Use in CI after `bm ci collect` prepares a ProjectUpdateContext; return only structured AgentSynthesis JSON for `bm ci pu...
  `basic-memory\skills\memory-ci-capture\SKILL.md`
- **memory-continue** - Resume prior work by rebuilding context from the Basic Memory knowledge graph — pick up where you left off using memory:// URLs, recent activity, and search. Use when starting a session or when the us...
  `basic-memory\skills\memory-continue\SKILL.md`
- **memory-curate** - Curate the Basic Memory knowledge graph: find orphan notes and suggest links, propose typed relations, merge duplicates, audit tags and folders, and build hub notes. Use to organize, connect, and impr...
  `basic-memory\skills\memory-curate\SKILL.md`
- **memory-defrag** - Defragment and reorganize agent memory files: split bloated files, merge duplicates, remove stale information, and restructure the memory hierarchy. Use when memory files have grown unwieldy, contain ...
  `basic-memory\skills\memory-defrag\SKILL.md`
- **memory-ingest** - Process unstructured external input (meeting transcripts, conversation logs, pasted documents) into structured Basic Memory entities. Extracts entities, searches for existing matches, proposes new ent...
  `basic-memory\skills\memory-ingest\SKILL.md`
- **memory-lifecycle** - Manage entity status transitions in Basic Memory: archive completed work, move notes between status folders, update frontmatter, and handle edge cases. Use when marking items complete, archiving old e...
  `basic-memory\skills\memory-lifecycle\SKILL.md`
- **memory-literary-analysis** - Analyze a complete literary work into a structured Basic Memory knowledge graph. Covers schema design, entity seeding, chapter-by-chapter processing, cross-referencing, validation, and graph explorati...
  `basic-memory\skills\memory-literary-analysis\SKILL.md`
- **memory-metadata-search** - Structured metadata search for Basic Memory: query notes by custom frontmatter fields using equality, range, array, and nested filters. Use when finding notes by status, priority, confidence, or any c...
  `basic-memory\skills\memory-metadata-search\SKILL.md`
- **memory-notes** - How to write well-structured Basic Memory notes: frontmatter, observations with semantic categories, relations with wiki-links, and best practices for building a rich knowledge graph. Use when creatin...
  `basic-memory\skills\memory-notes\SKILL.md`
- **memory-onboarding** - Guide someone new to Basic Memory through designing and building a complete personal knowledge system — interview them about what they want to track, propose a structure, build it with schemas and ins...
  `basic-memory\skills\memory-onboarding\SKILL.md`
- **memory-reflect** - Sleep-time memory reflection: review recent conversations and daily notes, extract insights, and consolidate into long-term memory. Use when triggered by cron, heartbeat, or explicit request to reflec...
  `basic-memory\skills\memory-reflect\SKILL.md`
- **memory-research** - Research an external subject using web search, synthesize findings into a structured Basic Memory entity. Use when asked to research a company, person, technology, or topic — or when a bare name or UR...
  `basic-memory\skills\memory-research\SKILL.md`
- **memory-schema** - Schema lifecycle management for Basic Memory: discover unschemaed notes, infer schemas, create and edit schema definitions, validate notes, and detect drift. Use when working with structured note type...
  `basic-memory\skills\memory-schema\SKILL.md`
- **memory-tasks** - Task management via Basic Memory schemas: create, track, and resume structured tasks that survive context compaction. Uses BM's schema system for uniform notes queryable through the knowledge graph.
  `basic-memory\skills\memory-tasks\SKILL.md`
- **pr-create** - Use when explicitly creating or updating a Basic Memory pull request. This compatibility entry point delegates the full workflow to pull-request and the latest-head Codex gate to pr-review-loop.
  `basic-memory\.agents\skills\pr-create\SKILL.md`
- **pr-description** - Use when opening or updating a GitHub PR - writes a detailed PR description that explains what changed, why it changed, how it was implemented, and how it was tested.
  `basic-memory\.agents\skills\pr-description\SKILL.md`
- **pr-review-loop** - Enforce the Basic Machines GitHub PR review loop before merging. Use whenever Codex is preparing to merge, squash-merge, auto-merge, declare a PR ready, monitor Codex comments, address review feedback...
  `basic-memory\.agents\skills\pr-review-loop\SKILL.md`
- **pull-request** - Drive GitHub pull request work end to end. Use when Codex is asked to open, update, describe, push to, monitor, review, address comments on, declare ready, or merge a PR. Covers branch hygiene, PR des...
  `basic-memory\.agents\skills\pull-request\SKILL.md`
- **pythonic-code** - Write, refactor, and review Python for clarity, explicit behavior, local reasoning, strong types, constructive domain modeling, and minimal abstraction. Use when creating or changing nontrivial Python...
  `basic-memory\.agents\skills\pythonic-code\SKILL.md`

## caveman (21)

- **cavecrew** - When to delegate to `cavecrew-investigator` (locate code), `cavecrew-builder` (1-2 file edit) or `cavecrew-reviewer` (diff review) instead of working inline or using `Explore`. Their output is compres...
  `caveman\skills\cavecrew\SKILL.md`
- **caveman** - Ultra-compressed communication mode that cuts output tokens while keeping technical accuracy. Levels: lite, full, ultra and the wenyan variants. Use for /caveman, "caveman mode", "talk like caveman", ...
  `caveman\skills\caveman\SKILL.md`
- **caveman-commit** - Write a Conventional Commits message compressed to intent only. Use for "write a commit", "commit message", /commit or /caveman-commit.
  `caveman\skills\caveman-commit\SKILL.md`
- **caveman-compress** - Compress a memory file such as CLAUDE.md or a todo list into caveman format to save input tokens, keeping a readable backup. Trigger: /caveman-compress.
  `caveman\skills\caveman-compress\SKILL.md`
- **caveman-discover** - Find and label every LLM workflow in the repository so Caveman Cloud groups spend by workflow instead of one bucket. Use for "discover workflows" or breaking LLM spend down by workflow.
  `caveman\skills\caveman-discover\SKILL.md`
- **caveman-evidence-review** - Read-only review of Caveman Cloud evidence: cost, Cave Score, workflows, traces, latency, errors, routing, savings. Use when asked what Caveman found or where LLM spend goes.
  `caveman\skills\caveman-evidence-review\SKILL.md`
- **caveman-explore** - Read-only repository explorer for cold-start orientation, broad cross-file localization, or when a direct search failed. Skip it when the exact file or symbol is already named. Returns path:line citat...
  `caveman\skills\caveman-explore\SKILL.md`
- **caveman-help** - Quick-reference card for caveman modes, skills and commands. Trigger: /caveman-help or "caveman help".
  `caveman\skills\caveman-help\SKILL.md`
- **caveman-learn** - Act on a Caveman learn report - review the ranked token sinks, apply cost-lowering fixes with per-edit consent, and report what those fixes returned. Use when asked to lower an agent's token cost, wha...
  `caveman\skills\caveman-learn\SKILL.md`
- **caveman-manage** - Inspect Caveman Cloud's experiment lifecycle and block unsafe execution. Use when asked to start, approve, cancel, promote or roll back a Caveman experiment.
  `caveman\skills\caveman-manage\SKILL.md`
- **caveman-optimize** - Turn a Caveman optimization observation into an operator-chosen candidate with a paired baseline evaluation. Use when asked to inspect or evaluate a Caveman optimization report. Needs explicit approva...
  `caveman\skills\caveman-optimize\SKILL.md`
- **caveman-review** - Compressed code review - one line per finding with location, problem and fix. Use for /caveman-review, "review this PR", or "review the diff".
  `caveman\skills\caveman-review\SKILL.md`
- **caveman-setup** - Wire a repository through the Caveman Cloud gateway so every LLM request is measured, with no behavior change. Use for "set up caveman" or adding LLM spend observability.
  `caveman\skills\caveman-setup\SKILL.md`
- **caveman-stats** - Show recorded output and cache-read token usage and mode attribution for the current Claude Code session, or locate the host's native usage report. Trigger: /caveman-stats.
  `caveman\plugins\caveman\skills\caveman-stats\SKILL.md`
- **caveman-stats** - Show recorded output and cache-read token usage and mode attribution for the current Claude Code session, or locate the host's native usage report. Trigger: /caveman-stats.
  `caveman\skills\caveman-stats\SKILL.md`
- **investigate-first** - Diagnose ambiguous failures before editing. Use for unknown causes, intermittent behavior, performance regressions, or investigations needing evidence-ranked hypotheses.
  `caveman\skills\investigate-first\SKILL.md`
- **lean-build** - Build feature work with high overbuilding risk. Use for new behavior, product slices, or integrations where repository reuse, strict scope, and an explicit stop condition matter.
  `caveman\skills\lean-build\SKILL.md`
- **migration** - Implement reversible compatibility-safe transitions. Use for schema, data, API, protocol, configuration, or dependency migrations requiring rollback and preservation proof.
  `caveman\skills\migration\SKILL.md`
- **safe-refactor** - Restructure code while preserving behavior. Use for extraction, consolidation, ownership moves, or cleanup where verification must bracket structural edits.
  `caveman\skills\safe-refactor\SKILL.md`
- **surgical-patch** - Fix bugs and small behavior changes at the narrowest responsible layer. Use when regression proof, preserved surrounding behavior, and task-relevant tests matter.
  `caveman\skills\surgical-patch\SKILL.md`
- **verify-and-stop** - Prove existing work meets acceptance conditions without expanding scope. Use for validation-only tasks, completion checks, focused gate runs, and last-mile proof.
  `caveman\skills\verify-and-stop\SKILL.md`

## claude-code (10)

- **Agent Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\plugin-dev\skills\agent-development\SKILL.md`
- **claude-opus-4-5-migration** *(auch im Fundus)* - Migrate prompts and code from Claude Sonnet 4.0, Sonnet 4.5, or Opus 4.1 to Opus 4.5. Use when the user wants to update their codebase, prompts, or API calls to use Opus 4.5. Handles model string upda...
  `claude-code\plugins\claude-opus-4-5-migration\skills\claude-opus-4-5-migration\SKILL.md`
- **Command Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\plugin-dev\skills\command-development\SKILL.md`
- **frontend-design** *(auch im Fundus)* - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `claude-code\plugins\frontend-design\skills\frontend-design\SKILL.md`
- **Hook Development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\plugin-dev\skills\hook-development\SKILL.md`
- **MCP Integration** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\plugin-dev\skills\mcp-integration\SKILL.md`
- **Plugin Settings** *(auch im Fundus)* - This skill should be used when the user asks about
  `claude-code\plugins\plugin-dev\skills\plugin-settings\SKILL.md`
- **Plugin Structure** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\plugin-dev\skills\plugin-structure\SKILL.md`
- **Skill Development** *(auch im Fundus)* - This skill should be used when the user wants to
  `claude-code\plugins\plugin-dev\skills\skill-development\SKILL.md`
- **Writing Hookify Rules** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-code\plugins\hookify\skills\writing-rules\SKILL.md`

## claude-plugins-official (29)

- **access** *(auch im Fundus)* - Manage Discord channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the Discord channel.
  `claude-plugins-official\external_plugins\discord\skills\access\SKILL.md`
- **access** - Manage Telegram channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the Telegram channel...
  `claude-plugins-official\external_plugins\telegram\skills\access\SKILL.md`
- **access** *(auch im Fundus)* - Manage iMessage channel access — approve pairings, edit allowlists, set DM/group policy. Use when the user asks to pair, approve someone, check who's allowed, or change policy for the iMessage channel...
  `claude-plugins-official\external_plugins\imessage\skills\access\SKILL.md`
- **agent-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\plugin-dev\skills\agent-development\SKILL.md`
- **build-mcp-app** *(auch im Fundus)* - This skill should be used when the user wants to build an
  `claude-plugins-official\plugins\mcp-server-dev\skills\build-mcp-app\SKILL.md`
- **build-mcpb** *(auch im Fundus)* - This skill should be used when the user wants to
  `claude-plugins-official\plugins\mcp-server-dev\skills\build-mcpb\SKILL.md`
- **build-mcp-server** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\mcp-server-dev\skills\build-mcp-server\SKILL.md`
- **cardputer-buddy** *(auch im Fundus)* - Iterate on the Cardputer-Adv MicroPython app bundle (Claude Buddy, Snake, Hello) after the device is already provisioned via m5-onboard. Use when the user wants to add a new app, push a single changed...
  `claude-plugins-official\plugins\cwc-makers\skills\cardputer-buddy\SKILL.md`
- **claude-automation-recommender** *(auch im Fundus)* - Analyze a codebase and recommend Claude Code automations (hooks, subagents, skills, plugins, MCP servers). Use when user asks for automation recommendations, wants to optimize their Claude Code setup,...
  `claude-plugins-official\plugins\claude-code-setup\skills\claude-automation-recommender\SKILL.md`
- **claude-md-improver** *(auch im Fundus)* - Audit and improve CLAUDE.md files in repositories. Use when user asks to check, audit, update, improve, or fix CLAUDE.md files. Scans for all CLAUDE.md files, evaluates quality against templates, outp...
  `claude-plugins-official\plugins\claude-md-management\skills\claude-md-improver\SKILL.md`
- **claude-security** *(auch im Fundus)* - The Claude Security menu — pick a job: scan the codebase (the whole repository or a scoped part of it), scan changes (this branch's or a pull request's diff, or one commit), or suggest patches (findin...
  `claude-plugins-official\plugins\claude-security\skills\claude-security\SKILL.md`
- **command-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\plugin-dev\skills\command-development\SKILL.md`
- **configure** *(auch im Fundus)* - Set up the Discord channel — save the bot token and review access policy. Use when the user pastes a Discord bot token, asks to configure Discord, asks
  `claude-plugins-official\external_plugins\discord\skills\configure\SKILL.md`
- **configure** *(auch im Fundus)* - Check iMessage channel setup and review access policy. Use when the user asks to configure iMessage, asks
  `claude-plugins-official\external_plugins\imessage\skills\configure\SKILL.md`
- **configure** - Set up the Telegram channel — save the bot token and review access policy. Use when the user pastes a Telegram bot token, asks to configure Telegram, asks
  `claude-plugins-official\external_plugins\telegram\skills\configure\SKILL.md`
- **example-command** *(auch im Fundus)* - An example user-invoked skill that demonstrates frontmatter options and the skills/<name>/SKILL.md layout
  `claude-plugins-official\plugins\example-plugin\skills\example-command\SKILL.md`
- **example-skill** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\example-plugin\skills\example-skill\SKILL.md`
- **hook-development** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\plugin-dev\skills\hook-development\SKILL.md`
- **m5-onboard** *(auch im Fundus)* - End-to-end onboarding for a freshly-plugged-in M5Stack ESP32 device (Cardputer, Cardputer-Adv, Core, CoreS3, Stick) — detect on USB, flash UIFlow 2.0 firmware, and install the Claude Buddy MicroPython...
  `claude-plugins-official\plugins\cwc-makers\skills\m5-onboard\SKILL.md`
- **math-olympiad** *(auch im Fundus)* - Solve competition math problems (IMO, Putnam, USAMO, AIME) with adversarial
  `claude-plugins-official\plugins\math-olympiad\skills\math-olympiad\SKILL.md`
- **mcp-integration** - This skill should be used when the user asks to
  `claude-plugins-official\plugins\plugin-dev\skills\mcp-integration\SKILL.md`
- **playground** *(auch im Fundus)* - Creates interactive HTML playgrounds — self-contained single-file explorers that let users configure something visually through controls, see a live preview, and copy out a prompt. Use when the user a...
  `claude-plugins-official\plugins\playground\skills\playground\SKILL.md`
- **plugin-settings** *(auch im Fundus)* - This skill should be used when the user asks about
  `claude-plugins-official\plugins\plugin-dev\skills\plugin-settings\SKILL.md`
- **plugin-structure** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\plugin-dev\skills\plugin-structure\SKILL.md`
- **project-artifact** - Generate and publish a project status artifact — an opinionated, tabbed status page for a project too big for one update (overview & success criteria, the workstream sequence, next steps, plus backgro...
  `claude-plugins-official\plugins\project-artifact\skills\project-artifact\SKILL.md`
- **receipts** *(auch im Fundus)* - Generate a personal Claude Code usage & impact report (
  `claude-plugins-official\plugins\receipts\skills\receipts\SKILL.md`
- **session-report** *(auch im Fundus)* - Generate an explorable HTML report of Claude Code session usage (tokens, cache, subagents, skills, expensive prompts) from ~/.claude/projects transcripts.
  `claude-plugins-official\plugins\session-report\skills\session-report\SKILL.md`
- **skill-development** *(auch im Fundus)* - This skill should be used when the user wants to
  `claude-plugins-official\plugins\plugin-dev\skills\skill-development\SKILL.md`
- **writing-hookify-rules** *(auch im Fundus)* - This skill should be used when the user asks to
  `claude-plugins-official\plugins\hookify\skills\writing-rules\SKILL.md`

## codex (17)

- **babysit-pr** - Babysit a GitHub pull request after creation by continuously polling review comments, CI checks/workflow runs, and mergeability state until the PR is merged/closed or user help is required. Diagnose f...
  `codex\.codex\skills\babysit-pr\SKILL.md`
- **code-breaking-changes** - Breaking changes
  `codex\.codex\skills\code-review-breaking-changes\SKILL.md`
- **code-review** - Run a final code review on a pull request
  `codex\.codex\skills\code-review\SKILL.md`
- **code-review-change-size** - Change size guidance (800 lines)
  `codex\.codex\skills\code-review-change-size\SKILL.md`
- **code-review-context** - Model visible context
  `codex\.codex\skills\code-review-context\SKILL.md`
- **code-review-testing** - Test authoring guidance
  `codex\.codex\skills\code-review-testing\SKILL.md`
- **codex-pr-body** - Update the title and body of one or more pull requests.
  `codex\.codex\skills\codex-pr-body\SKILL.md`
- **imagegen** - Generate or edit raster images when the task benefits from AI-created bitmap visuals such as photos, illustrations, textures, sprites, mockups, or transparent-background cutouts. Use when Codex should...
  `codex\codex-rs\skills\src\assets\samples\imagegen\SKILL.md`
- **openai-docs** - Use for Codex models/pricing, scheduled tasks, skills, settings, setup, troubleshooting, customization, automations, and self-knowledge—including 'you,' 'your,' 'this app,' or 'this coding agent' when...
  `codex\codex-rs\skills\src\assets\samples\openai-docs\SKILL.md`
- **path-types** - Choose Rust types for operating system paths across the Codex repository. Use when defining new path-bearing types or explicitly migrating existing ones.
  `codex\.codex\skills\path-types\SKILL.md`
- **plugin-creator** - Create and scaffold plugin directories for Codex with a required `.codex-plugin/plugin.json`, optional plugin folders/files, valid manifest defaults, and personal-marketplace entries by default. Use w...
  `codex\codex-rs\skills\src\assets\samples\plugin-creator\SKILL.md`
- **remote-tests** - Testing against remote executors in integration tests.
  `codex\.codex\skills\remote-tests\SKILL.md`
- **review-agent** - Perform a read-only, defect-first review of a specified code change and return every actionable finding. Use when another agent delegates review of uncommitted changes, a base-branch diff, a commit, o...
  `codex\codex-rs\skills\src\assets\samples\review-agent\SKILL.md`
- **skill-creator** - Create or update a Codex skill with appropriately scoped instructions and any needed supporting resources.
  `codex\codex-rs\skills\src\assets\samples\skill-creator\SKILL.md`
- **skill-installer** - Install Codex skills into $CODEX_HOME/skills from a curated list or a GitHub repo path. Use when a user asks to list installable skills, install a curated skill, or install a skill from another repo (...
  `codex\codex-rs\skills\src\assets\samples\skill-installer\SKILL.md`
- **test-tui** - Guide for testing Codex TUI interactively
  `codex\.codex\skills\test-tui\SKILL.md`
- **update-v8-version** - Update Codex's pinned `v8` / `rusty_v8` versions, validate the release-candidate path, and investigate failed V8 canary or artifact builds. Use when asked to bump V8, update `rusty_v8` artifacts, prep...
  `codex\.codex\skills\update-v8-version\SKILL.md`

## copilot-worktrees (21)

- **brainstorming** - You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\brainstorming\SKILL.md`
- **cordis-plugin-development** - Create, modify, debug, or extend dynamic Cordis Plugins, including Host Services and Events, Client Slot and theme UI, Package-private Client-to-Host calls, dynamic Tools, version updates, approval fa...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\apps\cli\node_modules\@deepseek-ai\dsh-acp\node_modules\@deepseek-ai\dsh-token-meter\node_modules\@deepseek-ai\dsh-llm-retry\node_modules\@deepseek-ai\dsh-llm-deepseek\node_modules\@deepseek-ai\dsh-plugin-package-inventory-deepseek\node_modules\@deepseek-ai\dsh-agent-presets\presets\cordis\skills\cordis-plugin-development\SKILL.md`
- **dsh-archive-agent-notes** - Use when adding, auditing, pruning, archiving, restoring, or reviewing Agent Notes in deepseek-harness; checks every new note for superseded active records, classifies implemented notes by future deci...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-archive-agent-notes\SKILL.md`
- **dsh-doc** - Create, restructure, review, audit, or migrate DeepSeek Harness Markdown documentation, package READMEs, and the documentation website using audience-first hierarchy, kind-mapped YAML metadata, biling...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-doc\SKILL.md`
- **dsh-find-simplifications** - 'Use when working in the deepseek-harness repo to find non-obvious simplification candidates, remove redundant comments or implementation-heavy documentation, write proposed Agent Notes or inline TODO...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-find-simplifications\SKILL.md`
- **dsh-merging-stacked-prs** - Use when landing a stack of dependent GitHub PRs (A ← B ← C, where each bases on the one below) onto master, merging a PR whose base is another open PR's branch, or whenever a request mentions
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-merging-stacked-prs\SKILL.md`
- **dsh-pre-push-checks** - Use before pushing, force-pushing, marking ready for review, or claiming checks pass on a deepseek-harness branch, and immediately after gh stack sync publishes rewritten branches, to select the small...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-pre-push-checks\SKILL.md`
- **dsh-translate-docs** - Manually run the extended DeepSeek Harness bilingual-document workflow, including generated briefings, delegated prose translation, whole-document translation, and scoped pairing verification.
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-translate-docs\SKILL.md`
- **dsh-trim-cot-leakage** - Use when auditing or fixing prose that reads like a leaked reasoning transcript — dead design-session citations such as (decision N), audit item codes, or §N of uncommitted drafts; change narration su...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\dsh-trim-cot-leakage\SKILL.md`
- **editing-cordis-compositions** - Use when creating, changing, or validating a Cordis composition for this harness — writing or editing an agent preset, adding or removing a plugin row, deciding whether something belongs to the host c...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\apps\cli\node_modules\@deepseek-ai\dsh-acp\node_modules\@deepseek-ai\dsh-token-meter\node_modules\@deepseek-ai\dsh-llm-retry\node_modules\@deepseek-ai\dsh-llm-deepseek\node_modules\@deepseek-ai\dsh-plugin-package-inventory-deepseek\node_modules\@deepseek-ai\dsh-agent-presets\presets\cordis\skills\editing-cordis-compositions\SKILL.md`
- **executing-plans** - Use when you have a written implementation plan to execute in a separate session with review checkpoints
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\executing-plans\SKILL.md`
- **finishing-a-development-branch** - Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\finishing-a-development-branch\SKILL.md`
- **frontend-design** - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `copilot-worktrees\claude-code\mfaupel95-silver-bassoon\plugins\frontend-design\skills\frontend-design\SKILL.md`
- **record-browser-gif** - Record browser or Web UI interaction demos as optimized GIFs using the available built-in browser, state-based frame capture, and deterministic encoding, then attach the GIF to a pull request with `gh...
  `copilot-worktrees\deepseek-harness\mfaupel95-refactored-sniffle\.agents\skills\record-browser-gif\SKILL.md`
- **requesting-code-review** - Use when completing tasks, implementing major features, or before merging to verify work meets requirements
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\requesting-code-review\SKILL.md`
- **subagent-driven-development** - Use when executing implementation plans with independent tasks in the current session
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\subagent-driven-development\SKILL.md`
- **task-observer** - Monitors task execution for skill improvement opportunities. Use during ANY multi-step task, agentic workflow, or work session where the agent uses tools and produces deliverables. Captures patterns, ...
  `copilot-worktrees\one-skill-to-rule-them-all\mfaupel95-miniature-fishstick\SKILL.md`
- **test-driven-development** - Use when implementing any feature or bugfix, before writing implementation code
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\test-driven-development\SKILL.md`
- **using-superpowers** - Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\using-superpowers\SKILL.md`
- **writing-plans** - Use when you have a spec or requirements for a multi-step task, before touching code
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\writing-plans\SKILL.md`
- **writing-skills** - Use when creating new skills, editing existing skills, or verifying skills work before deployment
  `copilot-worktrees\superpowers\mfaupel95-glowing-waddle\skills\writing-skills\SKILL.md`

## deepseek-harness (21)

- **cordis-plugin-development** - Use when authoring, installing, configuring, or debugging persistent plugins and MCP connections in the current Harness profile.
  `deepseek-harness\packages\preset\agent-presets\presets\cordis\skills\cordis-plugin-development\SKILL.md`
- **dsh-archive-agent-notes** - Use when adding, auditing, pruning, archiving, restoring, or reviewing Agent Notes in deepseek-harness; checks every new note for superseded active records, classifies implemented notes by future deci...
  `deepseek-harness\.agents\skills\dsh-archive-agent-notes\SKILL.md`
- **dsh-ci-test-reliability** - Design, review, and diagnose DeepSeek Harness tests and fixtures that can fail nondeterministically under CI concurrency, shared host resources, clocks, process-global state, subprocesses, network lis...
  `deepseek-harness\.agents\skills\dsh-ci-test-reliability\SKILL.md`
- **dsh-code-review** - Use when reviewing a pull request in the deepseek-harness repo — orients the reviewer to this codebase's standards (AGENTS.md conventions, defensive patterns, ADRs, quality gates) and the review-speci...
  `deepseek-harness\.agents\skills\dsh-code-review\SKILL.md`
- **dsh-doc** - Create, restructure, review, audit, or migrate DeepSeek Harness Markdown documentation, package READMEs, and the documentation website using audience-first hierarchy, kind-mapped YAML metadata, biling...
  `deepseek-harness\.agents\skills\dsh-doc\SKILL.md`
- **dsh-find-simplifications** - 'Use when working in the deepseek-harness repo to find non-obvious simplification candidates, remove redundant comments or implementation-heavy documentation, write proposed Agent Notes or inline TODO...
  `deepseek-harness\.agents\skills\dsh-find-simplifications\SKILL.md`
- **dsh-merging-stacked-prs** - Use when landing a stack of dependent GitHub PRs (A ← B ← C, where each bases on the one below) onto master, merging a PR whose base is another open PR's branch, or whenever a request mentions
  `deepseek-harness\.agents\skills\dsh-merging-stacked-prs\SKILL.md`
- **dsh-pre-push-checks** - Use before pushing, force-pushing, marking ready for review, or claiming checks pass on a deepseek-harness branch, and immediately after gh stack sync publishes rewritten branches, to select the small...
  `deepseek-harness\.agents\skills\dsh-pre-push-checks\SKILL.md`
- **dsh-prose-standard** - Use when writing, reviewing, restoring, trimming, or auditing prose in the deepseek-harness repo, including deciding where documentation or comments are required across Markdown, JSDoc, code and test ...
  `deepseek-harness\.agents\skills\dsh-prose-standard\SKILL.md`
- **dsh-speed-up-perf** - 'Use when investigating or optimizing DeepSeek Harness performance, designing realistic synthetic benchmarks or CI performance gates, profiling long Sessions or Web responsiveness, or turning performa...
  `deepseek-harness\.agents\skills\dsh-speed-up-perf\SKILL.md`
- **dsh-translate-docs** - Manually run the extended DeepSeek Harness bilingual-document workflow, including generated briefings, delegated prose translation, whole-document translation, and scoped pairing verification.
  `deepseek-harness\.agents\skills\dsh-translate-docs\SKILL.md`
- **dsh-trim-cot-leakage** - Use when auditing or fixing prose that reads like a leaked reasoning transcript — dead design-session citations such as (decision N), audit item codes, or §N of uncommitted drafts; change narration su...
  `deepseek-harness\.agents\skills\dsh-trim-cot-leakage\SKILL.md`
- **editing-cordis-compositions** - Use when creating, changing, or validating a Cordis composition for this harness — writing or editing an agent preset, adding or removing a plugin row, deciding whether something belongs to the host c...
  `deepseek-harness\packages\preset\agent-presets\presets\cordis\skills\editing-cordis-compositions\SKILL.md`
- **model-only-skill** - Prove user-disabled skills remain available to the model.
  `deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\model-only-skill\SKILL.md`
- **office-docx** - Create, read, edit, and check Word documents (.docx), including reports, letters, and formatted tables. Use when a DOCX file is an input or requested deliverable.
  `deepseek-harness\packages\skill\skill-office\assets\office-docx\SKILL.md`
- **office-pptx** - Create, read, edit, and check PowerPoint presentations (.pptx), including slide text, tables, images, and charts. Use when a PPTX file is an input or requested deliverable.
  `deepseek-harness\packages\skill\skill-office\assets\office-pptx\SKILL.md`
- **office-xlsx** - Read, create, and modify Excel workbooks (.xlsx), including cell values, formulas, formatting, and pandas analysis. Use when an Excel workbook is an input or deliverable.
  `deepseek-harness\packages\skill\skill-office\assets\office-xlsx\SKILL.md`
- **preview-tour** - Inspect the bundled Preview workspace and its deterministic Session examples.
  `deepseek-harness\packages\experimental\webworker-runtime\tests\fixtures\vfs-example\workspace\.agents\skills\preview-tour\SKILL.md`
- **record-browser-gif** - Record browser or Web UI interaction demos as optimized GIFs using the available browser-control workflow, optional Playwright Videos for higher capture frame rates, and deterministic encoding, then a...
  `deepseek-harness\.agents\skills\record-browser-gif\SKILL.md`
- **snapshot-skill** - Exercise project skill discovery and loading in snapshot tests.
  `deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\snapshot-skill\SKILL.md`
- **user-only-skill** - Prove model-disabled skills stay outside the model catalog.
  `deepseek-harness\snapshots\session\skill-load\workspace\.dsh\skills\user-only-skill\SKILL.md`

## everything-claude-code (11)

- **backend-patterns** - Backend architecture patterns, API design, database optimization, and server-side best practices for Node.js, Express, and Next.js API routes.
  `everything-claude-code\skills\backend-patterns\SKILL.md`
- **clickhouse-io** - ClickHouse database patterns, query optimization, analytics, and data engineering best practices for high-performance analytical workloads.
  `everything-claude-code\skills\clickhouse-io\SKILL.md`
- **coding-standards** - Universal coding standards, best practices, and patterns for TypeScript, JavaScript, React, and Node.js development.
  `everything-claude-code\skills\coding-standards\SKILL.md`
- **continuous-learning** - Automatically extract reusable patterns from Claude Code sessions and save them as learned skills for future use.
  `everything-claude-code\skills\continuous-learning\SKILL.md`
- **eval-harness**
  `everything-claude-code\skills\eval-harness\SKILL.md`
- **frontend-patterns** - Frontend development patterns for React, Next.js, state management, performance optimization, and UI best practices.
  `everything-claude-code\skills\frontend-patterns\SKILL.md`
- **project-guidelines-example**
  `everything-claude-code\skills\project-guidelines-example\SKILL.md`
- **security-review** - Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensitive features. Provides comprehensive security checklist and ...
  `everything-claude-code\skills\security-review\SKILL.md`
- **strategic-compact** - Suggests manual context compaction at logical intervals to preserve context through task phases rather than arbitrary auto-compaction.
  `everything-claude-code\skills\strategic-compact\SKILL.md`
- **tdd-workflow** - Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with 80%+ coverage including unit, integration, and E2E tests.
  `everything-claude-code\skills\tdd-workflow\SKILL.md`
- **verification-loop**
  `everything-claude-code\skills\verification-loop\SKILL.md`

## gbrain (115)

- **academic-verify** *(auch im Fundus)* - Verify a research claim or academic citation by tracing it through publication → methodology → raw data → independent replication. Routes through perplexity-research for the actual web lookup, then fo...
  `gbrain\skills\academic-verify\SKILL.md`
- **adversary-tracking** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\adversary-tracking\SKILL.md`
- **archive-crawler** *(auch im Fundus)* - Universal archivist for personal file archives (Dropbox/B2/Gmail-takeout/local-mount/hard-drive-dump). Filters for high-value content (the user's own writing, ideas, relationships) and surfaces it int...
  `gbrain\skills\archive-crawler\SKILL.md`
- **article-enrichment** *(auch im Fundus)* - Transform raw article text dumps in the brain into structured pages with executive summary, verbatim quotes, key insights, why-it-matters, and cross-references. Replaces walls-of-text with quotable, a...
  `gbrain\skills\article-enrichment\SKILL.md`
- **ask-user** *(auch im Fundus)* - Reusable pattern for presenting the user with explicit choices and gating execution until they respond. Used by other skills when a decision point requires human input before proceeding. Platform-agno...
  `gbrain\skills\ask-user\SKILL.md`
- **blog-ingest** *(auch im Fundus)* - Feed and whole-publication ingestion: turn an entire blog, newsletter, or RSS/Atom archive into brain source pages. Covers feed discovery, pagination walking, normalization to a common article shape, ...
  `gbrain\skills\blog-ingest\SKILL.md`
- **book-mirror** *(auch im Fundus)* - Take any book (EPUB/PDF), produce a personalized chapter-by-chapter analysis. Each chapter is preserved in detail (The Chapter) and mirrored back to the reader's actual life (The Mirror) using brain c...
  `gbrain\skills\book-mirror\SKILL.md`
- **book-mirror** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\book-mirror\SKILL.md`
- **brain-ingest-gate** *(auch im Fundus)* - Pre-write quality gate for content entering the brain. No raw copies: a bare cp/mv into the brain repo is a bug. Before any new page lands, resolve named entities registry-first (a vector score is a f...
  `gbrain\skills\brain-ingest-gate\SKILL.md`
- **brain-link-discipline** *(auch im Fundus)* - When you report a brain page to the user — created, edited, committed, or relayed from a subagent — a working link is part of the deliverable, in the SAME message. Derive the path mechanically (git ls...
  `gbrain\skills\brain-link-discipline\SKILL.md`
- **brain-ops** *(auch im Fundus)* - Core read/write cycle for the generic agent-workspace fixture.
  `gbrain\test\fixtures\generic-agents-workspace\skills\brain-ops\SKILL.md`
- **brain-ops** *(auch im Fundus)* - Brain knowledge base operations. The core read/write cycle: brain-first lookup, read-enrich-write loop, source attribution, ambient enrichment, back-linking. Read this before any brain interaction.
  `gbrain\skills\brain-ops\SKILL.md`
- **brain-ops** *(auch im Fundus)* - Read, enrich, and write brain pages with source attribution.
  `gbrain\test\fixtures\skill-catalog\skills\brain-ops\SKILL.md`
- **brain-ops** *(auch im Fundus)* - Core read/write cycle for the OpenClaw reference fixture.
  `gbrain\test\fixtures\openclaw-reference-minimal\skills\brain-ops\SKILL.md`
- **brain-pdf** *(auch im Fundus)* - Generate a publication-quality PDF from any brain page via the gstack make-pdf binary. Strips YAML frontmatter, sanitizes emoji, applies running headers and page numbers. Brain page is always the sour...
  `gbrain\skills\brain-pdf\SKILL.md`
- **brain-search** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\brain-search\SKILL.md`
- **brain-taxonomist** *(auch im Fundus)* - Filing gate for ALL brain writes. Consulted before creating any new brain page to determine the correct path. Reads the ACTIVE schema pack via `gbrain schema show --json` — no hardcoded directory tabl...
  `gbrain\skills\brain-taxonomist\SKILL.md`
- **briefing** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\briefing\SKILL.md`
- **briefing** *(auch im Fundus)* - Compile daily briefing with meeting context, active deals, and citation tracking
  `gbrain\skills\briefing\SKILL.md`
- **broken** *(auch im Fundus)*
  `gbrain\test\fixtures\skill-catalog\skills\broken\SKILL.md`
- **bulk-ingestion** *(auch im Fundus)* - End-to-end discipline for turning any large data source (audio libraries, email takeouts, document corpora, chat exports, API dumps) into brain pages at scale. The lifecycle spine: SCHEMA → ACCESS → T...
  `gbrain\skills\bulk-ingestion\SKILL.md`
- **calendar-prep** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\calendar-prep\SKILL.md`
- **capture** *(auch im Fundus)* - Save any thought or content into the brain via one CLI command. The single human-facing entrypoint that replaces
  `gbrain\skills\capture\SKILL.md`
- **chat-connectors** *(auch im Fundus)* - Connect a ChatGPT or Claude account and sync its conversation history into the brain automatically. Cookie paste-in is the primary lane; sync is incremental (watermark + trailing-window gap-heal), and...
  `gbrain\skills\chat-connectors\SKILL.md`
- **citation-fixer** *(auch im Fundus)* - Audit and fix citation formatting across brain pages. Ensures every fact has an inline [Source: ...] citation matching the standard format. Extended in v0.25.1: scans for broken tweet/post references ...
  `gbrain\skills\citation-fixer\SKILL.md`
- **citation-graph-ingest** *(auch im Fundus)* - Build a TYPED citation/reference graph over an ingested corpus — not just embeddings. Flat similarity retrieval cannot tell you that document A *overrules* B, *distinguishes* C, or *relies_on* D. This...
  `gbrain\skills\citation-graph-ingest\SKILL.md`
- **civic-intelligence** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\civic-intelligence\SKILL.md`
- **cold-start** *(auch im Fundus)* - Day-one data bootstrapping for a new brain. Sequences the highest-leverage data sources to go from empty brain to useful brain in one session. Uses ClawVisor for safe credential handling — the agent n...
  `gbrain\skills\cold-start\SKILL.md`
- **company-brainify** *(auch im Fundus)* - Extract a sanitized shared team/company brain from a personal brain. Strips internal ratings, compensation, performance assessments, retention and political dynamics from pages, takes, and facts acros...
  `gbrain\skills\company-brainify\SKILL.md`
- **compliant-callout** *(auch im Fundus)* - External-lookup skill with canonical Convention callout
  `gbrain\test\fixtures\brain-first-skills\compliant-callout\SKILL.md`
- **compliant-phase** *(auch im Fundus)* - External-lookup skill with explicit Phase 1 brain heading
  `gbrain\test\fixtures\brain-first-skills\compliant-phase\SKILL.md`
- **compliant-position** *(auch im Fundus)* - Skill that runs gbrain search before external lookup
  `gbrain\test\fixtures\brain-first-skills\compliant-position\SKILL.md`
- **concept-synthesis** *(auch im Fundus)* - Deduplicate and synthesize raw concept stubs into a tiered intellectual map (T1 Canon to T4 Riff), tracing idea evolution across sources over time. Transforms thousands of raw concept pages into a cur...
  `gbrain\skills\concept-synthesis\SKILL.md`
- **content-creation** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\content-creation\SKILL.md`
- **context-audit** *(auch im Fundus)* - Token-hygiene audit of the always-loaded context stack — CLAUDE.md, AGENTS.md, auto-memory MEMORY.md, and the bootstrap-rendered identity files (SOUL.md, USER.md, ACCESS_POLICY.md, HEARTBEAT.md) or th...
  `gbrain\skills\context-audit\SKILL.md`
- **context-now** *(auch im Fundus)* - ALWAYS-ON time-sensitivity discipline for the OpenClaw reference fixture.
  `gbrain\test\fixtures\openclaw-reference-minimal\skills\context-now\SKILL.md`
- **conversation-archive** *(auch im Fundus)* - Import AI-assistant chat exports (ChatGPT, Claude, Perplexity) and agent session transcripts into the brain as one dated page per conversation under conversations/, validate each page against the nati...
  `gbrain\skills\conversation-archive\SKILL.md`
- **correction-pipeline** *(auch im Fundus)* - When the user corrects a factual error, root-cause it immediately. Don't just note the correction — trace the error to its source, fix the source, and prevent recurrence. Every factual error is either...
  `gbrain\skills\correction-pipeline\SKILL.md`
- **cron-scheduler** *(auch im Fundus)* - Schedule management with staggering, quiet hours, and wake-up override. Validates schedules, prevents collisions, and gates delivery during quiet hours.
  `gbrain\skills\cron-scheduler\SKILL.md`
- **cross-modal-review** *(auch im Fundus)* - Quality gate via second model. Spawn a different AI model to review work before committing. Includes refusal routing: if one model refuses, switch silently to the next. Extended in v0.25.1 with struct...
  `gbrain\skills\cross-modal-review\SKILL.md`
- **daily-digest** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\daily-digest\SKILL.md`
- **daily-task-manager** *(auch im Fundus)* - Task lifecycle management with stable task IDs. Add, complete, defer, remove, and review tasks with deterministic action routing and fail-closed ambiguity handling. Maintains a running task list as a ...
  `gbrain\skills\daily-task-manager\SKILL.md`
- **daily-task-prep** *(auch im Fundus)* - Morning preparation. Calendar lookahead, meeting context loading, open threads from yesterday, active task review. Extends briefing with actionable prep.
  `gbrain\skills\daily-task-prep\SKILL.md`
- **data-loss-gate** *(auch im Fundus)* - Confirmation gate before any bulk delete, cleanup, or destructive operation that could result in data loss — shell-level (rm -rf, git rm, bulk sed) or brain-level (bulk forget, delete sweeps, purge-de...
  `gbrain\skills\data-loss-gate\SKILL.md`
- **data-research** *(auch im Fundus)* - Structured data research: search sources, extract structured data, archive raw sources, maintain canonical tracker pages, deduplicate. Parameterized via YAML recipes for investor updates, donations, c...
  `gbrain\skills\data-research\SKILL.md`
- **db-repair** *(auch im Fundus)* - Auto-fix gbrain's Postgres access so the brain stays available. When any gbrain command or MCP tool result carries a `GBRAIN_DB_ACCESS <reason>` marker (or an operator reports the brain database is do...
  `gbrain\skills\db-repair\SKILL.md`
- **draft-in-voice** *(auch im Fundus)* - Ghostwrite content in a specific person's voice from a VALIDATED voice profile — tweets, replies, short posts, launch copy, recruiting blurbs, emails. Loads the subject's voice profile (people/<slug>-...
  `gbrain\skills\draft-in-voice\SKILL.md`
- **eiirp** *(auch im Fundus)* - Everything In Its Right Place. The universal post-work organizer. After any significant work session, EIIRP runs a 7-phase audit: (1) inventory every output, (2) walk taxonomy to decide where each lan...
  `gbrain\skills\eiirp\SKILL.md`
- **email-triage** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\email-triage\SKILL.md`
- **enrich** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\enrich\SKILL.md`
- **enrich** *(auch im Fundus)* - Enrich brain pages with tiered enrichment protocol. Creates and updates person/company pages with compiled truth, timeline, and cross-links. Use when a new entity is mentioned or an existing page need...
  `gbrain\skills\enrich\SKILL.md`
- **executive-assistant** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\executive-assistant\SKILL.md`
- **exempt-frontmatter** *(auch im Fundus)* - Pure-infra skill that opts out via frontmatter
  `gbrain\test\fixtures\brain-first-skills\exempt-frontmatter\SKILL.md`
- **fact-check** *(auch im Fundus)* - Systematic claim-by-claim verification for any content before it ships. Modeled on professional fact-checking desks (The New Yorker, ProPublica, IFCN standards): extract every verifiable claim, check ...
  `gbrain\skills\fact-check\SKILL.md`
- **flight-tracker** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\flight-tracker\SKILL.md`
- **frontmatter-guard** *(auch im Fundus)* - Validate and auto-repair YAML frontmatter on brain pages. Catches malformed pages before they enter the brain (missing closing ---, nested quotes, slug mismatches, null bytes, empty frontmatter, YAML ...
  `gbrain\skills\frontmatter-guard\SKILL.md`
- **functional-area-resolver** *(auch im Fundus)* - Compress an agent's routing file (RESOLVER.md or AGENTS.md) by converting granular skill-per-row tables into functional-area dispatchers. Each area lists sub-skills in a "(dispatcher for: ...)" clause...
  `gbrain\skills\functional-area-resolver\SKILL.md`
- **gbrain** *(auch im Fundus)* - Search and write the company knowledge brain. Use for any question about the org, people, projects, decisions, or history, and to persist durable knowledge beyond this scope's notebook.
  `gbrain\docs\integrations\qm-harness-snippets\SKILL.md`
- **gbrain-advisor** *(auch im Fundus)* - Proactive "make the most of gbrain" coaching. Runs `gbrain advisor` on a cadence and pings the user with the top high-leverage actions for their brain: version drift, pending migrations, stalled jobs,...
  `gbrain\skills\gbrain-advisor\SKILL.md`
- **gbrain-upgrade** *(auch im Fundus)* - Keep gbrain current. When a `gbrain` invocation prints an `UPGRADE_AVAILABLE <old> <new>` marker (or `gbrain self-upgrade --check-only` reports an update), apply it per the configured self_upgrade.mod...
  `gbrain\skills\gbrain-upgrade\SKILL.md`
- **gift-advisor** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\gift-advisor\SKILL.md`
- **google-loops** *(auch im Fundus)* - Set up and operate the Gmail/Calendar/Contacts connector and the open-loop engine: who is waiting on the user, what they promised, and the context needed to respond. Covers painless BYO OAuth setup (e...
  `gbrain\skills\google-loops\SKILL.md`
- **idea-ingest** *(auch im Fundus)* - Ingest links, articles, tweets, and ideas into the brain. Fetch content, save to brain with analysis, create author people page, and cross-link. Use when the user shares a link or says "read this", "s...
  `gbrain\skills\idea-ingest\SKILL.md`
- **idea-lineage** *(auch im Fundus)* - Trace one idea's evolution through the brain: first mention, best articulation, related concepts, reversals, contradictions, abandoned branches, and the current live version. Use for single-idea conce...
  `gbrain\skills\idea-lineage\SKILL.md`
- **ingest** *(auch im Fundus)* - Route content to specialized ingestion skills. Detects input type and delegates.
  `gbrain\skills\ingest\SKILL.md`
- **investor-update-ingest** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\investor-update-ingest\SKILL.md`
- **maintain** *(auch im Fundus)* - Brain health checks: back-link enforcement, citation audit, filing validation, stale info detection, orphan pages, and benchmarks. Use when asked to check brain health, run maintenance, or audit quali...
  `gbrain\skills\maintain\SKILL.md`
- **measure-before-you-fix** *(auch im Fundus)* - Before fixing a slow/stale/timeout alert, measure the step yourself. Kill the theory with a stopwatch, not a code change. Measure-first ops triage for temporal alerts (stale, timeout, freshness, wedge...
  `gbrain\skills\measure-before-you-fix\SKILL.md`
- **media-ingest** *(auch im Fundus)* - Ingest video, audio, PDF, book, screenshot, and GitHub repo content into the brain. Multi-format handling with entity extraction and backlink propagation. Covers video-ingest, youtube-ingest, and book...
  `gbrain\skills\media-ingest\SKILL.md`
- **meeting-ingestion** *(auch im Fundus)* - Ingest meeting transcripts from ANY meeting recorder into brain pages with attendee enrichment, entity propagation, and timeline merge. One unified pipeline: normalize the source into a standard trans...
  `gbrain\skills\meeting-ingestion\SKILL.md`
- **meeting-prep** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-compact-resolver\skills\meeting-prep\SKILL.md`
- **migrate** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\migrate\SKILL.md`
- **migrate** *(auch im Fundus)* - Universal migration from Obsidian, Notion, Logseq, markdown, CSV, JSON, Roam
  `gbrain\skills\migrate\SKILL.md`
- **minion-orchestrator** *(auch im Fundus)* - Unified Minions skill for both deterministic shell jobs and LLM subagent orchestration. Replaces the older `gbrain-jobs` routing intent. Use when: submitting gbrain jobs, shell/background tasks, spawn...
  `gbrain\skills\minion-orchestrator\SKILL.md`
- **missing-brain-first** *(auch im Fundus)* - External-lookup skill with NO brain-first compliance
  `gbrain\test\fixtures\brain-first-skills\missing-brain-first\SKILL.md`
- **multi-pattern** *(auch im Fundus)* - Skill that uses multiple external tools without compliance
  `gbrain\test\fixtures\brain-first-skills\multi-pattern\SKILL.md`
- **negation-prose** *(auch im Fundus)* - Skill where brain reference precedes a negation-prose mention
  `gbrain\test\fixtures\brain-first-skills\negation-prose\SKILL.md`
- **no-external** *(auch im Fundus)* - Skill that operates purely on local state
  `gbrain\test\fixtures\brain-first-skills\no-external\SKILL.md`
- **perplexity-research** *(auch im Fundus)* - Brain-augmented web research. Sends brain context about a topic to Perplexity, which searches the web with citations and returns what is NEW vs what the brain already knows. Use for entity enrichment,...
  `gbrain\skills\perplexity-research\SKILL.md`
- **postgres-adopt** *(auch im Fundus)* - Detect which gbrain engine is in use (PGLite vs Postgres), prefer Postgres for agent-harness installs, install/provision Postgres (Supabase discovery via SUPABASE_ACCESS_TOKEN, local Postgres, opt-in ...
  `gbrain\skills\postgres-adopt\SKILL.md`
- **publish** *(auch im Fundus)* - Share brain pages as beautiful password-protected HTML with zero LLM calls
  `gbrain\skills\publish\SKILL.md`
- **query** *(auch im Fundus)* - Answer questions using the brain's knowledge with 3-layer search, synthesis, and citation propagation. Use when the user asks a question, wants a lookup, or needs information from the brain.
  `gbrain\skills\query\SKILL.md`
- **query** *(auch im Fundus)* - Look up brain pages in the generic agent-workspace fixture.
  `gbrain\test\fixtures\generic-agents-workspace\skills\query\SKILL.md`
- **query** *(auch im Fundus)* - Look up brain pages in the OpenClaw reference fixture.
  `gbrain\test\fixtures\openclaw-reference-minimal\skills\query\SKILL.md`
- **query** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\query\SKILL.md`
- **query-helper** *(auch im Fundus)*
  `gbrain\test\fixtures\skill-catalog\skills\query-helper\SKILL.md`
- **reference-pack** *(auch im Fundus)* - Reference skill demonstrating the 10/10 skillpack contract. Adds a
  `gbrain\examples\skillpack-reference\skills\reference-pack\SKILL.md`
- **repo-architecture** *(auch im Fundus)* - Where new brain files go. Decision protocol for filing brain pages by primary subject, not by format or source. Reference for all brain-writing skills.
  `gbrain\skills\repo-architecture\SKILL.md`
- **reports** *(auch im Fundus)* - Save and load timestamped reports. Keyword routing for fast lookup. Cron jobs save output as reports; the agent or user queries them by keyword. Includes the Actionability Gate: delivery-time link che...
  `gbrain\skills\reports\SKILL.md`
- **research-compendium** *(auch im Fundus)* - Deep-research a topic end to end and produce a permanent, reusable knowledge asset: archive every primary source verbatim (gated by the user's privacy/retention posture), write one 1:1 summary per sou...
  `gbrain\skills\research-compendium\SKILL.md`
- **resolve-before-asking** *(auch im Fundus)* - Gate on identity questions to the user. Before any "who is X?" (or role / relationship question) reaches the user, exhaust the brain's lookup chain: think → search + page read → mounted sources → time...
  `gbrain\skills\resolve-before-asking\SKILL.md`
- **retrieval-reflex** *(auch im Fundus)* - When/what to retrieve — open the brain page for a salient entity before answering from memory.
  `gbrain\recipes\retrieval-reflex\skills\retrieval-reflex\SKILL.md`
- **schema-author** *(auch im Fundus)* - Evolve your brain's schema pack. Add page types, propose new ones from corpus scans, backfill page.type on existing pages, audit pack health. Triggers when an agent notices untyped pages, custom domai...
  `gbrain\skills\schema-author\SKILL.md`
- **schema-unify** *(auch im Fundus)* - Migrate a brain from gbrain-base (or any pack) to gbrain-base-v2's 14-canonical-type taxonomy via gbrain onboard --check + the unify-types Minion handler. Collapses 94 noisy types to 15 canonical with...
  `gbrain\skills\schema-unify\SKILL.md`
- **setup** *(auch im Fundus)*
  `gbrain\test\fixtures\openclaw-mixed-merge\skills\setup\SKILL.md`
- **setup** *(auch im Fundus)* - Add keyless GBrain memory to an existing agent, or connect a hosted brain while preserving identity and configuration
  `gbrain\skills\setup\SKILL.md`
- **signal-detector** *(auch im Fundus)* - Always-on ambient signal capture for the OpenClaw reference fixture.
  `gbrain\test\fixtures\openclaw-reference-minimal\skills\signal-detector\SKILL.md`
- **signal-detector** *(auch im Fundus)* - Opt-in ambient signal capture. After explicit enablement, applies on substantive inbound messages to detect original thinking and entity mentions. Use an authorized sub-agent where supported; otherwis...
  `gbrain\skills\signal-detector\SKILL.md`
- **skill-autobench** *(auch im Fundus)* - Author an eval for an existing skill from its REAL usage history, not its spec. Mine invocations from the brain's conversation archive (conversations/) and per-harness session transcripts — a user cor...
  `gbrain\skills\skill-autobench\SKILL.md`
- **skill-creator** *(auch im Fundus)* - Create new skills following the GBrain conformance standard. Generates SKILL.md with frontmatter, Contract, Phases, Output Format, and Anti-Patterns. Checks MECE against existing skills. Updates manif...
  `gbrain\skills\skill-creator\SKILL.md`
- **skillify** *(auch im Fundus)* - The meta skill. Turn any raw feature into a properly-skilled, tested, resolvable unit of agent capability. Idempotent: running on an existing skill improves it (bug fix, new input, quality pass) inste...
  `gbrain\skills\skillify\SKILL.md`
- **skill-optimizer** *(auch im Fundus)* - Self-evolving skill optimization via SkillOpt-paper-grounded text-space optimizer.
  `gbrain\skills\skill-optimizer\SKILL.md`
- **skillpack-check** *(auch im Fundus)* - Run `gbrain skillpack-check` to produce an agent-readable JSON health report for the gbrain install. Wraps `gbrain doctor` + `gbrain apply-migrations --list` so a host agent (your OpenClaw's morning-b...
  `gbrain\skills\skillpack-check\SKILL.md`
- **skillpack-harvest** *(auch im Fundus)* - Lift a proven skill from a host repo (e.g. your OpenClaw fork) back into gbrain's bundle so other clients can scaffold it. Editorial workflow: the CLI does the file copy + privacy lint; this skill dri...
  `gbrain\skills\skillpack-harvest\SKILL.md`
- **smoke-test** *(auch im Fundus)* - Health smoke tests + auto-fix for gbrain installs (and OpenClaw services when present). Run after machine/container restarts or whenever something seems broken. Tests critical services, auto-fixes bou...
  `gbrain\skills\smoke-test\SKILL.md`
- **soul-audit** *(auch im Fundus)* - Re-run or deepen the agent's identity interview. Drives the SHARED bootstrap answer bank (state/interview.json) via `gbrain bootstrap interview --set/--show/--confirm`, then re-renders the identity fi...
  `gbrain\skills\soul-audit\SKILL.md`
- **strategic-reading** *(auch im Fundus)* - Read a book, article, transcript, or case study through the lens of a specific strategic problem you're facing. Produces an applied playbook that maps the source onto the problem and gives short/mediu...
  `gbrain\skills\strategic-reading\SKILL.md`
- **testing** *(auch im Fundus)* - Skill validation framework PLUS daily test-suite health and regression intelligence. Validates skill conformance (frontmatter, manifest coverage, resolver coverage). Runs the project test suite in tie...
  `gbrain\skills\testing\SKILL.md`
- **two-tier-extraction** *(auch im Fundus)* - Tiered LLM extraction pattern for large corpus processing (email archives, document dumps, transcript libraries). A utility-tier model triages and classifies at speed; the reasoning tier does the defa...
  `gbrain\skills\two-tier-extraction\SKILL.md`
- **typo-frontmatter** *(auch im Fundus)* - Skill with typo in brain_first declaration
  `gbrain\test\fixtures\brain-first-skills\typo-frontmatter\SKILL.md`
- **voice-note-ingest** *(auch im Fundus)* - Ingest a voice note with exact-phrasing preservation (never paraphrased). Routes content to originals/, concepts/, people/, companies/, ideas/, personal/, or voice-notes/ based on a decision tree. The...
  `gbrain\skills\voice-note-ingest\SKILL.md`
- **voice-persona-mars** *(auch im Fundus)* - Route to Mars (introspective thought partner / demo showman voice persona). Used when the operator wants depth, meaning, or impressive social demos rather than logistics. Mars handles SOLO mode (philo...
  `gbrain\recipes\agent-voice\skills\voice-persona-mars\SKILL.md`
- **voice-persona-venus** *(auch im Fundus)* - Route to Venus (sharp executive-assistant voice persona). Used for logistics — calendar, tasks, recent messages, brain lookups — at sub-second phone-call latency. The default voice persona unless DEFA...
  `gbrain\recipes\agent-voice\skills\voice-persona-venus\SKILL.md`
- **voice-post-call** *(auch im Fundus)* - Post-call handling for a voice session — turn the transcript into a brain page, post the summary to the operator's messaging surface, archive the audio. The pipeline is the contract; the firing paths ...
  `gbrain\recipes\agent-voice\skills\voice-post-call\SKILL.md`
- **webhook-transforms** *(auch im Fundus)* - Generic framework for converting external events (SMS, meetings, social mentions) into brain-ingestible signals. Define a transform function, register a webhook URL, and incoming events get processed ...
  `gbrain\skills\webhook-transforms\SKILL.md`

## graphify (1)

- **graphify** - Use for any question about a codebase, its architecture, file relationships, or project content — especially when graphify-out/ exists, where the question should be treated as a graphify query first. ...
  `graphify\graphify\skill.md`

## kraken-cli (59)

- **kraken-alert-patterns** *(auch im Fundus)* - Price alerts, threshold monitoring, and notification triggers for agents.
  `kraken-cli\skills\kraken-alert-patterns\SKILL.md`
- **kraken-autonomy-levels** *(auch im Fundus)* - Progress from manual trading to full agent autonomy with controlled risk at each level.
  `kraken-cli\skills\kraken-autonomy-levels\SKILL.md`
- **kraken-basis-trading** *(auch im Fundus)* - Capture the spot-futures price spread with delta-neutral basis trades.
  `kraken-cli\skills\kraken-basis-trading\SKILL.md`
- **kraken-dca-strategy** *(auch im Fundus)* - Dollar cost averaging with scheduled buys and performance tracking.
  `kraken-cli\skills\kraken-dca-strategy\SKILL.md`
- **kraken-earn-staking** *(auch im Fundus)* - Discover staking strategies, allocate funds, and track earn positions.
  `kraken-cli\skills\kraken-earn-staking\SKILL.md`
- **kraken-error-recovery** *(auch im Fundus)* - Handle order failures, network errors, and duplicate submissions safely.
  `kraken-cli\skills\kraken-error-recovery\SKILL.md`
- **kraken-fee-optimization** *(auch im Fundus)* - Minimize trading fees through maker orders, volume tiers, and fee-aware execution.
  `kraken-cli\skills\kraken-fee-optimization\SKILL.md`
- **kraken-funding-carry** *(auch im Fundus)* - Earn funding rate payments by positioning on the paying side of perpetuals.
  `kraken-cli\skills\kraken-funding-carry\SKILL.md`
- **kraken-funding-ops** *(auch im Fundus)* - Manage deposits, withdrawals, and wallet transfers safely.
  `kraken-cli\skills\kraken-funding-ops\SKILL.md`
- **kraken-futures-risk** *(auch im Fundus)* - Futures-specific risk management: leverage, funding rates, margin, and liquidation awareness.
  `kraken-cli\skills\kraken-futures-risk\SKILL.md`
- **kraken-futures-trading** *(auch im Fundus)* - Place, manage, and monitor futures orders across the full lifecycle.
  `kraken-cli\skills\kraken-futures-trading\SKILL.md`
- **kraken-grid-trading** *(auch im Fundus)* - Grid trading strategy with layered buy and sell orders across a price range.
  `kraken-cli\skills\kraken-grid-trading\SKILL.md`
- **kraken-lab-experiment** *(auch im Fundus)* - Run the Autoresearch Lab lifecycle end-to-end: freeze a hypothesis with mechanical success criteria and a sealed session plan, drive recorded and replayed paper runs, score them honestly, and read the...
  `kraken-cli\skills\kraken-lab-experiment\SKILL.md`
- **kraken-liquidation-guard** *(auch im Fundus)* - Prevent futures liquidation through margin monitoring and emergency procedures.
  `kraken-cli\skills\kraken-liquidation-guard\SKILL.md`
- **kraken-market-intel** *(auch im Fundus)* - Read market state with low-noise data pulls and streaming updates.
  `kraken-cli\skills\kraken-market-intel\SKILL.md`
- **kraken-mcp-integration** *(auch im Fundus)* - Connect MCP clients to kraken-cli for native tool calling without subprocess wrappers.
  `kraken-cli\skills\kraken-mcp-integration\SKILL.md`
- **kraken-multi-pair** *(auch im Fundus)* - Monitor multiple trading pairs simultaneously for screening and comparison.
  `kraken-cli\skills\kraken-multi-pair\SKILL.md`
- **kraken-order-types** *(auch im Fundus)* - Complete reference for all spot and futures order types and modifiers.
  `kraken-cli\skills\kraken-order-types\SKILL.md`
- **kraken-paper-strategy** *(auch im Fundus)* - Test strategy logic on paper trading before touching live funds.
  `kraken-cli\skills\kraken-paper-strategy\SKILL.md`
- **kraken-paper-to-live** *(auch im Fundus)* - Promote a validated paper strategy to live trading, gated on lab experiment evidence plus safety checks.
  `kraken-cli\skills\kraken-paper-to-live\SKILL.md`
- **kraken-playground** *(auch im Fundus)* - Paper-trading sandbox over workspace sessions: record live market data and agent decisions inside a session window, replay and score it later.
  `kraken-cli\skills\kraken-playground\SKILL.md`
- **kraken-portfolio-intel** *(auch im Fundus)* - Portfolio analysis, P&L tracking, trade history, and export reports.
  `kraken-cli\skills\kraken-portfolio-intel\SKILL.md`
- **kraken-rate-limits** *(auch im Fundus)* - Understand Kraken API rate limits and adapt agent behavior when limits are hit.
  `kraken-cli\skills\kraken-rate-limits\SKILL.md`
- **kraken-rebalancing** *(auch im Fundus)* - Portfolio rebalancing to maintain target allocations across assets.
  `kraken-cli\skills\kraken-rebalancing\SKILL.md`
- **kraken-risk-operations** *(auch im Fundus)* - Operational risk controls for live agent trading sessions.
  `kraken-cli\skills\kraken-risk-operations\SKILL.md`
- **kraken-setup** *(auch im Fundus)* - Install kraken-cli, create API credentials, and go from paper trading to live in under five minutes.
  `kraken-cli\skills\kraken-setup\SKILL.md`
- **kraken-shared** *(auch im Fundus)* - Shared runtime contract for kraken-cli: auth, invocation, parsing, and safety.
  `kraken-cli\skills\kraken-shared\SKILL.md`
- **kraken-spot-execution** *(auch im Fundus)* - Execute spot orders with validation, confirmation gates, and post-trade checks.
  `kraken-cli\skills\kraken-spot-execution\SKILL.md`
- **kraken-stop-take-profit** *(auch im Fundus)* - Manage stop-loss and take-profit orders for risk-bounded positions.
  `kraken-cli\skills\kraken-stop-take-profit\SKILL.md`
- **kraken-subaccount-ops** *(auch im Fundus)* - Create and manage subaccounts with inter-account transfers.
  `kraken-cli\skills\kraken-subaccount-ops\SKILL.md`
- **kraken-tax-export** *(auch im Fundus)* - Export trade history, ledgers, and cost basis data for tax reporting.
  `kraken-cli\skills\kraken-tax-export\SKILL.md`
- **kraken-twap-execution** *(auch im Fundus)* - Execute large orders as time-weighted slices to reduce market impact.
  `kraken-cli\skills\kraken-twap-execution\SKILL.md`
- **kraken-ws-streaming** *(auch im Fundus)* - Real-time data streaming via WebSocket for spot and futures.
  `kraken-cli\skills\kraken-ws-streaming\SKILL.md`
- **recipe-basis-trade-entry** *(auch im Fundus)* - Enter a spot-futures basis trade when the premium exceeds a target threshold.
  `kraken-cli\skills\recipe-basis-trade-entry\SKILL.md`
- **recipe-daily-pnl-report** *(auch im Fundus)* - Generate a daily profit and loss summary from trades and balances.
  `kraken-cli\skills\recipe-daily-pnl-report\SKILL.md`
- **recipe-drawdown-circuit-breaker** *(auch im Fundus)* - Automatically stop trading when portfolio drawdown exceeds a threshold.
  `kraken-cli\skills\recipe-drawdown-circuit-breaker\SKILL.md`
- **recipe-earn-yield-compare** *(auch im Fundus)* - Compare earn strategy yields across assets and lock types to find the best rate.
  `kraken-cli\skills\recipe-earn-yield-compare\SKILL.md`
- **recipe-emergency-flatten** *(auch im Fundus)* - Cancel all orders and close all positions in an emergency.
  `kraken-cli\skills\recipe-emergency-flatten\SKILL.md`
- **recipe-fee-tier-progress** *(auch im Fundus)* - Track 30-day trading volume progress toward the next fee tier.
  `kraken-cli\skills\recipe-fee-tier-progress\SKILL.md`
- **recipe-funding-rate-scan** *(auch im Fundus)* - Scan perpetual contracts for attractive funding rate carry opportunities.
  `kraken-cli\skills\recipe-funding-rate-scan\SKILL.md`
- **recipe-futures-hedge-spot** *(auch im Fundus)* - Hedge a spot holding with a short futures position to lock in value.
  `kraken-cli\skills\recipe-futures-hedge-spot\SKILL.md`
- **recipe-launch-grid-bot** *(auch im Fundus)* - Deploy a grid trading bot with paper validation and live safety controls.
  `kraken-cli\skills\recipe-launch-grid-bot\SKILL.md`
- **recipe-morning-market-brief** *(auch im Fundus)* - Generate a morning market summary with prices, volume, and portfolio state.
  `kraken-cli\skills\recipe-morning-market-brief\SKILL.md`
- **recipe-multi-pair-breakout-watch** *(auch im Fundus)* - Monitor multiple pairs for price breakouts from defined ranges.
  `kraken-cli\skills\recipe-multi-pair-breakout-watch\SKILL.md`
- **recipe-paper-strategy-backtest** *(auch im Fundus)* - Backtest a trading strategy using paper trading against live prices.
  `kraken-cli\skills\recipe-paper-strategy-backtest\SKILL.md`
- **recipe-playground-dca** *(auch im Fundus)* - Example driver: drive a time-based dollar-cost-averaging hypothesis into a recorded session.
  `kraken-cli\skills\recipe-playground-dca\SKILL.md`
- **recipe-playground-dca-triggered** *(auch im Fundus)* - Example driver: dip-triggered dollar-cost-averaging on a live WebSocket stream, recorded to a session.
  `kraken-cli\skills\recipe-playground-dca-triggered\SKILL.md`
- **recipe-playground-price-alert** *(auch im Fundus)* - Example driver: drive a price-level-alert hypothesis into a recorded session.
  `kraken-cli\skills\recipe-playground-price-alert\SKILL.md`
- **recipe-playground-rebalance** *(auch im Fundus)* - Example driver: drive a portfolio-rebalance hypothesis into a recorded session.
  `kraken-cli\skills\recipe-playground-rebalance\SKILL.md`
- **recipe-playground-webhook** *(auch im Fundus)* - Example driver: turn incoming webhook signals into validated paper trades inside a recorded session.
  `kraken-cli\skills\recipe-playground-webhook\SKILL.md`
- **recipe-portfolio-snapshot-csv** *(auch im Fundus)* - Export a portfolio snapshot with balances and valuations to CSV.
  `kraken-cli\skills\recipe-portfolio-snapshot-csv\SKILL.md`
- **recipe-price-level-alerts** *(auch im Fundus)* - Set up price level alerts that notify when key levels are crossed.
  `kraken-cli\skills\recipe-price-level-alerts\SKILL.md`
- **recipe-session-post-mortem** *(auch im Fundus)* - Narrate a recorded session's post-mortem: replay the window, explain the P&L decomposition in plain terms, and deliver a presentation-ready summary.
  `kraken-cli\skills\recipe-session-post-mortem\SKILL.md`
- **recipe-start-dca-bot** *(auch im Fundus)* - Set up and run a dollar cost averaging bot from paper test to live.
  `kraken-cli\skills\recipe-start-dca-bot\SKILL.md`
- **recipe-subaccount-capital-rotation** *(auch im Fundus)* - Rotate capital between subaccounts based on strategy performance.
  `kraken-cli\skills\recipe-subaccount-capital-rotation\SKILL.md`
- **recipe-track-orderbook-depth** *(auch im Fundus)* - Monitor order book depth and bid-ask imbalance for liquidity signals.
  `kraken-cli\skills\recipe-track-orderbook-depth\SKILL.md`
- **recipe-trailing-stop-runner** *(auch im Fundus)* - Ride a trend with a trailing stop that locks in profits on reversal.
  `kraken-cli\skills\recipe-trailing-stop-runner\SKILL.md`
- **recipe-weekly-rebalance** *(auch im Fundus)* - Run a weekly portfolio rebalance to maintain target asset allocations.
  `kraken-cli\skills\recipe-weekly-rebalance\SKILL.md`
- **recipe-withdrawal-to-cold-storage** *(auch im Fundus)* - Safely withdraw funds to a pre-approved cold storage address.
  `kraken-cli\skills\recipe-withdrawal-to-cold-storage\SKILL.md`

## laya (1)

- **typer** - Typer best practices and conventions. Use when working with Typer CLIs. Keeps Typer code clean and up to date with the latest features and patterns, updated with new versions. Write new code or refact...
  `laya\.venv\Lib\site-packages\typer\.agents\skills\typer\SKILL.md`

## obsidian-skills (6)

- **defuddle** - Extract clean Markdown from HTML pages with Defuddle CLI.
  `obsidian-skills\skills\defuddle\SKILL.md`
- **json-canvas** *(auch im Fundus)* - Create and edit JSON Canvas files (.canvas) with nodes, edges, groups, and connections. Use when working with .canvas files, creating visual canvases, mind maps, flowcharts, or when the user mentions ...
  `obsidian-skills\skills\json-canvas\SKILL.md`
- **knap** - Render Markdown from templates and structured data using Knap CLI. Use when the user asks to apply a Knap template, turn JSON or CSV data into notes, batch-generate Markdown files, or format Defuddle ...
  `obsidian-skills\skills\knap\SKILL.md`
- **obsidian-bases** *(auch im Fundus)* - Create and edit Obsidian Bases (.base files) with views, filters, formulas, and summaries. Use when working with .base files, creating database-like views of notes, or when the user mentions Bases, ta...
  `obsidian-skills\skills\obsidian-bases\SKILL.md`
- **obsidian-cli** *(auch im Fundus)* - Interact with Obsidian vaults using the Obsidian CLI to read, create, search, and manage notes, tasks, properties, and more. Also supports plugin and theme development with commands to reload plugins,...
  `obsidian-skills\skills\obsidian-cli\SKILL.md`
- **obsidian-markdown** *(auch im Fundus)* - Create and edit Obsidian Flavored Markdown with wikilinks, embeds, callouts, properties, and other Obsidian-specific syntax. Use when working with .md files in Obsidian, or when the user mentions wiki...
  `obsidian-skills\skills\obsidian-markdown\SKILL.md`

## odysseus (2)

- **odysseus** - Use when the user asks Codex to read or write Odysseus data (todos, email, calendar, memory, documents) or to launch/monitor/stop a Cookbook model-serve task through the scoped Codex Agent API. Requir...
  `odysseus\integrations\codex\skills\odysseus\SKILL.md`
- **odysseus** - Use when the user asks Claude Code to read or write Odysseus data (todos, email, calendar, memory, documents) or to launch/monitor/stop a Cookbook model-serve task through the scoped Claude Agent API....
  `odysseus\integrations\claude\skills\odysseus\SKILL.md`

## one-skill-to-rule-them-all (1)

- **task-observer** - Monitors task execution for skill improvement opportunities. Use during ANY multi-step task, agentic workflow, or work session. Captures patterns, user corrections and methodology worth preserving as ...
  `one-skill-to-rule-them-all\SKILL.md`

## openmontage (92)

- **3d-asset-generation** - Generate, reconstruct, inspect, and route production 3D assets for OpenMontage worlds using Atlas Cloud, fal.ai, licensed catalogs, and Blender.
  `openmontage\.agents\skills\3d-asset-generation\SKILL.md`
- **acestep** - AI music generation with ACE-Step 1.5 — background music, vocal tracks, covers, stem extraction for video production. Use when generating music, soundtracks, jingles, or working with audio stems. Trig...
  `openmontage\.claude\skills\acestep\SKILL.md`
- **agents** - Build voice AI agents with ElevenLabs. Use when creating voice assistants, customer service bots, interactive voice characters, or any real-time voice conversation experience.
  `openmontage\.claude\skills\agents\SKILL.md`
- **ai-video-gen** - Generate AI videos from text prompts using multiple provider gateways. Use when: (1) Generating videos from text descriptions, (2) Creating AI-generated video clips for content production, (3) Image-t...
  `openmontage\.agents\skills\ai-video-gen\SKILL.md`
- **ai-video-gen** - Generate AI videos from text prompts using multiple provider gateways. Use when: (1) Generating videos from text descriptions, (2) Creating AI-generated video clips for content production, (3) Image-t...
  `openmontage\.claude\skills\ai-video-gen\SKILL.md`
- **atlas-cloud** - Generate or edit images and videos through the Atlas Cloud gateway. Use for Atlas-hosted Seedance 2.5/2.0, Gemini Omni Flash, MiniMax H3, Seedream 5.0, GPT Image 2, Nano Banana 2, or when one ATLASCLO...
  `openmontage\.agents\skills\atlas-cloud\SKILL.md`
- **avatar-video** - Create AI avatar videos with precise control over avatars, voices, scripts, scenes, and backgrounds using HeyGen's v2 API. Use when: (1) Choosing a specific avatar and voice for a video, (2) Writing e...
  `openmontage\.claude\skills\avatar-video\SKILL.md`
- **azure-speech-to-text** - Transcribe audio to text using Azure AI Speech (Fast Transcription REST API). Use when converting audio/video to text, generating subtitles, or processing spoken content in OpenMontage. Optional cloud...
  `openmontage\.claude\skills\azure-speech-to-text\SKILL.md`
- **azure-text-to-speech** - Generate neural narration audio using Azure AI Speech (REST text-to-speech). Use when synthesizing voiceovers or narration in OpenMontage. Optional cloud TTS provider — preferred when AZURE_SPEECH_KEY...
  `openmontage\.claude\skills\azure-text-to-speech\SKILL.md`
- **beautiful-mermaid** - Render Mermaid diagrams as SVG and PNG using the Beautiful Mermaid library. Use when the user asks to render a Mermaid diagram.
  `openmontage\.claude\skills\beautiful-mermaid\SKILL.md`
- **bfl-api** - BFL FLUX API integration guide covering endpoints, async polling patterns, rate limiting, error handling, webhooks, and regional endpoints with Python and TypeScript code examples.
  `openmontage\.claude\skills\bfl-api\SKILL.md`
- **canvas-procedural-animation** - Use p5.js/canvas for local procedural character effects: particles, weather, squash/stretch, walk cycles, and environmental motion.
  `openmontage\.agents\skills\canvas-procedural-animation\SKILL.md`
- **character-animation-qa** - Review local character animation with schema checks, Playwright browser previews, frame sampling, and FFmpeg/ffprobe final output checks.
  `openmontage\.agents\skills\character-animation-qa\SKILL.md`
- **character-rigging** - Build data-driven 2D character rigs for local animation: parts, pivots, layers, constraints, views, and reusable rig packages.
  `openmontage\.agents\skills\character-rigging\SKILL.md`
- **comfyui** - Use when working with ComfyUI workflows in OpenMontage, including comfyui_image/comfyui_video/comfyui_music, custom workflow_json/workflow_path inputs, output_node selection, missing model setup, LoRA...
  `openmontage\.agents\skills\comfyui\SKILL.md`
- **create-video** - Create videos from a text prompt using HeyGen's Video Agent. Use when: (1) Creating a video from a description or idea, (2) Generating explainer, demo, or marketing videos from a prompt, (3) Making a ...
  `openmontage\.claude\skills\create-video\SKILL.md`
- **d3-viz** - Creating interactive data visualisations using d3.js. This skill should be used when creating custom charts, graphs, network diagrams, geographic visualisations, or any complex SVG-based data visualis...
  `openmontage\.claude\skills\d3-viz\SKILL.md`
- **dashscope** - DashScope (Alibaba Cloud Bailian / 阿里云百炼) integration — image generation (qwen-image-2.0-pro), text-to-speech (qwen3-tts-flash), and ASR with word-level timestamps (qwen3-asr-flash-filetrans). Use whe...
  `openmontage\.agents\skills\dashscope\SKILL.md`
- **doubao-tts** - Generate Mandarin and multilingual narration with Volcengine Doubao Speech 2.0. Use when creating Chinese voiceovers, when the user prefers Doubao/Volcengine/火山引擎/豆包 TTS, or when narration needs chara...
  `openmontage\.agents\skills\doubao-tts\SKILL.md`
- **elevenlabs** - Generate AI voiceovers, sound effects, and music using ElevenLabs APIs. Use when creating audio content for videos, podcasts, or games. Triggers include generating voiceovers, narration, dialogue, sou...
  `openmontage\.agents\skills\elevenlabs\SKILL.md`
- **elevenlabs** - Generate AI voiceovers, sound effects, and music using ElevenLabs APIs. Use when creating audio content for videos, podcasts, or games. Triggers include generating voiceovers, narration, dialogue, sou...
  `openmontage\.claude\skills\elevenlabs\SKILL.md`
- **faceswap** - Swap faces in a video using AI via the HeyGen API. Use when: (1) Replacing a face in a video with another face, (2) Face swapping from a source image onto a target video, (3) Creating personalized vid...
  `openmontage\.claude\skills\faceswap\SKILL.md`
- **fastapi** *(auch im Fundus)* - FastAPI best practices and conventions. Use when working with FastAPI APIs, Pydantic models, dependencies, streaming responses including Server-Sent Events (SSE), and serving frontend apps. Keeps Fast...
  `openmontage\.venv\Lib\site-packages\fastapi\.agents\skills\fastapi\SKILL.md`
- **ffmpeg** - Video and audio processing with FFmpeg. Use for format conversion, resizing, compression, audio extraction, and preparing assets for Remotion. Triggers include converting GIF to MP4, resizing video, e...
  `openmontage\.claude\skills\ffmpeg\SKILL.md`
- **fish-audio-tts** - Generate expressive, multilingual narration with fish.audio (S1 / S2-generation models) and reuse cloned voices via reference_id. Use when the user prefers fish.audio/Fish Audio TTS, wants a specific ...
  `openmontage\.agents\skills\fish-audio-tts\SKILL.md`
- **flux-best-practices** - Comprehensive guide for BFL FLUX image generation models. Covers prompting, T2I, I2I, structured JSON, hex colors, typography, multi-reference editing, and model-specific best practices for FLUX.2 and...
  `openmontage\.claude\skills\flux-best-practices\SKILL.md`
- **framer-motion** - Use when implementing Disney's 12 animation principles with Framer Motion in React applications
  `openmontage\.claude\skills\framer-motion\SKILL.md`
- **gemini-omni** - Generate and conversationally edit short videos with Google Gemini Omni Flash (`gemini-omni-flash-preview`). Use when: (1) iterating on a clip with natural-language edits instead of regenerating ("mak...
  `openmontage\.agents\skills\gemini-omni\SKILL.md`
- **grok-media** - xAI Grok image and video generation guide covering authentication, endpoints, prompt structure, image editing, reference-image video, and async polling.
  `openmontage\.agents\skills\grok-media\SKILL.md`
- **gsap-core** - Official GSAP skill for the core API — gsap.to(), from(), fromTo(), easing, duration, stagger, defaults, gsap.matchMedia() (responsive, prefers-reduced-motion). Use when the user asks for a JavaScript...
  `openmontage\.agents\skills\gsap-core\SKILL.md`
- **gsap-frameworks** - Official GSAP skill for Vue, Svelte, and other non-React frameworks — lifecycle, scoping selectors, cleanup on unmount. Use when the user wants animation in Vue, Nuxt, Svelte, SvelteKit, or asks about...
  `openmontage\.agents\skills\gsap-frameworks\SKILL.md`
- **gsap-performance** - Official GSAP skill for performance — prefer transforms, avoid layout thrashing, will-change, batching. Use when optimizing GSAP animations, reducing jank, or when the user asks about animation perfor...
  `openmontage\.agents\skills\gsap-performance\SKILL.md`
- **gsap-plugins** - Official GSAP skill for GSAP plugins — registration, ScrollToPlugin, ScrollSmoother, Flip, Draggable, Inertia, Observer, SplitText, ScrambleText, SVG and physics plugins, CustomEase, EasePack, CustomW...
  `openmontage\.agents\skills\gsap-plugins\SKILL.md`
- **gsap-react** - Official GSAP skill for React — useGSAP hook, refs, gsap.context(), cleanup. Use when the user wants animation in React or Next.js, or asks about GSAP with React, useGSAP, or cleanup on unmount. Recom...
  `openmontage\.agents\skills\gsap-react\SKILL.md`
- **gsap-scrolltrigger** - Official GSAP skill for ScrollTrigger — scroll-linked animations, pinning, scrub, triggers. Use when building or recommending scroll-based animation, parallax, pinned sections, or when the user asks a...
  `openmontage\.agents\skills\gsap-scrolltrigger\SKILL.md`
- **gsap-timeline** - Official GSAP skill for timelines — gsap.timeline(), position parameter, nesting, playback. Use when sequencing animations, choreographing keyframes, or when the user asks about animation sequencing, ...
  `openmontage\.agents\skills\gsap-timeline\SKILL.md`
- **gsap-utils** - Official GSAP skill for gsap.utils — clamp, mapRange, normalize, interpolate, random, snap, toArray, wrap, pipe. Use when the user asks about gsap.utils, clamp, mapRange, random, snap, toArray, wrap, ...
  `openmontage\.agents\skills\gsap-utils\SKILL.md`
- **heygen** - [DEPRECATED] Use `create-video` for prompt-based video generation or `avatar-video` for precise avatar/scene control. This legacy skill combines both workflows — the newer focused skills provide clear...
  `openmontage\.claude\skills\heygen\SKILL.md`
- **hyperframes** - READ THIS FIRST for any request to make, create, edit, animate, or render a video, animation, or motion graphic — a promo, explainer, captioned clip, title card, overlay, or any composition. HyperFram...
  `openmontage\.agents\skills\hyperframes\SKILL.md`
- **hyperframes-animation** - All animation knowledge for HyperFrames — atomic motion rules, multi-phase scene blueprints, scene transitions, broader motion-design techniques, AND the seven runtime adapters (GSAP default, plus Lot...
  `openmontage\.agents\skills\hyperframes-animation\SKILL.md`
- **hyperframes-cli** - HyperFrames CLI dev loop. Use when running npx hyperframes init, add, catalog, capture, lint, validate, inspect, layout, snapshot, preview, play, render, publish, lambda, doctor, browser, info, upgrad...
  `openmontage\.agents\skills\hyperframes-cli\SKILL.md`
- **hyperframes-core** - The HyperFrames composition contract — build one renderable project. Use for composition structure, the `data-*` timing attributes, `class=
  `openmontage\.agents\skills\hyperframes-core\SKILL.md`
- **hyperframes-creative** - Non-animation creative direction for HyperFrames videos. Use for design spec (frame.md / design.md) handling, palettes, typography, narration, beat planning, audio-reactive visuals, composition patter...
  `openmontage\.agents\skills\hyperframes-creative\SKILL.md`
- **hyperframes-media** - Audio and media assets for HyperFrames compositions, produced by one shared audio engine (`scripts/audio.mjs`) — multi-provider TTS (HeyGen / ElevenLabs / Kokoro local), background music + sound effec...
  `openmontage\.agents\skills\hyperframes-media\SKILL.md`
- **hyperframes-registry** - Install and wire registry blocks and components into HyperFrames compositions. Use when running hyperframes add, installing a block or component, wiring an installed item into index.html, or working w...
  `openmontage\.agents\skills\hyperframes-registry\SKILL.md`
- **kling-official** - Official Kling direct API guidance for OpenMontage providers. Use before calling `kling_official_video`, `kling_official_image`, `kling_tts`, `kling_avatar`, or `kling_lip_sync`.
  `openmontage\.agents\skills\kling-official\SKILL.md`
- **lottie-bodymovin** - Use when implementing Disney's 12 animation principles with Lottie animations exported from After Effects
  `openmontage\.claude\skills\lottie-bodymovin\SKILL.md`
- **ltx2** - AI video generation with LTX-2.3 22B — text-to-video, image-to-video clips for video production. Use when generating video clips, animating images, creating b-roll, animated backgrounds, or motion con...
  `openmontage\.claude\skills\ltx2\SKILL.md`
- **lyria** - Generate and validate music with Google Lyria 3 through the Gemini Interactions API. Use before calling OpenMontage `google_music`, designing Lyria 3 Clip or Pro prompts, using image-to-music or custo...
  `openmontage\.agents\skills\lyria\SKILL.md`
- **manimce-best-practices** - Trigger when: (1) User mentions "manim" or "Manim Community" or "ManimCE", (2) Code contains `from manim import *`, (3) User runs `manim` CLI commands, (4) Working with Scene, MathTex, Create(), or Ma...
  `openmontage\.claude\skills\manimce-best-practices\SKILL.md`
- **manim-composer** - Trigger when: (1) User wants to create an educational/explainer video, (2) User has a vague concept they want visualized, (3) User mentions "3b1b style" or "explain like 3Blue1Brown", (4) User wants t...
  `openmontage\.claude\skills\manim-composer\SKILL.md`
- **manimgl-best-practices** - Trigger when: (1) User mentions "manimgl" or "ManimGL" or "3b1b manim", (2) Code contains `from manimlib import *`, (3) User runs `manimgl` CLI commands, (4) Working with InteractiveScene, self.frame,...
  `openmontage\.claude\skills\manimgl-best-practices\SKILL.md`
- **media-use** - Agent Media OS — resolve any media need (BGM, SFX, image, icon) into a frozen local file + ledger record. One verb (`resolve`) handles the full cascade — project cache, global cache, HeyGen catalog se...
  `openmontage\.agents\skills\media-use\SKILL.md`
- **minimax-h3** - Generate MiniMax H3 (Hailuo 3.0) video through the official MiniMax v2 API, fal.ai, Runway, ComfyUI Partner Nodes, or local open weights in ComfyUI. Use for 4-15 second 2K clips, first/last-frame anim...
  `openmontage\.agents\skills\minimax-h3\SKILL.md`
- **motion-graphics** - Use when the user wants a short, design-led motion graphic where motion is the message: kinetic typography, stat or number count-up, chart/data-viz hit, logo sting, brand lockup, lower-third, callout,...
  `openmontage\.agents\skills\motion-graphics\SKILL.md`
- **music** - Generate music using ElevenLabs Music API. Use when creating instrumental tracks, songs with lyrics, background music, jingles, or any AI-generated music composition. Supports prompt-based generation,...
  `openmontage\.claude\skills\music\SKILL.md`
- **music-to-video** - Use when the user has a music track (an audio file, or a video to pull audio from) and wants a beat-synced HyperFrames video, calm to hard-hitting. The music drives everything: one analyzer reads it o...
  `openmontage\.agents\skills\music-to-video\SKILL.md`
- **playwright-recording** - Record browser interactions as video using Playwright. Use for capturing demo videos, app walkthroughs, and UI flows for Remotion videos. Triggers include recording a demo, capturing browser video, sc...
  `openmontage\.claude\skills\playwright-recording\SKILL.md`
- **pose-library-design** - Design reusable 2D character pose libraries, action cycles, and expression states for data-driven animation.
  `openmontage\.agents\skills\pose-library-design\SKILL.md`
- **remotion** - Toolkit-specific Remotion patterns — custom transitions, shared components, and project conventions. For core Remotion framework knowledge (hooks, animations, rendering, etc.), see the `remotion-offic...
  `openmontage\.claude\skills\remotion\SKILL.md`
- **remotion-best-practices** - Best practices for Remotion - Video creation in React
  `openmontage\.claude\skills\remotion-best-practices\SKILL.md`
- **remotion-to-hyperframes** - 'Port an existing Remotion (React) composition to HyperFrames HTML. Use ONLY when the user explicitly asks to port/convert/migrate/translate a Remotion source. Do NOT use: (a) authoring a new HyperFra...
  `openmontage\.agents\skills\remotion-to-hyperframes\SKILL.md`
- **seedance-2-0** - Generate cinematic clips with ByteDance Seedance 2.0 — the preferred premium video model in OpenMontage when a paid gateway is configured. Use when: (1) producing trailers, teasers, hype edits, or pre...
  `openmontage\.agents\skills\seedance-2-0\SKILL.md`
- **seedance-2-5** - Generate 4-30 second cinematic video with ByteDance Seedance 2.5 through fal.ai, Volcengine Ark, Runway, or ComfyUI Partner Nodes. Use for long single generations, synchronized audio, and large multim...
  `openmontage\.agents\skills\seedance-2-5\SKILL.md`
- **setup-api-key** - Guides users through setting up an ElevenLabs API key for ElevenLabs MCP tools. Use when the user needs to configure an ElevenLabs API key, when ElevenLabs tools fail due to missing API key, or when t...
  `openmontage\.claude\skills\setup-api-key\SKILL.md`
- **sound-effects** - Generate sound effects from text descriptions using ElevenLabs. Use when creating sound effects, generating audio textures, producing ambient sounds, cinematic impacts, UI sounds, or any audio that is...
  `openmontage\.claude\skills\sound-effects\SKILL.md`
- **speech-to-text** - Transcribe audio to text using ElevenLabs Scribe v2. Use when converting audio/video to text, generating subtitles, transcribing meetings, or processing spoken content.
  `openmontage\.claude\skills\speech-to-text\SKILL.md`
- **svg-character-animation** - Animate SVG character rigs with GSAP, CSS transforms, Remotion frame control, and HyperFrames-compatible browser previews.
  `openmontage\.agents\skills\svg-character-animation\SKILL.md`
- **synthetic-screen-recording** - Synthetic terminal-style screen recording guidance for Remotion `TerminalScene`.
  `openmontage\.agents\skills\synthetic-screen-recording\SKILL.md`
- **tailwind-design-system** - Build scalable design systems with Tailwind CSS v4, design tokens, component libraries, and responsive patterns. Use when creating component libraries, implementing design systems, or standardizing UI...
  `openmontage\.claude\skills\tailwind-design-system\SKILL.md`
- **text-to-speech** - Generate speech audio from text using HeyGen's Starfish TTS model. Use when: (1) Generating standalone speech audio files from text, (2) Converting text to speech with voice selection, speed, and pitc...
  `openmontage\.claude\skills\text-to-speech\SKILL.md`
- **threejs-animation** - Three.js animation - keyframe animation, skeletal animation, morph targets, animation mixing. Use when animating objects, playing GLTF animations, creating procedural motion, or blending animations.
  `openmontage\.claude\skills\threejs-animation\SKILL.md`
- **threejs-fundamentals** - Three.js scene setup, cameras, renderer, Object3D hierarchy, coordinate systems. Use when setting up 3D scenes, creating cameras, configuring renderers, managing object hierarchies, or working with tr...
  `openmontage\.claude\skills\threejs-fundamentals\SKILL.md`
- **threejs-geometry** - Three.js geometry creation - built-in shapes, BufferGeometry, custom geometry, instancing. Use when creating 3D shapes, working with vertices, building custom meshes, or optimizing with instanced rend...
  `openmontage\.claude\skills\threejs-geometry\SKILL.md`
- **threejs-interaction** - Three.js interaction - raycasting, controls, mouse/touch input, object selection. Use when handling user input, implementing click detection, adding camera controls, or creating interactive 3D experie...
  `openmontage\.claude\skills\threejs-interaction\SKILL.md`
- **threejs-lighting** - Three.js lighting - light types, shadows, environment lighting. Use when adding lights, configuring shadows, setting up IBL, or optimizing lighting performance.
  `openmontage\.claude\skills\threejs-lighting\SKILL.md`
- **threejs-loaders** - Three.js asset loading - GLTF, textures, images, models, async patterns. Use when loading 3D models, textures, HDR environments, or managing loading progress.
  `openmontage\.claude\skills\threejs-loaders\SKILL.md`
- **threejs-materials** - Three.js materials - PBR, basic, phong, shader materials, material properties. Use when styling meshes, working with textures, creating custom shaders, or optimizing material performance.
  `openmontage\.claude\skills\threejs-materials\SKILL.md`
- **threejs-postprocessing** - Three.js post-processing - EffectComposer, bloom, DOF, screen effects. Use when adding visual effects, color grading, blur, glow, or creating custom screen-space shaders.
  `openmontage\.claude\skills\threejs-postprocessing\SKILL.md`
- **threejs-shaders** - Three.js shaders - GLSL, ShaderMaterial, uniforms, custom effects. Use when creating custom visual effects, modifying vertices, writing fragment shaders, or extending built-in materials.
  `openmontage\.claude\skills\threejs-shaders\SKILL.md`
- **threejs-textures** - Three.js textures - texture types, UV mapping, environment maps, texture settings. Use when working with images, UV coordinates, cubemaps, HDR environments, or texture optimization.
  `openmontage\.claude\skills\threejs-textures\SKILL.md`
- **threejs-world-generation** - Build deterministic, editable, free-viewpoint Three.js worlds from text or structured briefs. Use for cinematic 3D terrain, semantic regions, procedural biomes, explicit landmarks, environmental scatt...
  `openmontage\.agents\skills\threejs-world-generation\SKILL.md`
- **vercel-composition-patterns** - React composition patterns that scale. Use when refactoring components with
  `openmontage\.claude\skills\vercel-composition-patterns\SKILL.md`
- **vercel-react-best-practices** - React and Next.js performance optimization guidelines from Vercel Engineering. This skill should be used when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patter...
  `openmontage\.claude\skills\vercel-react-best-practices\SKILL.md`
- **video-download** - Download video and audio from YouTube and 1000+ sites using yt-dlp. No API keys needed. Use when: (1) Downloading a video from YouTube or other sites, (2) Extracting audio from a video URL, (3) Downlo...
  `openmontage\.claude\skills\video-download\SKILL.md`
- **video-edit** - Edit videos locally using ffmpeg. Trim, concat, resize, speed, overlay, extract audio, compress, and convert. Use when: (1) Trimming or cutting video segments, (2) Concatenating multiple clips, (3) Re...
  `openmontage\.claude\skills\video-edit\SKILL.md`
- **video-toolkit** - Create professional videos autonomously using claude-code-video-toolkit — AI voiceovers, image generation, music, talking heads, and Remotion rendering.
  `openmontage\.claude\skills\video_toolkit\SKILL.md`
- **video-translate** - Translate and dub existing videos into multiple languages using HeyGen. Use when: (1) Translating a video into another language, (2) Dubbing video content with lip-sync, (3) Creating multi-language ve...
  `openmontage\.claude\skills\video-translate\SKILL.md`
- **video-understand** - Understand video content locally using ffmpeg frame extraction and Whisper transcription. No API keys needed. Use when: (1) Understanding what a video contains, (2) Transcribing video audio locally, (...
  `openmontage\.claude\skills\video-understand\SKILL.md`
- **visual-style** - Create, extract, and apply portable visual design systems via visual-style.md files. Use when: (1) Creating a visual-style.md design system from scratch, (2) Extracting a visual style from a website U...
  `openmontage\.claude\skills\visual-style\SKILL.md`
- **web-design-guidelines** - Review UI code for Web Interface Guidelines compliance. Use when asked to
  `openmontage\.claude\skills\web-design-guidelines\SKILL.md`
- **website-to-video** - Capture a general website/URL and turn it into a HyperFrames video (site tour, showcase, or social clip from the site's own visuals). Uses headless Chrome screenshots + brand assets. Use when intent i...
  `openmontage\.agents\skills\website-to-video\SKILL.md`

## ProjectAtlas (2)

- **codex-coding-plugin** - Build, review, or fix ProjectAtlas plugin/runtime installer integration for Codex, Claude Code, and OpenCode, especially version convergence, stale ProjectAtlas cache repair, MCP config generation, sk...
  `ProjectAtlas\skills\codex-coding-plugin\SKILL.md`
- **projectatlas** - Use ProjectAtlas as the atlas-first orientation layer before broad source reads, with MCP-first task startup, short-alias worktree registration and routing, safe targeted initialization, ranked naviga...
  `ProjectAtlas\plugins\projectatlas\skills\projectatlas\SKILL.md`

## Scrapling (1)

- **scrapling-official** - Scrape web pages using Scrapling with anti-bot bypass (like Cloudflare Turnstile), stealth headless browsing, spiders framework, adaptive scraping, and JavaScript rendering. Use when asked to scrape, ...
  `Scrapling\agent-skill\Scrapling-Skill\SKILL.md`

## skills (20)

- **academy-guide** - Stop and check this skill before finishing any reply to a question about how to use Claude or a Claude product — it recommends matching courses, tutorials, and use cases from Claude Academy (academy.c...
  `skills\skills\academy-guide\SKILL.md`
- **algorithmic-art** - Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or...
  `skills\skills\algorithmic-art\SKILL.md`
- **brand-guidelines** - Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting...
  `skills\skills\brand-guidelines\SKILL.md`
- **canvas-design** - Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create ori...
  `skills\skills\canvas-design\SKILL.md`
- **claude-api** - Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration. TRIGGER — read BEFORE opening the target file; do...
  `skills\skills\claude-api\SKILL.md`
- **discernment-nudge** - After you give a substantive answer or draft that the user may act on — advice or recommendations, drafted artifacts such as goals, plans, pitches, proposals, or emails, estimates or projections, anal...
  `skills\skills\discernment-nudge\SKILL.md`
- **doc-coauthoring** - Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This wor...
  `skills\skills\doc-coauthoring\SKILL.md`
- **docx** - Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) or Word templates (.dotx files). Triggers include: any mention of 'Word doc', 'word document', ...
  `skills\skills\docx\SKILL.md`
- **frontend-design** *(auch im Fundus)* - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defau...
  `skills\skills\frontend-design\SKILL.md`
- **internal-comms** - A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal com...
  `skills\skills\internal-comms\SKILL.md`
- **mcp-builder** - Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate externa...
  `skills\skills\mcp-builder\SKILL.md`
- **pdf** - Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rota...
  `skills\skills\pdf\SKILL.md`
- **pptx** - Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting te...
  `skills\skills\pptx\SKILL.md`
- **skill-creator** *(auch im Fundus)* - Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill...
  `skills\skills\skill-creator\SKILL.md`
- **slack-gif-creator** - Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like
  `skills\skills\slack-gif-creator\SKILL.md`
- **template-skill** - Replace with description of the skill and when Claude should use it.
  `skills\template\SKILL.md`
- **theme-factory** - Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact t...
  `skills\skills\theme-factory\SKILL.md`
- **webapp-testing** - Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser l...
  `skills\skills\webapp-testing\SKILL.md`
- **web-artifacts-builder** - Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state manag...
  `skills\skills\web-artifacts-builder\SKILL.md`
- **xlsx** - Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .xltx, .csv, or .tsv file (e....
  `skills\skills\xlsx\SKILL.md`

## superpowers (15)

- **brainstorming** - You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.
  `superpowers\skills\brainstorming\SKILL.md`
- **diagnosing-superpowers** - Use when a superpowers session went wrong and your human partner wants to know why — repeated work, ignored plans, stumbles, poor results, a skill that didn't fire,
  `superpowers\skills\diagnosing-superpowers\SKILL.md`
- **dispatching-parallel-agents** - Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
  `superpowers\skills\dispatching-parallel-agents\SKILL.md`
- **executing-plans** - Use when executing an implementation plan in the current session as the implementer yourself — your human partner chose inline execution, or no subagent tool is available
  `superpowers\skills\executing-plans\SKILL.md`
- **finishing-a-development-branch** - Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
  `superpowers\skills\finishing-a-development-branch\SKILL.md`
- **receiving-code-review** - Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative...
  `superpowers\skills\receiving-code-review\SKILL.md`
- **requesting-code-review** - Use when completing tasks, implementing major features, or before merging to verify work meets requirements
  `superpowers\skills\requesting-code-review\SKILL.md`
- **subagent-driven-development** - Use when executing implementation plans with independent tasks in the current session
  `superpowers\skills\subagent-driven-development\SKILL.md`
- **systematic-debugging** - Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
  `superpowers\skills\systematic-debugging\SKILL.md`
- **test-driven-development** - Use when implementing any feature or bugfix, before writing implementation code
  `superpowers\skills\test-driven-development\SKILL.md`
- **using-git-worktrees** - Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
  `superpowers\skills\using-git-worktrees\SKILL.md`
- **using-superpowers** - Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
  `superpowers\skills\using-superpowers\SKILL.md`
- **verification-before-completion** - Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence...
  `superpowers\skills\verification-before-completion\SKILL.md`
- **writing-plans** - Use when you have a spec or requirements for a multi-step task, before touching code
  `superpowers\skills\writing-plans\SKILL.md`
- **writing-skills** - Use when creating new skills, editing existing skills, or verifying skills work before deployment
  `superpowers\skills\writing-skills\SKILL.md`
