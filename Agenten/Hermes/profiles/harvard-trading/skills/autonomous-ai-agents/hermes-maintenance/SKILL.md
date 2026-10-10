---
name: hermes-maintenance
description: "Use to repair a Hermes install (update, venv, SQLite WAL)."
version: 1.0.1
license: MIT
tags: [hermes, update, sqlite, venv, uv, wal-reset, maintenance]
---

# Hermes Maintenance (update / runtime repair)

Covers the non-trivial parts of keeping a Hermes install current and its
runtime healthy. The bundled `hermes-agent` skill covers feature geography;
this one carries the *repair* workflow that `hermes update` does not always
finish cleanly on its own.

## Egress/iron-proxy: no native Windows binaries (hard blocker)

`hermes egress setup` tries to install `iron-proxy` as a native Windows binary. Neither v0.39.0 nor the latest (v0.49.0, repo moved to `paradigmxyz/iron-proxy`) ships Windows binaries — GitHub release assets are darwin_amd64/arm64 + linux_amd64/arm64 only. Docker on this host (WSL2 backend) doesn't help: the Hermes egress manager spawns the daemon as a native host process, and the docker sandbox runner itself is blocked by the same missing `proxy.yaml` (chicken-egg).

**Fastest fix when `proxy.enabled: true` blocks every terminal/execute_code call:** just disable it — no rollback needed.

    hermes config set proxy.enabled false

The docker_egress check reads config.yaml fresh on every sandbox build, so the running gateway picks the change up immediately (no restart). Verify with a trivial `terminal` call.

Only if the user really wants egress on Windows: run iron-proxy manually as a Linux/WSL/Docker container (repo `paradigmxyz/iron-proxy`) — Hermes will not manage that daemon (no status/auto-start), so prefer plain `enabled: false` unless explicitly asked.

Quick check after any of this: terminal tool must run without `proxy.enabled true iron-proxy not configured`.

## PYTHONHOME poisoning: hermes.exe crashes with a fake "corrupt Python"

Symptom: every `hermes` CLI call dies with `Fatal Python error: init_import_site: Failed to import the site module`, `AttributeError: module '_thread' has no attribute 'start_joinable_thread'` and `SyntaxError: f-string: unmatched '('` — tracebacks that mix the venv's own site-packages with Stdlib files from `AppData\Roaming\uv\python\cpython-3.13...`. Looks like a corrupt Python install, but the runtime is fine: a **stray `PYTHONHOME` in the calling process environment** points the venv's 3.11 binary at a 3.13 Stdlib. The MCP-server supervisor (windows-mcp/ant) exports `PYTHONHOME=<...>\uv\python\cpython-3.13-windows-x86_64-none` and every PowerShell session spawned through it inherits it; the Windows Registry (HKCU/HKLM Environment) is clean.

Diagnosis in one line (run via the windows-mcp PowerShell tool, which has the poisoned env): `Write-Output $env:PYTHONHOME` — if set, that's it. Confirm the venv is healthy with `Remove-Item Env:PYTHONHOME; venv\Scripts\python.exe -c "import sys; print(sys.base_prefix)"` (must print the venv's own base, e.g. `.hermes-runtime\python\cpython-3.11...`).

Fix: `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` (and set `$env:HERMES_HOME`) at the top of every PowerShell one-liner that invokes `hermes.exe` through the windows-mcp/desktop-commander tools. Do NOT reinstall uv Python or touch the venv for this: a `hermes.exe` that fails only because of PYTHONHOME is not a
repair case — clear the variable, then `hermes --version` and `hermes doctor`
are the whole test. Also note the venv has no `hermes_agent` module — the importable package is `hermes_cli` (`import hermes_agent` fails by design; editable-install finder is `__editable___hermes_agent_0_21_1_finder`).

- `hermes update` pulls git, reinstalls deps into `venv`, migrates config
  format, pauses/restarts the gateway profile(s). It can require approval
  (it restarts the gateway / kills running agents).
- Config format migrations bump silently, e.g. `v39 → v40`.
- `hermes doctor` is the post-update verification. Not all warnings are
  fatal; the SQLite WAL one is the one that matters.

## Update only on a clean checkout

