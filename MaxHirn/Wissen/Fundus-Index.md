# Fundus-Index

Erzeugt von `Agenten/Werkzeuge/fundus-suche.ps1 -Index`. Nicht von Hand pflegen.

Geklonte Fremd-Repos: **175 eindeutige Skills** in 9 Repos (237 Dateien, 62 byte-identische Kopien zusammengefasst).

Nicht in der Hermes-Bibliothek geladen; Zugriff ueber `Agenten/Werkzeuge/fundus-suche.ps1 -Begriff "<wort>"`.

## cli (13)

- **firecrawl** - Any live-web task via the Firecrawl CLI — including ordinary web research: searching the web, reading or extracting pages, gathering sources, discovering site URLs, bulk extraction, downloading a site...
  `cli\skills\firecrawl\SKILL.md`
- **firecrawl-agent** - Autonomously navigate websites and extract structured data across pages. Use when the task requires navigation or no suitable ready-made workflow or data provider covers it.
  `cli\skills\firecrawl-agent\SKILL.md`
- **firecrawl-alexandria** - Find a direct path to structured data through ready-made workflows, data APIs, and indexes. Follow the search skill to discover and inspect tools, then the scrape skill to execute them.
  `cli\skills\firecrawl-alexandria\SKILL.md`
- **firecrawl-crawl** - Bulk-extract many pages from one site or section. Use for "crawl", "everything under /docs", or content spanning linked pages.
  `cli\skills\firecrawl-crawl\SKILL.md`
- **firecrawl-developer-index** - Search an index of public repositories, GitHub issues, merged pull requests, repository READMEs, and curated documentation sites. Use when a programming question needs external documentation or upstre...
  `cli\skills\firecrawl-developer-index\SKILL.md`
- **firecrawl-download** - Save a site or section as local files (markdown, screenshots). Use for "download the site", offline docs, or a local copy for reference.
  `cli\skills\firecrawl-download\SKILL.md`
- **firecrawl-interact** - Drive a live browser on a scraped page: click, fill forms, log in, paginate, infinite-scroll. Use when content requires interaction or a scrape failed or returned incomplete content.
  `cli\skills\firecrawl-interact\SKILL.md`
- **firecrawl-map** - Discover and list a site's URLs, with search filtering. Use for "map the site" or "find the URL for" requests — when the user knows the site but not the exact page, or wants site structure.
  `cli\skills\firecrawl-map\SKILL.md`
