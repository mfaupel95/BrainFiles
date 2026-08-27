# Hermes Agent

Zweiter Agent neben Claude, von Nous Research. Eingebunden am **23.08.2026**,
Version **v0.20.5** (2026.8.19). Arbeitet auf demselben Vault, demselben Archiv
und denselben MCP-Servern wie Claude — siehe [[Verbindungen]].

## Wo was liegt

| | Pfad | warum dort |
|---|---|---|
| **Daten** | `MaxHirn/Hermes/` | `HERMES_HOME`, als Benutzervariable gesetzt. Konfiguration, Skills, Gedächtnis, Sitzungen, Protokolle. 500 Dateien, 55 MB. |
| **Code** | `C:\Hermes` | 111.754 Dateien, 1,6 GB. Bewusst **nicht** im Vault (Obsidian) und **nicht** unter `%LOCALAPPDATA%` — Begründung unten. |
| **Sicherungen** | `MaxHirn/Hermes/.sicherung/` | PATH vorher/nachher, Claude-Desktop-Konfiguration, `config.yaml`, `.env`, drei Installationsprotokolle |

Startbefehle: `hermes chat` (CLI), `hermes --tui`, `hermes desktop`,
`hermes dashboard`. Alle vier teilen Konfiguration, Sitzungen, Skills und
Gedächtnis. `hermes -z "…"` ist der Einmal-Modus für Skripte.

## `%LOCALAPPDATA%` bedeutet in einer Claude-Sitzung etwas anderes

**Das ist der wichtigste Merksatz dieser Notiz.** Claude Desktop läuft als
verpackte Windows-App (MSIX). Schreibzugriffe auf `AppData\Local` werden dabei
in den App-Container umgeleitet:

```
C:\Users\faupe\AppData\Local\hermes
  ist in Wirklichkeit
C:\Users\faupe\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Local\hermes
```

Der erste Installationsversuch landete genau dort — beide Pfade zeigten
**exakt dieselben 111.754 Dateien / 1.591 MB**, was die Umleitung bewies. Zwei
Folgen: ein Zurücksetzen von Claude Desktop hätte Hermes mitgelöscht, und aus
einem normalen PowerShell-Fenster wäre der Code vermutlich unsichtbar gewesen.
Das hätte den unangenehmsten Fehlertyp ergeben — läuft, wenn Claude es startet,
bricht, wenn Max es startet.

**Regel für die Zukunft:** Wird über eine Claude-Sitzung Software installiert,
niemals `%LOCALAPPDATA%`, `%APPDATA%` oder `$env:LOCALAPPDATA` als Ziel
verwenden. Immer einen ausgeschriebenen Pfad außerhalb von `AppData` angeben.
Auch `-ShowResolvedPaths` des Installers half nicht — es meldete denselben
umgeleiteten Pfad. Zuverlässig ist nur die Gegenprobe **nach** der
Installation: `hermes --version` nennt das echte Verzeichnis.

## Konfiguration

In `MaxHirn/Hermes/config.yaml`:

- `model.default: claude-opus-5`, `model.provider: anthropic`
- **`base_url` entfernt** — stand voreingestellt auf OpenRouter und hätte den
  Claude-Zugang umgangen
- `approvals.mode: manual`, `timeout: 300` (unbeantwortet = abgelehnt),
  dazu eine `deny`-Liste gegen Massenlöschung
- `checkpoints.enabled: true`
- `mcp_servers:` mit allen **11** Servern, aus `claude_desktop_config.json`
  übersetzt

In `MaxHirn/Hermes/.env`:

- `HERMES_WRITE_SAFE_ROOT=C:\Users\faupe\Documents\BrainFiles\MaxHirn`
  — **Schreib-Sandbox, geprüft und aktiv.** Hermes kann überall lesen, aber nur
  innerhalb des Vaults schreiben.

## Skills

- **83 mitgelieferte** Skills unter `Hermes/skills/` (94 `SKILL.md` insgesamt
  minus die 11 eigenen; die frühere Angabe 82 war um eins zu niedrig)
- **11 eigene** unter `Hermes/skills/claude-code-imports/`, importiert mit
  `hermes import-agent claude-code --source "…\MaxHirn\.claude"`

Der Import fand **keine** MCP-Server — die stehen in
`claude_desktop_config.json`, nicht in `~/.claude.json`, wo Hermes sucht.
Deshalb wurden sie von Hand übertragen.

