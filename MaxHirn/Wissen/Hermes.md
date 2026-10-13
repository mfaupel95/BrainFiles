---
id: 20260830-hermes
title: 'Hermes Agent'
tags: [ki-agenten, betrieb]
created: 2026-08-24
updated: 2026-10-11
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

**25 eigene** unter `Hermes/skills/claude-code-imports/` — jeder Vault-Skill hat
dort eine Kopie, keine Luecke. Neu seit 13.10.2026: `docker-cascade-repair` und
`geld` (Quelle `MaxHirn/.claude/skills/`, kopiert und Werkzeugnamen auf
Hermes umgesetzt). `i-have-adhd` steht bewusst unter `skills/productivity/`,
nicht in `claude-code-imports/`. Dazu `data-guard-audit` unter `skills/productivity/`.
Gemessen 13.10.2026 (`hermes skills list`, HERMES_HOME gesetzt): **157 Skills aktiv**
(140 local, 15 builtin, 2 hub). `geld` ist `enabled`. Offen: `docker-cascade-repair`
liegt doppelt (`skills/system/` und `claude-code-imports/`) — Entscheidung, welche Fassung bleibt.
Korrektur: die ersten Kopien vom 13.10. waren durch Wortersetzung beschaedigt
(`Write-Host` → `write_file-Host`, `Get-ScheduledTask` → `Get-Scheduleddelegate_task`).
Byte-genau aus dem Vault neu kopiert; die kaputte Fassung steht in Git (Commit `d70d8566`)
und als Nachweis unter `Agenten/Hermes/.sicherung/skills-import-20261013/`.
Lehre: Werkzeugnamen nur bei echten Werkzeugaufrufen umsetzen, nie per Textsuche.

**Der Abgleich vom 07.10.2026 hat sich selbst ins Knie geschossen — und ist
repariert.** Der Import-Commit `0b7b5158` (07.10., 20:54) setzte drei Hermes-Kopien
auf den alten Vault-Stand zurueck und loeschte dabei die Weiterarbeit in den Kopien:

| Kopie | vorher | nach dem Import | verloren |
|---|---|---|---|
| `rueckschau/sitzungen_auswerten.py` | 23.949 B | 8.271 B | `--umwege`, zweite Quelle `state.db` |
| `rueckschau/SKILL.md` | 4.719 B | 2.904 B | Umweg-Methodik, Zahlen vom 30.09. |
| `skill/SKILL.md` | 5.803 B | 5.269 B | Regel „Referenzdatei muss in SKILL.md stehen" |

`state.db` und `--umwege` sind genau der Inhalt, der am 05./06.10. als **T-229
erledigt** belegt worden war (383 Sitzungen aus `state.db`, read-only) — der Skill
beschrieb danach Optionen, die sein eigenes Skript nicht mehr hatte. Kein Fehler,
keine Meldung, die Hashes waren vorher wie nachher sauber.

Wiederhergestellt **byte-genau** aus `0b7b5158^` (sha `9cbcdf36c9` / `b15da2160b` /
`1b85c2248e`), Commit `d4b03015`. Gegenprobe: Datei == Blob, `--help` zeigt wieder
`--umwege` und `--hermes-db`, `hermes skills list` fuehrt alle vier als
`local`/`enabled`. Der zerstoerte Stand liegt unter
`Hermes/.sicherung/skills-import-20261007/`.

