# Der Update-Lauf Schritt fuer Schritt

Referenz zu `SKILL.md`, Abschnitt **Procedure**. Stand 25.09.2026 (Lauf 49 → 60 Commits,
HEAD `d0cb567273`). Beleg fuer diesen Lauf: `Agenten/Hermes/logs/update-20260925-detached.log`.

## 1. Vor dem Lauf messen

```powershell
cd <checkout>; git status --porcelain | head -30; git log -1 --oneline
git fetch origin --quiet; git rev-list --count HEAD..origin/main
git diff --stat HEAD..origin/main -- pyproject.toml requirements.txt requirements-dev.txt uv.lock
git diff --name-only HEAD..origin/main | grep -E 'docker-compose|package\.json|CI_CD|build'   # Kollision mit eigenem Arbeitsbaum?
```

- Kein Treffer im `diff --stat` auf die Abhaengigkeitsdateien = der Rueckstand ist unkritisch, ein
  Aufschub bis zum naechsten Schliessen kostet nichts.
- Der Abstand ist eine Momentaufnahme: waehrend des Laufs kamen 18 neue Commits dazu
  (`rev-list` direkt nach dem Lauf ist die Zahl, die zaehlt).
- Zweiter Stash/Eigentum pruefen: `git stash list` — Autostash-Reste aus alten Laeufen bleiben
  liegen und sind ein eigener Task, kein Blocker.

## 2. Der abgeloeste Lauf (Skript-Skelett)

```powershell
$ErrorActionPreference = 'Continue'
Remove-Item Env:PYTHONHOME, Env:PYTHONPATH -ErrorAction SilentlyContinue
$env:HERMES_HOME = '<HERMES_HOME>'
$checkout = '<HERMES_HOME>\hermes-agent'
$log = '<HERMES_HOME>\logs\update-<datum>-detached.log'
$py  = "$checkout\venv\Scripts\python.exe"
"START $(Get-Date -Format o)"               | Out-File $log -Encoding UTF8
"BEFORE_HEAD $(git -C $checkout log -1 --format=%h)" | Out-File $log -Append -Encoding UTF8
Set-Location $checkout
& $py -m hermes_cli.main update --yes 2>&1 | Out-File $log -Append -Encoding UTF8
$rc = $LASTEXITCODE
"AFTER_HEAD $(git -C $checkout log -1 --format=%h)"  | Out-File $log -Append -Encoding UTF8
"Abstand nachher: $(git -C $checkout rev-list --count HEAD..origin/main)" | Out-File $log -Append -Encoding UTF8
"EXIT=$rc"                                   | Out-File $log -Append -Encoding UTF8
"Log-Ende"                                  | Out-File $log -Append -Encoding UTF8
```

Starten (aus dem `terminal`-Werkzeug, damit der Lauf die Sitzung ueberlebt):

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','<pfad>.ps1' -PassThru
```

- `--yes` faehrt ohne Rueckfragen (Config-Migration, Stash-Restore). `--keep-stash` parkt lokale
  Aenderungen, statt sie zurueckzuholen — nur benutzen, wenn das gewollt ist.
- **Log immer mit `-Encoding UTF8` schreiben.** PS 5.1 `Tee-Object` schreibt UTF-16 (jedes zweite
  Byte NUL) und `grep -c "Log-Ende"` findet dann nichts, obwohl der Lauf fertig ist.
- Nach dem Start ist der aufrufende Werkzeugaufruf tot (Gateway-Neustart). Weiterarbeiten NUR ueber
  die Logdatei und `Get-Process -Id <pid>`.

## 3. Exit-Codes lesen

| `EXIT=` | Bedeutung | Nacharbeit |
|---|---|---|
| `0` | fertig | `hermes doctor`, fertig |
| `1` | Code+Deps fertig, EIN Dienst kam nicht zurueck | `Start-ScheduledTask -TaskName 'Hermes_Dashboard'`, danach `curl http://127.0.0.1:9119/` = 200 |
| `2` | Halter blockiert den venv-Umbau, Code kann stehenbleiben | Halter schliessen (Nutzer), `AFTER_HEAD` gegen `git log -1` pruefen, erneut fahren |

Der Exitcode allein beweist nichts. Immer drei Zeugen: `AFTER_HEAD` im Log, `git log -1` im
Checkout, `rev-list --count HEAD..origin/main`.

## 4. Halter zaehlen (nicht raten)

- Kanonisch: `hermes_cli.update_cmd_windows._detect_venv_python_processes()` und
  `_hermes_holder_subcommand()`; `_self_and_non_gateway_ancestor_pids()` ueberspringt die eigene
  Ahnenschaft — ein aus der Session gestarteter Scan meldet deshalb `[]`.
