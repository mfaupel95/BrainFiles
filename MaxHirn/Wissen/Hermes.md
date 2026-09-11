---
id: 20260830-hermes
title: 'Hermes Agent'
tags: [ki-agenten, betrieb]
created: 2026-08-24
updated: 2026-09-07
related: [20260830-verbindungen, 20260831-python-versionen]
summary: 'Einrichtung, Ablageorte und Fallstricke des Hermes-Agenten neben Claude.'
---

# Hermes Agent

Zweiter Agent neben Claude, von Nous Research. Eingebunden am **23.08.2026**,
Version **v0.21.0** (2026.8.31, Stand 31.08.2026). Arbeitet auf demselben Vault, demselben Archiv
und denselben MCP-Servern wie Claude — siehe [[Verbindungen]].

## Wo was liegt

| | Pfad | warum dort |
|---|---|---|
| **Daten** | `../Agenten/Hermes/` | `HERMES_HOME`, als Benutzervariable gesetzt. Konfiguration, Skills, Gedächtnis, Sitzungen, Protokolle. 500 Dateien, 55 MB. |
| **Code** | `C:\Hermes` | 111.754 Dateien, 1,6 GB. Bewusst **nicht** im Vault (Obsidian) und **nicht** unter `%LOCALAPPDATA%` — Begründung unten. |
| **Sicherungen** | `../Agenten/Hermes/.sicherung/` | PATH vorher/nachher, Claude-Desktop-Konfiguration, `config.yaml`, `.env`, drei Installationsprotokolle |

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

In `../Agenten/Hermes/config.yaml`:

- **Modell seit 26.08.2026 nicht mehr Anthropic** (geprüft 27.08.2026 in
  `config.yaml`, Datei zuletzt geändert 26.08. 19:41 — also nach der Störung):

  ```yaml
  model:
    default: upstage/solar-pro4:free
    provider: nous
    base_url: https://inference-api.nousresearch.com/v1
  ```

  **Überholt seit 31.08.2026.** Dieser Nous-Stand galt nur zwischen dem 26. und
  dem 31.08. Aktuell steht dort wieder (gemessen 31.08., 23:20 über
  `hermes status`):

  ```yaml
  model:
    default: claude-opus-5
    provider: anthropic
  ```

  Damit läuft Hermes wieder über Anthropic, nicht über die Nous-Cloud-API. Der
  Hergang steht unten unter „Modell-Eintrag wiederhergestellt".
- `approvals.mode: manual`, `timeout: 300` (unbeantwortet = abgelehnt),
  dazu eine `deny`-Liste gegen Massenlöschung
- `checkpoints.enabled: true`
- `mcp_servers:` mit allen **11** Servern, aus `claude_desktop_config.json`
  übersetzt

In `../Agenten/Hermes/.env`:

- `HERMES_WRITE_SAFE_ROOT=C:\Users\faupe\Documents\BrainFiles\MaxHirn`
  — **Schreib-Sandbox, geprüft und aktiv.** Hermes kann überall lesen, aber nur
  innerhalb des Vaults schreiben.

## Skills

- **23 eigene** unter `Hermes/skills/claude-code-imports/` — Abgleich mit dem Vault
  vom 10.09.2026. Dazu `data-guard-audit` unter `skills/productivity/`.
  Gegengeprüft mit `hermes skills list` (HERMES_HOME gesetzt): 113 Skills geladen,
  alle neuen `local` und `enabled`.
- **Der erste Import** lief am 23.08.2026 mit
  `hermes import-agent claude-code --source "…\MaxHirn\.claude"` und holte 11 Skills.
  Am 10.09.2026 fehlten 11 weitere, die inzwischen im Vault entstanden waren
  (`absturz-recovery`, `local-ai-config-doctor`, `marktbriefing`, `rueckschau`,
  `sichern`, `skill`, `system`, `umzug`, `verbindungen`, `vergleich`,
  `videoanalyse`), dazu `sprache` aus `.claude/skills-sicherung/`. Nachgezogen als
  Kopie der Skill-Ordner — nicht über den Importer, damit nichts anderes angefasst wird.
