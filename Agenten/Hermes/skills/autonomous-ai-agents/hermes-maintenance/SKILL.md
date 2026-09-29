---
name: hermes-maintenance
description: "Repair a Hermes install: update, venv, SQLite WAL."
version: 1.1.0
author: Hermes
license: MIT
platforms: [windows]
tags: [hermes, update, sqlite, venv, uv, wal-reset, maintenance]
metadata:
  hermes:
    tags: [Hermes, Update, SQLite, Windows, Maintenance]
---

# Hermes Maintenance (update / runtime repair)

Covers the non-trivial parts of keeping a Hermes install current and its
runtime healthy. The bundled `hermes-agent` skill covers feature geography;
this one carries the *repair* workflow that `hermes update` does not always
finish cleanly on its own.

## When to Use

- `hermes update` exits non-zero, or the install sits N commits behind `origin/main`.
- `hermes doctor` reports the SQLite `WAL-reset bug`, npm advisories, or leftover gateway warnings.
- Every `hermes` call dies with `Fatal Python error: init_import_site` (PYTHONHOME section below).
- `mcp_<server>_*` tools silently vanish from sessions.
- The gateway drops out, or its log says "Another gateway instance … started".
- A maintenance run is finished and the findings have to be written down (Wiki, TASKS.md, commit).

## Prerequisites

- `HERMES_HOME` set, checkout at `<HERMES_HOME>/hermes-agent` (e.g. `C:\Hermes`).
- `PYTHONHOME`/`PYTHONPATH` cleared in EVERY shell that calls `hermes.exe`.
- Absolute paths in scripts — a relative program name resolves against the CALLER's cwd.
- PowerShell 5.1 available (scheduled tasks, holder counts); write `.ps1` with `write_file`.
- `uv` installed when the SQLite runtime repair has to fire (see below).
- Git access to the checkout; a GitHub remote only if the user wants the record pushed.

## How to Run

Every step goes through the `terminal` tool. Write each PowerShell step to a file with
`write_file` and invoke it from the `terminal` tool as
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/…/schritt.ps1"` — inline
`-Command` strings lose `$_` to the bash layer. Read logs with `read_file` or narrow them with
`search_files`; never load a whole update log into context.

## Quick Reference

    hermes update --check                  # update available? (counts from the INSTALLED version)
    hermes update --plan                   # read-only: profiles + services that will restart
    git -C <checkout> fetch origin --quiet; git -C <checkout> rev-list --count HEAD..origin/main
    git -C <checkout> diff --stat HEAD..origin/main -- pyproject.toml requirements*.txt uv.lock
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',<ps1> -WindowStyle Hidden -PassThru
    Start-ScheduledTask -TaskName 'Hermes_Dashboard'
    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/
    hermes doctor
    git -C <checkout> log -1 --oneline
    Get-NetTCPConnection -LocalPort 9900 -State Listen | Select-Object -ExpandProperty OwningProcess
    npm audit --json --workspaces=false
    Get-ScheduledTask | Where-Object { $_.TaskName -like 'Hermes_Gateway*' }

## Procedure

1. **Freeze the checkout.** `git -C <checkout> status --porcelain`; if anything is dirty, secure
   that work in its own commit first — the update ends in a `git pull`. Never `reset --hard`,
   `checkout -- <datei>` or `stash` someone else's work.
2. **Measure the real gap.** `fetch` + `rev-list --count HEAD..origin/main` + `diff --stat` on
   `pyproject.toml`/`requirements*.txt`/`uv.lock`. No dependency changes = the pending commits are
   safe to defer. `hermes update --check`'s number counts from the installed version and lies.
3. **`hermes update --plan` and show the restart list** to the user before the real run. Note the
   dashboard entry: the plan promises a restart the run does not always deliver (see step 8).
4. **Handle holders.** Exit 2 is a holder, not a failure; the dashboard's PID pair and the TUI
   backends hold the venv. Count them with the canonical functions in
   `hermes_cli/update_cmd_windows.py`, never with a command-line substring.
