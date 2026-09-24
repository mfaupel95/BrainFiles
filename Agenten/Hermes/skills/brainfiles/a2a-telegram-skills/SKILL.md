---
name: a2a-telegram-skills
category: brainfiles
description: Use when A2A peers or skillsbot fail. Fixes A2A wiring.
---

# A2A-Zugriff auf die Skills + Telegram-Bruecke (skillsbot)

## Was wo liegt
- A2A-Server von Hermes: Port 9900 (config.yaml `gateway.platforms.a2a`, Agent `hermes-maks-pc`).
- **Agent-Card**: `GET http://127.0.0.1:9900/.well-known/agent-card.json` (legacy auch `/agent.json`).
- **JSON-RPC 2.0**: `POST http://127.0.0.1:9900/` — NUR die Wurzel. `/a2a` gibt 404 und war der Fehler in der alten Peer-Konfig.
- Methoden: `SendMessage` (params.message{messageId, role:ROLE_USER, parts:[{text}]}), `GetTask` (params.id), optional `contextId` fuer Mehrfach-Turns.
- Antwort: `result.task.status.message.parts[].text` (TASK_STATE_COMPLETED); zwischendurch pollt man `GetTask` (A2A_REPLY_TIMEOUT 300 s).
- **Auth eingehend**: Bearer-Token aus `A2A_PEER_TOKENS` in `Agenten/Hermes/.env` (Format `name:token,name:token`). Ohne Token 401. Token NIE ausgeben.
- Peer-Konfig fuer a2a_call/a2a_orchestrate: `config.yaml` `a2a_agents.<name>: {url, auth:{type:bearer,token}, capabilities}`. URL muss die WURZEL sein.

## Schnelltest (ohne Token anzuzeigen)
```powershell
$tok=((Get-Content '...\Agenten\Hermes\.env' | ? {$_ -match '^A2A_PEER_TOKENS='}) -split '=',2)[1].Trim().Split(',')[0].Split(':',2)[1]
Invoke-RestMethod -Uri 'http://127.0.0.1:9900/' -Method Post -ContentType 'application/json' -Headers @{Authorization='Bearer '+$tok} -Body '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"messageId":"t1","role":"ROLE_USER","parts":[{"text":"Antworte nur mit PONG"}]}}}'
```