- **Sechs Bestandsskills waren älter als der Vault** (`archiv`, `dokument`, `geld`,
  `posteingang`, `schaden`, `tagesbriefing`): sie zeigten auf
  `MaxHirn\Claude\ArchivSuche` — den Ordnernamen von vor dem 30.08.2026, den es nicht
  mehr gibt. Auf Vault-Stand gezogen; die ersetzten Fassungen liegen in
  `Hermes/.sicherung/skills-import-20260910/`. Alle 11 Bestandsskills sind damit
  zeichengleich mit `MaxHirn/.claude/skills/`. Die frühere Nacharbeit (absolute Pfade
  in vier Skills) ist damit überholt.
- **Nacharbeit in den Hermes-Kopien** (Originale unverändert — für Claude stimmen sie so):
  `AskUserQuestion` → `clarify` (`sprache`), `WebFetch` → `web_extract` (`videoanalyse`).

Der Import fand **keine** MCP-Server — die stehen in
`claude_desktop_config.json`, nicht in `~/.claude.json`, wo Hermes sucht.
Deshalb wurden sie von Hand übertragen.

**Offen: die Kommandozeilenwege der Skills passen nicht zur Terminal-Konfiguration.**
12 der 23 Skills rufen Vault-Pfade auf, und zwar vault-relativ
(`Archiv\ArchivSuche\.venv\Scripts\python.exe`, `..\Agenten\Routinen\…`) — so, wie
Claude Code sie mit dem Vault als Arbeitsverzeichnis benutzt. Hermes hat aber
`terminal.backend: docker`, `cwd: Agenten\Hermes` und
`docker_mount_cwd_to_workspace: false`; der Container sieht außer dem Skill-Ordner
nichts vom Vault (nur `tools/environments/docker.py` mountet Skills read-only).
Am 10.09.2026 startete zusätzlich überhaupt kein Terminal mehr: `proxy.enabled: true`,
aber `iron-proxy` nicht eingerichtet — Abhilfe laut Fehlermeldung `hermes egress setup`.
Bis das Terminal läuft und im Vault steht, sind diese Skills in Hermes nur Text.
## Gedächtnis-Zuständigkeit

`Wissen/` ist die einzige Wahrheit. `Hermes/memories/` ist Arbeitsspeicher und
wird nie als Beleg zitiert. Festgehalten in [[AGENTS.md]], die
Hermes anstelle der `CLAUDE.md` liest.

## Offene Punkte

1. ~~Anmeldung fehlt~~ — erledigt am 23.08.2026. Anthropic-Token per
   `hermes config set ANTHROPIC_TOKEN` in `../Agenten/Hermes/.env` eingetragen,
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

[[Verbindungen]] · [[Projekte]] · [[Portabilitaet]] · [[Hardware]] · [[Python-Versionen]] · [[AGENTS.md]]

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

## Umzugsschaden und Reparatur, 31.08.2026

Nach der Ordnerteilung vom 30.08. (`MaxHirn/Hermes/` → `../Agenten/Hermes/`)
**startete Hermes überhaupt nicht mehr.** `HERMES_HOME` war korrekt nachgezogen,
die Daten waren vollständig — aber drei absolute Pfade zeigten weiter auf den
alten Ort. Genau die Falle aus [[Portabilitaet]], hier in voller Länge:

| Was | zeigte auf | Symptom |
|---|---|---|
| `bin/hermes.cmd`, `bin/hermes-acp.cmd` | `…\MaxHirn\Hermes\hermes-agent\venv\Scripts\hermes.exe` | „Das System kann den angegebenen Pfad nicht finden" |
| `hermes-agent/venv/pyvenv.cfg`, Zeile `home =` | alter Pfad **und** ein Python-Ordner, den es nicht mehr gab (`cpython-3.11-…` statt `cpython-3.11.15-…`) | — |
| `venv/Scripts/*.exe` (uv-Trampoline) | alten venv-Pfad, **einkompiliert in der Binärdatei** | `uv trampoline failed to spawn Python child process` |