5. **Repair the npm pins BEFORE the run** if `npm audit` is dirty: a package pinned twice (direct
   dependency + `overrides`) needs both pins bumped, or `npm install` dies with `EOVERRIDE`.
6. **Detach the run.** Write a `.ps1` that clears `PYTHONHOME`/`PYTHONPATH`, sets `HERMES_HOME`,
   runs `venv\Scripts\python.exe -m hermes_cli.main update --yes` from the checkout, pipes an
   UTF-8 log and prints `BEFORE_HEAD`, `AFTER_HEAD`, `Abstand`, `EXIT=`; start it hidden. The
   invoking tool call gets interrupted by the gateway restart — the log is the evidence.
7. **Read the END of the log.** `EXIT=` plus `AFTER_HEAD` vs `BEFORE_HEAD` vs the real
   `git -C <checkout> log -1 --oneline`. Exit code alone proves nothing.
8. **Triage the exit code:** `1` = one service (usually the dashboard) was not brought back —
   `Start-ScheduledTask -TaskName 'Hermes_Dashboard'`, then HTTP 200 on port 9119.
   `2` = holder. `0` = done.
9. **`hermes doctor` triage:** fix a `WAL-reset bug` line (SQLite repair section); npm advisories
   have their own fix; the photon duplicate lines are a false alarm of the shared credential
   store — measure before deleting anything.
10. **Legacy gateway starters:** measure the task list before believing `gateway status`; usually
    only the FILES are left. Move them into `<HERMES_HOME>/.sicherung/gateway-service-legacy-<datum>/`
    — do not run `gateway uninstall`, it replaces the live launcher.
11. **Prove the runtime identity.** Which interpreter serves the gateway (`ExecutablePath`), who
    listens on the port, what `gateway_state.json` says. Since 25.09.2026 that is
    `<HERMES_HOME>/tools/python-3.14.7…`, not the checkout venv.
12. **Write it down:** Wiki page (`Wiki/Betrieb/Hermes.md`, lessons under `Wiki/Lektionen/`),
    every untouched point as a task in `Archiv/TASKS.md`, then commit only your own paths and
    push. A maintenance run without that record repeats itself next month.

Step-by-step detail, log line shapes, exit-code table, the detach-skript skeleton and the
bookkeeping pattern: load `references/update-run-procedure.md`.

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

Kurzfassung: (1) Checkout saubern - `git status --porcelain` im Checkout, fremde Arbeit vorher
sichern; (2) `hermes update --plan` lesen und dem Nutzer die Neustart-Liste zeigen; (3) Halter
beachten - Exit 2 ist ein Halter, kein Fehler, und `hermes --version` zeigt nach einem blockierten
Lauf die GEHOLTE, nicht die ausgecheckte Fassung; (4) losgeloest starten (Skript + `Start-Process`),
sonst stirbt der Updater mit der Sitzung; (5) `--force-venv` NICHT nehmen und den Live-Checkout nie
von Hand pullen.
Fehlertexte, die Warteprobe-Falle und die Messbefehle im Detail: `references/update-run-procedure.md`,
Abschnitt "Aeltere Lauf-Mechanik".
## Nach dem Lauf: Exit 1 trotz erfolgreichem Update (25.09.2026)

Ein Lauf kann mit **Exit 1** enden, obwohl Code gepullt, Node/TUI/Web/Desktop gebaut und die
Python-Abhaengigkeiten installiert sind. Im Log steht dann:

> A web dashboard/serve process was stopped during update and could not be auto-restarted.
> Planned runtimes the restart phase never touched: ✗ dashboard [default] pid … — planned mechanism: respawn-argv

Beleg aus demselben Log: `EXIT=1`, `AFTER_HEAD` != `BEFORE_HEAD`, `Abstand nachher: 0 Commits`.
Nachziehen mit dem **Task**, nicht mit dem CLI-Befehl:

    Start-ScheduledTask -TaskName 'Hermes_Dashboard'
    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/    # muss 200 sein