- **firecrawl-monitor** - Alert by webhook/email on web changes — use for "monitor/watch/track/alert me when": recurring checks on known URLs (prefer over repeated one-off scrapes) or web-wide watches for new results (queries ...
  `cli\skills\firecrawl-monitor\SKILL.md`
- **firecrawl-parse** - Convert a local file (PDF, DOCX, XLSX, HTML, …) to markdown, or answer questions about its content. Use whenever the input is a file path, not a URL.
  `cli\skills\firecrawl-parse\SKILL.md`
- **firecrawl-research-index** - Find the papers that answer a research query in Firecrawl's research paper index — a corpus of paper abstracts whose largest share is biomedical and life-science literature (PubMed, bioRxiv, medRxiv),...
  `cli\skills\firecrawl-research-index\SKILL.md`
- **firecrawl-scrape** - Read a known webpage or execute a discovered workflow or data-provider capability. Use for page content or structured results once the URL or tool is selected.
  `cli\skills\firecrawl-scrape\SKILL.md`
- **firecrawl-search** - Find web sources with query-relevant page excerpts and optional full-page content, and discover workflows, data APIs, and indexes. Use for web research or finding structured records, listings, transcr...
  `cli\skills\firecrawl-search\SKILL.md`

## context7 (6)

- **context7-cli** - Use the ctx7 CLI to fetch library documentation, manage AI coding skills, and configure Context7 MCP. Activate when the user mentions
  `context7\skills\context7-cli\SKILL.md`
- **context7-docs** - Fetch up-to-date documentation and code examples for any library, framework, SDK, CLI tool, or cloud service. Use whenever the user asks about a specific library — even well-known ones like React, Nex...
  `context7\packages\pi\skills\context7-docs\SKILL.md`
- **context7-mcp** - This skill should be used when the user asks about libraries, frameworks, API references, or needs code examples. Activates for setup questions, code generation involving libraries, or mentions of spe...
  `context7\skills\context7-mcp\SKILL.md`
- **context7-mcp** - Fetches current, version-specific library documentation and code examples through the Context7 MCP server. Use whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service, ...
  `context7\plugins\agent-plugins\context7\skills\context7-mcp\SKILL.md`
- **dynamic-resources** - Example skill loaded from resources_discover
  `context7\node_modules\.pnpm\@earendil-works+pi-coding-agent@0.78.1_zod@4.5.4\node_modules\@earendil-works\pi-coding-agent\examples\extensions\dynamic-resources\SKILL.md`
- **find-docs** - Retrieves up-to-date documentation, API references, and code examples for any developer technology. Use this skill whenever the user asks about a specific library, framework, SDK, CLI tool, or cloud s...
  `context7\skills\find-docs\SKILL.md`

## financial-services (72)

- **3-statement-model** - Complete, populate and fill out 3-statement financial model templates (Income Statement, Balance Sheet, Cash Flow Statement) . Use when asked to fill out model templates, complete existing model frame...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\3-statement-model\SKILL.md`
- **accrual-schedule** - Build the period-end accrual schedule — for each accrual, compute the entry, cite the support, and draft the JE. Use during month-end close; the JE is a draft for controller approval, not a posting.
  `financial-services\plugins\vertical-plugins\fund-admin\skills\accrual-schedule\SKILL.md`
- **ai-readiness** - Scan the portfolio for the highest-leverage AI opportunities and rank where to deploy operating-partner time. Ingests quarterly updates and financials across multiple portfolio companies, identifies q...
  `financial-services\plugins\vertical-plugins\private-equity\skills\ai-readiness\SKILL.md`
- **alts-brief** - Prepare a meeting-ready alternative-investments brief for a client, household, IRA, trust, or named account before a review — pulls the alts book from iCapital or Addepar (positions, NAV vs. commitmen...
  `financial-services\claude-for-financial-advisors\skills\alts-brief\SKILL.md`
- **audit-xls** - Audit a spreadsheet for formula accuracy, errors, and common mistakes. Scopes to a selected range, a single sheet, or the entire model (including financial-model integrity checks like BS balance, cash...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\audit-xls\SKILL.md`
- **bond-futures-basis** - Analyze the bond futures basis by pricing futures, identifying the cheapest-to-deliver, and comparing with yield curves to assess delivery option value and basis trading opportunities. Use when analyz...
  `financial-services\plugins\partner-built\lseg\skills\bond-futures-basis\SKILL.md`
- **bond-relative-value** - Perform relative value analysis on bonds by combining pricing, yield curve context, credit spreads, and scenario stress testing. Use when analyzing bond richness/cheapness, computing spread decomposit...
  `financial-services\plugins\partner-built\lseg\skills\bond-relative-value\SKILL.md`
- **break-trace** - Root-cause a reconciliation break to its source transaction or posting — follow the audit trail from the break row back to the originating entry on each side and state what differs and why. Use after ...
  `financial-services\plugins\vertical-plugins\fund-admin\skills\break-trace\SKILL.md`
- **buyer-list** - Build and organize a universe of potential acquirers for sell-side M&A processes. Identifies strategic and financial buyers, assesses fit, and prioritizes outreach. Use when preparing for a sell-side ...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\buyer-list\SKILL.md`
- **catalyst-calendar** - Build and maintain a calendar of upcoming catalysts across a coverage universe — earnings dates, conferences, product launches, regulatory decisions, and macro events. Helps prioritize attention and p...
  `financial-services\plugins\vertical-plugins\equity-research\skills\catalyst-calendar\SKILL.md`
- **cim-builder** - Structure and draft a Confidential Information Memorandum for sell-side M&A processes. Organizes company information into a professional, investor-ready document with consistent formatting and narrati...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\cim-builder\SKILL.md`
- **clean-data-xls** - Clean up messy spreadsheet data — trim whitespace, fix inconsistent casing, convert numbers-stored-as-text, standardize dates, remove duplicates, and flag mixed-type columns. Use when data is messy, i...
  `financial-services\plugins\vertical-plugins\financial-analysis\skills\clean-data-xls\SKILL.md`
- **client-report** - Generate professional client-facing performance reports with portfolio returns, allocation breakdowns, and market commentary. Suitable for quarterly or annual distribution. Triggers on
  `financial-services\plugins\agent-plugins\meeting-prep-agent\skills\client-report\SKILL.md`
- **client-review** - Prepare for client review meetings with portfolio performance summary, allocation analysis, talking points, and action items. Pulls together account data into a concise meeting-ready format. Use befor...
  `financial-services\plugins\agent-plugins\meeting-prep-agent\skills\client-review\SKILL.md`
- **competitive-analysis** - Framework for building competitive landscape decks — market positioning, competitor deep-dives, comparative analysis, strategic synthesis. Use when the user asks for a competitive landscape, competito...
  `financial-services\plugins\agent-plugins\market-researcher\skills\competitive-analysis\SKILL.md`
- **compliance** - Review any client-facing message or material (emails, letters, newsletters, social posts, website copy, presentations, performance reports, proposals) for compliance with SEC rules that govern investm...
  `financial-services\claude-for-financial-advisors\skills\compliance\SKILL.md`
- **comps-analysis** - Build institutional-grade comparable company analyses with operating metrics, valuation multiples, and statistical benchmarking in Excel/spreadsheet format.
  `financial-services\plugins\agent-plugins\pitch-agent\skills\comps-analysis\SKILL.md`
- **datapack-builder** - Build professional financial services data packs from various sources including CIMs, offering memorandums, SEC filings, web search, or MCP servers. Extract, normalize, and standardize financial data ...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\datapack-builder\SKILL.md`
- **dcf-model** - Real DCF (Discounted Cash Flow) model creation for equity valuation. Retrieves financial data from SEC filings and analyst reports, builds comprehensive cash flow projections with proper WACC calculat...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\dcf-model\SKILL.md`
- **dd-checklist** - Generate and track comprehensive due diligence checklists tailored to the target company's sector, deal type, and complexity. Covers all major workstreams with request lists, status tracking, and red ...
  `financial-services\plugins\vertical-plugins\private-equity\skills\dd-checklist\SKILL.md`
- **dd-meeting-prep** - Prepare for due diligence meetings — management presentations, expert network calls, customer references, and advisor sessions. Generates targeted question lists, benchmarks to reference, and red flag...
  `financial-services\plugins\vertical-plugins\private-equity\skills\dd-meeting-prep\SKILL.md`
- **deal-screening** - Quickly screen inbound deal flow — CIMs, teasers, and broker materials — against the fund's investment criteria. Extracts key deal metrics, runs a pass/fail framework, and outputs a one-page screening...
  `financial-services\plugins\vertical-plugins\private-equity\skills\deal-screening\SKILL.md`
- **deal-sourcing** - PE deal sourcing workflow — discover target companies, check CRM for existing relationships, and draft personalized founder outreach emails. Use when sourcing new deals, prospecting companies in a sec...
  `financial-services\plugins\vertical-plugins\private-equity\skills\deal-sourcing\SKILL.md`
- **deal-tracker** - Track multiple live deals with milestones, deadlines, action items, and status updates. Maintains a deal pipeline view and surfaces upcoming deadlines and overdue items. Use when managing a book of bu...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\deal-tracker\SKILL.md`
- **deck-refresh** - Updates a presentation with new numbers — quarterly refreshes, earnings updates, comp rolls, rebased market data. Use whenever the user asks to
  `financial-services\plugins\agent-plugins\pitch-agent\skills\deck-refresh\SKILL.md`
- **earnings-analysis** - Create professional equity research earnings update reports (8-12 pages, 3,000-5,000 words) analyzing quarterly results for companies already under coverage. Fast-turnaround format focusing on beat/mi...
  `financial-services\plugins\agent-plugins\earnings-reviewer\skills\earnings-analysis\SKILL.md`
- **earnings-preview** - Build pre-earnings analysis with estimate models, scenario frameworks, and key metrics to watch. Use before a company reports quarterly earnings to prepare positioning notes, set up bull/bear scenario...
  `financial-services\plugins\agent-plugins\earnings-reviewer\skills\earnings-preview\SKILL.md`
- **earnings-preview-single** - Generate a concise 4-5 page equity research earnings preview for a single company. Analyzes the most recent earnings transcript, competitor landscape, valuation, and recent news to produce a professio...
  `financial-services\plugins\partner-built\spglobal\skills\earnings-preview-beta\SKILL.md`
- **equity-research** - Generate comprehensive equity research snapshots combining analyst consensus estimates, company fundamentals, historical prices, and macroeconomic context. Use when researching stocks, comparing estim...
  `financial-services\plugins\partner-built\lseg\skills\equity-research\SKILL.md`
- **estate-and-tax-brief** - Prepare a meeting-ready estate and tax brief for a household — opens with what was discussed and actioned since the last meeting (Wealthbox/Redtail/Salesforce), pulls the estate plan from Wealth.com (...
  `financial-services\claude-for-financial-advisors\skills\estate-and-tax-brief\SKILL.md`
- **fixed-income-portfolio** - Review fixed income portfolios by pricing multiple bonds, retrieving reference data, analyzing cashflows, and running scenario analysis. Use when reviewing bond portfolios, computing portfolio duratio...
  `financial-services\plugins\partner-built\lseg\skills\fixed-income-portfolio\SKILL.md`
- **fsi-strip-profile** - Creates professional investment banking strip profiles (company profiles) for pitch books, deal materials, and client presentations. Generates 1-4 information-dense slides with quadrant layouts, chart...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\strip-profile\SKILL.md`
- **funding-digest** - Generate a polished one-page PowerPoint slide summarizing key takeaways from recent funding rounds and notable capital markets activity across a user's watched sectors or companies. Use this skill whe...
  `financial-services\plugins\partner-built\spglobal\skills\funding-digest\SKILL.md`
- **fx-carry-trade** - Evaluate FX carry trade opportunities by combining spot rates, forward points, interest rate differentials, volatility surface analysis, and historical price trends. Use when analyzing carry trades, c...
  `financial-services\plugins\partner-built\lseg\skills\fx-carry-trade\SKILL.md`
- **gl-recon** - Reconcile general ledger to subledger for a trade date or period — match at the position or transaction level, surface breaks, and classify each break by likely cause. Use for daily or month-end recon...
  `financial-services\plugins\vertical-plugins\fund-admin\skills\gl-recon\SKILL.md`
- **ib-check-deck** - Investment banking presentation quality checker. Reviews a pitch deck or client-ready presentation for (1) number consistency across slides, (2) data-narrative alignment, (3) language polish against I...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\ib-check-deck\SKILL.md`
- **ic-memo** - Draft a structured investment committee memo for PE deal approval. Synthesizes due diligence findings, financial analysis, and deal terms into a professional IC-ready document. Use when preparing for ...
  `financial-services\plugins\vertical-plugins\private-equity\skills\ic-memo\SKILL.md`
- **idea-generation** - Systematic stock screening and investment idea sourcing. Combines quantitative screens, thematic research, and pattern recognition to surface new long and short ideas. Use when looking for new ideas, ...
  `financial-services\plugins\agent-plugins\market-researcher\skills\idea-generation\SKILL.md`
- **initiating-coverage** - Create institutional-quality equity research initiation reports through a 5-task workflow. Tasks must be executed individually with verified prerequisites - (1) company research, (2) financial modelin...
  `financial-services\plugins\vertical-plugins\equity-research\skills\initiating-coverage\SKILL.md`
- **investment-proposal** - Create professional investment proposals for prospective clients. Covers the firm's approach, proposed allocation, expected outcomes, and fee structure. Use when pitching new clients or presenting a n...
  `financial-services\plugins\agent-plugins\meeting-prep-agent\skills\investment-proposal\SKILL.md`
- **kyc-doc-parse** - Parse an investor or client onboarding packet into structured KYC fields — identity, ownership, control, source of funds, and document inventory. Use as the first step of KYC screening; output feeds t...
  `financial-services\plugins\agent-plugins\kyc-screener\skills\kyc-doc-parse\SKILL.md`
- **kyc-rules** - Apply the firm's KYC/AML rules grid to a parsed onboarding record — assign a risk rating, list every rule outcome with the rule cited, and flag what's missing or escalation-worthy. Use after kyc-doc-p...
  `financial-services\plugins\agent-plugins\kyc-screener\skills\kyc-rules\SKILL.md`
- **lbo-model** - This skill should be used when completing LBO (Leveraged Buyout) model templates in Excel for private equity transactions, deal materials, or investment committee presentations. The skill fills in for...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\lbo-model\SKILL.md`
- **macro-rates-monitor** - Build macroeconomic and rates dashboards combining macro indicators, yield curves, inflation breakevens, and swap rates. Use when monitoring macro conditions, analyzing yield curve shape, decomposing ...
  `financial-services\plugins\partner-built\lseg\skills\macro-rates-monitor\SKILL.md`
- **merger-model** - Build accretion/dilution analysis for M&A transactions. Models pro forma EPS impact, synergy sensitivities, and purchase price allocation. Use when evaluating a potential acquisition, preparing merger...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\merger-model\SKILL.md`
- **model-update** - Update financial models with new data — quarterly earnings, management guidance, macro changes, or revised assumptions. Adjusts estimates, recalculates valuation, and flags material changes. Use after...
  `financial-services\plugins\agent-plugins\earnings-reviewer\skills\model-update\SKILL.md`
- **morning-note** - Draft concise morning meeting notes summarizing overnight developments, trade ideas, and key events for coverage stocks. Designed for the 7am morning meeting format — tight, opinionated, actionable. T...
  `financial-services\plugins\agent-plugins\earnings-reviewer\skills\morning-note\SKILL.md`
- **nav-tieout** - Tie an LP statement to the fund's NAV pack — recompute the LP's capital account from the NAV components and flag any line that doesn't agree. Use before LP statements are distributed.
  `financial-services\plugins\vertical-plugins\fund-admin\skills\nav-tieout\SKILL.md`
- **onboarding** - Welcome and set up a new Claude for Financial Advisors user. Gets to know the advisor's RIA, learns their day-to-day pain points and tech stack, walks them through connecting their tools, explains the...
  `financial-services\claude-for-financial-advisors\skills\onboarding\SKILL.md`
- **option-vol-analysis** - Analyze option volatility by combining vol surface data, option pricing with Greeks, and historical price data to assess implied vs realized volatility. Use when pricing options, analyzing volatility ...
  `financial-services\plugins\partner-built\lseg\skills\option-vol-analysis\SKILL.md`
- **pitch-deck** - Populates investment banking pitch deck templates with data from source files. Use when: user provides a PowerPoint template to fill in, user has source data (Excel/CSV) to populate into slides, user ...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\pitch-deck\SKILL.md`
- **portfolio-monitoring** - Track and analyze portfolio company performance against plan. Ingests monthly/quarterly financial packages (Excel, PDF), extracts KPIs, flags variances to budget, and produces summary dashboards. Use ...
  `financial-services\plugins\vertical-plugins\private-equity\skills\portfolio-monitoring\SKILL.md`
- **portfolio-rebalance-review** - Run a portfolio review for a client or household — performance pulled from Orion, allocation drift analysis vs. IPS or model portfolio, model-portfolio mapping, rebalance preparation with tax-aware re...
  `financial-services\claude-for-financial-advisors\skills\portfolio-rebalance-review\SKILL.md`
- **post-meeting** - Turn a client meeting into next-best-action follow-up for a financial advisor — no drafting required. Given a meeting (via Zocks, Wealthbox, or a pasted transcript), finds the right household, drafts ...
  `financial-services\claude-for-financial-advisors\skills\post-meeting\SKILL.md`
- **ppt-template-creator** - Creates self-contained PPT template SKILLS (not presentations) from user-provided PowerPoint templates. Use ONLY when a user wants to create a reusable skill from their template. For creating actual p...
  `financial-services\plugins\vertical-plugins\financial-analysis\skills\ppt-template-creator\SKILL.md`
- **pptx-author** - Produce a .pptx file on disk (headless) instead of driving a live PowerPoint document — for managed-agent sessions with no open Office app.
  `financial-services\plugins\agent-plugins\pitch-agent\skills\pptx-author\SKILL.md`
- **pre-meeting** - Prepare a complete client review meeting prep document for a financial advisor, for whatever timeframe the review covers (quarterly, annual, ad hoc). Given a household name or email and a timeframe, p...
  `financial-services\claude-for-financial-advisors\skills\pre-meeting\SKILL.md`
- **process-letter** - Draft process letters and bid instructions for sell-side M&A processes. Covers initial indication of interest (IOI) instructions, final bid procedures, and management meeting logistics. Triggers on
  `financial-services\plugins\vertical-plugins\investment-banking\skills\process-letter\SKILL.md`
- **prospect-intake** - Start a new prospect's intake, with or without their files in hand — a request naming a new prospect and attaching no documents is a normal starting point, because Step 1 searches the connected tools ...
  `financial-services\claude-for-financial-advisors\skills\prospect-intake\SKILL.md`
- **returns-analysis** - Build quick IRR/MOIC sensitivity tables for PE deal evaluation. Models returns across entry multiple, leverage, exit multiple, growth, and hold period scenarios. Use when sizing up a deal, stress-test...
  `financial-services\plugins\vertical-plugins\private-equity\skills\returns-analysis\SKILL.md`
- **roll-forward** - Build a roll-forward schedule for a balance-sheet account — beginning balance plus activity less reversals equals ending balance, with each component tied to GL. Use for month-end close packages and a...
  `financial-services\plugins\vertical-plugins\fund-admin\skills\roll-forward\SKILL.md`
- **sector-overview** - Create comprehensive industry and sector landscape reports covering market dynamics, competitive positioning, key players, and thematic trends. Use for client requests, sector initiations, thematic re...
  `financial-services\plugins\agent-plugins\pitch-agent\skills\sector-overview\SKILL.md`
- **skill-creator** - Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workfl...
  `financial-services\plugins\vertical-plugins\financial-analysis\skills\skill-creator\SKILL.md`
- **swap-curve-strategy** - Analyze the interest rate swap curve by pricing swaps at multiple tenors, overlaying government and inflation curves, and identifying curve trade opportunities. Use when analyzing swap curves, computi...
  `financial-services\plugins\partner-built\lseg\skills\swap-curve-strategy\SKILL.md`
- **tear-sheet** - Generate professional company tear sheets using S&P Capital IQ data via the Kensho LLM-ready API MCP server. Use this skill whenever the user asks for a tear sheet, company one-pager, company profile,...
  `financial-services\plugins\partner-built\spglobal\skills\tear-sheet\SKILL.md`
- **teaser** - Draft anonymous one-page company teasers for sell-side M&A processes. Creates a compelling summary without revealing the company's identity, designed to gauge buyer interest before NDA execution. Trig...
  `financial-services\plugins\vertical-plugins\investment-banking\skills\teaser\SKILL.md`
- **thesis-tracker** - Maintain and update investment theses for portfolio positions and watchlist names. Track key data points, catalysts, and thesis milestones over time. Use when updating a thesis with new information, r...
  `financial-services\plugins\vertical-plugins\equity-research\skills\thesis-tracker\SKILL.md`
- **unit-economics** - Analyze unit economics for PE targets — ARR cohorts, LTV/CAC, net retention, payback periods, revenue quality, and margin waterfall. Essential for software/SaaS, recurring revenue, and subscription bu...
  `financial-services\plugins\vertical-plugins\private-equity\skills\unit-economics\SKILL.md`
- **value-creation-plan** - Structure post-acquisition value creation plans with revenue, cost, and operational levers mapped to an EBITDA bridge. Includes 100-day priorities, KPI targets, and accountability frameworks. Use when...
  `financial-services\plugins\vertical-plugins\private-equity\skills\value-creation-plan\SKILL.md`
- **variance-commentary** - Write flux commentary for every P&L and balance-sheet line over threshold — current vs prior period and vs budget, with the driver explained from underlying activity. Use for the month-end close packa...
  `financial-services\plugins\vertical-plugins\fund-admin\skills\variance-commentary\SKILL.md`
- **verify** - Verify changes to the claude-for-msft-365-install admin scripts and commands by driving them against an isolated fake $HOME.
  `financial-services\claude-for-msft-365-install\.claude\skills\verify\SKILL.md`
- **xlsx-author** - Produce a .xlsx file on disk (headless) instead of driving a live Excel workbook — for managed-agent sessions with no open Office app.
  `financial-services\plugins\agent-plugins\pitch-agent\skills\xlsx-author\SKILL.md`

## fintool (1)

- **fintool** - Financial trading CLIs — spot and perp trading on Hyperliquid, Binance, Coinbase, OKX. Prediction markets on Polymarket. Deposit and withdraw across chains. LLM-enriched price quotes with trend analys...
  `fintool\skills\SKILL.md`

## notebooklm-py (2)

- **fastapi** - FastAPI best practices and conventions. Use when working with FastAPI APIs, Pydantic models, dependencies, streaming responses including Server-Sent Events (SSE), and serving frontend apps. Keeps Fast...
  `notebooklm-py\.venv\Lib\site-packages\fastapi\.agents\skills\fastapi\SKILL.md`
- **notebooklm** - Install, authenticate, troubleshoot, and operate Gemini Notebook through the notebooklm-py CLI or typed async Python API. Use for notebook and source management, grounded chat and research, and artifa...
  `notebooklm-py\SKILL.md`

## OmniRoute (72)

- **assess-patch-risk** - Assess an immutable patch artifact's program impact, regression risk, and auto-merge eligibility. Use for generated patch files, provider pull-request diffs, or commit ranges when reviewers need evide...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\assess-patch-risk\SKILL.md`
- **attack-path-analysis** - Use when Codex is already in the attack-path-analysis phase of a security scan or the user explicitly asks to trace a security finding from source to sink and calibrate severity. Do not use as the pri...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\attack-path-analysis\SKILL.md`
- **bridge-proof** - This skill should be used when the user invokes the bridge-check command or asks to verify the isolated Devin bridge.
  `OmniRoute\tests\fixtures\devin-bridge\e2e-workspace\.claude\skills\bridge-proof\SKILL.md`
- **cli-a2a** - Interact with the OmniRoute A2A server from the CLI. Send tasks, inspect skill execution history, and test the JSON-RPC 2.0 agent-to-agent protocol interactively.
  `OmniRoute\skills\cli-a2a\SKILL.md`
- **cli-backup-sync** - Backup and restore OmniRoute data from the CLI. Trigger incremental snapshots, sync to cloud storage, manage backup schedules, and restore from archive files.
  `OmniRoute\skills\cli-backup-sync\SKILL.md`
- **cli-batches** - Submit and monitor batch inference jobs from the CLI. Upload and manage files for batch processing, retrieve results, and integrate batch pipelines with CI/CD workflows.
  `OmniRoute\skills\cli-batches\SKILL.md`
- **cli-chat** - Send chat completions, stream responses, and start an interactive REPL session from the CLI. Supports all OmniRoute providers, combo routing, and system prompt configuration.
  `OmniRoute\skills\cli-chat\SKILL.md`
- **cli-compression** - Configure and test prompt compression from the CLI. Manage RTK filters, Caveman rules, stacked compression modes, and preview compression output with real prompts.
  `OmniRoute\skills\cli-compression\SKILL.md`
- **cli-contexts** - Manage context engineering configurations, RTK filter sets, and conversation sessions from the CLI. Apply context-relay settings and inspect active context pipelines.
  `OmniRoute\skills\cli-contexts\SKILL.md`
- **cli-cost-usage** - View cost breakdowns, token usage, and call logs from the CLI. Filter by provider, model, or date range. Export usage reports and inspect per-connection spending.
  `OmniRoute\skills\cli-cost-usage\SKILL.md`
- **cli-eval** - Create and run evaluation suites, watch live benchmark progress, view scorecards, compare model performance, and integrate eval runs with CI workflows from the CLI.
  `OmniRoute\skills\cli-eval\SKILL.md`
- **cli-health** - Check server health, component status, and live metrics from the CLI. Run `health`, `health components`, and `health watch` for a real-time dashboard of circuit breakers and provider status.
  `OmniRoute\skills\cli-health\SKILL.md`
- **cli-keys** - Create, list, rotate, and revoke OmniRoute API keys from the CLI. Manage OAuth flows for provider authentication and inspect key scopes and expiration.
  `OmniRoute\skills\cli-keys\SKILL.md`
- **cli-mcp** - Inspect the MCP server status, list registered tools and scopes, run tool invocations, and manage MCP audit logs from the CLI.
  `OmniRoute\skills\cli-mcp\SKILL.md`
- **cli-models** - Query available AI models, list model aliases, and browse the full model catalog from the CLI. Filter by provider, search by capability, and resolve model name variants.
  `OmniRoute\skills\cli-models\SKILL.md`
- **cli-plugins-skills** - Manage Omni Skills (list, install, test, remove), plugins (create, configure), and persistent memory (search, add, clear) from the CLI.
  `OmniRoute\skills\cli-plugins-skills\SKILL.md`
- **cli-policy-audit** - Inspect audit logs, manage access policies, view telemetry data, and review request history from the CLI. Filter by event type, user, or time range for compliance workflows.
  `OmniRoute\skills\cli-policy-audit\SKILL.md`
- **cli-providers** - Manage provider connections from the CLI: list available/configured providers, add, test, test-all, validate, rotate API keys, and view per-provider metrics.
  `OmniRoute\skills\cli-providers\SKILL.md`
- **cli-resilience** - Inspect and manage circuit-breaker states, connection cooldowns, quota limits, and backoff levels from the CLI. Reset stuck providers and configure resilience thresholds.
  `OmniRoute\skills\cli-resilience\SKILL.md`
- **cli-routing** - Create, list, update, and delete routing combos from the CLI. Test routing strategies, inspect combo metrics, and configure fallback chains interactively.
  `OmniRoute\skills\cli-routing\SKILL.md`
- **cli-serve** - Start, stop, and restart the OmniRoute server from the CLI. Manage daemon mode, port configuration, auto-recovery, system tray integration, and the dashboard open shortcut.
  `OmniRoute\skills\cli-serve\SKILL.md`
- **cli-setup** - Run initial setup, configure global CLI settings, manage environment variables, check for updates, and configure autostart via the CLI setup and config commands.
  `OmniRoute\skills\cli-setup\SKILL.md`
- **cli-skill-collector** - Detect installed CLI coding tools (Claude Code, Codex, Cursor, Copilot, Cline and more), search GitHub for matching agent skills, and install them to the detected tools via OmniRoute's built-in APIs.
  `OmniRoute\skills\cli-skill-collector\SKILL.md`
- **cli-tunnel** - Start and stop tunnel connections (ngrok, Cloudflare, custom) from the CLI. Inspect active tunnel URLs, configure authentication, and test external reachability.
  `OmniRoute\skills\cli-tunnel\SKILL.md`
- **config-codex-cli** - Step-by-step agent workflow to configure the OpenAI Codex CLI on any machine (Linux, macOS, Windows) to use OmniRoute as an OpenAI-compatible backend. Detects OS and shell, writes config.toml and 7 na...
  `OmniRoute\skills\config-codex-cli\SKILL.md`
- **deep-security-scan** - Use when the user asks for a deep, exhaustive, multi-pass, or variance-reducing repository-wide or scoped-path Codex Security scan. Run repeated complete independent Standard scans with the Codex Secu...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\deep-security-scan\SKILL.md`
- **define-security-policy** - Define, review, or update SECURITY.md guidance for a repository or component. Use when the user wants to clarify what Codex Security should review, what is out of scope, which security properties must...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\define-security-policy\SKILL.md`
- **dotenv** - Load environment variables from a .env file into process.env for Node.js applications. Use when configuring apps with secrets, setting up local development environments, managing API keys and database...
  `OmniRoute\node_modules\natural\node_modules\dotenv\skills\dotenv\SKILL.md`
- **dotenvx** - Use dotenvx to run commands with environment variables, manage multiple .env files, expand variables, and encrypt env files for safe commits and CI/CD.
  `OmniRoute\node_modules\natural\node_modules\dotenv\skills\dotenvx\SKILL.md`
- **finding-discovery** - Use when Codex is already in the finding-discovery phase of a security scan or the user explicitly asks to discover candidate security findings in a repository or code change. Do not use as the primar...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\finding-discovery\SKILL.md`
- **fix-finding** - Use when the user explicitly asks to fix and verify a validated or plausible security finding. Do not use as the primary trigger for full PR, commit, branch, patch, or repository scans.
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\fix-finding\SKILL.md`
- **incur** - incur is a TypeScript framework for building CLIs that work for both AI agents and humans. Use when creating new CLIs.
  `OmniRoute\node_modules\incur\SKILL.md`
- **omni-agents-a2a** - Interact with OmniRoute via JSON-RPC 2.0 agent-to-agent protocol. 6 built-in A2A skills: smart-routing, quota-management, provider-discovery, cost-analysis, health-report, list-capabilities.
  `OmniRoute\skills\omni-agents-a2a\SKILL.md`
- **omni-api-keys** - Create, list, rotate, and revoke OmniRoute API keys. Control per-key scopes, spending limits, and expiration. Keys gate access to all proxy and management endpoints.
  `OmniRoute\skills\omni-api-keys\SKILL.md`
- **omni-auth** - Manage API key authentication and session tokens. Start here to authenticate requests via Bearer token, obtain session cookies, and configure login requirements for the OmniRoute API.
  `OmniRoute\skills\omni-auth\SKILL.md`
- **omni-budget** - Configure spending limits, token quotas, and rate-limit policies per API key or globally. Inspect current consumption and enforce cost controls across providers.
  `OmniRoute\skills\omni-budget\SKILL.md`
- **omni-cache** - Manage the LLM response cache. View cache statistics, clear entries, configure TTL policies, and control semantic-similarity caching thresholds.
  `OmniRoute\skills\omni-cache\SKILL.md`
- **omni-cli-tools** - Manage CLI tool integrations exposed via the API. List, configure, and invoke CLI tool plugins that extend OmniRoute's automation surface.
  `OmniRoute\skills\omni-cli-tools\SKILL.md`
- **omni-combos-routing** - Create and manage routing combos with 19 strategies (priority, weighted, round-robin, Auto-combo, and more). Configure fallback chains, test routing outcomes, and retrieve combo metrics.
  `OmniRoute\skills\omni-combos-routing\SKILL.md`
- **omni-compression** - Configure RTK (command output), Caveman (prose), and stacked compression modes. Manage language packs, custom rules, and test prompt compression reducing tokens by 60–90%.
  `OmniRoute\skills\omni-compression\SKILL.md`
- **omni-context-rtk** - Configure RTK filters, context engineering rules, and context relay settings. Test compression with real prompt samples and manage context transformation pipelines.
  `OmniRoute\skills\omni-context-rtk\SKILL.md`
- **omni-db-backups** - Trigger system backups, restore from backup files, and manage the SQLite database lifecycle. Supports export, import, and incremental snapshot strategies.
  `OmniRoute\skills\omni-db-backups\SKILL.md`
- **omni-github-skills** - Search, score, scan, and import agent skills from GitHub repositories that contain SKILL.md, CLAUDE.md, .cursorrules, and similar agent skill files. Discover community skills across many tool and prov...
  `OmniRoute\skills\omni-github-skills\SKILL.md`
- **omni-inference** - The core OpenAI-compatible inference endpoints: chat completions, embeddings, images, audio (TTS/STT), moderations, rerank, and the Responses API. The primary integration surface for AI agents.
  `OmniRoute\skills\omni-inference\SKILL.md`
- **omni-mcp** - Connect to the OmniRoute MCP server (110 tools, 3 transports: SSE/stdio/HTTP). Covers routing, cache, compression, memory, skills, providers, and audit tools across 33 permission scopes.
  `OmniRoute\skills\omni-mcp\SKILL.md`
- **omni-models** - Query available AI models across all configured providers. List models, resolve model aliases, and browse the full model catalog including provider-specific variants.
  `OmniRoute\skills\omni-models\SKILL.md`
- **omni-providers** - Manage provider connections, API keys, OAuth flows, and connection tests via the REST API. List, add, update, remove, and test AI provider integrations across OmniRoute's 327-provider catalog.
  `OmniRoute\skills\omni-providers\SKILL.md`
- **omni-proxies** - Configure HTTP/HTTPS/SOCKS proxies for upstream provider requests. Set per-provider or global proxy rules, test connectivity, and manage proxy rotation.
  `OmniRoute\skills\omni-proxies\SKILL.md`
- **omni-resilience** - Monitor provider health, circuit-breaker states, p50/p95/p99 latency metrics, and budget guard alerts. Inspect connection cooldowns and model lockouts in real time.
  `OmniRoute\skills\omni-resilience\SKILL.md`
- **omni-settings** - Read and update global application settings: system prompts, thinking budget, IP filters, payload rules, combo defaults, and require-login configuration.
  `OmniRoute\skills\omni-settings\SKILL.md`
- **omni-sync-cloud** - Synchronise OmniRoute configuration, provider connections, and settings to/from cloud storage. Manage cloud worker authentication and remote backup targets.
  `OmniRoute\skills\omni-sync-cloud\SKILL.md`
- **omni-tunnels** - Create and manage secure tunnels (ngrok, Cloudflare Tunnel, custom) to expose OmniRoute to the internet or share access with remote agents and CI pipelines.
  `OmniRoute\skills\omni-tunnels\SKILL.md`
- **omni-usage-logs** - Access detailed call logs and usage analytics. Filter by provider, model, time range, status, and cost. Export logs and aggregate token usage across all connections.
  `OmniRoute\skills\omni-usage-logs\SKILL.md`
- **omni-version-manager** - Install, start, stop, restart, and update embedded services (9Router, CLIProxyAPI). Monitor service status, retrieve logs, and configure auto-start for local-only service endpoints.
  `OmniRoute\skills\omni-version-manager\SKILL.md`
- **omni-webhooks** - Register, list, test, and remove webhook endpoints. Configure event subscriptions (request.completed, request.failed, quota.exceeded, etc.) and manage delivery retries.
  `OmniRoute\skills\omni-webhooks\SKILL.md`
- **playwright-cli** - Automate browser interactions, test web pages and work with Playwright tests.
  `OmniRoute\node_modules\playwright-core\lib\tools\skills\playwright-cli\SKILL.md`
- **playwright-cli** - Automate browser interactions, test web pages and work with Playwright tests.
  `OmniRoute\packages\browser-pool\node_modules\playwright-core\lib\tools\skills\playwright-cli\SKILL.md`
- **playwright-cli** - Automate browser interactions, test web pages and work with Playwright tests.
  `OmniRoute\node_modules\@playwright\browser-chromium\node_modules\playwright-core\lib\tools\cli-client\skill\SKILL.md`
- **playwright-component-testing** - Set up component testing with Playwright using a story gallery — scaffold stories and a gallery dev page driven by the built-in mount fixture, no dedicated component-testing runtime. Use when asked to...
  `OmniRoute\packages\browser-pool\node_modules\playwright-core\lib\tools\skills\playwright-component-testing\SKILL.md`
- **playwright-component-testing** - Set up component testing with Playwright using a story gallery — scaffold stories and a gallery dev page driven by the built-in mount fixture, no dedicated component-testing runtime. Use when asked to...
  `OmniRoute\node_modules\playwright-core\lib\tools\skills\playwright-component-testing\SKILL.md`
- **playwright-trace** - Inspect Playwright trace files from the command line — list actions, view requests, console, errors, snapshots and screenshots.
  `OmniRoute\node_modules\playwright-core\lib\tools\skills\playwright-trace\SKILL.md`
- **playwright-trace** - Inspect Playwright trace files from the command line — list actions, view requests, console, errors, snapshots and screenshots.
  `OmniRoute\packages\browser-pool\node_modules\playwright-core\lib\tools\skills\playwright-trace\SKILL.md`
- **ponytail** - External agent skill (MIT, github.com/DietrichGebert/ponytail). Forces the laziest solution that actually works: question whether the task needs to exist at all (YAGNI), reuse what is already in the c...
  `OmniRoute\skills\ponytail\SKILL.md`
- **propose-security-hardening** - Develop evidence-backed structural and architectural security hardening proposals from vulnerability disclosures, supplied findings, incident or assessment documents, source code, or a completed Codex...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\propose-security-hardening\SKILL.md`
- **security-diff-scan** - Review a pull request, commit, branch diff, or working-tree patch for security vulnerabilities.
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\security-diff-scan\SKILL.md`
- **security-scan** - Use for a standard, single-pass security audit of an entire repository or a scoped path, package, folder, or submodule with no diff to review. This is the default repository scan. Do not use for PR, c...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\security-scan\SKILL.md`
- **threat-model** - Use when Codex is already in the threat-modeling phase of a security scan, the user explicitly invokes $threat-model, or the user explicitly asks to create, update, or persist a repository threat mode...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\threat-model\SKILL.md`
- **track-findings** - Track validated Codex Security findings in Linear, Jira, GitHub issues, or draft GitHub security advisories. Use it for one finding or an explicitly selected batch of up to 25 findings tracked as Line...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\track-findings\SKILL.md`
- **triage-finding** - Use when the user supplies or imports existing security findings, vulnerability reports, or security/vulnerability Jira/Linear tickets from scanners, advisories, GitHub, Atlassian Rovo, Linear, or sim...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\triage-finding\SKILL.md`
- **validation** - Use when Codex is already in the validation phase of a security scan or the user explicitly asks to determine whether one or more candidate security findings are valid. Do not use as the primary trigg...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\validation\SKILL.md`
- **verify-fix** - Use when the user asks whether an existing security fix, patch, finding, or completed issue actually remediates the original vulnerability without modifying the repository. Do not use to validate cand...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\verify-fix\SKILL.md`
- **vulnerability-writeup** - Turn vulnerability notes, disclosure reports, PoCs, source code, or Codex Security findings into self-contained, sceptically validated, natural-sounding vulnerability reports. Use for one vulnerabilit...
  `OmniRoute\node_modules\@openai\codex-security\_bundled_plugin\skills\vulnerability-writeup\SKILL.md`

## onchainos-skills (7)

- **okx-agentic-wallet** - Operate OKX Onchain OS wallets and execute or inspect on-chain transactions. Use for wallet login/status/accounts/addresses/balances/holdings; receive/send/transfer; swaps, bridges, limit orders, cont...
  `onchainos-skills\skills\okx-agentic-wallet\SKILL.md`
- **okx-agent-payments-protocol** - Handle agent payments and paid endpoints via x402, MPP, payment links, a2a-pay, and HTTP-payment recurring or metered billing. Use for HTTP 402/payment-required; paid Agent or A2MCP endpoints; x402/Pe...
  `onchainos-skills\skills\okx-agent-payments-protocol\SKILL.md`
- **okx-ai** - Operate OKX.AI agents and marketplace workflows. Use when the user wants to register or update an Agent identity; discover, publish, buy, or manage Agent services(tasks), including signal services; cr...
  `onchainos-skills\skills\okx-ai\SKILL.md`
- **okx-dapp-discovery** - Discover supported third-party DApps and route protocol-specific requests to OKX plugins without signing or broadcasting. Use for DApp discovery or comparison; a named protocol's operations or analyti...
  `onchainos-skills\skills\okx-dapp-discovery\SKILL.md`
- **okx-defi** - Discover and manage OKX-aggregated DeFi products and positions across protocols and chains. Use for generic or venue-agnostic yield, APY, or TVL discovery and history; DeFi deposits, staking, liquidit...
  `onchainos-skills\skills\okx-defi\SKILL.md`
- **okx-dex-market** - Query read-only DEX token, market, signal, social, trenches, and WebSocket data. Use for token search, rankings, liquidity, holders, risk metadata, clusters, and trades; prices, K-lines/OHLC, indexes,...
  `onchainos-skills\skills\okx-dex-market\SKILL.md`
- **okx-guide** - Guide users through installing or updating Onchain OS, getting started, OKX.AI introduction and role-registration routing, and customer support. Use when someone wants to install or update the Onchain...
  `onchainos-skills\skills\okx-guide\SKILL.md`

## one-skill-to-rule-them-all-main (1)

- **task-observer** - Monitors task execution for skill improvement opportunities. Use during ANY multi-step task, agentic workflow, or work session where the agent uses tools and produces deliverables. Captures patterns, ...
  `one-skill-to-rule-them-all-main\SKILL.md`

## OpenMobius-skill (1)

- **openmobius-skill** - Provides multi-school trading Q&A, chart/OHLCV analysis, annotation, and fresh-market workflows covering ICT/SMC, ChanLun, Wyckoff, Price Action, Order Flow, VSA, and Elliott Wave. Use for trading con...
  `OpenMobius-skill\SKILL.md`