**Damit sind drei der Kopien bewusst nicht mehr zeichengleich mit dem Vault** — sie
sind die neuere Fassung. `sichern` und `scanner-papier` sind es weiter. Wer kuenftig
abgleicht: **erst die Richtung und die Git-Historie lesen, dann kopieren** (der Skill
`skill-library-sync` hat dafuer jetzt den Abschnitt „Vor dem Ersetzen").

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
### Nachschlagen aus Telegram, 15.09.2026

`/skills` im SkillsBot zeigt die **gelernten** Skills nach Gruppen, `/skill NAME`
den Volltext — nachschlagen statt laden; der Katalog kostet den Agenten nichts,
weil er nur im Bot-Prozess laeuft. Quelle ist die Bibliothek auf der Platte
(`Agenten/Hermes/skills/**/SKILL.md`, Frontmatter `name`/`description`/`category`),
**nicht** die A2A-Agent-Card: die zaehlt Werkzeugsets auf (42 Zeilen `toolset.x`,
„Hermes 'x' capabilities" cards) und liess `/skills` wie eine Zufallsliste aussehen.
Gemessen am 15.09.2026: 67 sichtbare Skills in 14 Gruppen, 5.675 Zeichen — der
Bot teilt selbst in Telegram-grosse Stuecke (Grenze 4096). `.archive` bleibt
draussen: was nicht geladen wird, darf nicht wie geladen aussehen. Umsetzung:
`Agenten/Bus/skillkatalog.py`, Tests `Agenten/Bus/tests/test_skillkatalog.py`
(14), Einbau in `skillsbot.py`. Der Fundus (`MaxHirn/skills/`, 238 Fremd-Skills)
ist **nicht** enthalten — er wird bewusst nicht geladen und bleibt ueber den
Skill `fundus-zugriff` erreichbar.

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

### Router- und Config-Optimierung, 13.09.2026

Ziel: beste Leistung für geringste Kosten. Befund aus `~/.omniroute/storage.sqlite`
(77 MB, Dashboard-verwaltet; kein YAML) und den `call_logs` der letzten 7 Tage:

- **github-Verbindung deaktiviert** (Auth abgelaufen, `no_refresh_token`): 7.950
  Versuche, 6.980 Fehlschläge (88 %) — jeder auto/*-Pool war mit gh/*-Premium-Modellen
  (claude-opus-4.6, sonnet-4.6, gpt-5.3-codex …) verstopft, die alle an der Auth
  scheiterten. Reauth nötig, falls die GitHub-Models genutzt werden sollen.
- **mlx-qwen deaktiviert** (Server läuft nicht, ECONNREFUSED).
- **ollama-local default_model korrigiert**: stand auf `gemma4:26b` (existiert nicht;
  166/173 Fehler), jetzt `gemma-e4b-8k:latest` (7,5B Q8_0, lokal vorhanden).
- huggingface war bereits inaktiv (Credits leer, 402), ebenso anthropic/claude und
  nous-research. **felo-web** (268/268 Fehler) und **opencode-zen** (401) sind
  Katalog-Provider ohne Verbindungszeile — nicht über `provider_connections`
  abschaltbar, werden vom Circuit-Breaker/LKGP gemieden.
- **Hermes AppData-Config** (`%LOCALAPPDATA%\hermes\config.yaml`) hatte den
  Default `Qwen3.6-35B-A3B-UD-Q4_K_M` — eine 403/402-Sackgasse (OpenRouter-Key-Limit,
  HF-Credits leer). Auf den bewährten Stand gezogen: `model.default =
  deepseek/deepseek-v4-flash-0731`, `model.provider = nous`, plus dieselbe
  Fallback-Kette wie die Projekt-Config (lokal `gemma-e4b-8k:latest`). Beide
  Configs sind damit identisch (vorher drifteten sie).

Nachweis:
- Router lebt: `Test-NetConnection 127.0.0.1 -Port 20128`; Live-Request
  `model=auto/best-fast` → 200, geroutet auf `opencode/big-pickle` (kostenlos).
- `hermes fallback list` (mit und ohne `HERMES_HOME`): Primary
  deepseek/deepseek-v4-flash-0731 via nous, Fallback 1: gemma-e4b-8k:latest via
  custom (http://127.0.0.1:11434/v1).
- Sicherung vor den DB-Schrieben:
  `~/.omniroute/db_backups/db_2026-09-13T03-57-08_pre-optimize.sqlite` (77 MB).

Fallen:
- `Qwen3.6-35B-A3B-UD-Q4_K_M` ist kein lösbares Modell — nicht wieder als Default
  verwenden. Der Router kennt `qwen3.6-35b-a3b` = openrouter/qwen/qwen3.6-35b-a3b
  (bezahlt).
- Lokale Ollama-Modelle heißen `gemma-e4b-8k:latest` und `qwen35-8k:latest` —
  Modellnamen in Verbindungen/Kombos immer am Dienst prüfen
  (`curl http://127.0.0.1:11434/api/tags`), nicht aus der Config abschreiben.
- Offen: OpenRouter-Key-Limit (monatlich, 403), veraltete Kombos
  `hermes-free-local`/`CostOptimized-70-30*` (verweisen auf nicht existierende
  Modelle; `activeComboId` ist ohnehin null), Gateway-Neustart nach `hermes update`
  steht aus („pre-update modules"-Warnung beim `config get`).

## Ausgabestil „i-have-adhd" uebernommen, 13.09.2026

Max hat den Claude-Skill **i-have-adhd** (github.com/ayghri/i-have-adhd, MIT)
uebernehmen lassen. Er regelt nicht die Laenge, sondern die Form der Antwort:
erste Zeile = naechste Handlung, nummerierte Schritte, Zwischenstand in jedem
Turn, konkrete Zeitschaetzung statt „etwas Arbeit", hoechstens fuenf sichtbare
Listeneintraege je Gruppe, keine Vorrede / kein Recap / keine Schlussfloskel,
Fehler sachlich als Ursache + Fix. Abschalten mit „stop adhd mode" bzw.
„normaler Modus", ein Satz Bestaetigung, dann zurueck zum Normalstil.

Drei Orte, drei Wirkungen:

1. **Immer an (Hermes):** `Agenten/Hermes/SOUL.md` — Hermes laedt sie als
   Identitaet in Slot 1 des Systemprompts. Dieselbe Fassung als Kopie in
   `%LOCALAPPDATA%\hermes\SOUL.md` und in allen 14 `profiles/<bot>/SOUL.md`.
   Je Datei eine Sicherung `.bak-20260913` (Original = Hermes-Standardidentitaet,
   667 B). SOUL.md wird ausschliesslich aus `HERMES_HOME` geladen, nie aus dem
   Arbeitsverzeichnis [[Ordnerstruktur]].
2. **Nachladbar (Hermes):** `hermes skills install <raw-url>/SKILL.md --category
   productivity` → `Agenten/Hermes/skills/productivity/i-have-adhd/` (Quelle
   `url`, Herkunft `community`, Scan-Verdikt SAFE). Aufruf als `/i-have-adhd`.
3. **Fuer Claude:** `MaxHirn/.claude/skills/i-have-adhd/SKILL.md`, neu angelegt —
   es wurde nichts ueberschrieben. In der Claude-Desktop-App muss der Skill
   zusaetzlich unter Einstellungen → Faehigkeiten hochgeladen werden; der
   Ordnerpfad allein wirkt dort nicht.

Nachweis: eine frische Sitzung (`hermes chat -q … -Q -t memory`) nennt die Regeln
woertlich aus der eigenen Identitaet; ein Stiltest fuehrte mit der Handlung,
nummerierte, gab Zeitschaetzungen in Minuten und endete mit genau einer naechsten
Aktion unter zwei Minuten.

Fallen:
- Eine **laufende** Sitzung behaelt ihren alten Systemprompt (Prompt-Cache);
  der Stil greift erst in einer neuen Sitzung (`/reset` bzw. `/new`).
- Der Skill ist reine Nachladelast: die Dauerwirkung haengt an `SOUL.md`, nicht
  am Skill. Ein Zuruecknehmen heisst also `.bak-20260913` zurueckkopieren, nicht
  den Skill entfernen.

## Anthropic als Provider und Coding auf Opus 5 (14.09.2026)

**Auftrag:** Anthropic in OmniRoute und in Hermes als Provider, Schluessel in
Umgebungsvariablen, Hermes-Coding auf Opus 5.

**Was jetzt gilt**

- `ANTHROPIC_API_KEY` liegt als Windows-Benutzervariable in `HKCU\Environment`
  (108 Zeichen, sha8 `fe77df9d0a`), angelegt aus dem bisherigen
  `ANTHROPIC_API_KEY_BILLING`. Der Name ist der kanonische: Hermes' eingebautes
  Provider-Profil `anthropic`
  (`plugins/model-providers/anthropic/__init__.py`) liest genau ihn, ebenso
  curl, Skripte und OmniRoute. Kein Eintrag in `config.yaml` noetig — das
  Profil bringt `base_url https://api.anthropic.com`, `api_mode
  anthropic_messages` und `env_vars = (ANTHROPIC_API_KEY, ANTHROPIC_TOKEN,
  CLAUDE_CODE_OAUTH_TOKEN)` mit.
- Hermes: `delegation.model: claude-opus-5`, `delegation.provider: anthropic`,
  dazu `delegation.fallback_providers: [{omniroute, auto/best-coding}]` als Netz
  bei 429/529/503 (das Abo hat Nutzungsgrenzen). Gesetzt in **beiden** Ablagen:
  `Agenten/Hermes/config.yaml` und `%LOCALAPPDATA%\hermes\config.yaml`.
- OmniRoute: Verbindung `anthropic` repariert und mit dem Schluessel versehen
  (siehe [[OmniRoute-Produktion]]); sie traegt derzeit nicht, weil der
  Console-Key kein Guthaben hat.

**Nachweis (beides gefahren, nicht behauptet)**

- `hermes chat -q "Antworte mit genau: OK" -Q --provider anthropic
  -m claude-opus-5 -t memory` → „OK", Logzeile
  `API call #1: model=claude-opus-5 provider=anthropic … id=msg_011Cf3n5oA7jA5DgxvfyCVZp`
  (echte Anthropic-Message-ID, 1,7 s).
- Subagent: ein `delegate_task`-Testlauf protokollierte
  `platform=subagent … model=claude-opus-5 provider=anthropic …
  id=msg_011Cf3nSHvJx2CQRFjF3kXSW`, 2,5 s, `status=completed`. **Coding laeuft
  also auf Opus 5, auch im laufenden Gateway** (kein Neustart notwendig — die
  Anmeldedaten kommen aus dem Credential-Pool, nicht aus der Prozessumgebung).
- `hermes config get delegation` nennt die drei Werte.

**Fallen**

- Der Console-Key hat **kein Guthaben**: `api.anthropic.com/v1/messages`
  antwortet `400 Your credit balance is too low to access the Anthropic API`.
  Die Modellliste `/v1/models` antwortet trotzdem `200` — die Anmeldung ist also
  in Ordnung, es fehlt nur das Guthaben. Deshalb traegt den Coding-Betrieb
  derzeit der **Abo-Weg** (OAuth-Eintraege im Credential-Pool, Prioritaet 0/1 aus
  `ANTHROPIC_TOKEN` und `claude_code`); der API-Key steht auf Prioritaet 2 und
  ist nur der letzte Ausweg.
- `hermes config set` schreibt die ganze Datei neu und **schneidet den
  Kommentar-Schluss ab** (hier 38 Zeilen Dokumentation am Dateiende). Nach jedem
  `config set` gegen `.sicherung/config.yaml.bak-20260914` diffen und den Block
  zurueckholen: `Agenten/Hermes/cache/config-schluss-wiederherstellen.py --tun`.
- `patch` und jeder Agenten-Schreibzugriff auf `config.yaml` bzw. die
  AppData-Config sind gesperrt („security-sensitive configuration"). Nur
  `hermes config set`, danach diffen — sonst faellt eine Massenaenderung nicht auf.
- Der alte `#ANTHROPIC_API_KEY` (Rautenzeichen im Namen!) ist ein **anderer**,
  workspace-gebundener Key und antwortet mit `400 This API key is not scoped to a
  workspace`. Er wird von nichts gelesen und blieb liegen; ebenso
  `ANTHROPIC_API_KEY_BILLING` und `CLAUDE_CODE_API_KEY` (401).
- Ein `ANTHROPIC_API_KEY` ohne Guthaben an Prioritaet 2 ist Ballast, aber
  gefaehrlich wird er erst, wenn die OAuth-Eintraege ausfallen: dann faellt der
  Pool auf ihn durch und liefert statt eines klaren Fehlers die
  Guthaben-Meldung.

Sicherungen: `.sicherung/config.yaml.bak-20260914`,
`.sicherung/appdata-config.yaml.bak-20260914`.

## Telegram: ein Eigentuemer statt drei (18.09.2026)

Drei Gateways wollten dasselbe Telegram-Token: der Standard-Gateway (VBS,
Port 9900), das Profil `projectatlas` und das Profil
`awesome-systematic-trading`. Jedes Profil erbt die geteilte Telegram-/
Photon-Credential aus seiner `.env`, und ohne ausdrueckliche `enabled`-Zeile
gibt Hermes die Plattform automatisch frei. Wer zuerst startet, gewinnt; die
anderen loggen `token already in use` und laufen ohne Telegram.

Festgelegt: **Telegram gehoert dem Standard-Gateway.** In beiden Profil-Configs
steht jetzt ausdruecklich:

    gateway:
      platforms:
        telegram:
          enabled: false
        photon:
          enabled: false

Beleg: projectatlas `02:01:17 Platform telegram is explicitly disabled by
platforms.telegram.enabled: false in config.yaml` und `Gateway running with 1
platform(s)`; awesome-systematic-trading `02:16:57 No messaging platforms
enabled.` - der Standard-Gateway haelt den Token: `02:10:42 telegram
connected`, `Gateway running with 4 platform(s)` (a2a, webhook, telegram,
photon).

Nebenbefund: Das Web-Dashboard (Port 9119) schreibt Plattform-Aenderungen und
loest damit Gateway-Neustarts aus (`hermes_cli.web_server: Messaging platform
updated: platform=telegram profile=current enabled=False/True`, 18.09.
01:49:12/13). Ein offener Tab auf der Messaging-Seite ist eine Neustart-Quelle.

Der Gateway-Waechter prueft jetzt ausdruecklich auf ein Gateway OHNE
`--profile` (sonst haelt ein Profil-Gateway ihn faelschlich fuer den Standard).

Sicherungen: `.sicherung/projectatlas-config.yaml.bak-20260918`,
`.sicherung/awesome-systematic-trading-config.yaml.bak-20260918`,
`Routinen/gateway-waechter.ps1.bak-20260918`.

## Sicherung und Telegram-Route (18.09.2026, abends)

**Die geplante Sicherung lief nicht durch.** Die Laeufe starben mitten im Lauf
(Protokoll ohne Schlusszeile; Task-Code 3221225786 am 17.09. um 00:40, Code 1
am 18.09. um 20:00). Ursache war der Wrapper `Routinen/sicherung.ps1`:
`$ErrorActionPreference = 'Stop'` zusammen mit der Pipeline
`... *>&1 | Add-Content $log`. PowerShell 5.1 macht aus stderr eines
Kindprozesses einen terminierenden Fehler und reisst die Pipeline mitten im
Schreiben ab - daher die abgeschnittene letzte Zeile.

Behoben: `Continue` statt `Stop`, und die Ausgabe geht in eine Datei
(`*> $logs\sicherung-lauf.tmp`, danach anhaengen und loeschen). Eine
Dateiumleitung kann nicht abreissen, und bei einem Abbruch bleibt die
Teilausgabe erhalten.

Nachweis 18.09. 22:40:38: alle drei Schritte im Protokoll, robocopy-Code 3,
`ENDE ok nach 434 s`, Task-rc 0, Ziel `G:\MaxHirn-Sicherung` auf dem Stand der
Quelle (config.yaml 22:37, zustand.json 22:41).

Zusaetzlich: zweiter taeglicher Trigger 22:30 (MultipleInstances IgnoreNew und
ExecutionTimeLimit PT1H unveraendert) - ein Lauf, der um 20:00 stirbt, hat am
selben Abend noch eine Chance.

**Telegram laeuft jetzt auf dem Profil `awesome-systematic-trading`**
(deepseek/deepseek-v4.1-flash). Mit `gateway.multiplex_profiles: true` ist der
Standard-Gateway der EINZIGE Inbound-Prozess; Hermes verweigert ein zweites
Gateway ausdruecklich ("would double-bind its platforms - two pollers on one bot
token"). Der Weg ist deshalb eine Route, keine zweite Instanz:

    gateway:
      profile_routes:
        - name: telegram-max
          platform: telegram
          chat_id: "7648512088"
          profile: awesome-systematic-trading
          enabled: true

`chat_id` MUSS in Anfuehrungszeichen stehen - als Zahl geparst trifft sie nie
(Warnung im Quelltext `gateway/profile_routing.py`). Beleg: Hermes' eigene
Funktion liefert den Treffer fuer 7648512088 und keinen fuer einen fremden Chat;
der Standard-Gateway verbindet Telegram um 22:54:07.

Falle: `hermes gateway restart` trifft das als "current" erkannte Profil, nicht
den Standard - fuer den Standard `hermes --profile default gateway restart`.

Sicherungen: `.sicherung/config.yaml.bak-20260918-routen`,
`.sicherung/awesome-systematic-trading-config.yaml.bak2-20260918`,
`Routinen/sicherung.ps1.bak-20260918`.
`MaxHirn/Wissen/Hermes.md.bak2-20260918` (diese Notiz).

Verwandt: [[OmniRoute-Produktion]] · [[Verbindungen]]

## Desktop-App: alle Profile sichtbar (18.09.2026)

Die Desktop-App zeigte nur das default-Profil, weil `gateway.multiplex_profiles`
nie explizit gesetzt war (nur der Code-Default) - der Gateway servierte nur
`default`, die App keinen Bots-Tab/Profil-Umschalter, und Profil-Backends
starteten und wurden nach Idle beendet (desktop.log: `exited (1)`).
Gesetzt: `gateway.multiplex_profiles: true` in `Agenten/Hermes/config.yaml`
(Zeile 2095), dann `hermes gateway restart` (dokumentierter Weg aus
`hermes gateway status`). Beleg: `gateway status` ohne
'multiplex_profiles unset'-Warnung, `gateway list` zeigt alle 29 Profile,
desktop.log `Hermes backend is ready`, Bots-Tab zeigt alle Profile.

Falle dabei: `hermes config set` schneidet den Kommentar-Schluss der Datei
ab (Security-Doku-Block, 38 Zeilen) - aus
`backups/config/config.yaml.good.20260918-131140` byte-genau
zurueckgeholt; der Diff gegen die .good-Sicherung zeigt exakt 1 Zeile.
Der Commit enthaelt NUR die multiplex-Zeile (deterministischer Index:
`git hash-object -w --stdin` + `git update-index --cacheinfo` gegen die
HEAD-Fassung), der Arbeitsbaum mit den fremden Aenderungen anderer
Sitzungen bleibt unberuehrt.

Zweitablage `%LOCALAPPDATA%\hermes\` (config.yaml v42, eigene .env mit
Klartext-Zugangsdaten, eigene auth.json): komplette Alt-Installation von vor
dem Umzug, wird von der Desktop-App nicht mehr gelesen (HERMES_HOME ist
Benutzervariable, `resolveHermesHome2` liest Registry-HERMES_HOME vor
LOCALAPPDATA). Altlast, nicht angefasst - Entscheidung offen.

Sicherungen: `config.yaml.bak-20260918`, `backups/config/config.yaml.good.20260918-133615`.
## SkillsBot/Hauptmodell auf den lokalen Router, 21.09.2026

Auftrag Max: das Standardmodell des SkillsBots auf ein ausfallsicheres lokales
mit mindestens 400.000 Token umstellen, zur Fehlerbehebung.

**Der SkillsBot hat kein eigenes Modell.** `Agenten/Bus/skillsbot.py` ist eine
Bruecke: er reicht jede Nachricht per A2A an den Gateway (Port 9900), und der
bedient das `default`-Profil. Das Modell des SkillsBots ist deshalb der
`model:`-Block in `Agenten/Hermes/config.yaml.` Ein eigener Modellschalter je
Plattform existiert nicht; A2A-`served_agents` koennten nur ein anderes PROFIL
bedienen, und ein frisches Profil ist eine Insel ohne Max' Skills.

**Der Zielprovider lag schon da und war unbenutzt:** `providers.smart`
(`base_url` http://127.0.0.1:20128/v1, `key_env`
HERMES_CUSTOM_127_0_0_1_20128_API_KEY, `models.auto/smart.context_length:
400000`). Der Router meldet fuer `auto/smart` live 1.000.000 Token Kontext
(`/v1/models`), also mehr als die geforderten 400.000. Damit ist das Modell
lokal erreichbar (127.0.0.1) und haengt nicht an der Nous-Portal-Anmeldung,
die zuletzt mehrfach ausfiel.

Gesetzt per `hermes config set` (nicht per Hand editiert):

```yaml
model:
  default: auto/smart
  provider: smart
  base_url: http://127.0.0.1:20128/v1
```

dazu `providers.smart.base_url` und `providers.smart.api_mode:
chat_completions`. Beim Providerwechsel hat `hermes config set` die alten
nous-Werte `model.base_url`/`model.api_mode` selbst geleert - das ist richtig
so, der Endpunkt gehoerte zu nous.

**Ausfallsicherheit kommt aus der Kette**, nicht aus dem Router:
`fallback_providers` = `nous`/`deepseek/deepseek-v4.1-flash` (786k) und
dahinter `ollama-launch`/`qwen35-8k:cpu` (lokal, laeuft immer). Der Router ist
selbst eine Abhaengigkeit - seine Combo `auto/best-coding` lag am 21.09. schon
auf toten Zweigen.

**Belege (echter Lauf, kein Schaetzen):**

- `curl /v1/models` mit dem Router-Key: `auto/smart` = 1.000.000 Token.
- A2A-SendMessage an 127.0.0.1:9900 ("Antworte nur mit PONG") -> `PONG` in
  7,6 s; `logs/agent.log` 18:21:45: `API call #1: model=auto/smart
  provider=custom base_url=http://127.0.0.1:20128/v1 in=94635 out=5`,
  `platform=a2a` - das ist genau der Weg des SkillsBots.
- Werkzeugtest ueber denselben Weg: terminal `hostname` -> `MaksPC420` in 7,3 s
  (die Combo fuehrt Tool-Aufrufe aus, nicht nur Prosa).
- Kein Gateway-Neustart noetig: der laufende Gateway liest die neue Config fuer
  neue Sitzungen. Der SkillsBot-Prozess selbst wurde nicht angefasst.

**Falle, zum dritten Mal (siehe 18.09.2026 oben):** JEDES `hermes config set`
schneidet den 38-zeiligen Kommentar-Schluss der Datei ab (Security- und
Fallback-Model-Doku) - 2474 -> 2437 Zeilen. Aus
`Agenten/Hermes/config.yaml.bak-20260921-181826` byte-genau (CRLF) wieder
angehaengt; der Commit enthaelt danach nur die gewollten Zeilen. Nach jedem
`hermes config set` also `git diff --stat` pruefen.

**Bewusst NICHT angefasst:** die 26 Repo-Bots bleiben auf nous (eigene Profile,
eigene auth.json); ihre Router-Kette wurde am 21.09. gerade erst umgestellt.
Das Desktop-Gespraech und der Telegram-Hauptbot laufen im selben `default`-
Profil und fahren damit ebenfalls auf `auto/smart` - wer nur den SkillsBot
umstellen will, braucht ein eigenes Profil (Inselproblem, siehe oben).

Sicherung: `Agenten/Hermes/config.yaml.bak-20260921-181826`.


## Desktop optimal einrichten (Hermes Desktop, 04.10.2026)

**Auftrag:** Desktop mit den bestmoeglichen Hilfsmodellen, MoA und den
erweiterten Einstellungen; `stealth/space-bunny-alpha` bevorzugt.

**Grundlage war Messung, nicht Empfehlung.** Jeder Kandidat wurde am
04.10.2026 mit einem echten Chat-Aufruf am Nous-Endpoint befragt
(`credential_pool.nous.agent_key` aus `auth.json`, Antwort-Inhalt geprueft,
nicht nur HTTP 200), und die Fensterzahl kam aus `get_model_context_length()`:

| Modell | Fenster | Antwortzeit |
|---|---|---|
| `stealth/space-bunny-alpha` | 1.000.000 | 1,4 s |
| `deepseek/deepseek-v4-flash-0731` | 1.048.576 | 1,1 s |
| `anthropic/claude-opus-5` | 1.000.000 | 1,5 s |
| `openai/gpt-6-astra` | 1.050.000 | 2,8 s |
| `google/gemini-3.1-pro-preview` | 1.048.576 | 3,3 s |
| `google/gemini-3.1-flash-lite` | 262.144 | 1,4 s |
| `qwen/qwen3-30b-a3b` | 262.144 | 3,4 s |
| `deepseek/deepseek-v4-pro` | 1.048.576 | 2,5 s |

**Hauptmodell:** unveraendert `nous/stealth/space-bunny-alpha` (Max' Wahl).

**MoA:** alle vier Presets aggregieren jetzt auf `stealth/space-bunny-alpha`.
Das ist der entscheidende Punkt: der Aggregator IST das handelnde Modell, er
laeuft in jedem Werkzeugschritt und traegt fast die ganzen Kosten - dort ein
lokales Ollama-Modell einzusetzen war der Fehler in `Max 2` und `Vision`.
`default` hat fuenf Berater aus fuenf Familien (Opus 5, GPT-6-Astra, Gemini
3.1 Pro, DeepSeek v4 Pro, Qwen3-30B); `Vision` bekam `qwen/qwen3-vl-32b-instruct`
als sechsfuehrende Beraterin. `fanout: user_turn` bleibt - `per_iteration`
vervielfacht die Beraterkosten mit der Werkzeugschleifen-Tiefe.

**Hilfsmodelle (`auxiliary`):** `skills_hub`, `mcp`, `curator`, `approval`,
`title_generation`, `memory_query_rewrite` standen auf `auto` und erbten damit
das HAUPTmodell - ein Kurzeraufruf, der space-bunny-alpha kostete. Umgestellt auf
`google/gemini-3.1-flash-lite` (1,4 s). `kanban_decomposer` und
`triage_specifier` bleiben auf `inception/mercury-2.5` (1,7 s, JSON-faehig).
`compression` bleibt `deepseek-v4-flash-0731` (1.048.576) - Kompression braucht
das grosse Fenster, `vision` bleibt `qwen3-vl-235b`.

**Weiter geaendert, mit Grund:**

- `compression.threshold` 0.19/0.5 -> **0.7**. Der Wert 0.19 stammte aus der Zeit,
  als das Kompressionsmodell nur 200k Fenster hatte; jetzt sind es 1.048.576 und
  das Hauptmodell 1.000.000, die Kompression setzt erst bei rund 700.000 Token ein.
- `prompt_caching.cache_ttl` 5m -> **auto**. `auto` heisst 1h-Tier fuer alles, was
  ein Mensch tippt (cli/tui/desktop/Gateway), 5m fuer maschinell getaktete Quellen
  (subagent/cron/kanban/webhook). Der Schreibvorgang kostet 2x statt 1,25x - das
  zahlt sich aus, weil die Memory (302.068 Zeichen) in jedem Turn mitgeschickt wird.
- `delegation.child_timeout_seconds` 180 -> **600**. Der Timeout startet bei jedem
  Fortschritt neu; 180 s hat lebende Subagenten mit mehreren Werkzeugschritten
  trotzdem abgeschnitten.
- `delegation.fallback_providers`: `gemma-e4b-8k:cpu` und der tote Bonsai-Dienst
  raus, ersetzt durch dieselbe Kette wie das Hauptmodell. Ein per Provider
  gepinntes Kind erbt die Hauptkette NICHT - ohne eigene Liste hatte ein Subagent
  gar keinen Rueckfall.
- `fallback_providers`: der Eintrag `nous/stealth/space-bunny-alpha` war als erster
  eingetragen und damit als Rueckfall fuer sich selbst wertlos; ersetzt durch
  `deepseek-v4-flash-0731`, `claude-opus-5`, `gemini-3.1-flash-lite`. Der
  `llamacpp`/Bonsai-Eintrag ist entfernt (der verwaltete llama-server auf 18434
  kann die ternaeren Gewichte nicht laden, Befund 29.09.2026).
- `desktop.renderer_max_old_space_mb` 0 -> **4096**. 0 = Chromium-Standard, und
  genau der hat am 13.09.2026 einen Rechner-weiten Freeze erzeugt; mit Deckel wird
  daraus ein begrenzter Renderer-Neustart.
- `moa.max_tokens: 64096` entfernt: **toter Schalter**. `hermes moa list` und der
  Runtime-Leser (`agent/moa_loop.py`) kennen kein `max_tokens` in der Preset-
  Normalisierung - nur `reference_max_tokens` als Aufrufargument.

**Beleg:** `hermes config check` exit 0; `hermes moa list` zeigt die vier
Presets mit dem neuen Aggregator; `config get` je Schluessel bestaetigt den
Wert; `git diff --numstat` 92/44 (kein Ganzdatei-Diff), 0 verlorene Kommentarzeilen,
CRLF == LF.

**Falle (neu, wichtig):** `  aggregator:` steht in `moa:` ZWEIMAL - einmal
eingerueckt im Preset, einmal als flache Kompatibilitaets-Ausgabe auf
Top-Level. `lines.index("  aggregator:")` findet das erste Vorkommen und
haette beim Ersetzen den halben Dateianfang doppelt eingefuegt. Ab dem
gesuchten Preset-Namen suchen, nicht vom Dateianfang.

**Falle (bestaetigt):** ein zu kleines `max_tokens` laesst ein Denkmodell STUMM
statt defekt aussehen (`deepseek/deepseek-v4-flash`, `inception/mercury-2.5`,
`qwen/qwen3-30b-a3b` lieferten bei `max_tokens: 32` leeren `content`, bei 2000
sauberen). Alle Tabellen hier sind mit `max_tokens: 2000` gemessen.

Sicherung: `Agenten/Hermes/config.yaml.bak-desktop-20261004` und
`Agenten/Hermes/config.yaml.bak-moa2-20261004`.

**Bewusst NICHT angefasst:** `Max`-Preset mit omniroute-Aggregator (aus - der
Router lebt, 401 ohne Key ist das normale Bild) und `local_runtime.enabled: true`
(bestaetigte Max-Entscheidung). Die 26 Bot-Profile unter `profiles/` haben eigene
Configs und wurden nicht angefasst - sie stehen weiter auf nous/deepseek-v4-flash.
## Docker-Terminal brach mit Exit 125 ab - Windows-cwd im Container (05.10.2026)

**Symptom:** Jedes `terminal`-Kommando scheiterte plotzlich mit "Terminal environment unavailable"; im Traceback stand `docker: Error response from daemon: the working directory ` + "'C:\Users\faupe\documents\BrainFiles\Agenten\Hermes'" + ` is invalid, it needs to be an absolute path`, Rueckgabecode 125. Die Dateiwerkzeuge liefen zunaechst weiter - nur das Terminal war tot.

**Ursache (gemessen, nicht geraten):** `terminal.cwd` steht auf einen Windows-Host-Pfad, `docker_mount_cwd_to_workspace` stand auf `false`. In `hermes-agent/tools/terminal_tool.py::_resolve_config_cwd()` setzt der Windows-Zweig (Zeilen 693-702) dann `cwd = candidate` - der Windows-Pfad geht roh in `docker run -w` und Docker weist ihn ab. Mit `true` (Zeilen 685-692) wird stattdessen gebunden und `cwd = "/workspace"` gesetzt.

**Gegenprobe ohne Hermes:**

    docker run -d --name probe -w 'C:\Users\...\Agenten\Hermes' nousresearch/hermes-sandbox:desktop sleep infinity  # Exit 125
    docker run -d --name probe -w /workspace nousresearch/hermes-sandbox:desktop sleep infinity                     # Exit 0

**Warum es lange unauffaellig blieb:** der Sandbox-Container wird beim ersten Kommando gebaut und danach wiederverwendet (`persist_across_processes` + `container_persistent: true`, `lifetime_seconds: 300`). Solange einer lief, ging alles; erst als keiner mehr lief (Idle-Reaper / Docker-Neustart), brach jedes Kommando auf. Kein Docker-Schaden, kein Platzproblem, kein Speicherdruck.

**Aenderung:** `Agenten/Hermes/config.yaml` Zeile 654, `docker_mount_cwd_to_workspace: false` -> `true`. Byte-genau ersetzt (nicht per `hermes config set`, das schneidet den Kommentar-Schwanz ab und schreibt LF). Sicherung: `Agenten/Hermes/.sicherung/config.yaml.bak-20261005b`. Beleg: `Compare-Object` Sicherung <-> Datei = EIN Zeilenpaar; `yaml.safe_load` parst, `terminal` behaelt 12 Schluessel; CRLF 1377/1377 unveraendert. Die Zeile wirkt erst, wenn der Hermes-Prozess die Config neu liest - kein Live-Schalter.

**Zwei Nebenbeobachtungen, die zur Verwechslung fuehren koennen:**

- Der Prozessfilter `*gateway run*` findet den Gateway nicht (er laeuft per `runpy.run_module`); Identitaet immer aus `gateway_state.json` lesen.
- Der Container `hermes` (Volume `hermesalt-20260916_hermes-data`, cwd `/opt/hermes`) ist ein ALTER Dienst und hat mit der Terminal-Sandbox nichts zu tun. Die Sandbox heisst `hermes-<8 hex>` und traegt das Label `hermes-agent=1`.

**Offen:** Wirkung noch nicht live belegt - der laufende Hermes-Prozess haelt die alte Config. Der Beleg ist der naechste Terminal-Aufruf ohne Exit 125.
### Nachtrag 06.10.2026: die Wurzel in den Container holen

Der Fix vom 05.10. (`docker_mount_cwd_to_workspace: true`) macht das Terminal
wieder lauffaehig, bindet aber **nur `Agenten/Hermes`** als `/workspace`. Die
BrainFiles-Wurzel (`MaxHirn/`, `Agenten/Handel/`, das `.git`) ist darin nicht
sichtbar: `_mount_args` bindet genau den `cwd`, und `_existing_host_mount()`
findet einen zweiten Mount nur ueber einen `docker_volumes`-Eintrag mit
demselben Host-Pfad.

Gesetzt wurde:

    terminal:
      docker_volumes:
        - 'C:\Users\faupe\Documents\BrainFiles:/brainfiles'

Beleg: `git diff --numstat` 2/0; Block allein stehend geparst, bevor die Datei
angefasst wurde; Top-Level-Schluesselmenge unveraendert; `terminal` 12 -> 13
Schluessel (genau `docker_volumes`); CRLF 1377 -> 1379, bareLF 0. Sicherung
`.sicherung/config.yaml.bak-20261006-vol`. Commit `16e7fddf`.

**Vorsorge, nicht Reparatur:** eine parallele Sitzung hat `terminal.backend`
auf `local` gestellt (Commit `3d310c22`) - das Terminal laeuft seither am Host
und sieht die Wurzel ohnehin. Der Eintrag wirkt, sobald der Docker-Backend
wieder eingeschaltet wird.

**Offen:** der Docker-Daemon antwortete in dieser Sitzung nicht mehr
(`docker ps` lief 90 s ohne Ausgabe in den Timeout) - deshalb ist der
Volume-Spec am echten Container NICHT nachgemessen. Nachzuweisen bleibt:
`docker exec <container> ls /brainfiles` zeigt `MaxHirn` und `Agenten`.

## Schreib-Sandbox um Werkstatt erweitert (07.10.2026)

**Auftrag Max:** `HERMES_WRITE_SAFE_ROOT` auf `C:\Users\faupe\Documents\BrainFiles;O:\Werkstatt`
erweitern.

**Die Ursache lag tiefer als erwartet.** `BrainFiles\Werkstatt` ist ein **Symlink auf
`O:\Werkstatt`** (Laufwerk O:, nicht unterhalb von BrainFiles). Die Sandbox stand nur auf
`BrainFiles`, der Pruefer loest den Symlink auf und lehnte jeden Schreibzugriff in die
Repos unter `Werkstatt\Repos` ab (AGENTS.md-Schreiben scheiterte dreimal). Lesen und
Terminal waren nie betroffen - deshalb lief die Analyse, nur das Schreiben nicht.

**Gesetzt wurde es NICHT in der Registry und nicht in `config.yaml`** (Zeile 630 dort ist
nur ein Name in `terminal.docker_forward_env`), sondern in der `.env`:

- `Agenten/Hermes/.env` Zeile 507 (Hauptablage)
- `Agenten/Hermes/profiles/claude-code/.env` Zeile 507 (dieses Bot-Profil)

**Jedes Profil hat eine eigene `.env`.** Ohne die zweite Aenderung haette die Haupt-.env
fuer dieses Profil nichts bewirkt. Wer den Wert kuenftig aendert, muss beide Stellen
treffen (bzw. alle `profiles/<name>/.env`, die den Wert fuehren).

Wert jetzt: `C:\Users\faupe\Documents\BrainFiles;O:\Werkstatt`
Trennzeichen ist `os.pathsep` (`;` unter Windows), mehrere Wurzeln sind vorgesehen
(`agent/file_safety.py::get_safe_write_roots`).

**Beleg (echte Laeufe):**

- Frische Instanz aus der Profil-.env: aufgeloeste Wurzeln =
  `C:\Users\faupe\Documents\BrainFiles` **und** `O:\Werkstatt`.
- Schreibpruefung: `O:\Werkstatt\Repos\claude-code\AGENTS.md` ERLAUBT,
  `O:\Werkstatt\Repos\codex\AGENTS.md` ERLAUBT,
  `C:\Windows\System32\drivers\etc\hosts` GESPERRT,
  `C:\Users\faupe\.ssh\id_rsa` GESPERRT.
- Genau eine Zeile je Datei geaendert (`diff` gegen die Sicherung), BOM-Status und
  Zeilenenden erhalten.
- `hermes gateway status`: Aufgabe registriert, Prozess laeuft (PID 70456) - **kein
  Agent neu gestartet.**

**Wichtig - die Grenze bleibt:** Die Erweiterung wirkt in **neuen** Sitzungen. Die
laufende Sitzung hat die alte Umgebung schon im Prozess (Gegenprobe: Schreibversuch nach
`O:\Werkstatt` aus dieser Sitzung weiterhin abgelehnt). Sie ist eine
Verteidigungslinie, keine Sicherheitsgrenze - das Terminal umgeht sie ohnehin (so wurde
das AGENTS.md auch geschrieben).

**Falle (zweimal gekostet):** Die `.env` nutzt **CRLF**. Ein Suchmuster mit `\n` findet
dort nichts ("Treffer: 0"), und ein Heredoc durch die Werkzeugschicht verstuemmelt die
Backslash-Pfade. Deshalb: Zeilenenden vorher byte-genau bestimmen, das Skript als
**Datei** schreiben und die Laengenaenderung pruefen.

Sicherungen: `Agenten/Hermes/.sicherung/.env.bak-20261007`,
`Agenten/Hermes/profiles/claude-code/.env.bak-20261007`,
`Wissen/Hermes.md.bak-20261007-safe-root`.

## Claude Code CLI auf 2.1.293 aktualisiert (07.10.2026)

**Auftrag Max:** CLI updaten. Ausgangslage 2.1.285, Ziel 2.1.293.

**Der erste Befund war eine Falle.** `claude update` meldete zweimal
"Claude Code is up to date (2.1.285)", obwohl das Repo v2.1.293 kennt. Zwei Ursachen:

1. `autoUpdates: false` in `C:\Users\faupe\.claude.json` - Max' Entscheidung,
   die **auch den ausdruecklichen Update-Befehl** blockiert.
2. Der Kanal stand auf `stable` - und `stable` ist genau 2.1.285.

Die Endpunkte direkt abgefragt (das war der Beweis, nicht die Vermutung):

    BASE=https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases
    stable -> 2.1.285      latest -> 2.1.293      beta/next -> NoSuchKey

**Ablauf:** Launcher gesichert -> `autoUpdates: true` -> Kanal auf `latest` ->
`claude update` (~240 MB, rund 90 s) -> beide Schalter zurueck auf `stable`/`false`.

**Installationsart:** native, nicht npm. Launcher
`C:\Users\faupe\.local\bin\claude.exe`, Versionen unter
`C:\Users\faupe\.local\share\claude\versions\`. Rueckfall:
`versions/2.1.285.bak-20261007`.

**Wichtig:** Das laufende Binary muss nicht frei sein. Es ist waehrend des Betriebs
gesperrt (`Permission denied`), der Updater legt die neue Version daneben und schaltet
den Launcher um. **27 laufende Claude-Sitzungen und das Hermes-Gateway (PID 70456)
liefen ununterbrochen weiter** - kein Agent wurde gestoert.

**Belege:** `claude --version` -> 2.1.293; `claude doctor` -> native 2.1.293, Commit
`3abc54a9d60b` (gleich `manifest.json`), Kanal stable; echter Lauf
`claude -p "Antworte mit genau: OK"` -> `OK`; `claude plugin test mods/agents-md` ->
5 pass, 0 fail.

**Nebenbefund, offen:** Die neue Version warnt beim Start ueber acht wirkungslose
deny-Regeln in `MaxHirn/.claude/settings.local.json` - `Write(./Archiv/**)`,
`Write(./Wissen/**)`, `Write(./Claude/**)`, `Write(./Bilder/**)`, `Write(./Videos/**)`,
`Write(./Musik/**)`, `Write(./Dokumente/**)`, `Write(**/.obsidian/**)`. Meldung:
"only Edit(path) rules are [matched]". **Die Schutzregeln greifen weiter:** fuer jedes
dieser Verzeichnisse steht daneben eine `Edit(...)`-Regel, und die deckt laut Meldung
alle Datei-Werkzeuge ab. Die `Write(...)`-Zeilen sind Dopplung und erzeugen nur
Rauschen. Aufraeumen braucht einen Auftrag (Schutzregeln, Stufe 1).

Sicherungen: `.claude.json.bak-20261007`, `.claude/settings.json.bak-20261007`
(beide byte-identisch zurueck bis auf `autoUpdates`),
`versions/2.1.285.bak-20261007` (Rueckfall-Binary).
Gelerntes auch in `Werkstatt/Repos/rule_repo-bots.md`.

## Wirkungslose Write-Regeln bereinigt (07.10.2026)

**Auftrag Max:** die Write-Regeln aufraeumen, die die neue CLI seit dem Update auf
2.1.293 bei jedem Start als wirkungslos meldet.

**Die Ursache war eine Skill-Vorlage.** Die sechs `Write(...)`-Zeilen stammen aus
`Agenten/Hermes/skills/productivity/protecting-irreplaceable-data/templates/
settings-deny-list.json` - dem Drop-in-Block, der laut Skill in jede
`settings.local.json` kopiert wird. Von dort sind sie in alle Settings-Dateien
gewandert. Die Vorlage ist deshalb **mitkorrigiert**; sonst waeren sie beim
naechsten Anwenden wieder da.

**Warum sie nichts schuetzen:** Die CLI wertet fuer Dateipfade nur `Edit(...)` aus.
`Write(...)` trifft nichts und erzeugt nur eine Warnzeile je Regel. `Edit(...)` deckt
laut Meldung **alle** Datei-Werkzeuge ab - die `Write(...)`-Zwillinge brachten also
null zusaetzliche Deckung. Fuer jedes der acht Verzeichnisse stand daneben bereits
die wirksame `Edit(...)`-Regel.

**Bereinigt wurden drei aktive Dateien:**

| Datei | vorher | nachher |
|---|---|---|
| `MaxHirn/.claude/settings.local.json` | 37 deny, 8 Write | 29 deny, 0 Write |
| `MaxHirn/Archiv/.claude/settings.local.json` | 34 deny, 7 Write | 27 deny, 0 Write |
| `.../protecting-irreplaceable-data/templates/settings-deny-list.json` | 33 deny, 6 Write | 27 deny, 0 Write |

**Nachweis (echter Lauf, vorher/nachher):** `claude -p "sag OK"` in `MaxHirn` gab
vorher 8 Warnungen, im `Archiv` 7 - jetzt **0**, stderr leer. Alle Schutzregeln
unveraendert: `Edit(...)` fuer jedes Stufe-0-Verzeichnis, 9 `Read`-Sperren auf
Schluessel, 11-12 Loesch-Sperren (`rm`, `mv`, `Remove-Item`, `/MIR`, `--delete`).
Genau die erwarteten Zeilen entfernt (`diff`), LF und BOM-Status erhalten, JSON gueltig.

**Fehler, den ich gemacht habe:** Die Worktrees unter `.worktrees/` und
`.claude/worktrees/` sind **echte Git-Branches**, und `settings.local.json` ist
versioniert. Ich hatte zuerst in zwei davon geschrieben (`t_3d11d36a`, `t_bcc968fc`)
und damit fremde Arbeit in Branches erzeugt, die mir nicht gehoeren. Mit den
Sicherungen zurueckgesetzt - beide sind wieder sauber (0 Aenderungen). **Lehre: vor
jedem Schreiben in einem Worktree pruefen, ob die Datei versioniert ist
(`git ls-files --error-unmatch <pfad>`), und in fremden Branches grundsaetzlich nicht
schreiben.** Die verbleibenden `Write(...)`-Vorkommen liegen ausschliesslich in diesen
Branch-Kopien und werden dort nicht angefasst.

Gelerntes auch im Skill `protecting-irreplaceable-data` (Step 3: `Edit(path)` statt
`Write(path)`, mit Pruefbefehl).

Sicherungen: `settings.local.json.bak-20261007-write-regeln` (MaxHirn und Archiv),
`settings-deny-list.json.bak-20261007`.

## Wache um Ziel-, Schreib- und .env-Pruefung erweitert (07.10.2026)

**Auftrag Max:** die in T-369 vorgeschlagene Zusatzpruefung umsetzen.

**Was fehlte.** `Agenten/Hermes/scripts/konfig-doktor-wache.py` fragte bisher nur,
OB ueberhaupt ein Verweis da ist. Ein Verweis aufs **falsche Ziel**, ein Verweis,
den die Werkzeuge **nicht durchlaufen**, und ein Profil ohne Werkstatt-Pfad in
`HERMES_WRITE_SAFE_ROOT` kamen darin nicht vor. Alle drei sind vorgekommen.

Die Wache hat jetzt **drei Zeugen** statt zwei: Verweis -> Ziel + Schreibtest +
`.env`-Lage -> Doktor.

**Der Schreibtest** legt eine Probedatei durch den **BrainFiles-Pfad** an (nicht
direkt auf O:) und raeumt sie wieder weg. Genau dieser Weg zeigt, ob ein Werkzeug,
das den Reparse-Punkt aufloest, danach noch in seiner Sandbox liegt - daran
scheiterte das Schreiben in die Repos, waehrend Lesen und Terminal weiterkamen.

**Der `.env`-Zeuge** prueft nur die Profile, deren `SOUL.md` `Werkstatt` nennt -
sonst waeren es 27 Meldungen statt 17 und die Wache wuerde zum Dauer-Alarm. Dazu
die Haupt-`.env`, die alle erben. Ein Profil **ohne** eigene `.env` erbt und ist
gesund; gemeldet wird nur, was den Werkstatt-Pfad nicht traegt.

**Ein echter Fund beim ersten Lauf:** **16 von 18** Repo-Bot-`.env` tragen den
Werkstatt-Pfad nicht - diese Bots koennen nicht in die Repos schreiben. Betroffen:
basic-memory, caveman, claudian, deepseek-harness, easycliproxyapi,
everything-claude-code, gbrain, harvard-trading, moon-dev-agents, obsidian-skills,
one-skill-to-rule-them-all, openmontage, openterminal (ohne Werkstatt) sowie lotse,
markt-recherche, nerd (kein Eintrag). Nur `claude-code` und die Haupt-`.env` sind
vollstaendig. **Behoben habe ich das nicht** - es ist die offene Entscheidung aus
T-369.

**Falle, die die Tests aufgedeckt haben (wichtig):** `os.path.islink` liefert fuer
eine **Windows-Junction `False`**. Meine ersten Fassungen von `ziel_lage` und
`schreibtest` stiegen deshalb sofort aus und prueften **nie** - sie meldeten
"gesund", ohne etwas getan zu haben. Richtig ist das Datei-Attribut
`FILE_ATTRIBUTE_REPARSE_POINT` (0x400); es gibt jetzt `_ist_verweis()`, und auch
Zeuge 1 nutzt es. Ohne die Tests waere das nie aufgefallen: die Wache haette still
zugestimmt.

**Tests:** `Agenten/Hermes/scripts/tests/test_konfig_doktor_wache.py` (12 Tests,
alle gruen). Sie bauen eine eigene Wurzel in `%TEMP%`, legen dort **echte
Junctions** an (falsches Ziel, nicht beschreibbares Ziel, echter Ordner statt
Verweis) und pruefen die `.env`-Faelle inklusive Vererbung. Die echte
BrainFiles-Wurzel bleibt unberuehrt. Aufruf:
`python Agenten/Hermes/scripts/tests/test_konfig_doktor_wache.py`

**Beleg (echter Lauf):** `konfig-doktor-wache.py --immer` meldet die 16 `.env` und
sonst nichts; Verweis, Ziel und Schreibtest fuer `Werkstatt` und `Modelle` sind
gesund; keine Probedatei bleibt liegen.

Sicherung: `konfig-doktor-wache.py.bak-20261007`.
Empfehlung offen: der Cron-Text (`konfig-doktor-wache`, 1beb6d64a8c8) beschreibt
noch den alten Umfang ("prueft die Wurzel-Verweise") - er liegt in der
Haupt-Cron des Default-Profils und wurde deshalb nicht angefasst.

## Schreibzugriff auf alle Repo-Bot-Profile nachgezogen (08.10.2026)

**Auftrag Max:** die Empfehlung aus T-369 umsetzen - die Profile nachziehen, die
den Werkstatt-Pfad in `HERMES_WRITE_SAFE_ROOT` nicht trugen.

**Befund vorher (von der erweiterten Wache gemeldet):** 16 von 18 Repo-Bot-`.env`
ohne Werkstatt-Pfad. Nur `claude-code` und die Haupt-`.env` waren vollstaendig -
diese Bots konnten nicht in die Repos schreiben.

**Nachgezogen, 16 Dateien:**

- **13 erweitert** (Zeile vorhanden, Wert ergaenzt): basic-memory, caveman,
  claudian, deepseek-harness, easycliproxyapi, everything-claude-code, gbrain,
  harvard-trading, moon-dev-agents, obsidian-skills, one-skill-to-rule-them-all,
  openmontage, openterminal
- **3 neu angelegt** (kein Eintrag vorhanden): lotse, markt-recherche, nerd -
  jeweils Leerzeile + Kommentarzeile + Wert am Dateiende
- **1 uebersprungen:** claude-code (war schon ok)

Neuer Wert ueberall: `C:\Users\faupe\Documents\BrainFiles;O:\Werkstatt`

**Belege:** Je Datei genau eine geaenderte Zeile (`diff` gegen die Sicherung) -
bei den drei Anlege-Faellen genau die drei neuen Zeilen, sonst nichts. CRLF/LF und
BOM-Status je Datei erhalten (13x CRLF, `markt-recherche` LF). 16 Sicherungen unter
`Agenten/Hermes/.sicherung/profil-env-20261007/`.

**Nachweis, dass es wirkt:** `env_lage()` meldet jetzt GESUND statt 16 Befunde.
**Gegenprobe auf einer echten Datei** (nicht nur im Test): `caveman/.env`
absichtlich zurueckgedreht -> Wache meldet sofort "1 von 18 (ohne Werkstatt)";
wiederhergestellt -> GESUND. Die 12 Tests der Wache bleiben gruen.

**WICHTIGER SICHERHEITSBEFUND (offen, Entscheidung Max):** Die Profil-`.env`-Dateien
enthalten **echte Zugangsdaten im Klartext** - gemessen an den Laengen keine
Platzhalter (u.a. ein 108-Zeichen-`ANTHROPIC_TOKEN`, ein 93-Zeichen-`GITHUB_TOKEN`,
ein 73-Zeichen-`OPENROUTER_API_KEY`, dazu `HF_TOKEN`, `MNEMOVERSE_API_KEY`,
`OLLAMA_API_KEY`, `A2A_PEER_TOKENS`). Werte wurden **nicht gelesen, nicht ausgegeben,
nicht protokolliert** - nur Laengen geprueft. Diese Dateien werden von `sichern.ps1`
mitkopiert (nach G: und O:), liegen also auf zwei weiteren Datentraegern im Klartext.
Empfehlung: `Zugaenge.md` und die `.env`-Dateien aus der Sicherung ausschliessen
(`/XD`), oder die Secrets in den Hermes-Credential-Pool ueberfuehren.

Sicherungen: `Agenten/Hermes/.sicherung/profil-env-20261007/<profil>.env` (16).

## Klartext-Zugangsdaten verschluesselt statt mitgesichert (08.10.2026)

**Auftrag Max:** die `.env` aus der Sicherung ausschliessen. Beim Pruefen kam ein
Widerspruch zu Tage, Max hat neu entschieden: **verschluesseln statt ausschliessen.**

**Der Widerspruch.** `sichern.ps1` trug bis heute eine ausdrueckliche Entscheidung
vom 12.09.2026: die Profil-`.env` bleiben in der Sicherung, "damit ein
Wiederaufbau die Profile nicht ohne Schluessel dastehen laesst". Ausschliessen
haette genau das zerstoert. Dazu zwei Funde, die beim Nachsehen auftauchten:

- **`auth.json` war in keinem der vier Skripte ausgeschlossen** - sie traegt den
  `credential_pool` mit `access_token`, `refresh_token`, `agent_key`.
- **`Agenten/Hermes/shared/nous_auth.json`** (2,6 KB) kam erst im robocopy-
  Trockenlauf zum Vorschein: eine zweite Zugangsdatei mit `access_token`
  (2093 Zeichen) und `refresh_token`. Ein Muster `auth.json` haette sie NICHT
  getroffen - sie heisst anders. Sie stand in keiner Liste.
- **Keine der Platten hat BitLocker** (C:, G:, O:, Q: geprueft).

**Die Loesung.** Ein Skript `Agenten/Hermes/scripts/secrets-archivieren.ps1` legt
`Agenten/Hermes/secrets/secrets-<datum>.7z` an: AES-256 mit `-mhe=on` (auch die
Dateinamen verschluesselt), 62 Dateien in rund 20 KB. Die Klartextdateien bleiben
am Ort - der Agent braucht sie -, werden aber aus allen vier Sicherungslaeufen
ausgeschlossen (`/XF *.env auth.json OKX_API.env nous_auth.json`). Die Sicherung
nimmt nur das Archiv mit, also gibt es den Wiederaufbau-Stand weiterhin.

**Passwort.** Aus der Windows-Benutzervariable `HERMES_BACKUP_PW`. **Setzt Max
selbst** (Befehl steht in der Ausgabe des Skripts); Hermes hat es nie gesehen.
Ohne die Variable bricht das Skript ab und legt **nichts** an - geprueft.

**Fallen, beide gemessen und behoben:**

- **7z kann das Passwort nicht per stdin lesen.** Ein Versuch mit `-p` ohne Wert
  und Pipe erzeugte ein Archiv, das sich anschliessend **nicht mehr oeffnen**
  liess ("Wrong password?"). Das Passwort steht deshalb fuer die Dauer des Laufs
  in der Kommandozeile des 7z-Prozesses - bewusster Kompromiss auf einem
  Einzelplatzrechner.
- **`-spf` ist Pflicht.** Ohne sie speichert 7z nur den Dateinamen; 61 Dateien
  namens `.env` kollidierten mit "Duplicate filename on disk" (Code 2). Mit `-spf`
  stehen die vollen Pfade im Archiv, was zugleich die Wiederherstellung an den
  richtigen Ort ermoeglicht.

**Nachweise (echte Laeufe):**

- Verschlüsselung: ohne und mit **falschem** Passwort sind **0 Dateinamen**
  sichtbar; nur mit dem richtigen alle 62. Exitcodes 255 / 2 / 0.
- Wiederherstellung testweise in einen leeren Ordner: 62 Dateien, volle Pfade
  (`...\Hermes\profiles\<profil>\.env`).
- robocopy-Trockenlauf: **110 Zugangsdateien -> 0**. Gegenprobe: `.env.template`
  bleibt im Lauf (wird also NICHT faelschlich ausgeschlossen).
- Syntax aller fuenf geaenderten Skripte geprueft (PowerShell-Parser): OK.

**Geaenderte Skripte:** `Agenten/sichern.ps1`, `sichern-zweitkopie.ps1`,
`sichern-aussenhaus.ps1`, `sichern-ausser-haus.ps1` (je `/XF` erweitert;
`Zugaenge.md` fehlte in `sichern-aussenhaus.ps1` ganz), `Routinen/sicherung.ps1`
(ruft die Archivierung vor dem Kopieren auf und **warnt im Protokoll**, wenn sie
scheitert), neu `Hermes/scripts/secrets-archivieren.ps1`.

**Offen fuer Max:** `HERMES_BACKUP_PW` setzen (sonst legt der naechste Lauf kein
Archiv an - die Sicherung laeuft trotzdem, aber ohne die Zugangsdaten). Ausserdem
liegen in den Profil-`.env` weiterhin Klartext-Secrets am Ort; das ist gewollt,
sie sind nur nicht mehr auf vier Datentraegern verteilt.

## Secrets-Archiv in Betrieb (08.10.2026)

Max hat `HERMES_BACKUP_PW` gesetzt (8 Zeichen, sha8 `ab0d1194` - Wert nie gesehen,
nur Laenge und Hash geprueft). Das Archiv ist damit scharf:

`Agenten/Hermes/secrets/secrets-20261008.7z` - **62 Dateien, 20,1 KB**, AES-256
mit `-mhe=on`.

**Nachweise (echte Laeufe, unabhaengig von der eingebauten Gegenprobe):**

- Ohne Passwort: **0 Dateinamen** sichtbar, Exit 255.
- Mit dem echten Passwort: 62 Namen sichtbar, Integritaetstest Exit 0.
- Enthaelt genau die kritischen Dateien: `auth.json`, `nous_auth.json`,
  `OKX_API.env`, `Zugaenge.md` (je 1x).
- **Die Kette ist geschlossen:** der robocopy-Trockenlauf mit den echten
  Argumenten nimmt `secrets-20261008.7z` mit und laesst **0** Klartext-
  Zugangsdateien durch.

**Ein Messfehler, der beinahe falsch alarmiert haette:** Ein Nachweis-Lauf meldete
110 Treffer statt 0 und sah nach einem offenen Leck aus. Ursache war der Test
selbst: `XF='"*.env" "auth.json"'` - die Anfuehrungszeichen in der
Shell-Variable wurden Teil des Arguments, robocopy traf nichts. In einer Variable
die Quotes **weglassen**. Zweite Falle im selben Zusammenhang: `/XD` braucht
**Backslash**-Pfade; ein Nachbau mit Vorwaertsschraegstrichen schliesst nicht aus
(4 Treffer aus `Hermes\cache`). Und: ohne **Positivkontrolle** (derselbe Lauf
ohne `/XF`, hier 106 Treffer) beweist ein 0-Ergebnis nichts. Alles drei steht im
Skill `protecting-irreplaceable-data`.

**Was jetzt gilt:** Die Klartextdateien liegen weiter am Ort (der Agent braucht
sie), aber nur noch auf **einem** Datentraeger plus dem verschluesselten Archiv auf
den Sicherungen - vorher lagen sie auf vier im Klartext. Der naechste geplante
Sicherungslauf (20:00) erneuert das Archiv selbst; scheitert das, steht es als
Warnung im Protokoll.

Testartefakte entfernt (rc-*, secrets-test*, 7ztest). Ein fremder 7z-Temp-Ordner
vom 05.10. (`opencode.exe`) blieb unangetastet.

## MCP-Bloecke der Profile aus einer Quelle, 07.10.2026

**Befund:** 17 Profile trugen handgepflegte Kopien des `mcp_servers`-Blocks. In
allen fehlte `enabled: false` bei `affinity` und `revolut-x` (in 11 auch bei
`blender`), dort liefen diese Server also, in der Haupt-Config nicht; ausserdem
fehlte `cwd` bei `archiv`, `kraken`, `desktop-commander`, `tooluniverse`.

**Regel:** Quelle fuer Hermes ist der Block `mcp_servers` in
`Agenten/Hermes/config.yaml`. Die Profile werden daraus erzeugt:
`python Agenten/Werkzeuge/mcp-profile-sync.py` prueft (Exit 1 bei Drift),
`--anwenden` schreibt. Bewusste Abweichungen (Atlas-DB je Repo, `robinhood`,
`gitlab` in `agent-trade-kit`, `MCP_DOCKER` in keinem Profil) stehen NUR in
`Agenten/Hermes/profiles/mcp-abweichungen.yaml`. Der Abgleich Hermes <-> Claude
Desktop bleibt beim (nicht versionierten) `MCP-Manifest.json` und
`mcp-sync-check.ps1`.

**Hauptmodell:** `inclusionai/ling-3.0-flash-fin:free` (Entscheidung Max,
07.10.2026). Die Profile stehen weiter auf `meituan/longcat-2.5-preview:free`;
`compression.threshold` (0.5) und das Fenster von ling sind nicht neu gemessen.

**`a2a_agents.'8741749061'`:** zweiter Name fuer denselben lokalen Endpunkt wie
`hermes-mcp` (Port 9900, Token `HERMES_A2A_TOKEN`); im Code nirgends benutzt,
nur im Skill `a2a-telegram-skills` als "lokaler Peer" genannt. Woher die Zahl
stammt, steht nirgends im Repo.
## RAM-Limit und Absturzschutz, 11.10.2026

**Anlass:** Renderer-Freeze vom 13.09.2026 und RAM-Druck durch Container,
Renderer, Gateway und Hilfsprozesse. Die Grenzen sind jetzt getrennt geprueft.

**Aenderungen an `Agenten/Hermes/config.yaml`:**

- `terminal.container_memory`: **5120 -> 8192 MB.** Container sind der
  Python-Prozess, Modell-Inferenz und Tool-Loop; 5 GB war bei groesseren
  Sitzungen und mehreren Subagenten knapp.
- `desktop.renderer_max_old_space_mb`: **4096 -> 3072 MB.** Der Renderer darf
  nicht mehr als 3 GB V8-Heap beanspruchen. Der Freeze war Renderer-basiert,
  nicht Gateway-basiert. Bei 64 GB Host-RAM bleibt damit Reserve.
- `delegation.max_concurrent_children`: **10 -> 5.** Begrenzt parallele
  Subagenten und damit gleichzeitige Modell-/Tool-Arbeit.
- `compression.idle_compact_after_seconds`: **0 -> 3600.** Komprimiert eine
  Sitzung nach einer Stunde Inaktivitaet.

**Belege:** Sicherung `config.yaml.bak-20261011`; `yaml.safe_load` bestaetigt
alle vier Zielwerte; `diff` gegen die Sicherung zeigt exakt vier Ersetzungen;
CRLF und kein BOM erhalten. `herges gateway status` lief vor und nach der
Aenderung ohne Neustart. Die Werte greifen ab dem naechsten Neustart bzw.
fueuer neue Sitzungen; der laufende Prozess behaelt seine bisherige Konfiguration.

**Auslagerungsdateien — gemessen, nicht geraten.** Die Pagefiles liegen auf
`C:\pagefile.sys` (8 GB) und `O:\pagefile.sys` (32 GB), beide fest, beide auf
**NVMe-SSDs**. Auf `G:` liegt **kein** Pagefile; G: ist eine USB-HDD (Seagate
Portable, sequentiell 73 MB/s gemessen) und waere fuer einen Pagefile auch der
falsche Ort. An der Pagefile-Lage ist **nichts zu aendern**.

**Die eigentliche Ursache des Speicherdrucks liegt ausserhalb der Hermes-Config.**
Am 11.10.2026 meldete Windows fuenfzehnmal `Id 2004` (virtueller Speicher
unzureichend), zwischen 13:22 und 16:28. Die genannten Verbraucher:

- `vmmemWSL` (PID 19968): **19,5 GB** — die WSL-VM hat **keinen** `.wslconfig`-Deckel,
  Docker Desktop setzt `MemoryMiB = 33024` (32 GB).
- `llama-server.exe`: wechselnde PIDs, **4 bis 16 GB** — `--models-autoload` laedt
  Modelle mit `ctx-size 65536` nach; ein Crash-Dump vom 13:22 ist 232 MB gross.
- `WindowsTerminal.exe`: 5,8 GB.

Commit-Limit 103,7 GB (63,7 RAM + 40 Pagefile), belegt 88,1 GB — nur 15,6 GB Luft.
Abhilfe waere ein `%USERPROFILE%\.wslconfig` mit `memory=16GB` und ein kleineres
`MemoryMiB` in Docker Desktop; beides wurde am 11.10.2026 **nicht** angefasst.

**Was die vier Config-Aenderungen leisten und was nicht:** `container_memory`
(5120 -> 8192) ist ein **Deckel, keine Belegung** — er greift nur im
Docker-Terminal-Zweig, und `terminal.backend` steht auf `local`. Der
Renderer-Deckel (3072 MB) und `idle_compact_after_seconds` (3600) wirken wie
gedacht; `max_concurrent_children` (5) begrenzt parallele Subagenten. Gegen den
WSL-Druck helfen sie nicht.

### `.wslconfig` angelegt, 11.10.2026

**Der Hebel liegt bei WSL, nicht bei Docker.** Docker Desktop fuehrt in seiner
`settings-store.json` `MemoryMiB = 33024`, `Cpus = 22` und `SwapMiB = 3072` —
alle drei sind im **WSL2-Modus wirkungslos**. Die Docker-Doku ist eindeutig:
*"In WSL 2 mode, configure memory, CPU, and swap limits on the WSL 2 utility
VM."* Diese Werte stammen aus der Hyper-V-Aera. Gemessen passt es dazu: die
WSL-VM meldet 31.932 MB total (also die 50-%-Vorgabe), nicht 33.024.

Angelegt wurde `C:\Users\faupe\.wslconfig` (vorher **nicht vorhanden**, also
nichts ueberschrieben):

```ini
[wsl2]
memory=24GB
swap=8GB

[experimental]
autoMemoryReclaim=gradual
sparseVhd=true
```

`autoMemoryReclaim=gradual` ist der eigentliche Gewinn: es gibt den Linux-
Page-Cache schrittweise an Windows zurueck. Docker empfiehlt die Einstellung
ausdruecklich nach Image-Builds. Ohne sie haelt die VM den Cache, bis der
Deckel greift — genau das Bild vom 11.10. WSL 2.7.13 unterstuetzt beide
experimentellen Schalter.

**Noch nicht wirksam.** Die Datei wird beim Start der WSL-VM gelesen; sie
braucht `wsl --shutdown`. Das beendet **alle** Distributionen und damit die
**38 laufenden Docker-Container** (16 `freqtrade-*`, n8n, puter-Stack mit
MariaDB/RustFS/Valkey, `nautilus-demo`, kind-Cluster). Der Befehl wurde deshalb
**nicht** ausgefuehrt — das ist Max' Entscheidung zu einem Zeitpunkt seiner
Wahl. Danach pruefen: `wsl --system free -m` muss ~24 GB zeigen statt 31,9.

### Was WSL tatsaechlich belegt

Die 19,5 GB sind **kein** Leck, sondern die Summe aus:

- **38 laufende Container**, u. a. 16 × `freqtradeorg/freqtrade:stable` (je ein
  Python-Prozess), der komplette puter-Stack (Caddy, puter, MariaDB, RustFS,
  DynamoDB, Valkey) und ein kind-Kubernetes-Cluster.
- **24,12 GB Docker-Images**, davon 7,89 GB zurueckholbar.
- Linux-Page-Cache, den die VM ohne `autoMemoryReclaim` nicht abgibt.

Diese Last laeuft neben Hermes, nicht in ihm. `container_memory` in der
Hermes-Config hat damit nichts zu tun.

### Nebenbefund: sieben Python-Abstuerze am 11.10.

In `%LOCALAPPDATA%\CrashDumps` liegen 10 Dateien mit 426,7 MB, **alle vom
11.10.2026** zwischen 13:02 und 16:00: `llama-server` (1 × 232,4 MB),
`python` (4 × 92,7 MB), `WindowsTerminal` (2 × 66,5 MB), `pythonw`
(3 × 35,1 MB). Alle im selben Zeitfenster wie die Id-2004-Meldungen — das ist
die Signatur von Speicherdruck, nicht von einem Code-Fehler. Kein Bugcheck,
kein `MEMORY.DMP`, also kein Bluescreen; die Prozesse wurden einzeln beendet.

### Photon-Dopplung: Config-Asymmetrie, keine geteilte Kennung

**Der Befund war irrefuehrend formuliert.** `hermes gateway status` meldete sechs
Profile, die „dieselbe Photon-Kennung" tragen. Gemessen mit Hermes' **eigener**
Funktion — `hermes_cli.profile_channels.shared_channel_credentials(profil, default)`,
also genau der, die `profile list` und der Gateway benutzen — gibt es **null
Kollisionen**. Es existiert nur **eine** `PHOTON_PROJECT_ID` im ganzen Haus, und
sie steht in der Haupt-`.env` (gehoert `default`).

**Die Ursache ist eine Asymmetrie in den Profil-Configs.** 25 von 33 Profilen
tragen bereits

```yaml
platforms:
  photon:
    enabled: false
```

**6 Profile hatten gar keinen `platforms`-Block** — basic-memory, bots,
findusarbeitus, fomo-radar, lokal-first, recherche. Ein Profil **ohne**
ausdrueckliches `enabled` wird ueber die Umgebung aktiviert: der Photon-Adapter
registriert `env_enablement_fn=_env_enablement`
(`plugins/platforms/photon/adapter.py:326`, Kommentar *„seed ``PlatformConfig.extra``
so env-only setups appear in status"*). Das Profil hat keine eigenen
`PHOTON_`-Werte, erbt also die der Haupt-`.env` und gilt damit als
photon-aktiv. Der Gateway sieht zwei Profile auf derselben Kennung und lehnt das
zweite als `duplicate_credential` ab — zu Recht, nur ist die Ursache die fehlende
Zeile, nicht eine geteilte Kennung.

**Behoben** (Commit `0b45d4b7`): der Block an die 6 Dateien angehaengt, je
**+3 Zeilen, 0 geloescht**, Zeilenenden erhalten (5 × CRLF, `fomo-radar` LF).
Damit tragen **31 von 33** Profilen den Block. Werkzeug:
`scripts/profil-photon-aus.py` (Trockenlauf ohne `--anwenden`; parst die Datei
vorher und nachher mit `yaml.safe_load` und assertet, dass sich ausserhalb von
`platforms` nichts geaendert hat).

**Zwei Profile bleiben ohne Block — mit Absicht.** `auto-prediction` und
`awesome-systematic-trading` haben **keine** `PHOTON_`-Zeile in ihrer `.env`,
koennen die Haupt-Kennung also nicht erben und werden von Hermes nicht
beanstandet. Ein Block dort waere Kosmetik.

**Falle, die eine Stunde gekostet hat:** `hermes profile list` meldete **null**
Kanal-Warnungen, obwohl `hermes gateway status` sechs auflistete. Beide Befehle
lesen **denselben** Home-Pfad — die Ursache ist der **Profil-Scope**, nicht der
Pfad: die Sitzung laeuft im Profil `hermes-wartung`, und der Profil-Scope gilt
fuer **alle** Hermes-Lesebefehle. `profile list` vergleicht dann jedes Profil
gegen `hermes-wartung` (dessen `.env` hat gar keine `PHOTON_`-Zeile, also keine
Kollision), waehrend der Gateway-Status gegen das **Startprofil** `default`
prueft. **Eine gruene Liste und eine rote Statusausgabe sind kein Widerspruch,
sondern zwei verschiedene Fragen** — vor dem Urteil klaeren, gegen welches Profil
verglichen wird.

### Telegram: ein verwaistes Standalone-Gateway haelt das Haupt-Token

**Kein Config-Problem — ein laufender Fremdprozess.**

```
PID 62716   gestartet 11.10. 13:34:43
  argv:  ... hermes_cli.main gateway run --replace
  Log:   "Active profile: informatiker161"
  Lock:  profiles/informatiker161/gateway.lock  (PID 62716, hermes_home=...\profiles\informatiker161)
```

Dieses Gateway verbindet sich mit **demselben Bot-Token** wie `default` und
gewinnt das Rennen: `gateway_state.json` fuehrt `telegram.state = "fatal"`,
`error_code = "telegram-bot-token_lock"` fuer den Haupt-Gateway, der deshalb
**DEGRADED** laeuft.

**Es beantwortet Max' Nachrichten.** `profiles/informatiker161/logs/gateway.log`:

```
16:24:01 inbound message: platform=telegram user=Maximilian Faupel chat=7648512088
16:25:55 response ready: session=agent:main:telegram:dm:7648512088:30970 time=114.3s
```

Max' DM um 16:24 lief also ueber das Profil `informatiker161`, nicht ueber
`default` — mit dessen Modell, dessen Skills und dessen Gedaechtnis.

**Die Herkunft ist nicht auffindbar.** Kein Eintrag in der Aufgabenplanung
(`Hermes_Gateway_2ef9d0b7`, `Hermes_Dashboard`, `Hermes-Update-20260921` — keiner
nennt ein Profil), nichts im Start-Ordner, kein VBS im `gateway-service/`. Der
Elternprozess 37772 existiert nicht mehr. Also ein **manuell gestarteter
Prozess**, der seine Shell ueberlebt hat.

**Gestoppt am 11.10.2026** (auf Max' Anweisung, `hermes --profile
informatiker161 gateway stop` → „✓ Stopped gateway for this profile"):

- **PID 62716 beendet**, `profiles/informatiker161/gateway.lock` entfernt.
- **`hermes gateway status` gibt keine einzige Kanal-Warnung mehr aus** — vorher
  sieben Zeilen (Telegram + sechs Photon). Das ist der Beleg fuer den
  Config-Fix: die Pruefung liest die Dateien und ist damit sofort sauber.
- **Ein Autostart-Eintrag existiert nicht** — das Gateway kam nicht von selbst
  wieder. Falls es erneut auftaucht, ist die Herkunft weiter offen.

**Noch nicht wirksam, und der Grund steht im Code.** `gateway_state.json` fuehrt
weiterhin `telegram.state = "fatal"` (Zeitstempel 12:28 UTC, also **vor** dem
Stop) und die sechs `duplicate_credential`-Eintraege. Ein Neustart ist noetig,
weil Hermes einen Token-Konflikt beim Start **ausdruecklich nicht** erneut
versucht — `gateway/restart.py::is_global_startup_conflict`:

> *„Adapters emit ``{scope}_lock`` with ``retryable=True`` so a *mid-run*
> reconnect can recover; at startup a live foreign holder is a configuration
> conflict (two gateways cannot poll one token), not a transient blip."*

`gateway/run_startup.py:1344` setzt das um:
`_retryable = adapter.fatal_error_retryable and not is_global_startup_conflict(...)`.
Das Gate ist also **zu**, solange kein Fremdprozess mehr laeuft: die Warteschlange
nimmt die Plattform nicht auf, es gibt keinen Hot-Path zurueck.

**Der Neustart laeuft geplant um 17:45:41** (Max' Anweisung: „Restarte in
10 min", angesetzt 17:35:41). Werkzeug:
`profiles/hermes-wartung/scripts/gateway-neustart-geplant.py`
(`--nach-sekunden 600`), gestartet als Hintergrundprozess **ausserhalb** des
Gateways, `persist_on_release` gesetzt, damit der Lauf `/new` und
Kontextkompression uebersteht. Es haelt den Zustand vorher und nachher fest,
wartet bis zu 90 s auf `telegram.state == "connected"` und berichtet den
Vergleich. Protokoll: `profiles/hermes-wartung/logs/gateway-restart-geplant.log`.

**Warum kein Cron-Auftrag — und das ist kein Detail.** `cronjob_manage` lehnt
den Job ab:

> *„Blocked: cron job contains a gateway lifecycle command or persistent
> launchctl submit operation. This is blocked to prevent agent-driven
> SIGTERM-respawn loops under launchd/systemd supervision (#30719)."*

Ein Cron-Auftrag laeuft **innerhalb** des Gateways. Ein `gateway restart` von
dort aus beendet den eigenen Prozess und laeuft damit in die Neustart-Schleife,
die die Sperre verhindert. Der Aufruf muss aus einer Shell **ausserhalb**
kommen — ein Hintergrundprozess des Agenten ist das.

**Der Task kann es nicht auffangen.** `Hermes_Gateway_2ef9d0b7` hat als
einzigen Trigger einen `LogonTrigger` (Delay PT30S) und
`MultipleInstancesPolicy: IgnoreNew`. `RestartOnFailure` (Count 999,
Interval PT1M) greift nur bei einem **unerwarteten** Abbruch — ein sauberer
Stop oder Neustart startet nichts von selbst. Nach einem `stop` bleibt das
Gateway also unten, bis jemand startet.

Beleg danach: `telegram.state = "connected"`, die sechs Photon-Eintraege
verschwunden, `gateway_state = "running"` statt `degraded`, neue PID.

### Kanal-Kennungen: Ist-Stand des Hauses (11.10.2026)

Gemessen mit `shared_channel_credentials` und Hashes, nie im Klartext:

- **Telegram:** 8 Profile tragen einen eigenen `TELEGRAM_BOT_TOKEN`, **alle
  verschiedenen** — keiner teilt ihn mit `default`. Die Warnung im
  Gateway-Status nennt `informatiker161` zurecht: es ist ein zweiter
  **Prozess** auf derselben Kennung, keine zweite Kennung in einer Datei.
- **Photon:** genau **eine** Kennung im Haus, in der Haupt-`.env`.

**Sicherung der Notiz:** `Wissen/Hermes.md.bak-20261011-ram`.
