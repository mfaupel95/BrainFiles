---
titel: Paperclip CLI (paperclipai) im Haus
aktualisiert: 2026-09-30
tags: [werkzeug, paperclip, node, windows]
---

# Paperclip CLI — was es ist und wie es hier läuft

> **Falle zuerst:** Der **verwaltete Installationsweg ist unter Windows kaputt.**
> `npx paperclipai install` bricht mit `ENOENT: no such file or directory,
> open 'C:\Users\faupe\.paperclip\cli\.install.lock.44332:1790795452679:81c3df72cb1ed8.tmp'`
> ab — der Sperr-Dateiname enthält **Doppelpunkte** (Unix erlaubt das, Windows
> nicht). Deshalb liegt die CLI hier als **npm-Installation in einem eigenen
> Prefix**, nicht im Store `~/.paperclip/cli`. Damit gibt es **kein
> `paperclipai update` und kein `paperclipai uninstall`** — aktualisiert wird
> über npm.

`paperclipai` ist die CLI zu Paperclip (npm-Paket `paperclipai`, Node-Programm,
`engines.node >= 24.11.0`). Sie ist ein Einzelbefehl mit Unterbefehlen für
Onboarding, Diagnose, Konfiguration, Dienste und die Arbeit gegen eine
Paperclip-Instanz (company, issue, agent, project, goal, token, board,
approval, activity, cost, finance, budget, org, workspace, environment …).

- Version hier: **2026.916.1** (Kanal `stable`)
- Node: `v26.7.0` aus dem Hermes-Baum (`Agenten/Hermes/tools/node-26.7.0-win32-x64`)
- Programm: `C:\Users\faupe\.local\npm\node_modules\paperclipai\dist\index.js`
- Aufruf: `paperclipai <befehl>` — aus PowerShell, cmd und bash

## Wie es hier installiert ist

```bash
# eigener Prefix, damit nichts in den Hermes-Baum oder nach %APPDATA% wandert
npm install -g --prefix "C:/Users/faupe/.local/npm" paperclipai@2026.916.1
```

npm legt die Shims direkt in den Prefix: `paperclipai.cmd` (Windows),
`paperclipai.ps1`, `paperclipai` (sh). Damit der Name **im PATH** liegt, steht
`C:\Users\faupe\.local\npm` in der Windows-Benutzer-PATH (angehängt am
01.10.2026, per `[Environment]::SetEnvironmentVariable(...,'User')` — **nicht**
`setx`, das schneidet bei 1024 Zeichen ab).