Erst danach gilt der Lauf als fertig. (Der Plan nennt denselben Dienst vorab:
`hermes update --plan` listet ihn als „restart: stop before code swap, relaunch with recorded
launch args" — was der Lauf nicht immer schafft.)

**Der Beleg steht im Receipt, nicht nur im Log.** `logs/update_receipts/latest.json` traegt bei
so einem Lauf `outcome: "partial"` mit `gateway_restart.incomplete: true`, `phase_error: "Could
not restart every paused Windows gateway"` und `killed_pids: [...]` — daneben
`pm_sync_outcome: "ok"` und `pm_exit_code: 0`, also ein gelungener Code-Teil. Das Receipt ist
die ERSTE Stelle zum Lesen; das Lauf-Log nur, wenn das Receipt fehlt oder mehr Detail braucht.

**Nachziehen mit Wartezeit messen.** Der Dashboard-Prozess entsteht erst ~10-15 s nach dem
Ausloesen, erreichbar (HTTP 200 auf 9119) ist er nach ~45 s. Ein Port-Check wenige Sekunden nach
`Start-ScheduledTask` meldet einen Ausfall, den es nicht gibt - und wer daraufhin ein zweites Mal
startet, legt einen zweiten Dienst neben den ersten.

## Halter-Probe: stirbt sie beim Import, meldet sie nie "0 Halter"

`tmp/venv_halter.py` (Datei, `sys.path.insert(0, <checkout>)`, danach
`from hermes_cli.update_cmd_windows import _detect_venv_python_processes`) brach am 25.09.2026
in **jedem** Lauf mit `ModuleNotFoundError: No module named 'ruamel'` ab, obwohl dieselbe
Importkette per `venv\Scripts\python.exe -m hermes_cli.main --version` und per `-c` aus
demselben venv fehlerfrei lief. Folge: die Warteaufgabe wartet 45 min auf "0 Halter"
und faehrt nichts.

**Ursache (geloest): das venv war unvollstaendig, nicht die Probe.** Ein abgebrochener
Update-Lauf hatte die Deps nicht nachgezogen (dieselbe Wurzel wie "Tools-Runtime ohne Deps"
unten: dort der `tools`-Python, hier das Checkout-venv). Nach
`venv\Scripts\python.exe -m pip install -e hermes-agent` laeuft DIESELBE Datei fehlerfrei und
findet die Halter im echten Betrieb (`.hermes-runtime`-Python + Dashboard-PID). Der
Datei-Aufruf mit eigenem `sys.path`-Eingriff ist also NICHT das Problem - die Probe war nur
der erste Aufrufer, der die Luecke getroffen hat.

Regel: Die Halter-Probe **einmal gegen einen bekannten Halter** gegenpruefen — bei laufendem
Dashboard muss die Probe dessen PID-Paar sehen (erwartet sind zwei Eintraege: der
`.hermes-runtime`-Interpreter und das Dashboard, der Gateway ist ausgenommen). Faellt die
Probe mit `ModuleNotFoundError` um, zuerst das venv pruefen
(`venv\Scripts\python.exe -c "import ruamel, hermes_cli.update_cmd_windows"`) statt die Probe
umzubauen. Kanonisch sind
`_detect_venv_python_processes()` und `_hermes_holder_subcommand()` in
`hermes_cli/update_cmd_windows.py`; eine eigene Prozessliste per Kommandozeilen-Teilstring ist
genau die Falle, die der Gateway-Waechter schon zweimal getroffen hat.

**Die Laufzeit liegt seit dem 25.09.2026 NICHT mehr im Checkout-venv.** Der Lauf legt
`<HERMES_HOME>/tools/` an (python-3.14.7, git-2.53.0, node-26.7.0, npm-12.0.2, ripgrep-15.2.0,
uv-0.12.3, ffmpeg, chromium, agent-browser) und der neu geschriebene Launcher
`gateway-service/Hermes_Gateway_<suffix>.vbs` startet den Gateway aus
`tools\python-3.14.7+…\python.exe` (dort kein `VIRTUAL_ENV` mehr), waehrend
`venv\Scripts\python.exe` weiter die Desktop-/Dashboard-Backends traegt. Halter-Pruefungen
deshalb am `ExecutablePath` festmachen und beim Bewerten von "Haltern" beide Baeume kennen
(`<checkout>/venv`, `<checkout>/.hermes-runtime`, `<HERMES_HOME>/tools`) — ein Launcher, der
nur auf das venv schaut, sieht den Gateway nicht mehr.

## Tools-Runtime ohne Deps: der stille degradierte Gateway

Der `tools/python-3.14.7…` ist ein **nackter Python** (site-packages enthaelt nur `pip`), bis
`pip install -e hermes-agent` die Deps hineinlegt. **Die leere Paketliste ist allein KEIN
Befund:** der Launcher setzt `PYTHONPATH=<checkout>`, und der Bootstrap zieht die Fremdpakete
zusaetzlich aus dem gestagten Umfeld
(`<HERMES_HOME>/installs/<hash>/environments/<id>/venv/Lib/site-packages`) - ein Gateway kann aus
diesem Python gesund laufen, waehrend `python.exe -c "import pydantic_core"` darin
`ModuleNotFoundError` meldet (Handproben stattdessen mit
`<checkout>/venv/Scripts/python.exe` fahren). Massgeblich ist der Import IM laufenden Prozess
bzw. das Fehlerbild unten, nicht `ls site-packages`. Bricht ein Update ab, BEVOR es die Deps in
den tools-Python installiert (z.B. weil es beim Pausieren des Gateways scheitert), laeuft der
Gateway danach aus einem Python ohne `pydantic`/`pydantic_core`/`openai` — und zwar **weiter**,
nur degradiert. Die Signatur ist eindeutig und haengt zusammen:

- **Alle MCP-Server parken** mit `AttributeError: module 'tools.mcp_tool' has no attribute
  'StdioServerParameters'` — das ist pydantic, das nicht geladen ist (der MCP-Client laeuft
  unter dem Launcher-Interpreter, nicht unter einem Server-venv).
- **`hosted_room_worker` stirbt 5×** mit `ModuleNotFoundError: No module named
  'pydantic_core._pydantic_core'`, dann "giving up restarts".
- **`hermes update` scheitert** mit `Could not inspect gateway PID for profile default` /
  `active gateway lock has no PID metadata` — der Gateway laeuft in halb-kaputtem Zustand.

Diagnose in zwei Zeilen: `Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>'` zeigt den
`ExecutablePath` des Gateways; dann `tools/python-3.14.7…/python.exe -c "import pydantic_core"`
— `ModuleNotFoundError` = die Ursache. Die gesunden Laufzeiten existieren parallel
(`<checkout>/venv` und die staged venvs unter `<HERMES_HOME>/installs/<hash>/environments/*/venv/`
tragen `pydantic_core 2.46.4`); der Gateway nutzt sie nur nicht.

Fix: `tools/python-3.14.7…/python.exe -m pip install -e hermes-agent` (aus `<HERMES_HOME>`),
dann den Gateway neu starten, damit er die MCP-Server wieder verbindet. Der Launcher-VBS setzt
`VIRTUAL_ENV=<HERMES_HOME>/tools` und `PYTHONPATH=<checkout>` — das allein installiert nichts;
die Deps muessen explizit in den tools-Python. Ein `hermes update`-Lauf, der bis zur
Dep-Installation durchlaeuft, erledigt das von selbst — der abgebrochene Lauf ist der
Regelfall, der es nicht tut.

**Nachweis nach dem Neustart:** der neue Gateway schreibt in `logs/gateway.log`, NICHT in
`gateway-stdio.log` (das bleibt auf dem alten Prozess stehen und sieht "tot" aus, obwohl der
neue laeuft). Der Beweis, dass der Deps-Fix gewirkt hat, sind die Zeilen
`✓ a2a connected / ✓ webhook connected / ✓ telegram connected / ✓ photon connected` im frischen
`gateway.log` PLUS ein echter MCP-Tool-Aufruf (z.B. `kraken_status` oder `archiv_statistik`
liefert Daten statt "parked"). Port 9900 kann beim frischen Start kurz ohne LISTEN sein, waehrend
der Gateway noch hochfaehrt — die `✓ … connected`-Zeilen sind der fruehere und eindeutigere
Beleg. Dashboard nachziehen: `Start-ScheduledTask -TaskName 'Hermes_Dashboard'` + HTTP 200 auf
Port 9119 (der Update-Lauf stoppt es und bringt es nicht immer zurueck).

## npm-Audit im Checkout: doppelte Pins brechen `npm install`

`js-yaml` steht im Checkout **zweimal** — als direkte Abhaengigkeit (`"js-yaml": "4.3.1"`) und
im `overrides`-Block (`"js-yaml@^4": "4.3.1"`). Nur eins zu heben laesst
`npm install --workspaces=false` mit
`npm error EOVERRIDE Override for js-yaml@4.3.2 conflicts with direct dependency` abbrechen.
Beide auf dieselbe Fassung setzen (4.3.2), dann `npm install --workspaces=false`, danach
`npm audit --json --workspaces=false` = 0 und `hermes doctor`:
"Browser tools (agent-browser) deps (no known vulnerabilities)". Der Fix liegt nur im
Arbeitsbaum des Checkouts und wird bei jedem Update mitgestasht und zurueckerstattet.

**Vor dem naechsten Hochziehen erst MESSEN, ob der Fix noch noetig ist** — ein spaeterer
Upstream-Stand kann die beiden Pins selbst konsistent gesetzt haben. Gegenprobe in einer
Zeile: `grep -n js-yaml package.json` muss `overrides` UND Direktabhaengigkeit auf DERSELBEN
Fassung zeigen; sind beide gleich, ist der alte Fix gegenstandslos und ein erneutes Anheben
waere ein neuer EOVERRIDE. Was `npm audit` dann noch meldet (typisch vitest-Advisories im
`web/`-Workspace), ist eine eigene Baustelle und kein Zeichen fuer den js-yaml-Pin.

**Verwaiste Autostashes: sichern, dann verwerfen — nie im Checkout committen.** Ein
abgebrochener Lauf laesst Autostashes liegen (`git stash list`), die bei jedem weiteren Lauf
als Warnung wieder auftauchen. Der Checkout wird von `hermes update` verwaltet: ein eigener
Commit dort blockiert den naechsten Pull. Also Inhalt als Patch sichern
(`git stash show -p "stash@{0}" > <HERMES_HOME>/logs/stash-sicherung/autostash-<datum>.patch`),
groesse pruefen (ein leerer Patch = Stash identisch mit HEAD) und danach `git stash drop` bis
die Liste leer ist. `git stash show -p "stash@{0}" -- <pfad>` scheitert mit "Too many
revisions specified" — den Pfad nicht als zweites Argument anhaengen.

## Photon-Doppelkennungen: Fehlalarm bei geteiltem Credential-Store

`hermes doctor` meldet fuer jedes Bot-Profil "Profiles 'default' and '<bot>' both hold the
same photon credential (PHOTON_PROJECT_ID/PHOTON_PROJECT_SECRET)" (25.09.2026: 18 Meldungen,
die **einzigen** verbliebenen Issues) und `hermes gateway status` leitet daraus "This gateway is
STANDALONE … Profiles NOT served (their bots stay silent)" ab. Ursache: die
`profiles/<bot>/auth.json` sind Symlinks auf `Agenten/Hermes/auth.json` — es ist EINE Kennung,
die je Profil neu gezaehlt wird. Die Bots laufen als Einzelauftraege (`hermes -p <name> chat -q`),
nicht als Multiplex-Adapter. **Nicht** reflexhaft die Kennung aus den Profilen loeschen; die
Meldung ist ein Befund der Konto-Zaehlung, kein Ausfall.

