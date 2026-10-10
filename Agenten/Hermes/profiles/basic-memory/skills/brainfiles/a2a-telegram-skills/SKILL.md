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
- Befehle im SkillsBot: /status (lokale Zustandsdateien, xperp vor scanner), /papierstatus (Live-Daten nie als Papier), /prognose [N] (prognose.py --kurz, 240 s Timeout), /skills, /hilfe. Unbekannte Slashbefehle nicht an A2A reichen; nur Freitext.
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

## Bekannte Zustände
- omniroute (Port 20128, LLM-Router, custom provider 'smart') kann aus sein: dann laufen Gateway-Antworten ueber Ausweichpfade oder scheitern. `Test-NetConnection 127.0.0.1 -Port 20128`.
- omniroute-Bearer-Token steht im Klartext in config.yaml (a2a_agents.omniroute.auth) — dokumentiertes Hermes-Muster, aber sekretaer.