> **Keine Weiterleitung in `~/.local/bin` anlegen.** Der erste Versuch legte dort
> `paperclipai.cmd` und `paperclipai` ab — und **blockierte damit `paperclipai run`**:
> `doctor` meldete `Managed install manifest: Managed install artifacts exist but
> C:\Users\faupe\.paperclip\cli\install.json is missing` und der Start brach ab
> („Doctor found blocking issues. Not starting server."). Ursache im Code:
> `hasManagedArtifacts()` prüft die Existenz von `install.json`, `.managed-install`,
> `current` **und dem Shim-Pfad `~/.local/bin/paperclipai`** — der selbstgebaute
> Shim sieht für die CLI wie eine halbe verwaltete Installation aus. Shim gelöscht,
> PATH umgestellt → `doctor`: 11 passed, 1 warning.

Nachweis: `paperclipai --version` → `2026.916.1` aus PowerShell, cmd und bash.

**Aktualisieren:**

```bash
npm install -g --prefix "C:/Users/faupe/.local/npm" paperclipai@latest
paperclipai --version
```

`paperclipai channels` nennt alle vier Kanäle und welchen diese Installation
folgt (Stand 30.09.2026: stable 2026.916.1, beta 2026.921.0-beta.1,
nightly 2026.930.0-nightly.0, canary 2026.930.0-canary.9).

## Was der verwaltete Weg gekonnt hätte (und warum er hier ausfällt)

`paperclipai install` sollte nach `~/.paperclip/cli/installs/<version>`
entpacken, `~/.paperclip/cli/current` darauf zeigen lassen, einen Eintrag in
`install.json` schreiben und einen Shim nach `~/.local/bin` legen — mit
Ein-Befehl-Update, Rollback und Hintergrunddienst. Er scheitert an der
Sperrdatei (`withInstallStoreLock` → `token = pid:Date.now():zufall` →
Dateiname mit Doppelpunkten). Gemessen: derselbe `writeFileSync` mit und ohne
Doppelpunkt im Namen — ohne geht, mit kommt `ENOENT`. Der Store ist zusätzlich
Unix-geprägt (`~/.local/bin`, `~/.bashrc`/`~/.zshrc`, Symlink `current`), ein
Fix müsste also mehr als den Dateinamen anfassen.

Offen: ob Paperclip Windows überhaupt unterstützt. Im npm-Paket steht **kein**
`os`-Feld (also nicht auf Linux/macOS eingeschränkt), und die eingebettete
PostgreSQL liegt auch als `@embedded-postgres/windows-x64` vor — es ist also
gemeint, nur nicht durchgemessen.

## Zwei npm-Eigenheiten, die hier aufgefallen sind

- npm 11.19 führt `postinstall`-Skripte **nicht** ohne Freigabe aus. Gemeldet
  wurden `@embedded-postgres/windows-x64` (`hydrate-symlinks.js`) und `ssh2`.
  **Geprüft und harmlos:** die `pg-symlinks.json` des Windows-Pakets ist leer
  (`[]`), das Skript hätte nichts getan; `ssh2` läuft ohne seine optionale
  Native-Erweiterung.
- `du -sh` über `~/.local/npm` (382 Pakete) läuft in MSYS minutenlang — die
  Größe lieber mit PowerShell messen.

## Erste Instanz (01.10.2026)

```bash
paperclipai onboard --yes --no-install-service   # Config + .env + Schluessel, dann Startversuch
paperclipai run                                  # Doctor + Server
```

Stand danach, gemessen:

| Was | Wert |
|---|---|
| Dashboard | `http://127.0.0.1:3100` (HTTP 200) |
| Instanz-PID | 80788 (`paperclipai run`, Kind der Hermes-Sitzung) |
| Datenbank | eingebettete PostgreSQL, `127.0.0.1:54329`, 19 Prozesse |
| Migrationen | 278 beim ersten Start |
| Daten | `~/.paperclip/instances/default/` (config.json, .env, db, secrets, logs, data) |
| Sicherung | automatisch, stündlich, 30 Tage Aufbewahrung |

**Der erste Start dauert rund drei Minuten** (initdb + 278 Migrationen) und sieht
dabei wie ein Hänger aus: nach `◇ Starting Paperclip server...` kommt lange
nichts. Fortschritt ist am Datenordner zu sehen (`db/PG_VERSION`, `db/pg_wal`),
nicht am Log. Erst danach `Server startup recovery complete on 127.0.0.1:3100`.

**Kein Hintergrunddienst unter Windows:** `doctor` sagt
`Background service: Service management is not supported on win32. Use paperclipai run instead.`
Es gibt also keinen Autostart und kein `service install` — nach einem Neustart
läuft der Server erst wieder, wenn `paperclipai run` erneut gestartet wird.

## Umgebungstest: „The environment test failed" (01.10.2026)

Symptom beim Anlegen des ersten Agenten (Adapter `claude_local`, Verbindung „My Claude
subscription"): `error · Claude hello probe failed. Exit code 1.` und
`error · The selected account has not completed a provider hello test.` Im Serverlog:

```
[paperclip] Claude ACP login probe did not complete { classification: 'nonzero_exit', exitCode: 1 }
[paperclip] Claude CLI hello probe failed { classification: 'nonzero_exit', exitCode: 1 }
```

**Ursache: eine `.env` im ARBEITSVERZEICHNIS des Servers.** `C:\Users\faupe\.env` trägt
`ANTHROPIC_API_KEY` (Max' Console-Schlüssel ohne Guthaben). Wird `paperclipai run` aus dem
Home gestartet, lädt der Server diese Datei in seine Prozessumgebung; jede Sonde und jeder
Agent erbt sie (`runChildProcess` mischt `sanitizeInheritedPaperclipEnv(process.env)`), und
Claude Code nimmt dann API-Key-Auth statt des Abo-Tokens → 401 → Exit 1. Die Sonde sagt es
selbst: `warn · claude_anthropic_api_key_overrides_subscription: ANTHROPIC_API_KEY is set`.
Ein `unset` vor dem Start hilft NICHT — die Datei wird beim Start neu geladen.

**Behoben:** Server aus `C:\Users\faupe\.paperclip` starten (dort liegt keine `.env`).
Danach `status: pass`, `claude_hello_probe_passed: Claude hello probe succeeded.`

Gegenprobe (dieselbe Sonde über die API, siehe unten):

| Arbeitsverzeichnis des Servers | Umgebung | Ergebnis |
|---|---|---|
| `C:\Users\faupe` | Abo-Token gesetzt | **fail** — `ANTHROPIC_API_KEY is set` + Exit 1 |
| `C:\Users\faupe\.paperclip` | Abo-Token gesetzt | **pass** |
| `C:\Users\faupe\.paperclip` | nur `ANTHROPIC_API_KEY` = Token | warn — Probe läuft in den Timeout |

**Zwei Dinge, die auf dem Weg geprüft wurden und NICHT die Ursache waren** (damit sie
niemand erneut sucht): das npm-Shim `claude.CMD` (Node kann `.CMD` ohne `shell:true` nicht
starten — `EINVAL` —, aber der Server loggte `exitCode: 1`, also lief das Kind; die Auflösung
traf ohnehin `claude.EXE`, weil `~/.local/bin` in der PATH vor `AppData\Roaming\npm` steht
und `.EXE` vor `.CMD` probiert wird) und alle Arg-Varianten (`--setting-sources user`,
`--model`, leerer stdin, das Minimal-Env der Sonde) — jede einzeln grün.

**Nebenbei installiert:** `claude install stable` legt
`C:\Users\faupe\.local\bin\claude.exe` ab (243 MB, 2.1.285) — die native Fassung statt des
npm-Shims. Unabhängig von der Ursache sinnvoll (Paperclips Auflösung und die `.CMD`-Falle).

**Werkzeug:** `Agenten/Routinen/paperclip-start.ps1` — startet nur, wenn Port 3100 frei ist,
im Arbeitsverzeichnis `%USERPROFILE%\.paperclip`, entfernt `ANTHROPIC_*` aus der eigenen
Umgebung, Log in `Agenten/Routinen/logs/paperclip-*.log`. Aufruf:
`powershell -File Agenten/Routinen/paperclip-start.ps1`. Kein Autostart: unter Windows gibt
es keinen Paperclip-Dienst (`Service management is not supported on win32`).

**Die Sonde ohne UI fahren** (spart den Weg über den Browser): im Modus `local_trusted`
nimmt der Server Anfragen von der Schleife ohne Anmeldung an.

```bash
curl -s -X POST "http://127.0.0.1:3100/api/companies/<companyId>/adapters/claude_local/test-environment" \
  -H "content-type: application/json" \
  -d '{"adapterConfig":{"command":"claude"},"environmentId":"<envId>","aiConnection":{"provider":"anthropic","method":"subscription","mode":"responsible_user"}}'
```

Company-ID und Environment-ID stehen in der eingebetteten Datenbank
(`postgres://paperclip:paperclip@127.0.0.1:54329/paperclip`, Tabellen `ai_connection_defaults`
und `environments`). Blockiert wird nur bei `status: fail` oder der Prüfung
`adapter_auth_missing` (UI-Regel `sH`); eine Antwort „Hallo!" statt „hello" ist eine Warnung.

## Was hier noch offen ist

- **Keine Identität der CLI.** Der Server läuft und der Umgebungstest ist grün, aber die CLI
  hat keine Board-Anmeldung. Weg: Dashboard im Browser (Konto anlegen, Sign-up ist erlaubt)
  oder `paperclipai connect --persona board`; `token board create` verlangt vorher eine
  bestehende Board-Sitzung.
- **Kein LLM-Provider** eingetragen (`LLM provider: No LLM provider configured`). Ohne Modell
  können Paperclip-Agenten nicht arbeiten — im Haus wären OmniRoute (127.0.0.1:20128) oder
  Ollama die Wege.
- **Kein Autostart.** Der Start-Wrapper existiert, eine geplante Aufgabe (Hausmuster) fehlt.
- **`.env` im Home ist eine Falle** für jedes Werkzeug, das dort gestartert wird — sie enthält
  Schlüssel und überschreibt nichts ahnende Prozesse. Absichtlich nicht angefasst.

## Funktionstest 06.10.2026 (T-253/T-254)

Durchlauf im Trockenmodus (keine echten Orders, keine Live-Aktionen):

| Schritt | Ergebnis |
|---|---|
| `paperclipai --version` | `2026.916.1` |
| `paperclipai doctor` | 10 passed, 2 warnings (Port 3100 belegt, key file permissions 666) |
| Server-Start (`paperclipai run` aus `~/.paperclip`) | HTTP 200 nach ~3 Minuten |
| `GET /api/companies` | 1 Company (`maks.sound`, `9a5aa980-...`) |
| `GET /api/companies/.../environments` | 1 Environment (`Local`, `131b9d1a-...`) |
| `POST .../adapters/claude_local/test-environment` | `status: fail` — `claude_hello_probe_auth_required` |

**Einziger offener Punkt:** Der Claude-ACP-Server ist vorhanden und konfiguriert
(`claude_oauth_token_configured`, `claude_acp_command_resolvable`), aber es fehlt eine
Claude-Login-Sitzung auf dem Host. Das ist keine Paperclip-Fehler, sondern eine
Umgebungsvoraussetzung — `claude login` im Terminal wäre der nächste Schritt.

**Nicht getestet (erfordert Max' Entscheidung):**
- Board-Anmeldung der CLI (`paperclipai connect --persona board`)
- LLM-Provider-Eintrag (OmniRoute oder Ollama)
- Autostart (geplante Aufgabe für den Wrapper)

## Aufrufbeispiele

```bash
paperclipai --version            # 2026.916.1
paperclipai channels             # Kanäle und dieser Stand
paperclipai --help               # 50+ Unterbefehle
paperclipai doctor               # Diagnose (ohne Instanz: meldet fehlende Config)
```