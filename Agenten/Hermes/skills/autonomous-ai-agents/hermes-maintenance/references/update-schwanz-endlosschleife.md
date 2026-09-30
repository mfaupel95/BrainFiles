# Update-Schwanz als Endlosschleife: "hermes update laeuft endlos, Gateway antwortet nicht"

Fall vom 30.09.2026, diagnostiziert aus einer CLI-Sitzung (nicht Desktop). Derselbe
Grundfall wie die "Desktop-Bootschleife" in SKILL.md, aber die Symptome heissen hier:
"der update laeuft im Kreis" und "der Gateway antwortet nicht".

## 1. Die Mechanik der Schleife (am Fall belegt)

- Ein Update-Lauf bricht in "Source update preparation" ab — hier: `[WinError 5] Zugriff
  verweigert: tools\.displaced-<hash>\DLLs\libcrypto-3-x64.dll` — NACHDEM er den Gateway
  force-stoppte. Das Receipt (`logs/update_receipts/latest.json`) traegt dann
  `outcome: "failed"` bei gezupltem Code (post_update.sha != pre_update.sha).
- Zurueck bleibt `installs/<hash>/source-completion-pending`. Ab dann faehrt JEDE
  Hermes-Inkraftsetzung (Gateway-Task, Dashboard, TUI, CLI) erst den Inline-Schwanz
  (~4 min: Node deps, TUI, Web, Desktop), scheitert an den Build-Locks der parallelen
  Versuche, und **bewaffnet den Marker neu** — das tut `venv_sync.py` absichtlich:
  der Marker wird VOR dem Tail geschrieben, ein Crash zwischen Dep-Commit und Tail
  soll die Obligation nicht verlieren.
- Der Task `Hermes_Dashboard` hat `RestartCount=999, RestartInterval=PT1M,
  MultipleInstances=IgnoreNew` (gemessen): er startet alle Minute einen frischen
  Schwanz-Versuch. Der Gateway-Waechter (2-min-Takt) startet toffe Gateways neu —
  beide zusammen naehren den Kreis von zwei Seiten.
- Gegenmass der Software: `source-completion-attempts` zaehlt Fehlschlaege;
  `COMPLETION_RETRY_BACKOFF_ATTEMPTS = 2`, `COMPLETION_RETRY_BACKOFF_SECONDS = 900`,
  `COMPLETION_RETRY_MAX_ATTEMPTS = 6` (venv_sync.py). Bei 6 Versuchen schweigt der
  Retry und meldet nur noch "run `hermes update` from a shell".

## 2. Diagnose in dieser Reihenfolge (je ein Terminal-Aufruf)

1. Marker + Zaehler: `ls -la installs/*/source-completion-pending
   installs/*/source-completion-attempts` — vorhanden = Schleife erklaert.
2. Verwaisten Claim ansehen: erste Zeile `.hermes-update-in-progress` ist eine PID;
   `Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>'` leer = Wrack.
3. Laeuft gerade ein Tail? Win32_Process mit `source_completion.py` in der
   CommandLine — das ist die Wurzel eines ganzen Baums (gemessen: zehn
   verschachtelte Kinder 73028->50812->...->55064).
4. Gateway-Identitaet: `gateway_state.json` (pid, updated_at, code_sha) — PID live
   pruefen (state kann "running" auf einer Leiche melden, Fall 5(e) in
   gateway-identitaet-und-wachen.md), Control-Pipe
   `[System.IO.Directory]::GetFiles('\\.\pipe\') | ? { $_ -match 'hermes-gateway' }`
   plus `Get-NetTCPConnection -State Listen -LocalPort 8644,9900` — das aus einer
   .ps1-DATEI fahren, nie -Command (Backslash-Falle). `logs/gateway.log`-Zeilen
   "exited UNCLEANLY" im 2-Minuten-Takt sind der Sturm.
5. Blocker: `ls tools/ | grep displaced` (ohne Prozess darauf = Aufraeumrest, §7
   gateway-identitaet-und-wachen.md), verwaistes
   `locks/desktop-build-<hash>.lock` (leere Datei, kein lebender Tail = entfernen),
   C:-Freiraum (~20 GB transient fuer den Desktop-Bau).

## 3. Prozessfilter-Fallen (heute zweimal fast selbst getreten)

- Der Filter `-match 'desktop'` trifft den MCP-Server
  `ant.dir.gh.wonderwhy-er.desktopcommandermcp` — VOR jedem Kill ParentProcessId
  und volle CommandLine ansehen; nur Baeume toeten, deren CommandLine
  `source_completion.py` traegt.
- Eine Abfrage mit `-match '... update'` findet ihre EIGENE bash-Huelle — Muster
  aus Teilen bauen und `$_.ProcessId -ne $PID` (Wachen-Falle (a)).
- `Disable-ScheduledTask` und `schtasks /change /disable` auf `Hermes_Dashboard` und
  `MaxHirn-Gateway-Waechter` gehen in der nicht erhoehten Sitzung mit
  0x80070005 zu. Nicht noetig: der Waechter prueft die BEDINGUNG (Prozess + Antwort)
  und wird von selbst still, sobald ein Gateway antwortet; der Dashboard-Sturm gibt
  her, sobald die Obligation weg ist.

## 4. Warum der Standalone-Tail die Schleife NICHT loest (gemessen)