## skillsbot (Agenten/Bus/skillsbot.py)
- Telegram <-> A2A-Bruecke: Max schreibt, der Bot reicht per A2A an hermes-maks-pc weiter (alle 43 Skills). Nur Standardbibliothek.
- Einrichtung: BotFather -> `setx SKILLSBOT_TOKEN <neuer Bot>` (NIE TELEGRAM_TOKEN ueberschreiben!), `setx TELEGRAM_CHAT_ID` (gleiche ID wie melder), `python skillsbot.py --probe` (Exit 0), Task: `Agenten/Routinen/skillsbot.ps1` als Admin.
- **Falle geteilter Bot**: TELEGRAM_TOKEN gehoert dauerlauf.py/melder.py (Handel, Freigaben). Zwei getUpdates-Poller an einem Token verschlucken Order-Freigaben. skillsbot verweigert deshalb den Dauerbetrieb ohne SKILLSBOT_TOKEN.
- Befehle im SkillsBot: /status, /papierstatus, /prognose [N] (prognose.py --kurz, 240 s Timeout), /skills [SUCHE], /skill NAME, /run NAME [Auftrag], /hilfe - dazu seit 15.09.2026 dieselben lesenden Handelsbefehle wie im Handelsbot: /lage, /bericht, /spuren, /spur NAME, /strategien, /indikatoren, /markt. Sie werden NICHT hier gebaut: handel_befehle.py reicht sie an `Handel/befehle.py` durch (eine Quelle fuer beide Bots), der Text laeuft wegen des fehlenden parse_mode durch `handel_befehle.klartext()`; die SkillsBot-Hilfe ist selbst ohne HTML-Marken. Der Text aller Handelsbefehle steht in `Agenten/Handel/befehle.py` - dort aendern, nicht in skillsbot.py. Unbekannte Slashbefehle nicht an A2A reichen; nur Freitext.
- **/run NAME [Auftrag] fuehrt einen Skill AUS** (16.09.2026), statt ihn nur zu zeigen: der Bot schickt
  per A2A "Fuehre den Skill 'NAME' aus" + Auftrag und gibt die Antwort zurueck. Ausgefuehrt wird NUR, was
  `skillkatalog.finde()` kennt UND `ladbar` ist; ein Teiltreffer muss eindeutig sein. Unbekannter Name,
  Tippfehler und Skills fremder Systeme enden OHNE A2A-Aufruf mit Begruendung - sonst liefe irgendein
  Skill und niemand erfuehre welcher. Vorher geht eine Zwischenmeldung raus ("Fuehre X aus - das kann
  bis 5 min dauern"). /skill bleibt LESEN, /run ist AUSFUEHREN - nicht zwei Wege fuer dasselbe.
- Freigabefenster nur durch den bestehenden Handelsbot schreiben lassen; keine zweite schreibende Bot-Instanz. dauerlauf.py kennt /freigabe_xperp, /ja_xperp STUNDEN (0 < h <= 24), /nein_xperp, /stop_xperp. Keine Anfrage erzeugen, keine Wachen aendern. Oeffnen nur bei vorhandener, nicht abgelaufener Anfrage. Stop schliesst das Einstiegsfenster, liquidiert keine Position.
- Prognose im SkillsBot ausfuehren, nicht synchron im Handelsbot: lange Marktanalysen blockieren dort Stop-Befehle und Herzschlag. Der vorhandene Prognosepfad bewertet Spot-Maerkte, keine SWAP-Signale.
- Normale SWAPs nicht mit XPERP gleichsetzen: okxf.instrument() kann SWAP abrufen, positionen()/offene_orders() sind noch FUTURES-gefiltert. SWAP-Live nicht als fertig ausgeben.
- Einrichtung mit Telegram getMe pruefen, nicht nur bool(Token); Format nur als Bool ausgeben. Geplanter Task registriert heisst nicht gestartet. Neuen Code erst nach Prozess-Neustart als aktiv melden; Handelsprozess mit offenem Live-Fenster nicht ungefragt neu starten.
- Zwei Dauerlauf-PIDs koennen Launcher und Kind sein: ParentProcessId und ExecutablePath pruefen, nicht Doppellauf behaupten.
- Tests: unittest discover unter Agenten/Bus/tests mit Muster test_handel_befehle.py sowie Agenten/Handel/tests. Freigabetests verwenden ausschliesslich temporaere freigabe_fenster.json. README unter Agenten/Bus beschreibt Bedienung.
- Verwende unter Windows keine PID-Lebendprobe via os.kill(pid, 0): das kann Prozesse beenden. SkillsBot verwendet eine lebenslang gehaltene OS-Dateisperre (msvcrt.locking / fcntl.flock); die Lockdatei bleibt bestehen, eine stale PID ist keine Sperre. Regressionen in Agenten/Bus/tests/test_skillsbot_sicherheit.py.
- Fuehre den Task mit pythonw.exe statt Konsolen-Python aus. skillsbot.ps1 registriert Anmeldung plus Wiederholung alle zwei Minuten mit IgnoreNew und StartWhenAvailable. Nach UAC-Registrierung Taskdefinition zuruecklesen und Prozess pruefen. Task-Code 0xC000013A belegt Abbruch, nicht Git-Loeschung. Ein Commit allein beendet keine Prozesse.
- Telegram-Ausgaben als Klartext nach UTF-16-Laenge teilen; HTML-Escaping vor dem Split zerreisst Entities. --probe muss bei fehlenden Voraussetzungen oder Telegram-Fehler einen Nichtnull-Exit liefern, auch wenn A2A antwortet. Identischen SKILLSBOT_TOKEN/TELEGRAM_TOKEN vor dem Polling ablehnen.
- Antworten koennen Emojis enthalten: stdout vor dem Drucken auf utf-8/replace stellen (`sys.stdout.reconfigure`), sonst UnicodeEncodeError in cp1252-Konsolen.

## Hermes-CLI richtig aufrufen (Windows, Stand 11.09.2026)
- `hermes.exe` (PATH) ist KAPUTT: hermes-agent\venv ist gegen uv-cpython-3.13 gebaut, dessen Python-Installation gemischt ist (SRE mismatch, f-string SyntaxError).
- Funktioniert: `.hermes-runtime\python\cpython-3.11-windows-x86_64-none\python.exe -m hermes_cli.main <args>` mit cwd=hermes-agent UND `PYTHONPATH=hermes-agent\venv\Lib\site-packages`.
- **PYTHONPATH-Falle**: Einmal gesetzt, bleibt es in der windows-mcp-PowerShell-Sitzung erhalten und vergiftet spaetere Python-Aufrufe (3.13-Lib auf 3.11 -> SRE mismatch). Vor Python-Aufrufen immer `$env:PYTHONPATH=''` setzen.
- config.yaml nie manuell editieren: `hermes_cli.main config set <key> <wert>`; unbekannte Schluessel warnen, werden aber gespeichert (ok fuer a2a_agents).

## Gateway-Waechter (MaxHirn-Gateway-Waechter, alle 2 min)
- **FALLE 19.09.2026, zweifach (Commit 3c5e0f6):** Der A2A-Gateway laeuft
  als `python.exe -m hermes_cli.main gateway run` und BINDET PORT 9900.
  `python -m tui_gateway.entry` ist das TUI/Desktop-JSON-RPC-Backend
  (node-/electron-Eltern), lauscht NICHT auf 9900 und ist NICHT der Gateway.
  Das alte Suchmuster `hermes_cli.main gateway` zu eng -> Waechter startete
  alle ~16 min neu (--replace-Handoff, A2A-Port ~90 s weg). Der spaetere
  "Fix" auf den Namen `tui_gateway` zu breit -> er hielt die Desktop-Backends
  fuer den Gateway; als der echte Gateway ausfiel, meldete der Waechter weiter
  "laeuft schon" und der Ausfall (~01:49 bis 14:16) blieb UNERKANNT, der
  SkillsBot scheiterte.
- RICHTIG (03c5e0f6): Port 9900 ist die ERSTE Wahrheit (offen + Test-
  NetConnection -> kein Start). Nur ein Prozess mit `hermes_cli.main gateway`
  zaehlt als Gateway; `tui_gateway` allein zaehlt NIE. Boot-Gnadenfrist 120 s
  gegen --replace-Churn, ein alter haengender Prozess wird neu gestartet.
- Symptom eines echten Ausfalls: `logs/gateway-waechter.log` waechst mit
  'Gateway nicht gefunden - Neustart ausgeloest' OHNE dass Port 9900 offen
  wird; der SkillsBot-Log zeigt `status: fehler`/300-s-A2A-Timeouts.

## a2a_agents-Peer-Wiring reparieren (config.yaml, Commit 47d5f8b)

**Mechanik:** `a2a_call`/`a2a_orchestrate` lesen `a2a_agents.<name>.auth.token`
aus der EFFEKTIVEN Config; `\${VAR}` wird beim Laden aus `os.environ` aufgeloest
(`hermes_cli/config.py::_expand_env_vars`). Der SkillsBot umgeht diese Config
und nutzt `A2A_PEER_TOKENS` direkt - er funktioniert also auch, wenn die Peers
fuer a2a_call tot sind.

**Diagnose in dieser Reihenfolge:**
1. **Endpunkt-Gesundheit vom Auth trennen.** `POST http://<host>:<port>/`
   (Wurzel) als JSON-RPC `SendMessage` "Antworte nur mit PONG" mit gueltigem
   Bearer aus `A2A_PEER_TOKENS`. Antwort 200 = Endpunkt UND Empfangs-Auth ok,
   der Rest liegt in der Ausfuehrung. 401 = Auth fehlt/falsch, Verbindungsfehler
   = Endpunkt tot.
2. **a2a_agents-Config lesen** (`read_file`, nicht `hermes config get` - der
   kennt Custom-Keys nicht, "Config key not set" ist normales Verhalten).
   Fehlt `auth.token` ganz -> 401. Steht ein Literal oder der falsche Key -> 400.
3. **Wo der akzeptierte Token lebt, erfragen, nicht raten.** Lokale Peers
   (Port 9900, Agents `hermes-mcp`/`8741749061`): erster Eintrag aus
   `A2A_PEER_TOKENS` in der `.env`. omniroute (20128): nur der Key, den der
   laufende Prozess als `OMNIROUTE_API_KEY` (Windows-Benutzervariable ==
   'Claude'-Key in `~/.omniroute/storage.sqlite`) traegt - der /v1-Key
   (`\${HERMES_CUSTOM_127_0_0_1_20128_API_KEY}`) wird mit 400 abgelehnt.
4. **Config auf Env-Referenz, nie Literal** (config.yaml ist versioniert):
   `hermes config set a2a_agents.<name>.auth.token '${<VAR>}'` - `config set`
   speichert String-Werte verbatim, die Referenz bleibt. `.env` fuer
   hermeseigene Werte (`HERMES_A2A_TOKEN` = erster A2A_PEER_TOKENS-Token, NICHT
   versioniert), Windows-Benutzervariable fuer Werte ausserhalb Hermes
   (`OMNIROUTE_API_KEY`).
5. **Aufloesung ohne Neustart belegen:** Subprozess mit den Env-Variablen im
   Bereich (`os.environ.update`), `load_user_config_effective()` laden und die
   `auth.token`-Werte gegen erwartete Hashes vergleichen (Werte nie ausgeben).
6. **Erneut `a2a_call`:** 400 -> 500-Start heisst Auth bestanden, nur die
   Ausfuehrung (Provider-Credentials) fehlt - separates Problem, nicht das
   Wiring. omniroute-Auth besteht so (500 statt 400).
7. **Nur eigene Hunks committen** (config.yaml ist bei diesem Nutzer fast immer
   sibling-gemischt): `git add -p`, eigene Hunks 'y', fremde 'n', dann
   `git diff --cached` lesen (nur eigene Zeilen) und OHNE Pathspec committen
   (`git commit -- <pfad>` committet den ARBEITSBAUM-Pfad, nicht den Index).

**Fallen:**
- Env-Var NUR in `.env` wirkt erst nach Prozess-Neustart (os.environ ist pro
  Prozess fix); eine Windows-Benutzervariable ist sofort in jedem bereits
  laufenden Prozess da, der sie beim Start geerbt hat. Lokale Peers aktivieren
  deshalb erst nach Gateway-Neustart, weil `HERMES_A2A_TOKEN` neu in `.env` ist.
- Verifiziert: lokale Peers `auth: {type: bearer, token: \${HERMES_A2A_TOKEN}}`,
  omniroute `token: \${OMNIROUTE_API_KEY}`.

- Der Bot hat dafuer den Befehl `/model` (rein lesend, kein A2A-Aufruf):
  Modell, Endpunkt, Kontextlaenge aus dem Providerblock und die Fallback-Kette.
## Modell des SkillsBots (21.09.2026)

- Der SkillsBot hat KEIN eigenes Modell: `skillsbot.py` reicht per A2A an den
  Gateway (9900), und der bedient das `default`-Profil. "SkillsBot-Modell" ist
  also der `model:`-Block in `Agenten/Hermes/config.yaml`. Einen Modellschalter
  je Plattform gibt es nicht; A2A-`served_agents`
  (`plugins/platforms/a2a/adapter.py`, `_load_served_agents`,
  `platforms.a2a.extra.agents`) koennen nur ein anderes PROFIL bedienen - und
  ein frisches Profil ist eine Insel ohne Max' Skills.
- Gesetzt am 21.09.2026 auf Auftrag Max ("ausfallsicheres lokales mit mindestens
  400000 Token"): `provider: smart`, `default: auto/smart`, `base_url`
  http://127.0.0.1:20128/v1. `providers.smart` traegt `context_length: 400000`,
  der Router meldet fuer `auto/smart` live 1.000.000. Die Ausfallsicherheit
  kommt aus `fallback_providers`: nous (786k) -> ollama-launch/qwen35-8k:cpu
  (lokal, laeuft immer). Der Router selbst ist eine Abhaengigkeit, keine
  Versicherung.
- Nachweis ohne Bot-Last: A2A-SendMessage an 127.0.0.1:9900 ("Antworte nur mit
  PONG"), dann `logs/agent.log` auf `model=... provider=...` mit `platform=a2a`
  lesen. Der laufende Gateway uebernimmt Config-Aenderungen fuer NEUE Sitzungen
  - kein Neustart noetig, der SkillsBot-Prozess wird nicht angefasst.
- **FALLE:** jedes `hermes config set` schneidet den 38-zeiligen
  Kommentar-Schluss der config.yaml ab (Security-/Fallback-Model-Doku). Nach
  JEDEM Set `git diff --stat` pruefen und den Schluss aus der `.bak`
  byte-genau (CRLF) wieder anhaengen.

## Bekannte Zustände
- omniroute (Port 20128, LLM-Router, custom provider 'smart') kann aus sein: dann laufen Gateway-Antworten ueber Ausweichpfade oder scheitern. `Test-NetConnection 127.0.0.1 -Port 20128`.
- omniroute-Bearer-Token ist seit 19.09.2026 eine Env-Referenz
  (`\${OMNIROUTE_API_KEY}`) in config.yaml - kein Klartext-Literal mehr in der
  versionierten Datei.
