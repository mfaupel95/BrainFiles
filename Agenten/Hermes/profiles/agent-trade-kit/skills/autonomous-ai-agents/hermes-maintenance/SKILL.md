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

Fix: `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` (and set `$env:HERMES_HOME`) at the top of every PowerShell one-liner that invokes `hermes.exe` through the windows-mcp/desktop-commander tools.

**Root cause + durable fix (18.09.2026):** the poison is not the supervisor — it is the MCP server's OWN venv. `ant` builds every Python MCP-server venv on a uv-managed base (`AppData\Roaming\uv\python\cpython-3.13...`), and a uv venv's `python.exe` sets `PYTHONHOME` in its OWN process environment at startup. Any child the server spawns (PowerShell from windows-mcp, subprocesses from archiv/kraken/mail/tooluniverse/blender) inherits it. Verify: run the server venv's python and print `os.environ.get('PYTHONHOME')` — a uv venv prints the base, a python.org venv prints `None`. Durable fix: rebuild the server venv on a python.org interpreter (`C:\Users\faupe\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv`), which does NOT set PYTHONHOME, then reinstall deps. `requires-python >=3.13` is satisfied by python.org 3.13. Pitfall: `pip install -e .` can silently skip deps when a dep is unsatisfiable (tooluniverse's `fitz>=0.0.1.dev2` has no PyPI release — only 0.0.0); the server only imports fitz in one lazy tool, so install `-e . --no-deps` + `pip install PyMuPDF` (provides the `fitz` module) + the rest of the dep list manually. The fix takes effect for NEW sessions (the current session's MCP servers were spawned with the old venv). Do NOT reinstall uv Python or touch the venv for this: a `hermes.exe` that fails only because of PYTHONHOME is not a
repair case — clear the variable, then `hermes --version` and `hermes doctor`
are the whole test. Full rebuild recipe per server (dep tables, the `fitz` workaround, child-process verification): load `references/mcp-venv-rebuild.md`. Also note the venv has no `hermes_agent` module — the importable package is `hermes_cli` (`import hermes_agent` fails by design; editable-install finder is `__editable___hermes_agent_0_21_1_finder`).

- `hermes update` pulls git, reinstalls deps into `venv`, migrates config
  format, pauses/restarts the gateway profile(s). It can require approval
  (it restarts the gateway / kills running agents).
- Config format migrations bump silently, e.g. `v39 → v40`.
- `hermes doctor` is the post-update verification. Not all warnings are
  fatal; the SQLite WAL one is the one that matters.

## Running an update: clean, plan, detach, verify

**1. Clean checkout first.** `hermes update` ends in a `git pull`. Uncommitted
changes in the checkout (someone editing `gateway/*.py`, or a `*.bak-*` sitting
next to it) make the pull fail or fight the other session's work. Check
`git -C <checkout> status --porcelain` first; if it is not empty, secure that
work first (see the `sichern` skill) and run the update when nobody is mid-edit.

**2. `hermes update --plan` before touching anything.** Read-only and explicitly
safe on a live fleet: it prints the install kind, every profile, and each running
Hermes service that will be restarted, with the restart command. Show that list to
the user before the real run — it is the difference between “an update” and “your
session and 15 profiles go down for a minute”. `--check` only asks whether an
update is available; `--yes` runs without prompts (config migration and
stash-restore); `--keep-stash` parks local changes instead of restoring them.

**3. Exit code 2 = venv rebuild blocked by a holder — and the code half may not have run either.**
Any process mapping the venv's own executable blocks the rebuild (typically the
desktop app's backend: `venv\Scripts\python.exe -m hermes_cli.main --profile …`;
on Windows the requesting session itself maps the venv, so exit 2 with your own
session still alive is the expected outcome, not a repair failure). The update
pauses the gateway, refreshes the Windows gateway launcher scripts and restarts
it, then exits 2 — the git pull can be skipped too. VERIFY the checkout before
concluding anything: `git -C <checkout> log -1 --oneline` and
`git rev-list --count HEAD..origin/main` after `git fetch origin`. It prints