**Nacharbeit:** In `archiv`, `dokument`, `posteingang` und `schaden` standen
acht Aufrufe von `.venv\Scripts\python.exe` relativ zum Arbeitsverzeichnis
`Claude/`. In den Hermes-Kopien sind sie auf absolute Pfade umgestellt. Die
Originale unter `MaxHirn/.claude/skills/` blieben unverändert — für Claude Code
stimmen sie so.

## Gedächtnis-Zuständigkeit

`Wissen/` ist die einzige Wahrheit. `Hermes/memories/` ist Arbeitsspeicher und
wird nie als Beleg zitiert. Festgehalten in [[../AGENTS.md|AGENTS.md]], die
Hermes anstelle der `CLAUDE.md` liest.

## Offene Punkte

1. ~~Anmeldung fehlt~~ — erledigt am 23.08.2026. Anthropic-Token per
   `hermes config set ANTHROPIC_TOKEN` in `MaxHirn/Hermes/.env` eingetragen,
   per `hermes status` gegengeprüft (Anthropic: erkannt, Provider Anthropic,
   Modell claude-opus-5). Ob das Abo die Nutzung durch einen fremden Agenten
   deckt, steht weiterhin in Anthropics Nutzungsbedingungen — technisch
   akzeptiert Hermes den Token (`hermes_cli/providers.py`,
   `agent/anthropic_adapter.py`).

2. ~~Computer-Use-Treiber nicht installiert~~ — erledigt am 23.08.2026, siehe unten.

3. **Messaging-Gateway bewusst aus.** Ohne Freigabeliste sperrt es alle Nutzer
   aus; es wurde nicht eingerichtet. Telegram, Discord, Slack und Signal sind
   damit offen für später.