**Die dritte Zeile ist der Merksatz:** `pyvenv.cfg` zu korrigieren reicht nicht.
Ein uv-Trampolin trägt den Zielpfad im Programm selbst; auch mit
`relocatable = true` überlebt es den Umzug nicht. Der Fehlertext wechselte nach
der Korrektur nur von „uncategorized error (os error 4551)" zu „entity not
found (os error 2)" — **ein anderer Fehler ist kein Fortschritt.**

### Was wirklich hilft: venv neu bauen

Die Python-Laufzeit unter `.hermes-runtime/python/generation-…` bleibt heil und
ist weiterverwendbar; nur das venv muss neu. Gegenprobe vorweg, ob die Laufzeit
läuft — `python.exe --version` gab hier *keine* Ausgabe, obwohl alles in Ordnung
war; erst `python.exe -c "print(123)"` bewies es.

```
uv venv <ziel> --python <runtime-python.exe> --relocatable
uv pip install --python <ziel>\Scripts\python.exe -e C:\Hermes -r pakete.txt
```

`pakete.txt` entsteht aus den `*.dist-info`-Ordnern des alten venv — das geht
**ohne** lauffähiges Python und reproduziert den Stand exakt (145 Pakete plus
den editable install von `C:\Hermes`):

```
ls -d *.dist-info | sed 's/\.dist-info$//' | sed 's/-\([0-9][^-]*\)$/==\1/'
```

Das alte venv wurde nur umbenannt (`venv.alt-20260831`), nicht gelöscht.

### Wrapper jetzt relativ

`bin/hermes.cmd` und `bin/hermes-acp.cmd` zeigen nicht mehr absolut, sondern
über `%~dp0` relativ zu ihrem eigenen Ort:

```
@echo off
"%~dp0..\hermes-agent\venv\Scripts\hermes.exe" %*
```

Damit überstehen sie den nächsten Umzug. Die `browser*`-Wrapper waren nie
betroffen.

**Falle beim Schreiben solcher Dateien:** `printf '…\venv\…'` frisst das `\v`
als Vertikaltabulator — aus `\venv` wird `env`. Heredoc benutzen, nicht
`printf`.

## Update auf v0.21.0, 31.08.2026

Nach der Reparatur `hermes update --backup --yes`: **v0.20.5 → v0.21.0**
(2026.8.31), `main @ 7beb0de6`. Gegengeprüft: `config.yaml` und `.env` per SHA1
unverändert, 96 Skills mit den 11 eigenen Importen unangetastet, cua-driver
weiter auf 0.21.0. Sicherungen in `.sicherung/*.bak-20260831-2130`.

**Der Rückstandszähler ist mit Vorsicht zu lesen.** Direkt nach dem Update
meldete `hermes --version` bereits wieder „8 commits behind" — das Repository
bekommt täglich Dutzende Commits. Maßgeblich ist die Release-Version, nicht der
Commit-Abstand. Zwischenzeitlich meldete es sogar „1598 commits behind", während
der Release aktuell war; der flache Klon (`--depth 1`) macht jede lokale
`git`-Zählung wertlos.

### Modell-Eintrag wiederhergestellt, 31.08.2026

`hermes status` meldete seit dem 31.08. **`Model: (not set)`** — der `model:`-Block
fehlte in `config.yaml`. Am 31.08. um 00:06 wurde die Datei von anderer Seite
umgebaut (6.891 → 8.945 Bytes). Der Block `default: claude-opus-5 / provider: anthropic`
wurde aus der Sicherung `.sicherung/config.yaml.bak-20260824-1805` wiederhergestellt.

## Python-Upgrade auf 3.13.15, 31.08.2026

**Durchgeführt auf Anforderung des Betreibers.** Siehe [[Python-Versionen]] für Details.

