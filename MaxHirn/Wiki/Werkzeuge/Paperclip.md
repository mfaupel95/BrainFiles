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
`paperclipai.ps1`, `paperclipai` (sh). Damit der Name **im PATH** liegt, gibt es
zwei Weiterleitungen in `C:\Users\faupe\.local\bin` (dieser Ordner steht in der
Windows-Benutzer-PATH — geprüft):

| Datei | Für |
|---|---|
| `~/.local/bin/paperclipai.cmd` | PowerShell, cmd (CRLF!) |
| `~/.local/bin/paperclipai` | bash/MSYS |

Sie rufen nur `C:\Users\faupe\.local\npm\paperclipai.cmd` auf und reichen die
Argumente durch. Nachweis: `paperclipai --version` → `2026.916.1` aus allen drei
Shells.

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

## Was hier noch NICHT passiert ist

Die CLI ist installiert, es läuft aber **keine Instanz**. Der nächste Schritt
wäre `paperclipai onboard --yes` (schreibt die Konfiguration, legt die
eingebettete PostgreSQL an) und `paperclipai run` (startet den Server), danach
`paperclipai connect` für die Anmeldung als Board. Der Server hält einen Port,
die eingebettete Datenbank lädt Binärdateien nach, und Onboarding kann einen
Hintergrunddienst einrichten — deshalb nicht ungefragt gestartet.

## Aufrufbeispiele

```bash
paperclipai --version            # 2026.916.1
paperclipai channels             # Kanäle und dieser Stand
paperclipai --help               # 50+ Unterbefehle
paperclipai doctor               # Diagnose (ohne Instanz: meldet fehlende Config)
```