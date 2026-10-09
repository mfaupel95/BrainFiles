# Claude Code Channels: Telegram-Bruecke

## Kurzsatz

Claude Code hat kein Telegram-Pendant fuer "Remote Control" (das ist rein
Cloud-/Account-gekoppelt, kein lokaler Port - anders als bei Codex, siehe
[[Codex-Remote-Control-Windows]]). Die passende, offizielle Funktion heisst
**Channels** (Research Preview): ein mitgeliefertes Plugin pusht Telegram-
Nachrichten in eine laufende Sitzung, Claude antwortet zweiseitig zurueck.
Kein eigener Code, keine Beruehrung mit `Agenten/Bus`/Hermes/skillsbot - ein
komplett getrenntes System fuer eine komplett andere Sitzung (diese
interaktive Claude-Code-CLI, nicht Hermes).

## Begriffsklaerung

| Begriff | Was es ist |
|---|---|
| **Remote Control** | `claude --remote-control` - Sitzung von claude.ai/Mobile-App aus steuern, ueber Anthropics Server, kein lokaler Port, kein Drittsystem-Zugang |
| **Channels** | `claude --channels plugin:...` - externe Quelle (Telegram/Discord/iMessage/eigener Server) druekt Nachrichten in eine laufende Sitzung, zweiseitig |

## Einrichtung (einmalig)

1. `/plugin marketplace add anthropics/claude-plugins-official`
2. `/plugin install telegram@claude-plugins-official` (User-Scope)
3. Eigener Bot-Token je Installation - **nicht** der Handelsbot-Token
   (`TELEGRAM_TOKEN`) oder der Hermes-Skillsbot-Token (`SKILLSBOT_TOKEN`),
   sonst Token-Kollision wie beim doppelten `getUpdates`-Polling (siehe
   `Agenten/Hermes/skills/brainfiles/a2a-telegram-skills/SKILL.md`). Token
   kommt von einem frischen BotFather-Bot, Umgebungsvariable
   `CLAUDECODE_TELEGRAMBOT` (Windows-Benutzervariable, `setx`).
   `/telegram:configure <Token>` schreibt nach
   `~/.claude/channels/telegram/.env` - nicht im Repo, nicht versioniert.
4. Start **mit** Kanal: `claude --channels plugin:telegram@claude-plugins-official`
   - Opt-in pro Sitzung, Absicht von Anthropic. Keine settings.json-Option fuer
     Dauerbetrieb.
5. Pairing: Nachricht an den Bot -> Pairing-Code -> im Terminal
   `/telegram:access pair <code>`, danach `/telegram:access policy allowlist`.

## Falle

Der erste vorgesehene Token (`FOMO_RADAR_TELEGRAMBOT`, eine seit laengerem
ungenutzte Variable) zeigte auf einen in Telegram bereits geloeschten Bot -
BotFather-Token bleiben technisch gueltig, auch wenn der Bot selbst nicht mehr
existiert bzw. nicht mehr auffindbar ist. Vor Wiederverwendung eines alten
Tokens in Telegram selbst pruefen (Bot suchen/anschreiben), nicht nur im Code
auf Referenzen greppen.

## Stand

Bot laeuft, Pairing erfolgt, Token-Variable `CLAUDECODE_TELEGRAMBOT`.
