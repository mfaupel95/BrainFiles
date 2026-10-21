---
id: 20260921-docker-und-sandbox
title: 'Betrieb — Docker und Sandbox'
tags: [betrieb, docker]
created: 2026-09-21
updated: 2026-10-21
related: ['[[Lektionen/Windows-Umgebung]]', '[[Betrieb/Hermes]]']
summary: 'Der Docker-Terminal-Backend als Sandbox, seine Grenzen, und windows-mcp als Rueckfallweg fuer Host-Arbeit.'
---

# Docker und Sandbox

## Aufbau

- `terminal`, `execute_code`, `read_file`, `search_files`, `patch` laufen in einem
  **Docker-Container** auf dem Host (Container z. B. `hermes-098f5c80`).
- **Ist Docker Desktop down, scheitern ALLE** mit „Docker daemon is not responding",
  „Terminal environment unavailable" oder „could not stat".
- Nach einem Docker-Neustart ist das Terminal wieder die Linux-Sandbox (`pwd=/root`,
  kein `/c`-Mount) — Host-Pfade sind dann nicht erreichbar.
- Der hauseigene CLI-Backend (`terminal.backend: local`) laeuft unveraendert lokal.

## Rueckfallweg

Ist der Dockerweg blockiert, **Host-Arbeit ueber windows-mcp PowerShell** fahren
(MCP-Server laeuft am Host, unabhaengig vom Sandbox-Container). Ebenso fuer:

- Massenlaeufe (Repos vorspulen, Dateien zaehlen) — im Sandbox-Terminal brachen sie bei
  Speicherdruck mit `WinError 1455` ab.
- Alles, was echte Windows-Dienste, Aufgabenplanung, Registry oder Laufwerke betrifft.

## Weitergeleitete Variablen

`terminal.docker_forward_env` in `Agenten/Hermes/config.yaml` listet 43 Variablen (alle
Schluesselnamen der Hermes-`.env` plus `OLLAMA_MODELS`, `HANDEL_RISIKO`, `HERMES_HOME`).
Geheimnisse stehen NICHT in der Config — der Sandbox-Container loest sie aus der Shell-Env
bzw. der `.env` auf.

**Nachweis im Container:** `env | grep -E 'OLLAMA|HANDEL|OMNIROUTE'`.
Setzen per `hermes config set terminal.docker_forward_env [...]` — mit den bekannten
`config set`-Fallen (siehe [[Betrieb/Hermes]]).

## Container mit Daueraufgaben

- `nautilus-demo` — OKX-Demo-Quoten-Node, `--restart unless-stopped`, Dummy-Env
  (die OKX-Factory verlangt die Variablen hart; echte Schluessel verlassen den Rechner nie).
- `ollama/ollama` auf `127.0.0.1:11437` (zweite Instanz neben dem Host-Ollama auf 11434).

GUI-Fenster-Automation ist fragil, wenn Max parallel am PC arbeitet (Fokus, virtuelle
Desktops, 150 % DPI) — Docker ist die robuste Startmethode.
## Entscheidung: `local` bleibt, Docker ist eingerichtet aber inaktiv (08.10.2026)

Anlass: `terminal.backend` stand auf `docker`, das Terminal fiel mit Exit 125 aus.
Frage von Max: „vor- und nachteile? erfahrungsgemaess eher probleme, da docker oft
nicht erreichbar." Darauf die Messung, nicht die Erinnerung.

### Was gemessen ist