4. **Zwei leere Ordnerhüllen** ohne Speicherbedarf:
   `C:\Hermes.broken-20260823-184612` und der geleerte Container-Pfad. Ihr
   Inhalt ist entfernt; das Löschen der Hüllen selbst wurde von der
   Sicherheitsprüfung blockiert (Pfade direkt unter `C:\`). Ohne Belang.

## Erledigt am 23.08.2026

- **`${env:…}` wird nicht aus der `.env` aufgelöst,** sondern nur aus der
  Prozessumgebung — die Konfiguration wird vorher gelesen. Betraf `mcp-memory`.
  Behoben: `MNEMOVERSE_API_KEY` steht jetzt als Benutzervariable in
  `HKCU\Environment`, so wie Kraken es macht (siehe [[Verbindungen]]). Die
  Warnung ist weg, geprüft über `hermes status`.
- **Verwaiste Erstinstallation entfernt** (1,6 GB im Claude-Container, per
  `robocopy /MIR` geleert; Rückgabecode 2 heißt bei `/MIR` „Extras entfernt",
  also Erfolg).
- **Benutzer-PATH gegengeprüft:** vorher 3, jetzt 6 Einträge, **kein einziger
  verloren**, `WindowsApps` unversehrt. Neu sind `Hermes\bin`, ripgrep und
  ffmpeg. Der fehlende ffmpeg-Eintrag war die Ursache des ersten
  Installationsabbruchs — ffmpeg 9.0 war längst installiert, nur unauffindbar.

## Computer-Use-Treiber (cua-driver), installiert 23.08.2026

`hermes computer-use install` genutzt der Standardpfad des Upstream-Installers
ist `%LOCALAPPDATA%\Programs\Cua\cua-driver\bin` — derselbe Container-Fehler
wie beim Hermes-Hauptinstall. Deshalb per `CUA_DRIVER_RS_INSTALL_DIR` und
`CUA_DRIVER_RS_HOME` umgeleitet:

- **Binaries/PATH-Eintrag:** `C:\Hermes\cua-driver\bin` (Junction auf die
  versionierte Release unter `C:\Hermes\cua-driver\home\packages\releases\`)
- Version **0.21.0**, im Benutzer-PATH ergänzt und über Registry-Abfrage
  gegengeprüft (nicht nur die Installer-Meldung geglaubt)
- **Stolperstein während der Installation:** `$env:TEMP`/`$env:TMP` zeigen auf
  `C:\WINDOWS\TEMP` — das ließ den `Add-Type`-C#-Compiler des Installers
  scheitern (Junction-Erstellung nutzt ein P/Invoke-Hilfsmodul). Für den
  Install-Lauf `TEMP`/`TMP` einmalig auf `C:\Hermes\cua-driver\tmp`
  umgebogen, kein Eingriff an der dauerhaften Benutzerkonfiguration.
  **Korrektur vom 24.08.2026:** Das ist *keine* Eigenheit der Claude-Sitzung,
  wie hier ursprünglich stand. `TEMP` und `TMP` sind als **Benutzervariablen**
  in `HKCU\Environment` auf `C:\WINDOWS\TEMP` gesetzt und gelten damit für
  jeden Prozess des Kontos. Ursache und Behebung: siehe unten.
- **Autostart-Task `\cua-driver-serve` wurde vom Installer automatisch
  angelegt** (RunLevel=Highest, „Bei der Anmeldung", startet
  `cua-driver.exe serve`). Von Max bestätigt, bleibt aktiv. Abschalten:
  `cua-driver.exe autostart disable`.
- **Telemetrie war standardmäßig aktiv, auf Wunsch abgeschaltet**
  (`cua-driver telemetry disable`, `source: persisted`, überlebt Updates).
  Installations-ID bleibt lokal liegen, wird aber nicht mehr gesendet;
  `telemetry reset-id` löscht sie ganz.

## Einstellungen nachgeschärft, 24.08.2026

Sicherung vorher: `Hermes/.sicherung/config.yaml.bak-20260824`.

| Einstellung | vorher | jetzt | warum |
|---|---|---|---|
| `stt.language` | `en` | `de` | Spracherkennung war auf Englisch — bei deutschem Diktat schlicht falsch |
| `stt.local.model` | `base` | `small` | `base` erkennt Deutsch merklich schlechter als Englisch |
| `prompt_caching.cache_ttl` | `5m` | `1h` | Max arbeitet in Schüben mit Pausen; nach >5 min war der Cache sonst kalt |
| `tool_loop_guardrails.hard_stop_enabled` | `false` | `true` | Notbremse gegen Endlosschleifen — `agent.max_turns` steht auf 500 |
| `mcp_servers.windows-mcp.env.ANONYMIZED_TELEMETRY` | `true` | `false` | Konsistenz zur abgeschalteten cua-driver-Telemetrie |

**Haken bei `cache_ttl: 1h`:** Anthropic berechnet das Schreiben eines
1h-Caches teurer als das eines 5m-Caches (Lesen kostet gleich wenig). Rechnet
sich, wenn Max tatsächlich nach Pausen an dieselbe Sitzung zurückkehrt —
bei vielen kurzen Einzelfragen mit je neuer Sitzung wäre `5m` günstiger.

**Nicht geändert, aber wissenswert:** `compression.threshold: 0.50` ist bei
Opus 5 wirkungslos — Hermes hebt den Wert für Modelle unter 512K Kontext
automatisch auf 0.75 an. Es wird also bei 75 % komprimiert, nicht bei 50 %.

## Erstes Update, 24.08.2026

Von `f293e72` (23.08.) auf **`057dcdf`** (24.08.2026, 17:19). `hermes --version`
meldet seither **„Up to date"** statt 386 Commits Rückstand. Python im
Arbeitsumfeld dabei von 3.11.9 auf 3.11.16 gehoben, Web-Oberfläche neu gebaut,
548 npm-Pakete installiert. Die Versionsnummer blieb bei v0.20.5 — sie ist an
den Release-Stand gebunden, nicht an den Commit.

Befehl: `hermes update --backup --yes`. Sicherungen liegen in
`Hermes/.sicherung/` (config.yaml, .env, auth.json, package-lock.json,
Registry-Export) und in `Hermes/backups/pre-update-2026-08-24-183036.zip`
(26 MB, ganzes `HERMES_HOME`, vom Updater selbst angelegt). Gegengeprüft:
`config.yaml` unverändert, `.env` per SHA1 unverändert, Modell und
Anthropic-Token weiterhin erkannt, 94 Skills mit den 11 eigenen Importen samt
ihrer absoluten Pfade unangetastet.

### Drei Blocker, die vorher weg mussten

1. **Der Klon ist flach** (`git clone --depth 1`, `.git/shallow` vorhanden,
   ein einziger Commit Historie). Deshalb sind lokale Vergleiche wertlos:
   `git rev-list --count main...origin/main` meldete „1 voraus, 1 zurück",
   obwohl 386 Commits fehlten. Der echte Rückstand kommt von Hermes über die
   GitHub-API. **Nicht auf `git`-Zählungen in diesem Repo verlassen.**
2. **Geparkt auf `feat/de-locale`** — einem rein lokalen Branch **ohne einen
   einzigen eigenen Commit**, am 24.08. von `main` abgezweigt und nie benutzt.
   `hermes update` erkennt so etwas und **überspringt dann das Code-Update**
   mit der Meldung „CODE UPDATE SKIPPED — checkout is parked on …", sobald
   der Arbeitsbaum außerdem unsauber ist. Zurück auf `main` gewechselt, es
   ging nichts verloren.
3. **`cua-driver/` liegt untracked im Git-Ordner** `C:\Hermes`. Der Updater
   räumt mit `git stash push --include-untracked` auf — der Treiber wäre
   mitgestasht worden. Eingetragen in `C:\Hermes\.git\info\exclude`, damit er
   für Git unsichtbar bleibt. Der Updater hat ihn danach korrekt als
   „already on the latest release (0.21.0)" erkannt.

### Neu und meldepflichtig: Skill-Curator

Das Update bringt eine **Hintergrundpflege für Skills** mit, standardmäßig an.
Erster Lauf ~7 Tage nach Installation, nur selbst erzeugte Skills im Zugriff,
nichts wird endgültig gelöscht (Archiv ist rückholbar). Vorschau ohne Eingriff:
`hermes curator run --dry-run`, abschalten mit `hermes curator pause`.

## Benutzer-Umgebungsvariablen: PowerToys-Schaden, 24.08.2026

Das PowerToys-Modul „Environment Variables" hat beim Speichern Sicherungskopien
mit dem Suffix `_PowerToys_Max 2026` angelegt — teils doppelt geschachtelt
(`ChocolateyInstall_PowerToys_Max 2026_PowerToys_Max 2026`) — und dabei
System-Variablen in die Benutzerebene kopiert. Gemessen: **59 Benutzervariablen,
davon 33 Duplikate**, darunter Kopien von `KRAKEN_API_SECRET` und `OKX_API_KEY`.

Zwei Einträge wirken sich aus:

- **`TEMP`/`TMP` → `C:\WINDOWS\TEMP`** statt `%USERPROFILE%\AppData\Local\Temp`.
  Das ist die wahre Ursache des cua-driver-Stolpersteins oben.
- **`PATHEXT`** überschreibt die System-Fassung und verliert dabei `.PY;.PYW`
  — anders als `Path` wird `PATHEXT` nicht zusammengesetzt, sondern ersetzt.
  Folge: `skript.py` lässt sich nicht mehr direkt aufrufen.

Behebung liegt als Skript bereit:
`Routinen/umgebungsvariablen-aufraeumen.ps1` (Testlauf ohne Schalter, echter
Lauf mit `-Ausfuehren`). Es löscht 33 Duplikate und 13 wirkungslose
System-Kopien, korrigiert `TEMP`/`TMP`, stellt `OneDriveConsumer` wieder her —
das existierte nur noch als Duplikat — und lässt die 11 echten Variablen in
Ruhe. Endstand 59 → 14. Sicherung vorher:
`Hermes/.sicherung/HKCU-Environment.bak-20260824.reg`.

**Aus einer Claude-Sitzung heraus nicht ausführbar:** Der Sicherheitsfilter
blockiert Registry-Schreibzugriffe (`Remove-ItemProperty` wie `reg delete`).
Max startet das Skript selbst; danach ist eine Neuanmeldung nötig.

## Verwandt

[[Verbindungen]] · [[Projekte]] · [[Portabilitaet]] · [[Hardware]] · [[../AGENTS.md|AGENTS.md]]

## Störung 26.08.2026 — „Problem mit den API-Keys"

**Zwei getrennte Ursachen. Keine davon war ein falscher Schlüssel.**

### 1. Abgelaufene OAuth-Tokens (die eigentliche Ursache)

```
hermes auth status anthropic   ->  anthropic: logged out
hermes auth list               ->  nur copilot
hermes auth reset anthropic    ->  Reset status on 0 anthropic credentials
```

„0 credentials" heißt: Hermes zählt die zwei Anthropic-Einträge aus `auth.json`
nicht mehr als Zugangsdaten — sie sind für ihn nicht erschöpft, sondern nicht
vorhanden.

| Eintrag in `auth.json` | Typ | Zustand |
|---|---|---|
| `env:ANTHROPIC_TOKEN`, Priorität 0 | oauth | `failure_reason: rate_limit` — stand schon in der Sicherung vom 24.08. |
| `claude_code`, Priorität 1 | oauth | `last_status: exhausted`, **abgelaufen 26.08.2026 00:47:45** |

**Der Kernfehler:** `ANTHROPIC_TOKEN` in der `.env` hat das Präfix
**`sk-ant-oat01-`** (108 Zeichen). Das ist ein **OAuth-Access-Token aus dem
Claude-Abo**, kein API-Key — ein Console-Key beginnt mit `sk-ant-api03-`.

Einen OAuth-Access-Token statisch in eine `.env` zu kopieren kann nicht dauerhaft
funktionieren: Er läuft ab, und das zugehörige Refresh-Token liegt dort nicht.
Der Eintrag war damit von Anfang an ein Verfallsdatum, kein Zugang.

**Behebung:**

| Weg | Befehl | Bewertung |
|---|---|---|
| **Abo weiternutzen** (empfohlen) | `hermes auth add anthropic --type oauth` | Browser-Login; Hermes verwaltet Token und Erneuerung danach selbst. Keine Zusatzkosten. |
| Console-API-Key | `hermes auth add anthropic --type api-key` | `sk-ant-api03-…` von console.anthropic.com. Läuft nicht ab, wird aber nach Verbrauch abgerechnet — zusätzlich zum Abo. |

**Danach `ANTHROPIC_TOKEN` aus der `.env` entfernen.** Er hat Priorität 0 und
steht damit vor dem frischen Login. *Nicht verifiziert*, ob Hermes bei einem
toten Eintrag sauber auf den nächsten durchfällt — dafür ist der Pool zwar
gebaut, aber ein abgelaufener Token an erster Stelle ist in jedem Fall Ballast.

Sicherung vor dem Eingriff: `.sicherung/auth.json.bak-20260826-1805`.

### 2. TLS-Handshake-Timeouts (der sichtbare Fehler)

`errors.log`, 17:42:51 und 17:46:52:

```
httpcore.ConnectTimeout: _ssl.c:989: The handshake operation timed out
anthropic.APITimeoutError: Request timed out or interrupted
```

**Das ist kein Schlüsselproblem.** Ein falscher oder abgelaufener Schlüssel
liefert HTTP 401 oder 429; hier kam gar keine TLS-Verbindung zustande.

Gegenprobe um 18:00 aus **Hermes' eigenem venv mit demselben `httpx`**: 5 von 5
Verbindungen zu `api.anthropic.com`, HTTP 401 (erwartet mit Dummy-Key), unter
1,3 s. Direkter TLS-Test 71 ms, TLS 1.3. Das Netz ist in Ordnung.

**Wahrscheinliche Ursache: NordVPN.** Der Prozess startete um **17:53:53**, also
nach den Fehlern; `NordLynx` ist Standardroute (`0.0.0.0/0 → 100.64.0.1`).
Ein Reconnect oder Kill-Switch erklärt genau dieses Muster. **Nicht bewiesen** —
aber wenn Hermes wieder ohne 401/429 hängenbleibt, zuerst hier nachsehen.

Passend dazu: `Copilot token exchange degraded to RAW token (exchange
unavailable)` und `Auxiliary title_generation: connection error on auto`. Auch
das sind Verbindungs-, keine Schlüsselfehler.

### 3. Was im Log wie ein Key-Problem aussieht, aber keins ist

`mcp-stderr.log`:

```
Some tools will not be loaded due to missing API keys: USPTO_API_KEY,
OPENAI_API_KEY, HF_TOKEN, BOLTZ_MCP_SERVER_HOST …
```

Stammt von **ToolUniverse**, nicht von Hermes, und betrifft optionale Werkzeuge
für Patent- und Biomedizin-Datenbanken. Ohne diese Schlüssel fehlen nur die
betreffenden Werkzeuge. Keine Handlung nötig.

### Merksatz für die Zukunft

**Erst den Fehlertyp lesen, dann die Ursache suchen.** Timeout ≠ 401 ≠ 429.
Das Wort „API key" im Log stand hier dreimal — und zeigte dreimal auf etwas
anderes: einmal auf ein Netzproblem, einmal auf einen abgelaufenen OAuth-Token,
einmal auf einen fremden MCP-Server, dem optionale Schlüssel fehlen.

### Nebenbefunde, noch offen

- `Auxiliary Nous client unavailable: no Nous authentication found (run: hermes auth)`
  — eigenes Nous-Login fehlt, betrifft nur Hilfsfunktionen.
- Copilot-Token-Exchange „degraded to RAW token": Enterprise-Modelle können mit
  `model_not_available_for_integrator` scheitern. Ohne Copilot-Nutzung folgenlos.
