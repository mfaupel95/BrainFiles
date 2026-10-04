---
id: 20260916-repo-bots
title: 'Repo-Bots: Flottenstand und Telegram-Zugang'
tags: [ki-agenten, betrieb]
created: 2026-09-16
updated: 2026-09-21
related: [20260830-hermes, 20260830-routinen]
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

## Flottenstand (Stand 19.09.2026)

15 Repo-Bots + Profile ohne Repo: `hermes-wartung` (Arbeitsbereich
`Agenten/Hermes`, angelegt 21.09.2026), `lotse` (Verteil-Bot, 21.09.2026),
`markt-recherche` (Marktdaten, 23.09.2026, siehe unten) sowie
`awesome-systematic-trading` und `one-skill-to-rule-them-all` ohne gesetztes
`terminal.cwd`.
Stand am 23.09.2026 aus `profiles/*/config.yaml` gezaehlt (nicht aus dieser
Tabelle); die Platte bleibt die Wahrheit.

| Repo (Werkstatt/Repos) | Bot | Besonderheit |
|---|---|---|
| Agent-Reach | agent-reach | Internet lesen ohne API-Gebuehren |
| agent-trade-kit | agent-trade-kit | OKX Trading-MCP-Server, neu 19.09.2026 |
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

## Regeldatei und SOUL.md (18.09.2026)

- **Eine Regeldatei fuer alle 27:** `Agenten\Hermes\profiles\rule_repo-bots.md`, eine Ebene hoeher als die Profilordner (Budget 6000 Zeichen). Sie traegt Stil und gemeinsame Betriebsregeln EINMAL; jede Sitzung liest sie zuerst und traegt Gelerntes dort ein.
- **SOUL.md je Bot individuell:** Repo, Aufbau, Aufgaben und Grenzen des jeweiligen Fremd-Repos, dazu der Verweis auf die Regeldatei - statt 27 wortgleicher Stiltexte (3030 Zeichen, MD5 D5EC74ACD025B18710647B2651F4A085).
- Alte Fassung gesichert: `profiles\.sicherung\SOUL-generisch-20260918.md`; Historie in Git.
- Git-Freigabe der Regeldatei: `!Agenten/Hermes/profiles/*.md` - ohne diese Zeile greift die Sperre `Agenten/Hermes/**`. Pruefen: `git check-ignore -v`. 

## Profil ohne Repo: hermes-wartung (21.09.2026)

Kein Fremd-Repo, sondern der Hermes-Baum selbst: Arbeitsverzeichnis
`Agenten/Hermes` statt `Werkstatt/Repos/<name>`. Angelegt mit
`hermes profile create hermes-wartung` (frisches Profil, kein `--clone`),
dann `providers.omniroute` (aus einem Bot-Profil kopiert),
`model.provider=omniroute` / `model.default=auto/best-coding`,
`terminal.cwd = Agenten/Hermes`, die drei Router-Schluesselnamen in die
eigene `.env` (keine Kanalzugangsdaten), `profile.yaml`-Beschreibung per
`hermes profile describe --text`. Belegter Aufruf: `pwd` meldet
`Agenten/Hermes`, Modell `auto/best-coding`.

Verwandt: [[Agent-Reach]], [[Moon-Dev-Agenten]], [[Projektatlas]], [[Routinen]].

## Profil ohne Repo: markt-recherche (23.09.2026)

Ein Recherche-Bot fuer aktuelle Krypto- und Aktienfragen - kein Repo,
sondern ein Arbeitsbereich im Haus: `terminal.cwd = Agenten\Handel`,
dort liegen die Marktdaten- und Auswertungswerkzeuge.

- **Angelegt:** `hermes profile create markt-recherche --clone-from
  hermes-wartung --description "..."` (der Klon bringt `providers`,
  `terminal.backend: local`, das Flottenmodell und die getrimmte
  Skill-Bibliothek mit; die Rollenbeschreibung fuer `/bots` kommt aus
  `profile.yaml`).
- **Rolle statt Wartung:** `profiles/markt-recherche/SOUL.md` wurde auf
  `Markt-Recherche` umgeschrieben (der Klon trug die Wartungs-Rolle).
- **Skills dazu:** `markt-recherche` (Verfahren, Werkzeugaufrufe,
  Belegpflicht), `handel-spur-studie`, `scrapling-ernte`, `fundus-zugriff`,
  `marktbriefing`, `notiz`.