venv unter `../Agenten/Hermes/hermes-agent/venv/` komplett neu mit Python 3.13.15 gebaut:
- Alte venvs gesichert (Backups mit Timestamp)
- 60+ Dependencies neu installiert
- Alle CLI-Entry-Points funktionieren: `hermes --version`, `hermes.cmd`, `python -m hermes_cli.main`
- Verifiziert: `hermes --version` meldet **Python: 3.13.15** ✓

**Bekannte Eigenheit:** Der editable install `hermes_agent` ist nicht per direktem Python-Import verfügbar (`import hermes_agent` schlägt fehl). Das ist nicht kritisch — Hermes funktioniert über CLI und wird über Entry-Points (`.exe`/`.cmd`) aufgerufen. Siehe [[Python-Versionen#Bekannte Eigenheit]].

**Nachtrag 31.08.2026, 23:30:** Dieser Neubau blieb unvollständig — ein
Stromausfall um 22:56 (`Kernel-Power 41`, siehe [[Hardware]]) durchtrennte den
Installationslauf. Es fehlten **77 Pakete**, darunter `anthropic` und `mcp`;
Hermes hätte weder mit dem Modell noch mit einem MCP-Server sprechen können,
meldete sich in `hermes status` aber als gesund. Nachinstalliert, jetzt
150 Pakete, alles gegengeprüft. **Nach einem venv-Neubau reicht
`hermes --version` als Prüfung nicht** — Importtest und Paketzahl gehören
dazu.

## Telegram-Gateway aktiviert und Auxiliary auf omniroute, 07.09.2026

### Messaging-Gateway (Telegram) eingerichtet

Der frühere Punkt „Messaging-Gateway bewusst aus" ist damit erledigt. Bot
**@HermesAgentMaksPCbot** (Anzeigename „HermesPCMax"), Token und erlaubte
User-ID in `%LOCALAPPDATA%\hermes\.env`:

- `TELEGRAM_BOT_TOKEN=…`
- `TELEGRAM_ALLOWED_USERS=7648512088` (nur diese ID darf den Bot nutzen)

Gateway läuft als geplanter Windows-Task `Hermes_Gateway` (Autostart) und im
Hintergrundprozess; Start/Stopp mit `hermes gateway start|stop`, Status mit
`hermes gateway status`. Verbindung geprüft: „Connected to Telegram (polling
mode)".

### Auxiliary-Modelle (Side-Tasks) auf omniroute umgestellt

**Auslöser:** `agent.auxiliary_client` meldete wiederholt „nous unhealthy
(payment / credit error)" — das Auxiliary-Modell lief über den Nous-Provider,
dessen Guthaben fehlt. Betroffen waren nur Side-Tasks (Compression, Vision,
Session-Search), nicht das Hauptgespräch.

**Lösung:** Side-Tasks auf den lokalen omniroute-Endpunkt gelegt. omniroute
ist ein lokaler Model-Router (Dashboard auf `http://127.0.0.1:20128`, siehe
[[Globale-npm-Tools-PATH]]), der per `auto/best-*`-Alias auf passende Modelle
routet. In `config.yaml` unter `auxiliary:`:

```yaml
auxiliary:
  vision:
    model: auto/best-vision
    base_url: http://127.0.0.1:20128/v1
    api_key: ${OMNIROUTE_API_KEY}
  compression:
    model: auto/best-fast
    base_url: http://127.0.0.1:20128/v1
    api_key: ${OMNIROUTE_API_KEY}
  session_search:
    model: auto/best-fast
    base_url: http://127.0.0.1:20128/v1
    api_key: ${OMNIROUTE_API_KEY}
```

Der Key steht in `%LOCALAPPDATA%\hermes\.env` als `OMNIROUTE_API_KEY` — in
`config.yaml` nur die `${…}`-Referenz, kein Klartext. Der Key ist ein
omniroute-Client-Key (nicht der Anthropic-Workspace-Key aus [[Zugaenge]]).

**Wichtig:** Die drei Task-Namen sind `vision`, `compression`,
`session_search`. Beim Setzen von `session_search` warnt das CLI „not a
recognized config key" — das ist kosmetisch, `_get_auxiliary_task_config`
liest das dict trotzdem (siehe `agent/auxiliary_client.py`). `base_url` +
`api_key` pro Task wird als `custom`-Endpoint aufgelöst.

**Nach api_key-Änderung ist ein Gateway-Neustart nötig** (`hermes gateway
restart`) — nur `compression.*`- und Kontext-Keys hot-reloaden. Nach dem
Reload: keine „nous unhealthy"-Warnung mehr in den Logs.

**Hinweis:** Das Hauptmodell in `config.yaml` stand zum Zeitpunkt der
Umstellung auf `claude-sonnet-5` / `anthropic` (nicht mehr
`deepseek-v4-flash` / `openrouter`) — von anderer Seite gesetzt, hier nicht
angefasst. Bei Bedarf gegenprüfen.

### Hauptmodell ebenfalls auf omniroute umgestellt, 07.09.2026

Das Hauptgespräch (Telegram + CLI) läuft jetzt ebenfalls über omniroute, nicht
mehr über einen externen Provider. `model:`-Block in `config.yaml`:

```yaml
model:
  default: auto/best-chat
  provider: custom
  base_url: http://127.0.0.1:20128/v1
  api_key: ${OMNIROUTE_API_KEY}
```

Das Hauptmodell nutzt für einen custom-Endpunkt inline `model.api_key`
(`hermes_cli/auth.py`); Built-in-Provider lesen den Key dagegen aus
env/auth. Verifiziert: `hermes status` meldet `Model: auto/best-chat /
Provider: Custom endpoint`, und ein Test-Turn (`hermes chat -q`) antwortete
sauber. omniroute routet `auto/best-chat` real (z. B. auf `big-pickle`).

**Merksatz:** Wird das Hauptmodell auf einen custom-Endpunkt umgestellt,
gehört der Key ebenfalls als `${…}`-Referenz in `config.yaml` und die `.env`-Variable ist vorher zu setzen — sonst löst der Endpunkt mit AUTH-Fehler ab.

### OmnIRoute als verwalteter Daemon, opencode-Provider, Autostart, 07.09.2026

**Problem:** omniroute lief als verwaister Kindprozess der Sitzung, der den Port
20128 hielt (`omniroute serve` ausbash-Background). Ein loses `node`-Prozess
(PID-Wechsel je Lauf) bediente den Endpunkt; `supervisor/.pid` zeigte einen
veralteten, toten PID. Der Server war so an keinen Prozess gebunden und
überlebte zwar das Terminal, aber unverwaltet.

**Lösung — als Daemon überführen:**
1. Loses Kind beenden, Port freigeben:
   `powershell Stop-Process -Id <PID> -Force`
2. Sauber starten:
   `omniroute serve --daemon`
   → startet detached, überlebt das Terminal, mit Auto-Restart über den
   `--daemon`-Supervisor. Verifiziert: `omniroute health` → **Status:
   healthy**, API HTTP 200.
3. **Beachte:** Ein zweiter `omniroute serve`-Versuch, während der Port schon
   von einem anderen omniroute-Prozess gehalten wird, crasht mit
   `EADDRINUSE … address already in use 127.0.0.1:20128` und gibt nach 2
   Restarts auf. Das ist normal (Port zu), kein Server-Fehler. Erst den
   Fremden beenden, dann neu starten.
4. `taskkill //PID … //F` funktioniert in der MSYS/git-bash-Shell NICHT
   (MSYS schluckt die `//`-Slashs) — stattdessen
   `powershell Stop-Process -Id <PID> -Force`.

**Autostart:** ist aktiv (geprüft 07.09.):
`omniroute autostart status` → `enabled: true / vbs-startup`. Belegt durch
`OmniRoute.vbs` und `OmniRoute Server.lnk` im Startup-Ordner
(`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`). omniroute
startet damit beim Windows-Login automatisch; der Hermes-Gateway-Task
`Hermes_Gateway` holt den Endpunkt bei Bedarf nach.

**opencode-Provider in omniroute angelegt** (Schema aus OpenAPI
`POST /api/providers`):
- `name: opencode`, `url: https://opencode.ai/zen/v1`, Bearer-API-Key
  (Client-Key `sk-afb…`, abgelegt in omniroutes verschlüsseltem
  Provider-Store `storage.sqlite`, nicht in der Hermes-`.env`).
- Damit sind `oc/…`-Modelle (z. B. `oc/big-pickle`) routbar; vorher scheiterte
  jeder `oc/…`-Call mit „This model requires an opencode API key — add one in
  Settings → Providers."
- Verifiziert: `POST /v1/chat/completions` mit `oc/big-pickle` → Router
  meldete `big-pickle`.

**Wichtig für Hermes:** Der `providers.omniroute`-Eintrag in der
Hermes-`config.yaml` (name/base_url/key_env/api_mode) ist nötig, damit MoA- und
Auxiliary-Slots den Endpunkt als benannten Provider auflösen. Ein bloßes
`provider: custom` ohne Namen löst im MoA- und Aux-Kanal NICHT auf
(base_url bleibt `moa://local` → „Connection error").

**Merksatz (Keys):** omniroute verwaltet Provider-Keys selbst in seinem
verschlüsselten Store; Hermes braucht nur einen *Client*-Key. Zwei getrennte
Keystores: der Hermes-Client-Key (in Hermes-`.env` als `OMNIROUTE_API_KEY`) und
der opencode-Provider-Key (nur in omniroute).

## MCP-Konfigurationsprüfung repariert, 10.09.2026

`Agenten/mcp-sync-check.ps1` war seit dem Anlegen kaputt und hat trotzdem jeden Tag
einen Fehlalarm erzeugt. Ursache war nicht nur die Kodierung: in Zeile 104 standen in
einem doppelt gequoteten PowerShell-String `\"`-Escapes, die PowerShell nicht kennt.
Allein dadurch 11 Parserfehler — auch unter PowerShell 7. Dazu UTF-8 ohne BOM unter
Windows PowerShell 5.1 (Umlaute wurden zu `Ã¼`) und `<script>` in Kommentaren. Ergebnis:
`systempruefung.ps1` meldete bei jedem Lauf „MCP-Konfiguration-Drift erkannt", ohne
dass irgendetwas geprüft wurde.

Was jetzt anders ist:

- Das Skript ist reines ASCII ohne BOM (läuft unter 5.1 und 7 identisch) und liest alle
  Eingabedateien explizit als UTF-8.
- Es vergleicht echte Mengen: Manifest ↔ Claude-Konfiguration ↔ Hermes-Konfigurationen.
  Fehlt ein erwarteter Server oder ist einer eingetragen, den das Manifest nicht kennt,
  gibt es Exit 1 mit Namensliste.
- Server mit dem Manifest-Feld `agenten` gelten bewusst nur für einen Agenten und werden
  als „bewusste Abweichung" ausgegeben, nicht als Fehler.
- Neu: Begleitprogramme (`braucht_port`) werden geprüft, und Verbindungsfehler aus
  `Hermes/logs/errors.log` werden eingeordnet — erklärt (Begleitprogramm aus) oder
  unerklärt (Warnung). Ohne das sah ein geparkter Server wie ein Ausfall aus.
- Die Claude-Konfiguration wird auch im MSIX-Container gefunden
  (`%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json`).
  Der alte Pfad `%APPDATA%\Claude\…` existiert auf diesem Rechner nicht.
- Ebenso werden die Profil-Configs gelesen: `Agenten/Hermes/config.yaml` **und**
  `Agenten/Hermes/profiles/<name>/config.yaml`. Ohne das meldete die Prüfung
  `mcp-memory` als fehlend, obwohl das Server im Profil `max` steht.

`MCP-Manifest.json` auf Version 1.1 nachgezogen: `mail` fehlte komplett, `filesystem`
stand als aktiv drin, obwohl es in keiner Laufzeitkonfiguration steht, `pdf-vault` stand
fälschlich auf `enabled: false`, und die `command`/`args` von desktop-commander,
windows-mcp, tooluniverse, mcp-memory und revolut-x zeigten auf Programme, die es so
nicht gibt (z. B. `npx @cloudflare/workers-ai build`).

**Merksatz:** Ein Wächter, der immer Alarm schlägt, ist kein Wächter. Nach jeder
Änderung an einem MCP-Server den Prüflauf zeigen — Exit 0 ist die Abnahme:
`powershell -ExecutionPolicy Bypass -File Agenten/mcp-sync-check.ps1 -Streng`.

**Offen (Stand 10.09.2026, 00:15):**

- `blender` ist bei Hermes geparkt (181 Fehlversuche in den letzten 3000 Log-Zeilen).
  Das ist erwartet, solange Blender mit dem Add-on nicht läuft (Port 28015) — kein Ausfall.
  `affinity` (Port 6767) aus demselben Grund.
- `mcp-memory` fehlt in der Claude-Konfiguration (am 10.09.2026, 23:32, während die App
  lief, aus der Datei verschwunden) und wurde am 11.09.2026 um 00:07 aus der
  Haupt-Config entfernt (Sicherung: `Agenten/Hermes/config.yaml.bak-20260910-mnemoverse`);
  es steht jetzt nur noch im Profil `max`. Die laufende Sitzung hatte den Server noch.
  Bis das geklärt ist, meldet die Prüfung genau diesen einen Fehler. Die Claude-Konfiguration
  darf nur bei geschlossener App geändert werden, sonst überschreibt sie den Speicher der App.
- Das Hermes-Terminal startet weiterhin nicht: `proxy.enabled: true`, aber `iron-proxy`
  nicht eingerichtet (`hermes egress setup`). Ausweichweg für Arbeiten am Vault: die
  MCP-Anbindung `windows-mcp` (PowerShell, Dateisystem, Registrierung).

### Klartext-Token aus `config.yaml` entfernt, 11.09.2026

`a2a_agents.omniroute.auth.token` stand im Klartext in `Agenten/Hermes/config.yaml`
(Zeile 2000). Der Wert war zeichengleich mit der Variablen
`HERMES_CUSTOM_127_0_0_1_20128_API_KEY` in `Agenten/Hermes/.env` — die legt Hermes
beim Einrichten des Custom-Providers selbst an. Die Zeile verweist jetzt darauf:
`token: ${HERMES_CUSTOM_127_0_0_1_20128_API_KEY}`.

- Eine Zeile geändert, sonst nichts: 2219 Zeilen wie vorher, CRLF, kein BOM.
- **Nachgeprüft über den echten Ladeweg** (`hermes_cli.env_loader.load_hermes_dotenv`
  + `hermes_cli.config.load_config`): der Wert löst sich zu denselben 35 Zeichen auf
  wie vorher (SHA-256-Anfang `32757f7e`). Die A2A-Anbindung an omniroute bleibt also
  unverändert funktionsfähig.
- Es war die **einzige** Klartextstelle der Datei; geprüft über alle Zeilen mit
  `api_key`, `token`, `secret`, `password`.
- Sicherung: `Hermes/.sicherung/config.yaml.bak-20260911`.
- In der `.env` liegen **drei** ähnlich benannte Variablen
  (`HERMES_CUSTOM_127_0_0_1_20128_API_KEY`, `HERMES_CUSTOM_LOCALHOST_20128_API_KEY`,
  `HERMES_CUSTOM_OMNIROUTE_API_KEY`); nur die erste trägt diesen Wert. Wer sie
  aufräumt, muss die Referenz in `config.yaml` mitziehen.
- **Falle:** `hermes config get a2a_agents.omniroute.auth.token` meldet
  „Config key not set". Der `a2a_agents`-Block steht nicht in `DEFAULT_CONFIG`, der
  Inspektionsbefehl findet ihn deshalb nicht — gelesen wird er trotzdem. Der Befehl
  taugt nicht als Kontrolle; dafür `load_config()` direkt benutzen.