| Groesse | Wert |
|---|---|
| Docker-Abstuerze in 30 Tagen (Application Error, „docker") | **10 - alle am 30.09.2026** |
| An den uebrigen 29 Tagen | **0** |
| Cron `docker-wache`: Laeufe / davon still (gesund) | 565 / **49 von 50 Ausgaben still** |
| Letzte Heilung durch die Wache | 07.10.2026, 23:25 (39 min vor der Messung) |

Die Erfahrung „Docker ist oft nicht erreichbar" trifft also EINEN Tag, nicht einen
Dauerzustand - und dieser Tag (30.09.) war der Commit-Erschoepfungs-Tag mit 31
App-Abstuerzen insgesamt. Der Eindruck entsteht, weil ein Docker-Ausfall immer das
**Terminal** mitnimmt, also die Arbeit sofort trifft.

### Der Ausschlussgrund gegen Docker in DIESEM Baum

BrainFiles traegt Windows-Programme und Windows-Pfade:

    Agenten/Handel/scanner/.venv/Scripts/python.exe
      -> PE32+ executable for MS Windows, x86-64

Fuenf Spur-venvs sind Windows-EXEs, `Routinen/handel-tests.ps1` sucht
`.venv\Scripts\python.exe`, und es gibt **62 PowerShell-Routinen**. Im
Linux-Container laeuft davon **keine**. Der Docker-Backend kann in diesem Repo
deshalb nur einen Teil der Arbeit tragen - und die Handel-Seite, das groesste
Stueck, gar nicht.

### Zwei Ausfallarten, die die Wache NICHT sieht

1. **`docker info` kann gesund sein, waehrend `docker run` scheitert.** Genau der
   Fall vom 06.10.: der Metadaten-Store war `read-only file system`
   (`write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db`),
   der Daemon antwortete aber. Die 25-s-Pruefung der Wache haette das durchgelassen.
2. **Architektur-Falle:** `nousresearch/hermes-sandbox:desktop` startet hier nicht
   (`exec /usr/bin/sleep: exec format error`, Exit 255). Fuer Mount-Gegenproben ein
   passendes Image nehmen (`nikolaik/python-nodejs:python3.11-nodejs20`).

### Die Entscheidung

**`local` bleibt.** Nicht weil Docker schlecht ist, sondern weil dieser Baum
Windows-Binaries, Windows-Pfade und PowerShell-Routinen fuehrt, die Docker nicht
ausfuehren kann. Fuer ein reines Python-Projekt auf einer Maschine, die man nicht
anfassen will, waere Docker die richtige Wahl.

**Die Kosten von `local` sind kleiner als sie klingen:** Das Risiko ist nicht
„Agent loescht alles", sondern derselbe Nutzer ohne Rueckfrage bei destruktiven
Kommandos. Dagegen wirkt die Sicherung billiger als ein Container: `.git` ist da,
die drei Kopien laufen, und [[Wissen/Schutzregeln]] greift unabhaengig vom Backend.

**Der Docker-Pfad bleibt vollstaendig eingerichtet und belegt** - Umschalten ist
jederzeit moeglich:

- `terminal.docker_mount_cwd_to_workspace: true` (Commit `16e7fddf`-Umfeld)
- `terminal.docker_volumes: ['C:\Users\faupe\Documents\BrainFiles:/brainfiles']`
  (Commit `16e7fddf`) - Beleg: `docker exec <c> ls /brainfiles` zeigt `MaxHirn`,
  `Agenten`, `Werkstatt`, `Modelle`, `.git` und ist beschreibbar (Commit `0c15bbcf`)
- Wache `docker-wache` (Cron `a41ae0df5b47`, 15 min) heilt weiter, unabhaengig vom
  aktiven Backend

## Falle: Compose-Projekt verschoben, Container zeigen auf den alten Pfad (21.10.2026)

**Befund puter:** `Werkstatt\Repos\puter` wurde am 14.10.2026 nach `Werkstatt\puter` verschoben, die
laufenden Container (Projekt `puter-selfhosted`) behielten aber ihre **Bind-Mounts auf den alten Pfad**
(`docker inspect` zeigt `Source` und das Label `com.docker.compose.project.working_dir`). Nach dem
Docker-Neustart am 20.10. 21:53 legte Docker die fehlenden Quellordner **leer und mit Docker-Rechten
neu an**: `Repos\puter\puter-selfhosted\puter\data\...` mit einer **frischen** MariaDB (161 MB, wird
seither beschrieben), waehrend die **echten Daten** (MariaDB 177 MB, Stand 14.10. 00:28) unberuehrt in
`Werkstatt\puter\...\data` liegen. `puter` (User `node`) und `puter-s3` (User `rustfs`) scheiterten
mit `mkdir volatile/runtime` bzw. `Permission denied (os error 13)` (Exit 1, 21.10. 21:16);
MariaDB, Valkey und Dynamo laufen dagegen scheinbar gesund - auf der falschen, leeren Datenbank.

**Merksatz:** Ein verschobenes Compose-Projekt erst **neu erzeugen**, nicht nur den Ordner schieben.
Nach jedem Umzug `docker inspect --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' <container>`
gegen den neuen Pfad halten. Ein Container, der "laeuft", beweist nicht, dass er die richtigen Daten
sieht - der Alt-Pfad taucht als **neuer leerer Ordner** auf. Reparatur (Entscheidung Max):
`docker compose` im neuen Ordner `down`, dann `up -d`, danach den leeren Alt-Baum pruefen und
verwerfen. **Ausgefuehrt 21.10.2026 ~23:10 (Max: "in Puter ist nichts Neues"):** Rueckfallkopie der echten
Daten (323 Dateien, 177 MB) nach `$CLAUDE_JOB_DIR\tmp\puter-data-vor-umstellung-20261021`, dann im Ordner
`Werkstatt\puter\puter-selfhosted` `docker compose down` und `docker compose up -d dynamo mariadb valkey s3 puter`
(bewusst nur die fuenf bisherigen Dienste; `caddy`, `smtp` und das Profil `ai` laufen nicht und waren auch
vorher nicht da). Ergebnis: alle fuenf `healthy`, Mount-Quellen unter `Werkstatt\puter\...`, `PuterServer has
fully booted`. **Falle dabei:** `up` zog `ghcr.io/heyputer/puter:main` und `amazon/aws-cli` neu, und die Log-Zeile
des Puter-Containers gibt das Admin-Passwort im Klartext aus (`password for admin is ...`, solange es nicht
geaendert wurde) - **Container-Logs von `puter` nie in Berichte oder Notizen kopieren**, das Passwort in Puter aendern.
Der Host-Port ist ohne `caddy` nicht veroeffentlicht (`docker port puter` leer); der Alt-Baum
`Werkstatt\Repos\puter` (leere Neuanlage, 161 MB frische MariaDB) ist jetzt unbenutzt und noch nicht geloescht.
Container-Namen der Gruppe: `puter`, `puter-s3`, `puter-mariadb`, `puter-valkey`,
`puter-dynamo` (plus `puter-caddy`, `puter-smtp`, `puter-ollama` laut Compose-Datei).

Verwandt: [[Betrieb/Wachen-und-Aufgaben]], [[Betrieb/Hermes]], [[Wissen/Schutzregeln]], [[Betrieb/Sicherung-und-Laufwerke]].