> Other Hermes processes are running from this install's venv: PID … ← Hermes backend (if the Desktop app is open, close it)
> dependency update would fail partway and leave a broken install.
> (or use `hermes update --force-venv` to proceed anyway at your own risk)

So never read "update ran" as "update done". After every update: read the log
tail, check the exit code, and read `hermes --version`, which prints
`upstream <sha> · local <sha> (+N carried commits)` — that line tells code-pulled-but-deps-
skipped apart from a clean run. Ground truth is git, not the update counter:
`hermes update --check`'s "N commits behind" counts from the installed version,
not from local HEAD, and can be far larger than the real gap — measure with
`git rev-list --count HEAD..origin/main` and judge urgency from
`git diff --stat HEAD..origin/main -- pyproject.toml requirements*.txt uv.lock`;
no dependency changes means the pending commits are safe to defer until Hermes
is closed. Do not use `--force-venv` to push past a holder; do not manually
`git pull` the live checkout (the sandbox refuses rewrites of the running
install — close Hermes and let `hermes update` do the pull); close the holder
(the user does that, not you) and run the update again.

**4. Detach the run and log it.** The update restarts the gateway, which kills
the very session that requested it — and an update process started from inside
that session dies with it, mid-dependency-install. Write a small `.ps1` that
clears `PYTHONHOME`/`PYTHONPATH`, sets `HERMES_HOME`, runs
`venv\Scripts\python.exe -m hermes_cli.main update --yes` from the checkout and
pipes everything to a log file, then start it with
`Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',<pfad> -WindowStyle Hidden -PassThru`.
The invoking tool call gets interrupted; the log file is the evidence, and the
next session reads it (`Log-Ende`, exit code, version before/after).

`<runtime-python>` is the VENV python (`venv\Scripts\python.exe`) — the bare
uv-managed base under `.hermes-runtime\python\cpython-3.11*` has NO
site-packages and dies instantly with `ModuleNotFoundError: No module named
'yaml'`. Use the venv python for the normal update path; the external
interpreter route below is only for the SQLite self-lock case.

PS 5.1 `Tee-Object` writes the log as UTF-16: every second byte is NUL, so
`grep -c "Log-Ende"` on the log returns 0 even after the run finished. Read it
with `tr -d '\0'` / `grep -a`, or write the log with `-Encoding UTF8`.

## Gateway-Ausfall: Diagnose und Waechter (Windows)

Erste Weiche bei „Gateway ist ausgefallen": Kernel-Power 41 in den letzten 24 h
zaehlen. Keiner = Prozessabsturz/Neustart, kein Hardware-Ausfall.

**Das Exit-Tagebuch lesen:** `<HERMES_HOME>/logs/gateway-exit-diag.log`
(JSON-Zeilen; Tags `gateway.start`, `asyncio.run.SystemExit`,
`gateway.exit_nonzero`, `gateway.previous_unclean_exit`). Ein
`SystemExit` mit Code 75 ist `GATEWAY_SERVICE_RESTART_EXIT_CODE` — ein
Neustart-Verbleib, kein Crash; ein echter Crash hinterlaesst ein
`previous_unclean_exit` beim naechsten Start (kein sauberer
`exit_clean`-Eintrag). `gateway.log` liefert die Begruendung der Stelle
(„Stopping gateway for restart...", „Another gateway instance started").

**„Another gateway instance (PID …) started during our startup. Exiting to
avoid double-running." = Doppelstart, nicht Absturz.** Ursache sind duplizierte
Gateway-Aufgaben: `Get-ScheduledTask | ? { $_.TaskName -like 'Hermes_Gateway*' }`.
Ein Legacy-Task einer frueheren Installation (Logon-Trigger) feuert weiter,
auch wenn sein VBS schon entschaerft ist — der Task selbst muss deaktiviert
oder entfernt werden (Admin), nicht nur das Skript. Der Eintrag
„Refreshed Windows gateway launcher scripts" im Update-Log ist kein Hinweis,
dass ein alter Task entsorgt wurde.