Die richtige Diagnose statt des Loeschens: `hermes gateway migrate --dry-run`. Sagt das Tool
"No secondary profile runs its own gateway; the only step is turning the flag on", ist der
einzige echte Schritt `hermes config set gateway.multiplex_profiles true` (danach Gateway neu
starten, damit es greift). Das stellt den Host auf den modernen One-Gateway-Modus, ohne die
geteilte Kennung anzutasten. Achtung beim `hermes config set`: danach `git diff config.yaml`
PRUEFEN (Zeilenende CRLF koennen umgebrochen werden) und die diff zeigt evtl. fremde
nebenlaeufige Aenderungen mit — nur die eigene Zeile stagen.

## Gateway-Ausfall: Diagnose und Waechter (Windows)

Zuerst `logs/gateway-exit-diag.log` lesen (Exit 75 = Neustart-Verbleib, echter Crash hinterlaesst
`previous_unclean_exit`) und Kernel-Power-41-Ereignisse zaehlen - keine heissen Prozess-, nicht
Hardware-Ausfall. "Another gateway instance … started" ist ein DOPPELSTART, kein Absturz: den
zweiten Starter suchen (Aufgabe, Launcher-Datei, `…\Startup\Hermes_Gateway_<profil>.vbs`) und
VOR dem Entfernen messen - meist ist die Aufgabe laengst weg und nur die Datei liegt da.
Endzustand: genau EIN Launcher-Task plus Waechter.
Vollstaendige Diagnose, Multiplex-Ursache, Exit-75-Schleife und Waechter-Einrichtung:
`references/gateway-ausfall.md`.
## SQLite WAL-reset bug — the real blocker

