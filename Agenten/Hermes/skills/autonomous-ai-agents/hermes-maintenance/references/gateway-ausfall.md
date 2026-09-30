<!-- Referenz zu hermes-maintenance, Abschnitt "Gateway-Ausfall". Stand 25.09.2026. -->

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
oder entfernt werden, nicht nur das Skript. Der Eintrag
„Refreshed Windows gateway launcher scripts" im Update-Log ist kein Hinweis,
dass ein alter Task entsorgt wurde.

**Erst MESSEN, dann handeln — meist ist der Task laengst weg und nur die DATEIEN
liegen noch da.** `Get-ScheduledTask | ? { $_.TaskName -like 'Hermes_Gateway*' }`
listet ueber ALLE Task-Pfade; fehlt der Legacy-Name darin, existiert er nicht mehr,
und die Warnung im `gateway status` bezieht sich nur auf die Dateien
(`gateway-service/Hermes_Gateway.vbs`, `…cmd`). Die Fehlermeldungen dafuer sind
„Es wurden keine MSFT_ScheduledTask-Objekte gefunden … TaskName Hermes_Gateway"
(`Unregister-ScheduledTask`) und „Das System kann die angegebene Datei nicht finden"
(`Export-ScheduledTask`) — beide heissen NUR „gibt es nicht (oder liegt in einem
anderen TaskPath, dann `-TaskPath` mitgeben)", nicht „kaputt".

**Der vom Doctor vorgeschlagene Weg `hermes gateway uninstall` + `hermes gateway install`
ist die schwere Loesung** und ersetzt dabei den LAUFENDEN Launcher samt seinem Task —
richtig nur, wenn der Starter wirklich neu erzeugt werden muss. Ist der Legacy-Task weg
und nur die Datei da, ist das kleinere und nachweisbare Vorgehen: die Altdateien nach
`<HERMES_HOME>/.sicherung/gateway-service-legacy-<datum>/` VERSCHIEBEN (nichts loeschen),
die Aufgabeliste und den laufenden Gateway pruefen und jeden Schritt in eine Logdatei
schreiben. Auf eine erhoehte Sitzung achten: eine bereits erhoehte Shell kann
`Unregister-ScheduledTask` ohne UAC-Prompt, eine normale braucht ihn.

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
`hermes gateway list`-Aufruf und kann ein „laeuft schon" vortaeuschen.
Derselbe Fehler in der anderen Richtung: ein Suchmuster `*gateway run*`
(z. B. beim Zaehlen der Gateway-Prozesse) trifft `docker-mcp.exe` — der Container
startet mit `docker MCP gateway run`. Eine Liste mit drei Treffern kann also EIN
Gateway plus zwei Docker-Prozesse sein. Gateway-Prozesse deshalb am
`ExecutablePath` und am Listener festmachen
(`Get-NetTCPConnection -LocalPort 9900 -State Listen` → `OwningProcess`), nicht am
Teilstring. Bei
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

**Update bricht ab mit „active gateway lock has no PID metadata" / „Could not inspect
gateway PID for profile default".** Das ist KEIN Gateway-Ausfall, sondern ein
Update-Vorlauf-Fehler: der laufende Gateway haelt `gateway.lock`, aber `gateway.pid`
fehlt (oder traegt keine PID-Metadaten), und `hermes update` kann den Prozess nicht
pausieren, weil es die PID nicht zuordnen kann. Ursache meist ein frueherer
fehlgeschlagener Update-Lauf, dessen Cleanup die pid-Datei entfernte, ohne den
Gateway zu stoppen. Diagnose: `cat gateway.pid` — fehlt die Datei oder ist sie leer,
waerend der Gateway laeuft (Port 9900 hat einen Listener), ist das der Fall. Der
Gateway selbst ist gesund; das Update muss nur die pid-Datei wiederherstellen
(Neustart des Gateways schreibt sie neu) oder mit `--replace` laufen. Nicht den
Gateway als „kaputt" behandeln — nur der Update-Vorlauf scheitert.

**Post-Update-Kaskade: `StdioServerParameters` + `pydantic_core` fehlen = kaputte
Installation, nicht MCP-Fehler.** Nach einem Update, das Code und venv inkonsistent
hinterlaesst, parken ALLE MCP-Server mit `AttributeError: module 'tools.mcp_tool'
has no attribute 'StdioServerParameters'` und der `hosted_room_worker` stirbt
5× mit `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`
(„giving up restarts"). Das ist die Signatur eines Code/venv-Mismatch nach dem
Update — der neue Code erwartet Dinge, die die Installation nicht hat. Nicht die
einzelnen MCP-Server reparieren; die Installation konsistent machen (venv neu
bauen / Update sauber zu Ende fahren), dann Gateway neu starten. Ein Waechter, der
einen toten Gateway neu startet, startet bei kaputter Installation einen kaputten
Gateway neu — der Waechter heilt einen Code/venv-Mismatch nicht.

**`exited UNCLEANLY (no exit path ran — SIGKILL / OOM / VM death, or a process kill
issued by the agent or one of its descendants)`** in `gateway-stdio.log` ist die
lifecycle_ledger-Signatur eines HARTEN Kills (kein sauberer Exit-Pfad). Mehrere
solcher Eintraege am selben Tag mit `last_heartbeat_at` deutlich vor dem Exit = der
Gateway wurde von aussen beendet (taskkill/pkill des Host-Interpreters, OOM, VM-
Tod), nicht ein Code-Crash. Beim Zaehlen der Ausfaelle diese Zeile als Crash werten,
`SystemExit`-75-Eintraege dagegen als Neustart-Verbleib.

**Start-Tot-Schleife durch den eigenen MCP-Faecher.** Startet der Gateway alle paar
Minuten neu, meldet `gateway_state.json` dabei `running`, waehrend 9900/8644 geschlossen
sind, und steht im Ledger `exited UNCLEANLY`, dann nicht den Gateway selbst verdaechtigen,
sondern seine KINDER zaehlen. Messung: alle Prozesse mit `MCP-Server` in der
Kommandozeile nach `ParentProcessId` gruppieren — eine Gruppe, deren Eltern-PID der
Gateway ist, nennt den Erzeuger. Den Zustandstext dabei nicht glauben: die ueber mehrere
Abfragen WECHSELNDE Gateway-PID ist der Beleg fuer die Schleife.

Der Gateway startet seine MCP-Server je bedientem Profil; bei vielen Profilen sind das
hunderte Prozesse, die den Commit (`FreeVirtualMemory`) leerfressen, bis er bei rund 1 GB
nicht mehr hochkommt und stirbt — der Waechter startet ihn, die Runde wiederholt sich.
Zwei Fallen dabei:

- **Beide Interpreten zaehlen.** Eine Zaehlung nur ueber `python.exe`/`pythonw.exe` sieht
die node-basierten MCP-Server nicht; die Zahl sieht gesund aus, waehrend der Rechner
  erstickt. Dieselbe Luecke hat die MCP-Wache selbst: sie raeumt nur python-Kinder auf
  und kann die node-Gruppen nicht bremsen.
- **Ueberschuss-Killen allein hilft nicht** — der Erzeuger startet in Sekunden nach.
  Reihenfolge: Prozesszahl UND Commit ueber Minuten im 10–15-s-Takt messen (eine
  Einzelmessung verpasst den Sturm), den Erzeuger ueber die Eltern-PID belegen, dann
  MCP-Umfang bzw. bediente Profile reduzieren oder die Wache auf beide Interpreten
  ausweiten. Erst danach ist die Schleife zu.

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
