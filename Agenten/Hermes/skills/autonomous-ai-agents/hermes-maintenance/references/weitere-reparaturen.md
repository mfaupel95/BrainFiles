<!-- Referenz zu hermes-maintenance: MCP-Tools, npm-Advisories, Egress, harmlose Warnungen. Stand 25.09.2026. -->

## MCP tools silently missing: launcher's system Python lacks `mcp`

Symptom: `hermes mcp test <server>` returns "MCP server '<x>' requires the 'mcp' Python SDK, but it is not installed", and no `mcp_<server>_*` tools appear in any session, even though every server venv has `mcp`.

Root cause: Hermes's own MCP client runs under the **launcher's interpreter** (e.g. `hermes.exe` in `AppData/.../Python313/Scripts`, system Python), not under any MCP-server venv. If that interpreter lacks `mcp`, MCP support is **silently disabled** at startup regardless of what the server venvs contain.

Check it directly, not via server venvs: `python -c "import mcp"` under the interpreter that launches `hermes`. Fix: `python -m pip install mcp` into that runtime, then `hermes gateway restart` (twice — once after install, and MCP tools only load in processes started *after* the install). Already-running sessions won't hot-reload MCP tools; start a new one.

## npm vulnerabilities: `doctor --fix` does not fix them

`hermes doctor` reports e.g. "Browser tools (agent-browser) has 2 npm vulnerabilities" / "web workspace has 6 npm vulnerabilities"; `doctor --fix` leaves them untouched. They are a build-tool advisory (`hermes_cli/doctor_tools.py::_check_npm_audit` audits 4 targets: checkout root with `--workspaces=false` [labelled "agent-browser"], `--workspace web`, `--workspace ui-tui`, the WhatsApp-bridge dir — each reported only if its `node_modules` exists).

Fix:
1. Enumerate: `npm audit --json --workspaces=false` and `npm audit --json --workspace web` (parse `metadata.vulnerabilities` + per-package `fixAvailable`).
2. `npm audit fix --workspaces=false` for the root.
3. Direct dep pinned exactly (e.g. `"vitest": "4.1.10"`): `npm audit fix --workspace web` answers "outside the stated dependency range" — bump the version in the workspace's `package.json` with `patch`, then `npm install --workspace web` (repeat for `ui-tui`).
4. Re-verify with the same `npm audit --json` — count 0 per target, then `hermes doctor` ends in "All checks passed" (expected benign leftovers besides it: orphan aliases).
5. The changed files (`package-lock.json`, `web/package.json`, `ui-tui/package.json`) sit in the hermes-agent git checkout — leave them uncommitted unless asked.

## Windows scheduling and terminal quoting (pitfalls that cost a session)

- **`schtasks` cannot set StartWhenAvailable — use `Register-ScheduledTask`.** `schtasks /create` has no flag for "Starten, sobald möglich". For that you need `Register-ScheduledTask` with `New-ScheduledTaskSettingsSet -StartWhenAvailable` (`$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable; Register-ScheduledTask -Settings $settings`). Every daily/weekly task that must survive Kernel-Power-41 reboots needs this.
- **Driving PowerShell through the bash `terminal` tool expands `$` variables.** An inline `powershell.exe -Command "Get-ScheduledTask … | ForEach-Object { '{0} | {1}' -f $_.TaskName }"` is parsed by bash first — `$_.TaskName` and `$action`/`$trigger` vanish and the command fails with `ExpectedValueExpression`. Write PowerShell to a `.ps1` file via `write_file` and invoke it with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/…/tmp_xyz.ps1"` instead. Same for `printf '…\venv\…'` which eats `\v` as vertical tab — use a heredoc or `write_file`.
- **PS 5.1 behandelt stderr von `git`/`hermes` als Fehler: mit `ErrorActionPreference='Stop'` und `2>&1` bricht ein .ps1-Skript mitten im Lauf ab (NativeCommandError).** In Skripten `ErrorActionPreference='Continue'` setzen, bei `git clone` `--quiet` verwenden, und Erfolg nur am Exit-Code/Ergebnis pruefen.
- **`$home` ist in PowerShell eine SCHREIBGESCHUETZTE automatische Variable.** Ein Wartungsskript
  mit `$home = '…\Agenten\Hermes'` bricht mit „Die Variable HOME kann nicht ueberschrieben
  werden" ab — und mit `$ErrorActionPreference='Continue'` laeuft es danach WEITER, baut alle
  Pfade aus dem stehengebliebenen `$home` (`C:\Users\<user>`), legt Log und Sicherung woanders
  an, verschiebt nichts und endet mit **Exit 0**. Ein erhoeht gestarteter Lauf meldet dann
  „gestartet und beendet, ExitCode: 0", obwohl nichts passiert ist. Eigene Pfadvariablen
  deshalb `$hermesHome`/`$basis`/`$wurzel` nennen — nicht `$home`, `$pid`, `$host`, `$error`,
  `$profile`. **Und den Exitcode nie als Beleg nehmen:** nach jedem Lauf
  `Test-Path` auf das Ziel plus Zeitstempel von jetzt pruefen, sonst meldet man einen
  Schreibvorgang als erledigt, den es nicht gab.
- **`hermes dashboard --stop` only sees CLI-started dashboards.** When the dashboard runs from its Scheduled Task (`Hermes_Dashboard` → wscript `Hermes_Dashboard.vbs`), `--stop` answers "No hermes dashboard processes running" although the PID pair exists. Kill by PID and restart with `Start-ScheduledTask -TaskName 'Hermes_Dashboard'`. The dashboard pair (venv python + `.hermes-runtime` python) is a venv holder — it appears in the update's holder list and must be closed before a rebuild can succeed.

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