- `installs/<hash>/environments/<id>/venv/Scripts/python.exe -I -B -u
  hermes_cli/source_completion.py --source <checkout> --finish-update --desktop
  --prepared` baute alles und schrieb `✓ Update complete! (v0.21.5+... )` —
  der pending-Marker blieb trotzdem stehen und die Obligation weiter offen.
  Begruendung im Code (`hermes_cli/AGENTS.md`, Update-Pipeline): der PARENT-Lauf
  haelt das Update-Lock und akzeptiert "only a correlated terminal result" —
  der Stamp-Commit gehoert zum `hermes update`, nicht zum handerufenen Tail.
  Der Standalone-Tail ist also nur fuer die Desktop-Bootschleife der richtige
  Eingriff (dort fehlt der Updater-Parent ganz), hier NICHT.
- Sonden-Falle: `pm.install.venv_is_current(project_root=<checkout>)` sagt True, der
  Wrapper `pm.venv_is_current(project_root=<checkout>)` (den `prepare_launch`
  benutzt, ueber den pm-runtime-Worker) sagt False. Massgeblich ist der Wrapper.
- `hermes pm install` pinned nur die Store-Tools (python/git/node/ffmpeg...) um —
  kein Stamp-Commit, kein Marker-Clear. Bewiesen wirkungslos gegen diese Schleife.

## 5. Reparatur, in dieser Reihenfolge

1. Tail-Baeume toeten: `taskkill /T /F /PID <wurzel mit source_completion.py>`;
   Dashboard-Baeume mit (`hermes_cli.main dashboard`) dazu (sie re-armen jede Minute).
2. `tools/.displaced-*` entfernen (kein Prozess damit befasst), verwaistes
   `locks/desktop-build-*.lock` loeschen, toten `.hermes-update-in-progress`-Claim loeschen.
3. Marker + Zaehler loeschen: `rm installs/<hash>/source-completion-pending
   installs/<hash>/source-completion-attempts` (entspricht `clear_completion()`;
   ein laufender Update-Arm tut das selbst, nie waehrend eines laufenden Laufs).
4. Den kanonischen Abschluss losgeloest fahren (Vorlage in
   update-run-procedure.md, Abschnitt "Detachable run"), mit
   `hermes-agent\venv\Scripts\python.exe -m hermes_cli.main update --yes`, log
   BEFORE_HEAD/AFTER_HEAD/EXIT=. NIE mit eigenem Zeitlimit. Der Lauf holt dabei
   auch frische Upstream-Commits — der Rueckstand waechst ~25/h.
5. Warten: erst laeuft der offene Tail nach (Node/TUI/Web/Desktop ~10 min), dann
   Fetch/Pull + Auto-Stash der Checkout-Aenderungen, dann Deps ueber alle Profile
   (10-30 min, hohe Last — Werkzeuge laufen dann in Timeouts, kein Defekt),
   Fleet-Matrix, Gateway-Neustart per Launcher.

## 6. Was der Update-Lauf fuer den Nutzer sichtbar tut (vorher ankundigen)

- Er schliesst die laufende Desktop-App: "Stopped running desktop app to free the
  build output (pid ...)" — Absicht (win-unpacked-Sperre), kein Absturz.
- Er pausiert/stoppt den Gateway — bis zu wenige Minuten ohne Telegram/A2A.
- "sync failed"-Zeilen je Profil waehrend "Syncing bundled skills to all profiles"
  sind am 30.09.2026 aufgetaucht; der Endstatus war offen — Nachweis fuehrt erst
  die Fleet-Matrix + `EXIT=`, nicht das Fehlen dieser Zeile.

## 7. Nachweis nach dem Lauf (alle vier)

- Der pending-Marker ist weg und BLEIBT weg: 1-2 Minuten warten — ein einzelner
  Fehlversuch schreibt ihn zurueck (mtime ist der Zeuge; dreimal gemessen).
- `hermes --version` antwortet in Sekunden, nicht Minuten (ohne Obligation kein
  Inline-Tail); kein "finishing an interrupted source update" in der Ausgabe.
- `gateway_state.json`: lebende PID, frisches `updated_at`, `code_sha` == Checkout-HEAD,
  Plattformen `connected`; keine neue "exited UNCLEANLY"-Zeile.
- Dashboard: `Start-ScheduledTask -TaskName 'Hermes_Dashboard'`, Prozess nach ~10-15 s,
  HTTP 200 auf 9119 nach ~45 s; ein Dashboard, das den Port nicht bindet, waehrend die
  Obligation noch offen war, ist kein zweiter Defekt — erst Marker-Clear abwarten.

## 8. Randbefunde

- Verwaistes `state-snapshots/.<ts>-pre-update.<pid>.partial` ist nicht loeschbar
  (Zugriff verweigert) solange ein fremder Prozess es haelt — der Snapshot-Schritt
  des Updates scheitert dann mit WinError 5, ist aber nicht toedlich (der Lauf
  faehrt ohne Snapshot fort). Auferaumen nach einem Neustart.
- `hermes update --plan` ist NICHT read-only gegen eine offene Obligation: es
  faehrt zuerst den Inline-Tail (und bewaffnet den Marker neu). Erst die
  Obligation klaeren, dann planen.
- Nach dem Schlusswort in logs/update-20260930-lauf4.log (Zeile "Windows
  cua-driver refresh deferred (autostart registration requires UAC)") bleibt
  `hermes computer-use install --upgrade` als interaktiver Rest — kein Fehler.