Die Zeile `SQLite X (WAL-reset bug)` (plus `state.db is in WAL mode`) meint die im Interpreter
GELINKTE SQLite-Fassung, nicht die Python-Version. Die Reparatur
(`repair_vulnerable_runtime` in `hermes_cli/managed_uv.py`) feuert im `hermes update` NUR, wenn
`uv` zur Laufzeit schon installiert ist: uv nachziehen, Update erneut fahren, mit
`hermes doctor` pruefen. Manueller Cutover, Windows-Selbstsperre und der `-I`-Smoke-Fehlalarm:
`references/sqlite-wal-reset.md`.
## Further repair cases (MCP tools, npm advisories, egress, benign warnings)

- **`mcp_<server>_*` verschwindet:** der MCP-Client laeuft unter dem INTERPRETER des Launchers,
  nicht unter einem Server-venv - fehlt dort das `mcp`-SDK, wird MCP still abgeschaltet. Dort
  nachinstallieren, danach `hermes gateway restart` (zweimal) und eine NEUE Sitzung starten.
- **npm-Advisories:** `doctor --fix` fasst sie nicht an; Root (`--workspaces=false`) und jede
  Workspace einzeln auditieren, exakt gepinnte Direktabhaengigkeiten heben, neu installieren,
  erneut auditieren.
- **`proxy.enabled is true but iron-proxy is not configured`:** unter Windows gibt es keine
  nativen iron-proxy-Binaries - schnellster Weg `hermes config set proxy.enabled false`.
- **Sonstige Update-Warnungen** (kranke venv, Lazy-Backend nicht aktualisiert, unbekannte
  Toolset-Namen) sind harmlos.
Genaue Befehle und Belege: `references/weitere-reparaturen.md`.
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

## Verification

Drei Zeilen beweisen einen Wartungslauf:

    git -C <checkout> rev-list --count HEAD..origin/main            # direkt nach dem Lauf: 0
    hermes doctor                                                   # kein WAL-reset, kein npm-Advisory
    curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/    # 200 (Dashboard lebt)

Fuer den Gateway zusaetzlich: `Get-NetTCPConnection -LocalPort 9900 -State Listen` muss einen
Prozess nennen, dessen `ExecutablePath` die erwartete Laufzeit ist (`<HERMES_HOME>/tools/python-3.14.7…`
seit dem 25.09.2026, davor das Checkout-venv). Ein `EXIT=0` im Log ist allein KEIN Nachweis.
