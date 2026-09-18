---
id: 20260916-repo-bots
title: 'Repo-Bots: Flottenstand und Telegram-Zugang'
tags: [bots, telegram, repos]
created: 2026-09-16
updated: 2026-09-18
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
- **Kanal-Zugangsdaten liegen NUR im Profil `default`** (seit 18.09.2026).
  Vorher trugen 17 Bot-Profile dieselbe Telegram- und Photon-Kennung wie das
  Hauptprofil; `hermes profile list` warnte je Profil, und ein Bot-Gateway, das
  auf demselben Token pollte, nahm dem Hauptgateway die Nachrichten weg (belegt:
  `projectatlas` hatte am 18.09. um 01:18 Telegram-Sitzungen, obwohl das
  Hauptgateway nur `default` bedient). Aufgeraeumt mit
  `Agenten/Hermes/scripts/profil-kanaele-bereinigen.py`: ohne Argument nur
  zeigen, mit `--anwenden` schreiben (je Profil erst `.env.bak-JJJJMMTT`).
  Danach: `hermes profile list` ohne Warnung, Multiplex-Migration frei.
  Gestrichen wurden **nur** `telegram` und `photon` — die geteilten
  `A2A_*`- und `SMS_*`-Zeilen der Profile sind eine eigene Entscheidung.
- **Bots laufen ueber den lokalen Router, nicht ueber ein eigenes Portal-Login**
  (18.09.2026). Profile sind Inseln: sie lesen nur ihr eigenes `auth.json`/`.env`.
  24 Bots standen auf `provider: nous` ohne Portal-Anmeldung — jeder `/bot`-Aufruf
  endete mit „not logged into Nous Portal“, danach griff die geerbte
  `fallback_providers`-Kette auf ein lokales 8k-Modell, das Hermes ablehnt
  (gemessen an `projectatlas`). Kanalzugangsdaten braucht der `/bot`-Weg nicht,
  eine Modellanmeldung schon. Jetzt fahren die Bots
  `model.provider=omniroute`, `model.default=auto/best-coding`: der Router-
  Schluessel steht schon in jeder Profil-`.env`, der `providers.omniroute`-Block
  in jeder `config.yaml`, und die Unteragenten des Hauptprofils fahren denselben
  Weg. Werkzeug:
  `Agenten/Hermes/scripts/bot-modell-auf-router.py` (Trockenlauf ohne Argument,
  `--anwenden` mit `config.yaml.bak-JJJJMMTT`, `--zuruecknehmen`); es holt
  ausserdem den von `hermes config set` abgeschnittenen Kommentar-Schluss der
  `config.yaml` zurueck (in 6 Profilen fehlten 38 Zeilen Doku).
  Die geerbte `fallback_providers`-Kette hat
  `Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py` in 14 Profilen
  entfernt (sie zeigte zuletzt auf dasselbe Router-Ziel und dann auf
  `gemma-e4b-8k:latest`, 8.192 Token — Hermes verlangt 64.000; faellt der Router
  aus, kommt jetzt die ehrliche Router-Meldung statt eines Kontextfenster-
  Fehlers). Unberuehrt:
  `superpowers` und `awesome-systematic-trading` (eigene Portal-Anmeldung) sowie
  `openmontage` (`llamacpp`, lokales Modell). Nachweis: 25 Profile umgestellt,
  0 Fehler, je Profil 2 Einfuegungen/3 Loeschungen gegen HEAD; live geantwortet:
  `basic-memory`, `projectatlas`, `skills`, `caveman`, `tradingview-mcp`,
  `gbrain`, `agent-reach`, `santiment`.
- **Neuer Bot = drei Ankerpunkte.** Profil anlegen (`--clone`), `terminal.cwd`
  setzen, `profile.yaml`-Beschreibung pflegen (der Kanban-Orchestrator sortiert
  danach). `/bots` zeigt beides von selbst.

Verwandt: [[Agent-Reach]], [[Moon-Dev-Agenten]], [[Projektatlas]], [[Routinen]].