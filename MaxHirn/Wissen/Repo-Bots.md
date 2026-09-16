---
id: 20260916-repo-bots
title: 'Repo-Bots: Flottenstand und Telegram-Zugang'
tags: [bots, telegram, repos]
created: 2026-09-16
updated: 2026-09-16
summary: 'Ein Hermes-Profil je Fremd-Repo in Werkstatt/Repos, erreichbar per Telegram ueber /bots und /bot NAME im SkillsBot.'
---

# Repo-Bots: Flottenstand und Telegram-Zugang

Je Fremd-Repo in `Werkstatt/Repos/` betreibt ein Hermes-Bot (Profil unter
`Agenten/Hermes/profiles/<name>/`, Arbeitsverzeichnis `terminal.cwd` auf den
Klon). Die Profile wurden mit `hermes profile create --clone` angelegt; sie
erben Modell, Werkzeuge und die getrimmte Skill-Bibliothek des Startprofils.

## Zugang per Telegram

Der SkillsBot (`Agenten/Bus/skillsbot.py`) ist die Telegram-Bruecke zu den
Bots:

- **`/bots`** — alle Profile mit Rolle (Name + `description` aus profile.yaml).
- **`/bot NAME NACHRICHT`** — eine Frage an das genannte Profil. Der SkillsBot
  startet einen frischen Einzelauftrag (`hermes -p NAME chat -q "..."`, kein
  Kontext, kein Gateway) und gibt die Antwort zurueck. Kaltstart 30-60 s,
  deshalb geht vorher eine Zwischenmeldung raus.
- Sicherheit: Der Name muss auf der Platte existieren (`profiles/<name>/
  config.yaml`), sonst kein Aufruf. Der A2A-Kontext des Hauptagenten bleibt
  unberuehrt. Der SkillsBot selbst fuehrt nichts aus — er stellt nur die
  Verbindung her.

Der Aufruf entfernt PYTHONHOME/PYTHONPATH aus der Umgebung (Falle: hermes.exe
aus einer MCP-Brueckensitzung) und setzt HERMES_HOME explizit, damit er nicht
vom Arbeitsverzeichnis des SkillsBot abhaengt.

## Flottenstand (Stand 16.09.2026)

26 Repo-Bots + das besondere Profil `nous` (kein Repo, deepseek-v4-flash-free).
Standgemessen mit `git ls-files Agenten/Hermes/profiles/` gegen
`ls Werkstatt/Repos/`.

| Repo (Werkstatt/Repos) | Bot | Besonderheit |
|---|---|---|
| Agent-Reach | agent-reach | Internet lesen ohne API-Gebuehren |
| basic-memory | basic-memory | Wissensspeicher, Repo warten |
| caveman | caveman | token-sparende Agenten-Kommunikation |
| claude-code | claude-code | Claude Code CLI |
| claude-plugins-official | claude-plugins-official | neu 16.09.2026 |
| claudian | claudian | neu 16.09.2026 |
| codex | codex | OpenAI Codex CLI |
| deepseek-harness | deepseek-harness | RL-Orchestrierung |
| EasyCLIProxyAPI | easycliproxyapi | CLI-Proxy-API |
| everything-claude-code | everything-claude-code | Doku/Plugins/Best Practices |
| gbrain | gbrain | neu 16.09.2026 |
| graphify | graphify | neu 16.09.2026 |
| Harvard-Algorithmic-Trading-with-AI | harvard-trading | |
| moon-dev-ai-agents | moon-dev-agents | 46 Agenten |
| Moon-Dev-Code | moon-dev-code | nur PDFs, nichts zu installieren |
| obsidian-skills | obsidian-skills | neu 16.09.2026, Skills fuer Obsidian |
| odysseus | odysseus | neu 16.09.2026 |
| one-skill-to-rule-them-all | one-skill-to-rule-them-all | Skill-Stack |
| OpenTerminal | openterminal | Trading-Dashboard |
| ProjectAtlas | projectatlas | Rust-Repository-Intelligenz |
| santiment | santiment | SanAPI/GraphQL-Wissen |
| Scrapling | scrapling | Web-Scraping |
| skills | skills | Anthropics Skills-Katalog |
| superpowers | superpowers | Skill-Suite |
| Trading-View-MCP-for-AI-by-Moon-Dev | tradingview-mcp | |
| winget-cli | winget-cli | neu 16.09.2026 |

Kein Bot: `copilot-worktrees` — das ist keine Repo, sondern eine lokale
Worktree-Sammlung zu den Schwester-Repos.

## Fallen

- **Profile sind nur teilweise versioniert.** Die `.gitignore`-Whitelist gibt
  je Profil genau `SOUL.md`, `config.yaml`, `profile.yaml` frei; der Rest
  (state.db, sessions, credentials) bleibt unversioniert, wie gewollt.
- **Abgleich gegen die Platte, nicht gegen diese Liste.** Die Liste altert wie
  jede Doku; die Wahrheit ist `ls Agenten/Hermes/profiles/` (ein Bot je
  `config.yaml`). `/bots` im SkillsBot liest die Platte, nicht diese Notiz.
- **Geteilte Credentials.** Alle Bots erben (wie die Altbestaende) die
  Telegram-/Photon-Credential des Hauptprofils — `hermes profile list` warnt
  davor. Solange die Bots ueber `/bot` angesprochen werden, ist das folgenlos;
  fuer ein Multplex-Gateway muesste jeder Bot eine eigene Credential bekommen
  oder die geteilte entfernt werden. Bewusst nicht angefasst.
- **Neuer Bot = drei Ankerpunkte.** Profil anlegen (`--clone`), `terminal.cwd`
  setzen, `profile.yaml`-Beschreibung pflegen (der Kanban-Orchestrator sortiert
  danach). `/bots` zeigt beides von selbst.

Verwandt: [[Agent-Reach]], [[Moon-Dev-Agenten]], [[Projektatlas]], [[Routinen]].