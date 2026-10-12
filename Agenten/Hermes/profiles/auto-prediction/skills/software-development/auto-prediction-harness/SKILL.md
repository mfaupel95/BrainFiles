---
name: auto-prediction-harness
description: Use when working in the Auto-Prediction harness repo.
version: 1.0.0
author: auto-prediction-bot
license: MIT
metadata:
  hermes:
    tags: [auto-prediction, studio, control-plane, prediction-markets, fixtures]
    related_skills: [dogfood, systematic-debugging, codex]
---

# Auto-Prediction harness

Research-only prediction-market harness (fork `mfaupel95/Auto-Prediction`, upstream
`TraderAlice/Auto-Prediction`). Studio UI + control plane + discovery + fixtures.
Repo: `C:\Users\faupe\Documents\BrainFiles\Agenten\Handel\OpenAlice\workspaces\workspaces\auto-prediction-modest-birch-bridge`.
It lives outside `Werkstatt\Repos\` on purpose (no junction on O:); relocation to
`Werkstatt\Repos\auto-prediction` requires updating `terminal.cwd`.

## When to Use

Load this skill when the task touches the Auto-Prediction harness at all:

- the user asks to start, restart, check, or use the studio (:5173) or control plane (:4100);
- work in the harness repo — discovery, fixtures, adapters, verifier, mutation review;
- questions about the harness' authority boundary, credentials, or model budget;
- any report about the harness, before writing it (see Reporting rules).

Covers: studio/control-plane lifecycle, authority-boundary verification, fixture
integrity, mutation review, and how reports for this repo must look.

Dieses Profil ist ein Bot in der Haus-Flotte. Kommt ein Auftrag an, der einem
anderen Bot gehoert (Handel, Wartung, Fremd-Repo), gilt `brainfiles-bot-betrieb`:
Zustaendigkeit messen, dann ueber `Agenten/Werkzeuge/lotse-route.py --an <ziel>`
verteilen statt selbst in fremde Bereiche zu schreiben.

## Reporting rules (always on)

- All reports in **German**, result first, then evidence. No preamble, no filler, no
  restating the request. User is result-oriented and wants perfect, verified output.
- Separate facts by provenance: tool-verified output vs. assumption. Label assumptions.
- State the **recommendation** once, plus the action you actually took. Do not offer
  menus of options when one path is clearly right — recommend, act on confirmation.
- Never mix the user's day-job context (carpentry business) into harness work; the two
  contexts stay separate.
- When the right move is *not* to act (see below), say so explicitly with a one-line
  reason — that counts as a result.

## Studio lifecycle: probe before restart

Never kill and relaunch a running studio as a reflex. A studio left running from a
previous day is normally still good: Vite HMR picks up source changes, so a stale
start time is not a reason to restart. Restarting buys only downtime and a Vite port
shift.

1. Probe first (read-only, free): run `scripts/studio-status.sh`.
2. If the UI answers HTTP 200 on :5173 and `/health` on :4100 reports
   `safeToLoad: true` / `startup.status: READY`, the studio is up — report the state and
   stop. Do not restart.
3. Restart **only** on explicit request (fresh code, or the user says so). End the
   existing processes first, otherwise Vite silently moves to another port.
4. Report the authority flags from `/health` verbatim every time — they are the proof
   that the harness is still non-value-moving.

Restart procedure:

```bash
# 1. identify the studio processes (PowerShell called from the bash terminal)
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Select-Object ProcessId,CreationDate,CommandLine | Format-List"
# 2. stop the ones whose CommandLine is 'node scripts/studio.mjs' / the repo's vite.js, then:
cd /c/Users/faupe/Documents/BrainFiles
pwsh -File "Werkstatt\auto-prediction-studio/studio-start.ps1"
```

The start script path is relative to `C:\Users\faupe\Documents\BrainFiles` — run it from
that cwd or the `Werkstatt\...` argument will not resolve. The script sets its own
`CODEX_HOME` and a `pnpm` shim itself; do not export those manually.

## Control-plane and UI contracts

- UI: `http://127.0.0.1:5173` (Vite, HMR active).
- Control plane: `http://127.0.0.1:4100`. The health endpoint is **`/health`** and returns
  `schemaVersion: pmh.studio-surface-health.v1` with `startup`, `catalogRefresh`,
  `liveExecutionEnabled`, `externalWriteAuthority`, `valueMovingAuthority`.
  `/api/health`, `/api/status`, `/api` all 404 — probing the wrong path looks like a dead
  service and triggers a needless restart.
- `catalogRefresh.status: DISABLED` with `lastResult: DEGRADED` is the known
  Discover-preflight 403 (in-process `CODEX_RESPONSES`); the `CODEX` profile
  (app-server, own `CODEX_HOME`) is still USABLE. Do not report it as a new fault and do
  not "fix" it by restarting the studio.

## Hard boundaries

- PROPOSE_ONLY. No live order, no signature, no token approval, no fund movement, no
  production trading credentials. Solvers propose; only the first-party exact verifier
  publishes a certificate.
- Never read, print or write credentials (`auth.json`, `.env`). Use the dedicated
  `CODEX_HOME` (`%USERPROFILE%\.codex-harness`) instead of `~/.codex/config.toml` with
  OmniRoute as provider — the latter makes the app-server return `account: null`.
- No push, no commit without an explicit order; work on own branch `<agent>/<thema>`.
- No model budget for scans or manual runs without explicit clearance. Previews and
  paused campaigns are free.
- Monetary values are `bigint` fixed-point, never JS `number`. Venue SDKs stay inside
  their adapter package. Read `PLANS.md` before non-trivial construction; keep
  `QUESTIONS.md` for non-blocking user decisions.

## Pitfalls

- **Fixtures are hash-checked and CRLF destroys them.** Never let an editor or tool
  rewrite line endings under `projects/fixtures/`; write with `-text` semantics.
- **Do not test port liveness by parsing `netstat` in the bash terminal** — piping it
  into a text filter (`grep`) reports "Binary file (standard input) matches" because of
  CRLF/wide characters, so a live port looks unhandled. Probe with `curl` HTTP status
  instead, and use `search_files` rather than shell text filters for anything else.
- **Fixture-checkout regression test needs a native source path, not a `file://` URL.**
  `real-candidate-preflight.test.ts` originally cloned via `pathToFileURL(...).href`
  (`file:///C:/…`); MSYS Git (`/mingw64/bin/git`) cannot resolve that and the clone
  fails with "does not appear to be a git repository". Pass the source as a plain native
  path (`sourceWithAttributes`), and raise that test's timeout past vitest's 5s default
  (it clones + loads the full corpus across multiple checkout modes). The git in the
  bash terminal is MSYS (`which git` → `/mingw64/bin/git`), not native Windows Git.
- **A filesystem-wide file search over `C:\Users\faupe` can fail** (ripgrep error).
  For known tooling, list the specific directory (`Werkstatt/auto-prediction-studio`)
  instead of searching the whole tree — the studio start script lives there and never
  needs a search.
- Do not create placeholder packages; a package owns working source and focused tests.
- Mutation work (`codex/mutation-<name>`, PR title `[mutation]`) is a candidate under
  selection, not a feature to merge; review it with ADOPT / PARTIAL_ADOPT / HOLD /
  ABANDON and keep the portfolio small and differentiated.

## Support files

- `scripts/studio-status.sh` — read-only studio/control-plane probe; prints HTTP codes
  and the health JSON with a restart verdict. Run before answering any start/restart
  request.