`hermes update` ends in a `git pull`. Uncommitted changes in the checkout
(someone editing `gateway/*.py`, or a `*.bak-*` sitting next to it) make the
pull fail or fight the other session's work — and the update restarts every
gateway profile, which severs any session currently talking through that
gateway. Check `git -C <checkout> status --porcelain` first; if it is not
empty, secure that work first (see the `sichern` skill) and run the update when
nobody is mid-edit.

## SQLite WAL-reset bug — the real blocker

Signs in `hermes doctor`:

- `SQLite X (WAL-reset bug)` with a fixed-version hint: 3.51.3+ / 3.50.7 /
  3.44.6.
- `state.db is in WAL mode` + the same for cron/projects/verification_evidence
  /kanban — exposed until SQLite is upgraded.

The version is the LINKED sqlite inside the Python interpreter, not the
Python version — ugrading Python alone can keep a vulnerable SQLite. On an
unstable host this is a real data-corruption risk, not theoretical.

### The fix: `repair_vulnerable_runtime`

Hermes ships a managed repair (`hermes_cli/managed_uv.py`:
`repair_vulnerable_runtime`) that:

1. provisions a uv-Managed Python generation with fixed SQLite
   (`uv python install`, probed + smoke-tested),
2. stages it under `<checkout>/.hermes-runtime/python`,
3. parks the live venv aside and cuts over, then reinstalls deps.

Every failure before cutover leaves the live venv untouched; post-cutover
smoke failures restore it synchronously.

**Key gate:** this repair fires automatically inside `hermes update` via
`ensure_uv()` — but ONLY if uv is already installed when the update runs.
If uv was missing at update time, the update rebuilds the venv with the
system Python and keeps the vulnerable SQLite.

So the fix sequence is:

1. Install uv if missing: `pip install uv` (it lands in `~/.local/bin`,
   already on PATH on this host).
2. Re-run `hermes update` so the repair path is armed.
3. Verify with `hermes doctor` — the SQLite `WAL-reset bug` line and the
   `is in WAL mode` DB warnings must both clear.

### When the repair itself fails: smoke-test false negative (Windows)

Even with uv present and run from an external interpreter, the repair can
return `STATUS: failed` / `detail: replacement environment did not pass
dependency and import smoke tests` while the candidate venv is actually
healthy. Root cause: the staging smoke check (`_smoke_candidate_venv` in
`hermes_cli/managed_uv.py`) launches the candidate with `-I` (isolated
mode), which DISABLES the editable-install sys.path finder. Hermes ships
top-level single-file modules (in `pyproject.toml [tool.setuptools]
py-modules`) that only resolve through that finder — e.g.
`hermes_state_holders` (imported by `hermes_state.py`). Under `-I` the
import fails: `ModuleNotFoundError: No module named 'hermes_state_holders'`.
The live venv fails this same `-I` import too, so it is a false negative,
not real breakage.

Confirm it's a false negative before concluding the candidate is broken:
run the exact same smoke import WITHOUT `-I` on the staged candidate. If it
returns rc 0 and links fixed SQLite, the candidate is good and only the
`-I` flag is to blame.

**Since the auto-repair won't cut over a candidate it misjudges, the manual
cutover is the fix.** The venv is fully regenerable (all real data lives in
HERMES_HOME) so this is low-risk and reversible:

1. Stop the gateway (`hermes gateway stop`) — a running `gateway run`
   process maps the venv and blocks the rename (Windows can't rename a dir
   a process executes from).
2. Locate the newest staged candidate:
   `<checkout>/.hermes-runtime/python/venv-candidate-*` (the fixed managed
   Python + built deps are already there). Verify its `Scripts/python.exe`
   reports fixed SQLite and passes the no-`-I` smoke.
3. Swap: `mv venv venv.bak.sqlite-repair && mv <candidate> venv`.
4. Verify: `venv/Scripts/python.exe -c "import sqlite3;print(sqlite3.sqlite_version)"`
   then `hermes doctor` (the `WAL-reset bug` line must be gone) and
   `venv/Scripts/python.exe -m hermes_cli.main gateway start`.
5. Optionally re-run `hermes update` from the new venv to refresh lazy
   backends / tool deps.

If the repair defers with `cannot verify Windows venv holders from this
update context`, it means the repair ran outside the real `hermes_cli.main`
context (the holder-detector lives on that module). Run it via
`<system-python> -m hermes_cli.main` (or a script that imports
`hermes_cli.main` so `_detect_venv_python_processes` is registered) — then
the remaining holder is just the gateway, which you stop as in step 1.
Full reproduction: `references/sqlite-repair-false-negative.md`.

