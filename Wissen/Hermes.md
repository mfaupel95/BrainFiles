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

- **82 mitgelieferte** Skills unter `Hermes/skills/`
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
- **Stolperstein während der Installation:** In der Claude-Sitzung zeigen
  `$env:TEMP`/`$env:TMP` auf `C:\WINDOWS\TEMP`, wo diese Sitzung keinen
  Schreibzugriff hat — das ließ den `Add-Type`-C#-Compiler des Installers
  scheitern (Junction-Erstellung nutzt ein P/Invoke-Hilfsmodul). Für den
  Install-Lauf `TEMP`/`TMP` einmalig auf `C:\Hermes\cua-driver\tmp`
  umgebogen, kein Eingriff an der dauerhaften Benutzerkonfiguration.
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

## Verwandt

[[Verbindungen]] · [[Projekte]] · [[Portabilitaet]] · [[../AGENTS.md|AGENTS.md]]