- **Anmeldung:** `auth.json` als Symlink auf den Root-Store (wie die 13
  verknuepften Profile), **keine** Kanalzugangsdaten - der Bot wird per
  `/bot markt-recherche ...` bedient.
- **Werkzeug:** `Agenten/Werkzeuge/marktdaten.py` (OKX fuer Krypto, Yahoo
  Chart fuer Aktien/Indizes/ETFs, RSS fuer Schlagzeilen; rein lesend, ohne
  Schluessel), Tests `Agenten/Handel/tests/test_marktdaten.py` (14).
- **Beleg:** `hermes -p markt-recherche chat -Q -q "..."` nannte am
  23.09.2026 BTC-USDT (OKX) und AAPL (Yahoo) je mit Quelle und Uhrzeit;
  `hermes profile list` ohne Warnzeile. Details:
  [[Marktdaten-und-Bot-markt-recherche]].

## Bots auf dem Nous-Portal (21.09.2026)

Ausloeser: Die Combo `auto/best-coding` des lokalen Routers zeigte auf einen toten
Zweig - `oc/big-pickle` antwortete mit 403 ("OpenCode's free tier can only be used
from within OpenCode") bzw. 500 server_error. Damit standen ALLE Bots still
(Stichprobe am Router: best-coding 403, best-fast 502, best-chat/pro-coding 503).

Umstellung (12 Profile + `hermes-wartung`): `model.provider=nous`,
`model.default=deepseek/deepseek-v4-flash-0731` - Werkzeug
`Agenten/Hermes/scripts/bot-modell-auf-nous.py` (Trockenlauf / `--anwenden` /
`--zuruecknehmen`, je Profil `config.yaml.bak-JJJJMMTT`).

Die Sitzung holt jedes Profil ueber einen SYMLINK auf den Root-Store, nicht ueber
eine Kopie: `Agenten/Hermes/scripts/auth-verknuepfen.ps1` (erhoehte Shell noetig,
ein UAC-Prompt) verweist `profiles/<bot>/auth.json` auf `Agenten/Hermes/auth.json`.
Grund: Ein Profil ohne eigene `auth.json` ist eine Insel und antwortet "Hermes is
not logged into Nous Portal"; die Sitzung zu KOPIEREN waere dieselbe Refresh-Kennung
in vielen Dateien, und eine Rotation entwertet die anderen. Der Symlink haelt EINEN
Store, fuer den Hermes Sperre und "Peer hat rotiert, uebernimm seinen Token"
mitbringt (`hermes_cli/auth.py::_nous_shared_store_lock`;
`auth_oauth_grants.py` behandelt einen Symlink auf den Root-Store ausdruecklich als
"kein Klon"). Profile mit eigener `auth.json` (basic-memory, caveman*, 
awesome-systematic-trading) und eigene Wege (openmontage/llamacpp,
awesome-systematic-trading/docker) blieben unberuehrt; *caveman hatte nur einen
Pool-Eintrag ohne Sitzung und wurde nach Sicherung ebenfalls verknuepft
(`profiles/.sicherung/caveman-auth.json.bak-20260921`).

Belege: `hermes -p <bot> chat -q "..."` antwortet je Bot (caveman, gbrain,
claudian, openterminal, moon-dev-agents), das Hauptprofil meldet weiter
`deepseek/deepseek-v4.1-flash auf nous` (keine entwertete Sitzung).

OFFEN: Dieselbe Umstellung gilt fuer die 17 Profile in `profiles/.deleted/`
(projectatlas, skills, superpowers, tradingview-mcp, agent-reach, nous, codex,
scrapling, ...; am 19.09.2026 weggelegt) - sie sind nicht erreichbar und wurden
nicht angefasst; ebenso bleibt der Router als Zweitweg unrepariert.


## clipproxy angelegt, alle Bots auf Nous (21.09.2026)

- **Neuer Bot `easycliproxyapi`** (Repo `Werkstatt\Repos\EasyCLIProxyAPI`,
  router-for-me: Tauri-Konsole fuer CLIProxyAPI). Angelegt mit
  `hermes profile create easycliproxyapi --clone-from openterminal --no-alias`,
  danach `terminal.cwd` auf sein Repo gezogen (3 Vorkommen: `cwd` plus die zwei
  projectatlas-Pfade), eigene `SOUL.md`, `profile.yaml`-Beschreibung und
  `auth.json` als Symlink auf den Root-Store. Beleg:
  `hermes -p easycliproxyapi chat -q "..." -Q -t terminal` antwortet
  `deepseek-v4-flash-0731 / nous / Werkstatt\Repos\EasyCLIProxyAPI`.
  `repos-zentrale.py --pruefen` fuehrt ihn (17 Bot-Profile, Gruppe EINRICHTEN -
  fuer das Repo ist noch kein Startbefehl belegt).
- **Alle Bots auf `nous / deepseek/deepseek-v4-flash-0731`:** 15 standen schon
  dort; `Agenten/Hermes/scripts/bot-modell-auf-nous.py --auch-lokale --anwenden`
  holte die zwei Ausnahmen herueber - `openmontage` (llamacpp, CLIP-mmproj als
  Hauptmodell ist gar nicht ladbar) und `awesome-systematic-trading` (docker).
  Der Schalter entfernt dabei ein lokales `model.base_url`, sonst zeigt der
  Aufruf weiter auf den lokalen Endpunkt. Ergebnis: 17 Profile umgestellt bzw.
  schon richtig, 0 Fehler, `hermes profile list` ohne Warnzeile. Live geprueft:
  `easycliproxyapi`, `openmontage`, `awesome-systematic-trading`.
- `awesome-systematic-trading` stand zusaetzlich auf `terminal.backend: docker`;
  die Docker-Probe lief in den 5-Sekunden-Timeout und der Lauf brach mit
  "Switch to a different model" ab - Ursache war der TERMINAL-Backend, nicht das
  Modell. Auf `local` gezogen (Hausstandard), danach antwortet er live.
- Zwei Fallen dabei: PowerShell 5.1 legt keinen Symlink an, auch mit
  eingeschaltetem Developer-Mode (`pwsh` 7 legt ihn ohne Erhoehung an); und
  `hermes config set` schreibt LF und schneidet den Kommentar-Schluss ab -
  5 Profil-Configs mussten zeilenweise auf ihr HEAD-Format geheilt werden.
- Von den 17 weggelegten Profilen in `profiles/.deleted/` ist damit
  `easycliproxyapi` wieder angelegt; die uebrigen 16 bleiben offen (siehe oben).

## Bot `nerd` fuer claude-red (22.09.2026)

- **Repo:** `Werkstatt\Repos\claude-red` = Fork `mfaupel95/claude-red` von
  `SnailSploit/Claude-Red` (MIT), vollstaendiger Klon, 7,3 MB, 44 Commits.
  Offensive-Security-Nachschlagewerk: **79 `SKILL.md` in 23 Kategorien**, kein
  startbares Programm. Als Faehigkeit im Fundus gefuehrt (Werkstatt-Index:
  24 Repos / 581 eindeutige Skills, davon claude-red 75) - **nicht** in die
  geladene Bibliothek importiert.
- **Bot:** `Agenten/Hermes/profiles/nerd`, `terminal.cwd` auf das Repo, Modell
  `nous / deepseek/deepseek-v4.1-flash`, `auth.json` als Symlink auf den
  Root-Store, eigene `SOUL.md` (Faehigkeitsliste, Grenzen: nur autorisierte
  Ziele, beratend statt ausfuehrend), Haus-Skills kopiert.
  Angelegt mit `hermes profile create nerd --no-alias`, danach
  `terminal.backend/cwd`, `providers.ollama-launch` + `fallback_providers`
  (lokales `qwen35-8k:cpu` zuerst) und `hermes profile describe`.
  Beleg: `hermes -p nerd chat -q "..." -Q -t terminal` nennt Arbeitsverzeichnis
  und Kategorien-/Dateizahl; `hermes profile list` ohne Warnzeile.
- **Falle (Defender):** Windows Defender hat beim Klonen vier `SKILL.md`
  eingeordnet (`Backdoor:PHP/Perhetshell.A!dha` fuer `offensive-sqli` und
  `offensive-rce`, `Trojan:Script/Wacatac.H!ml` fuer `offensive-file-upload`,
  dazu `offensive-shellcode`) und zweimal geloescht; nach `git checkout -- .`
  liegen sie wieder da, sind aber **nicht lesbar** („Datei enthaelt einen
  Virus"). Von 79 Dateien sind damit 75 nutzbar. `ls` beweist hier nichts -
  die Probe ist ein echter Lesevorgang, der Fundort `Get-MpThreatDetection`.
- **Offen (Entscheidung Max):** Defender-Ausnahme fuer den Ordner
  (`Add-MpPreference -ExclusionPath 'O:\Werkstatt\Repos\claude-red'`), danach
  sind die vier Dateien lesbar. Details: [[Claude-Red-und-nerd-Bot]].