- Halter sind seit dem 25.09.2026 nicht mehr nur das venv: `<HERMES_HOME>/tools/` traegt die
  eigene Werkzeugkette (python-3.14.7, git, node, npm, ripgrep, uv, ffmpeg, chromium,
  agent-browser), und der Launcher startet den Gateway daraus.
- **Falle:** Eine Probe als PYTHON-DATEI mit eigenem `sys.path`-Eingriff starb in jedem Lauf mit
  `ModuleNotFoundError: No module named 'ruamel'`, waehrend `-m hermes_cli.main --version` und
  `-c` aus demselben venv liefen. Eine Probe, die beim Import stirbt, meldet nie "0 Halter".
  Von aussen aufrufen (`-m`/`-c`, cwd = Checkout) und EINMAL gegen einen bekannten Halter
  gegenpruefen.

## 5. npm-Advisories im Checkout

```powershell
npm audit --json --workspaces=false        # Root, das ist "agent-browser" im Doctor
grep -n 'js-yaml' package.json             # direkte Abhaengigkeit UND overrides
```

- Ein Paket, das **zweimal** gepinnt ist (direkt + im `overrides`-Block), muss an BEIDEN Stellen
  gehoben werden; sonst bricht `npm install --workspaces=false` mit
  `EOVERRIDE … conflicts with direct dependency` ab.
- Danach `npm install --workspaces=false`, `npm audit --json --workspaces=false` = 0, und
  `hermes doctor` meldet "Browser tools (agent-browser) deps (no known vulnerabilities)".
- Der Fix liegt nur im Arbeitsbaum und wird bei jedem Update mitgestasht/zurueckerstattet.

## 6. Legacy-Gateway-Starter aufraeumen

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like '*ermes*' } |
  ForEach-Object { '[' + $_.TaskPath + '] ' + $_.TaskName + ' ' + $_.State }
