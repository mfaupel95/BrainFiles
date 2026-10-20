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
    # Kanal neu starten (detached, braucht stdin — nicht im Vordergrund)
    Start-Process -FilePath 'C:\Users\faupe\.local\bin\claude.exe' \
      -ArgumentList '--channels','plugin:telegram@claude-plugins-official' \
      -WindowStyle Hidden

- Prozesse finden: `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine
  -match 'channels plugin:telegram' -or ($_.Name -eq 'bun.exe' -and $_.CommandLine
  -match 'telegram/0.0.7') }`.
- Das Plugin startet asynchron — nach dem Start einige Sekunden warten, dann
  `bot.pid` und den bun-Prozess auf Port 3010 pruefen.
- Der Kanal braucht stdin: `claude --channels ...` im Vordergrund bricht mit
  "Input must be provided either through stdin or as a prompt argument" ab.
  Immer detached starten.
- Beleg des Neustarts: `getUpdates` mit dem neuen Token liefert `ok: true` und
  wartende Updates — nicht nur `getMe` (das beweist den Token, nicht den Kanal).