### Windows self-lock pitfall (hard requirement)

On Windows the repair refuses to cut over when the updater process maps the
venv it is replacing, printing:

> SQLite runtime repair deferred: <...> this process maps the live venv's
> own executable. Retrying `hermes update` from inside this venv cannot help.

Run the update from an interpreter OUTSIDE the venv being replaced:

    cd <checkout>   # e.g. C:/Hermes
    <system-python> -m hermes_cli.main update

Then verify `hermes doctor`.

## MCP tools silently missing: launcher's system Python lacks `mcp`

Symptom: `hermes mcp test <server>` returns "MCP server '<x>' requires the 'mcp' Python SDK, but it is not installed", and no `mcp_<server>_*` tools appear in any session, even though every server venv has `mcp`.

Root cause: Hermes's own MCP client runs under the **launcher's interpreter** (e.g. `hermes.exe` in `AppData/.../Python313/Scripts`, system Python), not under any MCP-server venv. If that interpreter lacks `mcp`, MCP support is **silently disabled** at startup regardless of what the server venvs contain.

Check it directly, not via server venvs: `python -c "import mcp"` under the interpreter that launches `hermes`. Fix: `python -m pip install mcp` into that runtime, then `hermes gateway restart` (twice — once after install, and MCP tools only load in processes started *after* the install). Already-running sessions won't hot-reload MCP tools; start a new one.

## Windows scheduling and terminal quoting (pitfalls that cost a session)

- **`schtasks` cannot set StartWhenAvailable — use `Register-ScheduledTask`.** `schtasks /create` has no flag for "Starten, sobald möglich". For that you need `Register-ScheduledTask` with `New-ScheduledTaskSettingsSet -StartWhenAvailable` (`$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable; Register-ScheduledTask -Settings $settings`). Every daily/weekly task that must survive Kernel-Power-41 reboots needs this.
- **Driving PowerShell through the bash `terminal` tool expands `$` variables.** An inline `powershell.exe -Command "Get-ScheduledTask … | ForEach-Object { '{0} | {1}' -f $_.TaskName }"` is parsed by bash first — `$_.TaskName` and `$action`/`$trigger` vanish and the command fails with `ExpectedValueExpression`. Write PowerShell to a `.ps1` file via `write_file` and invoke it with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/…/tmp_xyz.ps1"` instead. Same for `printf '…\venv\…'` which eats `\v` as vertical tab — use a heredoc or `write_file`.
- **PS 5.1 behandelt stderr von `git`/`hermes` als Fehler: mit `ErrorActionPreference='Stop'` und `2>&1` bricht ein .ps1-Skript mitten im Lauf ab (NativeCommandError).** In Skripten `ErrorActionPreference='Continue'` setzen, bei `git clone` `--quiet` verwenden, und Erfolg nur am Exit-Code/Ergebnis pruefen.

## Iron-proxy configuration for egress

When Hermes is configured with `proxy.enabled = true` (in config.yaml or via environment), the iron-proxy must be set up for outbound web requests (web_search, web_extract, browser_exec) and for certain tool dependencies that fetch from the internet. If not configured, tools will fail with:

    proxy.enabled is true but iron-proxy is not configured. Run `hermes egress setup` to mint tokens and write proxy.yaml.

### Fix

Run once (or when the proxy configuration changes):

    hermes egress setup

This will:

- Generate a certificate/key pair for iron-proxy
- Write `proxy.yaml` in the Hermes config directory (usually `~/.hermes/proxy.yaml`)
- Start the iron-proxy agent in the background (managed as a Hermes service)

After setup, verify with:

    hermes egress status

which should show the proxy agent as `Running`.

Note: The iron-proxy is required only for outbound connections; local file reads and terminal commands are unaffected.


## Other update warnings (mostly benign)

- "Checkout is current, but the venv is unhealthy: venv python missing" —
  the update recreates it; not fatal, but the runtime repair above is when
  it turns into a SQLite problem.
- "tool.dashboard failed to refresh / pip install failed: Failed to inspect
  Python interpreter ..." — one lazy backend keeps its previous version;
  retried on the next update. Not a blocker.
- "platform 'cli' references unknown toolset 'a2a'" + similar for
  google_chat/teams — stale toolset names; only matters if those platforms
  are used. Fix via `hermes tools`.
