# Claude Code Telegram-Kanal: Token-Rotation und Neustart

Der Claude Code Telegram-Kanal ist ein ANDERER Prozess als die Hermes-Bruecke
(SkillsBot/Gateway). Er laeuft als `claude --channels
plugin:telegram@claude-plugins-official` und liest den Token aus
`~/.claude/channels/telegram/.env`. Wer den Hermes-Bot neu startet, heilt den
Claude-Code-Bot nicht und umgekehrt.

## Prozessbild

- Kanalprozess: `claude.exe --channels plugin:telegram@claude-plugins-official`
  (aus `~/.local/bin/claude.exe`).
- Plugin-Server: `bun.exe` mit `bun run --cwd
  ~/.claude/plugins/cache/claude-plugins-official/telegram/0.0.7 --shell=bun
  --silent start` (package.json `start` = `bun install && bun server.ts`).
- Konfiguration: `~/.claude/channels/telegram/.env` (Token),
  `access.json` (dmPolicy/allowFrom), `bot.pid`.
- Kein Autostart-Eintrag und keine geplante Aufgabe — der Kanal wird manuell
  gestartet. Nach einem Neustart des Rechners muss er von Hand wieder hoch.

## Token rotieren

1. Bot bei @BotFather `/revoke` — der alte Token ist SOFORT 401.
2. Neuen Token in `~/.claude/channels/telegram/.env` eintragen.
3. **Enden pruefen:** ein per Python auf Windows geschriebenes `.env` ist CRLF;
   das Plugin splittet nach `'\n'` (`server.ts:38`) und liest dann einen Token
   mit haengendem `\r` → `getMe` 401, obwohl die Datei korrekt aussieht. Auf LF
   zurueckstellen: `b.replace(b'\r\n', b'\n')`.
4. Kanal neu starten (siehe unten).
5. Beleg: `getMe` mit dem neuen Token → `ok` UND `getUpdates` → `ok: true`
   (der Bot pollt). `getUpdates` parallel zum laufenden Poller nur EINMAL
   aufrufen (Polling-Konflikt).

## Neustart

    # Kanalprozess + Plugin-Prozesse beenden
    Stop-Process -Id <claude.exe-PID>,<bun-PIDs> -Force
    # Kanal ueber eine PowerShell MIT stdin starten (nicht direkt auf claude.exe)
    Start-Process -FilePath 'powershell.exe' \
      -ArgumentList '-NoExit','-Command','claude --channels plugin:telegram@claude-plugins-official' \
      -WindowStyle Hidden

- Prozesse finden: `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine
  -match 'channels plugin:telegram' -or ($_.Name -eq 'bun.exe' -and $_.CommandLine
  -match 'telegram/0.0.7') }`.
- **Der Kanal MUSS ueber eine PowerShell mit stdin gestartet werden, nicht
  direkt per `Start-Process` auf `claude.exe`.** Ein direkter Start erzeugt
  einen Kanalprozess OHNE Plugin-Kind (nur conhost/npx/docker als Kinder) —
  der Bot antwortet nicht, obwohl der Kanalprozess laeuft. Der Weg ueber
  `powershell -NoExit -Command claude --channels ...` startet das Plugin als
  Kind (bun-Prozess unter dem Kanal).
- **Das Plugin nutzt KEINEN Port** — es ist ein MCP-Server ueber
  StdioServerTransport (stdin/stdout), kein HTTP-Server. `bot.pid` und der
  bun-Prozess als Kind des Kanalprozesses sind die Lebenszeichen, nicht ein
  Port. **Port 3010 ist der JEV-Trader (Kuru/Monad-Bot), nicht das
  Telegram-Plugin** — einen Prozess nie nach Port-Aufschrift beenden, erst
  pruefen, was der Port wirklich haelt (HTTP-Test auf 127.0.0.1:3010 zeigt
  `{"model":"jev-latest",...}`).
- **Verwaiste `.in_use`-Markierungen blockieren das Plugin.** Nach mehreren
  Kanal-Neustarts sammeln sich unter
  `~/.claude/plugins/cache/claude-plugins-official/telegram/0.0.7/.in_use/`
  Dateien mit toten PIDs; das Plugin startet dann nicht als Kind. Vor dem
  Neustart die Markierungen toter Prozesse entfernen (PID-Existenz pruefen,
  nur tote loeschen).
- Das Plugin startet asynchron — nach dem Start einige Sekunden warten, dann
  `bot.pid` und den bun-Prozess als Kind des Kanalprozesses pruefen.
- Der Kanal braucht stdin: `claude --channels ...` im Vordergrund bricht mit
  "Input must be provided either through stdin or as a prompt argument" ab.
- Beleg des Neustarts: `getUpdates` mit dem neuen Token liefert `ok: true` und
  wartende Updates — nicht nur `getMe` (das beweist den Token, nicht den Kanal).
  Ein `409 Conflict` von `getUpdates` ist der Beweis, dass der Bot bereits
  pollt (der eigene Aufruf kollidiert mit dem laufenden Poller) — kein Fehler.