Get-ChildItem '<HERMES_HOME>\gateway-service'
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
```

- **Zuerst messen.** Fehlt `Hermes_Gateway` in der Liste, existiert die Aufgabe nicht mehr; die
  Warnung meint dann nur die Dateien. `Unregister-ScheduledTask` antwortet in dem Fall
  "Es wurden keine MSFT_ScheduledTask-Objekte gefunden … TaskName Hermes_Gateway",
  `Export-ScheduledTask` antwortet "Das System kann die angegebene Datei nicht finden" — beides
  heisst „gibt es nicht", nicht „kaputt".
- Altdateien nach `<HERMES_HOME>/.sicherung/gateway-service-legacy-<datum>/` **verschieben**
  (nichts loeschen), jeden Schritt in eine Logdatei schreiben.
- **`hermes gateway uninstall` + `install` NICHT nehmen**, solange der laufende Launcher
  funktioniert — der Weg ersetzt ihn mit.
- Eine bereits erhoehte Shell kann `Unregister-ScheduledTask` ohne UAC-Prompt; eine normale
  braucht ihn. Vorher pruefen:
  `[bool](([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))`.

## 7. Fehlalarme belegen, statt sie zu glauben

- **Photon-Doppelkennungen:** `PHOTON_PROJECT_ID`/`_SECRET`/`_ALLOWED_USERS`/`_HOME_CHANNEL`
  stehen NUR in der Haupt-`.env`; kein Bot-Profil hat eigene Werte. Die Meldung entsteht aus dem
  geteilten Credential-Store (`profiles/<bot>/auth.json` als Symlink).
  Messbefehl (Werte nie ausgeben, nur Namen):
  `Select-String -LiteralPath <profil-\.env> -Pattern '^\s*PHOTON'` → Namensliste.
- **Gateway-Prozesse:** `*gateway run*` trifft auch `docker-mcp.exe` ("docker MCP gateway run").
  Am `ExecutablePath` und am Listener festmachen:
  `Get-NetTCPConnection -LocalPort 9900 -State Listen` → `OwningProcess`.

## 8. Sperren und Aufraeumen am Rande

- `.git/index.lock` (0 Byte, alt): erst Alter und ECHTE git-Prozesse pruefen (alle `git fsmonitor--daemon`
  beweisen nichts), dann **umbenennen**, nie loeschen. In PS 5.1 gibt es die Dreiparameter-Form
  `[System.IO.File]::Move($q,$z,$true)` NICHT → `Move-Item -LiteralPath $q -Destination $z -Force`
  und danach `Test-Path` auf BEIDE Pfade.
- **Beenden:** `Stop-Process -Id <pid> -Force`; `taskkill /T /F /PID` tut in dieser Umgebung still
  nichts. Danach die Prozesszahl nachzaehlen.
- Hintergrund: drei Dauerlauf-Stufen und Waechter-Tasks laufen parallel — ein Maintenance-Lauf darf
  sie nicht mitreissen; nach dem Lauf Prozesszahlen gegenpruefen.

## 9. Abschluss (gehoert zum Lauf dazu)

- **Wiki:** `MaxHirn/Wiki/Betrieb/Hermes.md` bekommt einen datierten Abschnitt (was gemessen wurde,
  welcher Exitcode, welcher Belegpfad); neue Lehren unter `MaxHirn/Wiki/Lektionen/`.
- **TASKS.md:** jeder NICHT angefasste Punkt (Fremdarbeit, laufende Prozesse, offene Entscheidung)
  als eigener Task, neueste zuerst unter `## Offen`; erledigte Bloecke nach `## Erledigt`
  verschieben (`- [x]`).
- **Commit:** nur die eigenen Pfade mit `git add <pfad>` (nie `-A`), erst `git status --porcelain`
  auf die erste Spalte pruefen (vorgemerkte Fremdarbeit aus einer parallelen Sitzung), dann
  `git push origin master`. Textdateien sind gemischt LF/CRLF — nach jeder Aenderung
  `git diff --numstat` pruefen: eine gewollte Zeile zeigt `1 1`, eine ganze Datei = Zeilenenden
  zerschossen.

## Belegbeispiele (25.09.2026)

- Log: `START` → `BEFORE_HEAD a48c791` → Bauausgaben → `AFTER_HEAD d0cb567273` →
  `Abstand nachher: 0` → `EXIT=1` → `Log-Ende`.
- Ursache des Exit 1 im Log: "A web dashboard/serve process was stopped during update and could
  not be auto-restarted" plus `Planned runtimes the restart phase never touched: ✗ dashboard`.
- Nachweis danach: `curl http://127.0.0.1:9119/` = 200, Gateway pid aus `tools\python-3.14.7`
  mit Port 9900 als Listener, `hermes doctor` ohne SQLite-/npm-Meldung.

## Aeltere Lauf-Mechanik (Exit 2, Halter, Version-Anzeige)

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

read "update ran" "update done". FALLE (20.09.2026): after a blocked run `hermes --version` prints `upstream <sha>` with the FETCHED sha, not the checked-out one (printed 118984d7 while HEAD was still a51143fb). Only `git log -1 --oneline` in the checkout proves a pull happened. After every update: read log
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

**3b. Aber auch ein LOSGELOESTER Lauf wird vom eigenen TUI blockiert (21.09.2026).** Der Halter-Scan ueberspringt "sich selbst und die eigene Ahnenschaft" (`_self_and_non_gateway_ancestor_pids`) — ein aus der Session gestarteter Scan meldet deshalb `processes: []`, obwohl die TUI-Backends (`venv\Scripts\python.exe -m tui_gateway.entry`) die venv halten. Ein per `Start-Process` DETACHTER Updater hat diese Kette nicht mehr (Elternprozess tot) und sieht sie als Halter -> Abbruch mit Exit 2 VOR dem git pull (der Guard steht in `update_cmd.py:_cmd_update_impl` vor `_prepare_git_command`), Gateway wird pausiert und wieder gestartet, Code bleibt alt. Beleg: `AFTER_HEAD` im Log == `BEFORE_HEAD`. `--force-venv` NICHT nehmen (bei tausenden Commits Rueckstand + npm-Bauten strandet die Installation). Richtiger Weg, ohne dass Max Kommandos tippt: eine EINMAL-Aufgabe (Task Scheduler, `Register-ScheduledTask` ohne Admin moeglich, `-MultipleInstances IgnoreNew`, `-ExecutionTimeLimit` 4 h), die alle 20 s `venv\Scripts\python.exe` mit einem Probe-Skript aufruft, das `_detect_venv_python_processes()` ohne `gateway run`-Zeilen zaehlt (Gateways pausiert das Update selbst), und bei 0 Haltern `update --yes --keep-stash` faehrt; bis 3 Anlaeufe, weil ein Cron-/Bot-Lauf (`hermes -p <profil> chat -q`) jederzeit als Halter dazwischenkommen kann. Danach Hermes einmal schliessen = die einzige Nutzeraktion; die Aufgabe ueberlebt das Sitzungsende, der Waechter-Task der Session NICHT.

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