**Beim Verdacht „MCP-Server X war die Ursache":** zwei `starting MCP server …`-
Eintraege fuer denselben Server im Abstand von Sekunden sind ein zweiter
Gateway-Prozess (der Doppelstart), kein Serverfehler. Der Server ist Zeuge,
nicht Taeter.

**Zweite Form der Gateway-Dopplung: Login-Items im Startup-Ordner.** Ein
`hermes -p <profil> gateway start` legt `…\Startup\Hermes_Gateway_<profil>.vbs`
plus `profiles/<profil>/gateway-service/` an — pro Anmeldung ein zweites
Gateway neben dem Standard-Gateway. `Get-ScheduledTask` zeigt das NICHT.
Zusaetzlich pruefen:

    ls "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup" | grep -i hermes
    ls -d <HERMES_HOME>/profiles/*/gateway-service

Beweis sind die EIGENEN Logs der Profile (`profiles/<p>/logs/gateway.log`):
abwechselnde „Starting Hermes Gateway" / „Stopping gateway for restart",
„explicit --replace handoff completed" (ein Profil-Gateway nimmt dem
Standard-Gateway Token und Port weg) und im Standard-Log „another gateway
already holds the dispatcher lock". Mehrere Gateways auf einem Host
verdraengen sich gegenseitig; das Gateway faellt minutenlang aus. Entfernen
ohne Admin — `gateway uninstall` loescht Login-Item UND Launcher:

    hermes -p <profil> gateway stop
    hermes -p <profil> gateway uninstall

Endzustand: genau EIN Starter (Launcher-Task) plus der Waechter.

**Ohne `-p` gilt das STICKY Profil.** `hermes profile use` schreibt es
(`active_profile` im HERMES_HOME; `hermes gateway list` markiert es mit
„(current)"). Steht es auf einem Bot-Profil, meldet `hermes gateway status`
„No gateway process detected", obwohl das Standard-Gateway laeuft — und jeder
Aufruf ohne `-p` installiert/startet dort ein Gateway. Zurueck mit
`hermes profile use default` (die Datei verschwindet dann).

**Der Waechter erkennt Prozesse am Kommandozeilen-Teilstring**
(`hermes_cli.main gateway`) — das trifft auch einen kurzlebigen eigenen
`hermes gateway list`-Aufruf und kann ein „laeuft schon" vortaeuschen. Bei
Ausfaellen die Eltern-Kette ansehen (Launcher-VBS -> venv-python ->
`.hermes-runtime`-python), nicht dem Substring glauben; die PIDs stehen in
`gateway.pid`/`gateway_state.json`.

**Exitus-75-Restart-Schleife: Startup schafft die Sekundaerprofile nicht.** Loggt der Waechter alle ~6-8 min „Gateway nicht gefunden - Neustart ausgeloest" und zeigt `gateway-exit-diag.log` nur wiederholte `gateway.start`-Eintraege OHNE `previous_unclean_exit`, ist es kein Crash, sondern: Event-Loop blockiert beim Startup → `shutdown_watchdog` „missed 3 consecutive liveness probes; dumping all thread stacks" → Exit 75 → Supervisor/Waechter startet neu. Beweis im Thread-Dump, der in `logs/gateway-stdio.log` NACH der CRITICAL-Zeile steht: der Frame „Current thread" IST der Watchdog selbst — den Event-Loop-Thread (in `asyncio`-Frames, Stack endet ueber `gateway run`) lesen. Block in `ntpath.realpath` / `importlib.get_data` / `sqlite_util.open_db` waehrend `_start_secondary_profiles` (`restore_undelivered_completions`) = Start-Recovery ist die Blockade. Ausloeser meist ein LANGSAMER/INKONSISTENTER Sekundaerprofil-Start (27 Profile x ~1 s je im guten Fall; im schlechten Fall Netzwerk-Timeout wie `[Telegram] ... ConnectTimeout` = Minuten je Profil). Gegenprobe im `gateway.log`: schafft ein Start alle Profile in ~60 s und der naechste haengt beim ersten Profil, ist es Netzwerk/Last, kein Code-Fehler — kein Update repariert das; es heilt, sobald das Netzwerk antwortet. Watchdog-Timeout/Profilzahl anfassen nur mit Max-Entscheidung.

**Multiplex-Falle als Root Cause (19.09.2026, Commit 51ca333).** Wenn JEDES Bot-Profil
in `profiles/<p>/config.yaml` einen kopierten `gateway:`-Block traegt
(`a2a: enabled: true, extra: port: 9900`) UND die Haupt-config
`gateway.multiplex_profiles: true` setzt, faehrt der zentrale Gateway beim Start ALLE
Profile als Sekundaeradapter auf denselben Port 9900 hoch. Der Dump-Stack zeigt dann
nicht `restore_undelivered_completions`, sondern `_load_secondary_profile_config` →
`load_gateway_config` → `shared_loop_targets` → `plugin_entries` → `_resolve_all` →
`_load_plugin_scoped` → `_load_directory_module` → `exec_module` (synchron in der
Event-Loop) — ein Config-Fehler, KEIN Netz/Last-Fall. Erkennung: (a) `last_heartbeat_at`
ist in JEDEM `previous_unclean_exit`-Eintrag DERSELBE Zeitstempel (der Stamp kam seit
dem ersten Einfrieren nie mehr durch), waehrend `updated_at` weiterlaeuft; (b) die
CPU-Zeit des haengenden Prozesses waechst (hunderte Sekunden in Minuten) = Hot-Spin,
kein passiver Hang; (c) Kill-Kadenz ~16 min (nicht 6-8). Fix: `gateway.multiplex_profiles:
false` in der Haupt-config und obsolete `profile_routes`-Eintraege deaktivieren
(`enabled: false`) — die Bots laufen als Einzelauftraege (`hermes -p <name> chat -q`
via SkillsBot `/bot`), nicht als Multiplex-Adapter. Config byte-genau aendern (CRLF!):
`.bak-JJJJMMTT` anlegen, binaer lesen, `multiplex_profiles: true` → `false`,
`git diff --stat` muss 2 Zeilen zeigen; das patch-Werkzeug ist fuer Hermes-config.yaml
gesperrt (siehe hermes-config-ops), und in der gemischten Datei NUR die eigenen Zeilen
committen (deterministischer Index-Bau, siehe arbeitsbaum-git-hygiene — die Datei
kann fremde Update-Migrationszeilen enthalten). Beleg nach Neustart: `gateway_state.json`
zeigt `running`, `updated_at` altert nie ueber ~60 s, keine neue CRITICAL-Zeile in
`logs/gateway.log`, und der SkillsBot antwortet wieder (`Agenten/Bus/skillsbot.log`:
Test-Nachricht vorher `status: fehler`, nachher `status: ok` — er haengt ueber den
a2a-Port 9900 am Gateway).

**Vorsorge: ein Gateway-Waechter.** Kleines Skript (Ablage `Agenten/Routinen/`),
das alle 2 Minuten prueft, ob ein Prozess mit `hermes_cli.main gateway` in der
Kommandozeile lebt, und wenn keiner lebt, den offiziellen Launcher-VBS aus
`gateway-service/` via `wscript.exe //B //Nologo` startet; jede Aktion in eine
Logdatei unter `Routinen/logs/`. Selbsttest: bei laufendem Gateway muss es
still mit Exit 0 enden. Registrieren mit `Register-ScheduledTask`
(siehe „Windows scheduling" unten): Trigger `-AtLogOn` PLUS `-Once -At (jetzt+1
min) -RepetitionInterval 2 min -RepetitionDuration 3650 Tage`, Settings
`-StartWhenAvailable -ExecutionTimeLimit 2 min -MultipleInstances IgnoreNew`.
Die Registrierung verweigert eine nicht erhoehte Sitzung („Zugriff
verweigert") — den einen Admin-Befehl bekommt Max, danach lesend belegen
(`Get-ScheduledTaskInfo`).

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
