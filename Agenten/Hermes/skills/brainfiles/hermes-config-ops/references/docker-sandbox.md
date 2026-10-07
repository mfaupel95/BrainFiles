# Docker-Sandbox: Variablen hineinreichen, cwd, und was im Container sichtbar ist

Trigger: Tools laufen im Docker-Terminal-Backend (Desktop/GUI) und sehen
Variablen nicht — `${env:NAME}` bleibt leer, Ollama findet keine Modelle,
Werkzeuge laufen ohne Key. Der Sandbox-Container erbt die Host- oder
Profil-Umgebung **nicht von selbst**.

Zwei Schluessel unter `terminal:` legen fest, was hineinkommt:

- `terminal.docker_forward_env` — Liste von Variablen**Namen**. Hermes loest
deren Werte beim Ausfuehren aus der Shell-Umgebung, dann aus der Profil-`.env`
auf und injectet sie in den Container. Die echten Geheimnisse stehen **nie** in
der Config, nur die Namen — fuer Tokens/Keys ist das immer die richtige Wahl.
- `terminal.docker_env` — Literale `KEY: value`-Paare direkt in der Config.
Fuer statische Schalter (DEBUG, PYTHONUNBUFFERED), nicht fuer Geheimnisse.

Setzen und belegen:

    hermes config set terminal.docker_forward_env '["A","B"]'
    hermes config get terminal.docker_forward_env   # Block-Liste, kein String

`hermes config set` speichert den JSON/YAML-Wert als echte Liste (dieselbe
strukturierte Parsung wie bei `fallback_providers`) — kein Handedit, keine
eigenen Listenzeilen in der Datei.

Fallen:

- **Der Container erbt nur, was im Prozess steht, der Hermes startet.**
  Windows-Benutzervariablen (HKCU, z. B. `OLLAMA_MODELS`, `HANDEL_RISIKO`)
  findet `docker_forward_env` nur, wenn der Desktop/Gateway sie in seiner
  Umgebung hat (HKCU erben sie beim Start). Stehen sie nur in einer
  bash-Session, fehlen sie dem Container. Namen in die Forward-Liste
  aufnehmen; die Werte kommen aus HKCU.
- **Backend-Konfig gilt fuer alle Oberflaechen gleichzeitig.** Die CLI kann
  `terminal.backend: local` laufen, waehrend Desktop/GUI den Docker-Backend
  nutzt — `docker_forward_env` wirkt nur auf den Docker-Zweig, unabhaengig
  vom gerade aktiven Backend. „Im Docker verfuegbar" heisst: den Docker-Zweig
  der `terminal:`-Sektion konfigurieren, den aktiven Backend nicht umstellen.
- **Nachweis nur aus einer Docker-Sitzung.** Aus einer Host-`local`-Sitzung
  (git-bash) ist kein docker-exec-Nachweis moeglich; den Live-Check
  (`env | grep -E 'NAME'`) als Schritt dem Container-User ueberlassen.
  Config-seitig belegt: `hermes config get` + die Datei lesen.

## Jedes Kommando bricht mit Exit 125 ab: `-w` bekommt einen Host-Pfad

Trigger: **jeder** `terminal`-Aufruf scheitert mit
`subprocess.CalledProcessError ... returned non-zero exit status 125`, samt
einem langen `docker run`-argv im Traceback — waehrend Docker selbst laeuft
(`docker ps` antwortet). Der Fehler kommt aus dem Backend, nicht aus dem
Kommando, das man abgeschickt hat.

Ursache: `terminal.cwd` traegt einen **Windows-Host-Pfad**. Bei
`terminal.docker_mount_cwd_to_workspace: false` reicht
`terminal_tool._resolve_config_cwd` den Wert unveraendert weiter (Zweig
`elif env_type == "docker" and _is_windows_drive_path(cwd): ... cwd =
candidate`), und `docker run -w <hostpfad>` lehnt ab:

    docker: Error response from daemon: the working directory
    'C:\Users\...\Agenten\Hermes' is invalid, it needs to be an absolute path

`-w` erwartet einen Pfad **im Container**. Der Container entsteht nie, es gibt
keine Fehlermeldung im Kommando selbst und kein Log — nur den Traceback.

**Ein Mount macht den Host-Pfad nicht gueltig.** `-w <hostpfad>` scheitert
auch dann mit 125, wenn derselbe Pfad als `-v <hostpfad>:<ziel>` gebunden ist —
`-w` zeigt in den Container, nicht auf den Host. Und ein laufender
Sandbox-Container heilt es nicht dauerhaft: nach Ablauf wird neu gebaut, und
der Fehler faellt wieder an.

Beleg ohne Codeaenderung, direkt auf dem Host (Exitcode ist die Messung):

    docker run -d --name probe -w /workspace nousresearch/hermes-sandbox:desktop sleep infinity          # EXIT=0
    docker run -d --name probe -w 'C:\Users\...\Agenten\Hermes' nousresearch/hermes-sandbox:desktop sleep infinity   # EXIT=125
    docker rm -f probe

Der Umschreibpfad auf `/workspace` liegt **in derselben Funktion daneben**:
`if env_type == "docker" and mount_docker_cwd:` setzt `host_cwd = candidate;
cwd = "/workspace"`. Mit `true` bekommt `-w` also einen Container-Pfad, und das
Backend bindet den Host-Ordner selbst (`_mount_args`, `windows_cwd`). Die
Abhilfe ist damit `terminal.docker_mount_cwd_to_workspace: true` — und wie jede
Config-Aenderung gilt sie erst mit einem Lauf als belegt (SKILL.md Regel 8):

    hermes config get terminal.docker_mount_cwd_to_workspace   # verdrahtet
    <naechster terminal-Aufruf kehrt zurueck>                  # belegt

Weitere Fallen an derselben Stelle:

- **Den Windows-Pfad NICHT „reparieren".** Er steht so in der versionierten
  `config.yaml` und in der Historie unveraendert; er wird erst im Backend
  aufgeloest. Wer den `cwd`-Wert umschreibt, aendert das Arbeitsverzeichnis
  jeder Sitzung statt des Backends.
- **Die Schreibweise ist nicht die Ursache.** `documents` vs. `Documents`
  scheitert **beides** mit 125 — die Gross-/Kleinschreibung nicht als
  Erklaerung heranziehen, sonst sucht man an der falschen Stelle.
- **Der eigene Container kann ein voellig anderer sein.** `hermes`,
  `hermes-dashboard` und die Handels-Container sind Haus-Container mit eigenen
  Mounts (z. B. nur `/opt/data`) — darin existiert kein `/workspace` und damit
  kein Zeuge fuer den Sandbox-Container. Zustaendig ist allein
  `docker ps -a --filter label=hermes-agent=1`.
- **Fehlt der Container ganz, faellt der Fehler bei JEDEM Aufruf an.** Ist die
  gefilterte Liste leer, wird pro Kommando neu gebaut — dann ist die 125 kein
  einmaliger Startfehler, sondern der Dauerzustand.
- **`docker ps` und `docker run` haben verschiedene Voraussetzungen.** Dass
  `docker ps` antwortet, beweist nur den laufenden Daemon; die 125 kommt vom
  Daemon selbst und hat mit Erreichbarkeit nichts zu tun.
- **Der Container wird WIEDERVERWENDET — deshalb bleibt es lange unauffaellig.**
  `persist_across_processes` + `container_persistent: true` + ein Idle-Reaper
  (`terminal.lifetime_seconds`, Vorgabe 300 s): solange ein Sandbox-Container
  laeuft, gehen alle Kommandos durch, obwohl die Konfiguration falsch ist. Erst
  nach dem Reaper oder einem Docker-Neustart bricht **jedes** Kommando auf.
  Nie „laeuft doch" als Entwarnung nehmen — der Dauerzustand ist schon da und
  wartet nur.
- **Auch die Dateiwerkzeuge fallen mit.** `read_file`, `write_file` und `patch`
  gehen durch denselben Sandbox-Container; scheitern sie mit demselben
  Traceback, ist die **ganze** Werkzeugkette betroffen, nicht nur das Terminal.
  Dann alles ueber `mcp__windows_mcp__PowerShell` auf dem Host fahren —
  Dateien schreiben, lesen, pruefen, committen — bis die Config neu geladen ist.
- **Kein Live-Schalter: die Zeile wirkt erst nach dem Neuladen.** Der laufende
  Hermes-Prozess (Gateway/Desktop) haelt die alte Config. **Der Gateway-Launcher
  als geplante Aufgabe startet einen LEBENDEN Gateway nicht neu** — ein Aufruf
  wie `schtasks /run` kehrt mit Ergebnis 0 zurueck, waehrend dieselbe PID
  weiterlaeuft. Erst ein Neustart der Oberflaeche (oder ein Prozess, der die
  Config neu liest) bringt sie zur Wirkung. Also: Aenderung verdrahtet melden,
  Wirkung als offenen Beleg stehen lassen — nicht als Erfolg. **Ein Probelauf
  VOR dem Neustart scheitert weiter und sieht wie ein misslungener Fix aus.**
- **Aendern NIE per `hermes config set`.** Es schneidet den Kommentar-Schwanz
  der `config.yaml` ab und schreibt die Datei mit LF, obwohl sie CRLF fuehrt.
  Byte-genau ersetzen und danach drei Gegenproben: `Compare-Object`
  Sicherung <-> Datei = **ein** Zeilenpaar, `yaml.safe_load` parst (Schluessel-
  zahl des Blocks unveraendert), CRLF-Zaehler vor == nach. Vorher eine
  `.bak-JJJJMMTT` nach `.sicherung/`.

### Die Gegenprobe muss den HERMES-Aufruf nachbauen, nicht einen eigenen

Eine selbst gebaute `docker run`-Zeile prueft den eigenen Aufbau, nicht den Weg,
den Hermes geht. Wer zwei `-v …:/workspace` in denselben Aufruf schreibt, bekommt
`Duplicate mount point: /workspace` — und meldet das als Ursache, obwohl die
Mount-Liste im Traceback genau EINEN `/workspace` zeigt. Die eigene Zeile war
der Fehler.

Richtig ist, den Aufruf aus dem **Traceback** nachzubauen — Zeile fuer Zeile,
insbesondere die `-w`-Angabe und die `-v`-Liste. Erst wenn die eigene Zeile
dieselbe Meldung liefert wie der Traceback, ist es dieselbe Ursache. Das gilt
fuer jede Backend-Diagnose: der Traceback ist die Vorlage, nicht das Gedaechtnis.

### Was der Fix kostet: der Container sieht nur noch `terminal.cwd`

`docker_mount_cwd_to_workspace: true` repariert das Terminal, aendert aber den
Sichtbereich: gebunden wird **genau der `cwd`** (Mechanik und die drei Zustaende
stehen unten in der Tabelle *Die drei Zustaende von `cwd` x `mount_cwd`*).

Gemessen mit `cwd: …\Agenten\Hermes`: der Container hat `/workspace` =
`Agenten\Hermes` (WorkingDir `/workspace`), und **die BrainFiles-Wurzel ist
nicht da** — `/workspace/../MaxHirn` und `/workspace/../Agenten` existieren
nicht, kein `/mnt/c`, kein `/host-cwd`. Weil `Agenten/Hermes` kein eigenes
Repository ist, gibt es dort auch **kein `.git`**: `git` im Terminal kann die
Wurzel nicht erreichen.

Folge fuer die Arbeitsteilung — nicht als Fehler behandeln, sondern einplanen:

- Alles unterhalb `Agenten/Hermes` (Config, Skills, Profile) geht normal ueber
  `terminal`.
- Alles an der **Wurzel** (`MaxHirn/`, `Agenten/Handel/`, jedes `git` im
  BrainFiles-Repo) laeuft ueber `mcp__windows_mcp__PowerShell` (siehe Skill
  `windows-host-zugriff`).
- Wer das Terminal wieder auf die ganze Wurzel braucht, schaltet **nicht**
  `docker_mount_cwd_to_workspace` zurueck (das bricht alles) und schreibt auch
  **nicht** den `cwd` um (das verschiebt das Arbeitsverzeichnis jeder Sitzung),
  sondern ergaenzt `terminal.docker_volumes` um einen Eintrag, der die Wurzel
  bindet:

      terminal.docker_volumes: ["C:\\Users\\...\\BrainFiles:/brainfiles"]

  Der Pfad liegt ausserhalb des gemounteten `cwd`, wird also als eigener `-v`
  angehaengt statt ersetzt. Wie jede Config-Aenderung: byte-genau setzen, sichern,
  gegenproben, und die Wirkung als offenen Beleg melden, bis ein Lauf sie zeigt.

### PowerShell auf dem Host, solange kein Terminal da ist

`write_file`, `patch` und `read_file` brauchen denselben Container. Fuer die
Dauer des Ausfalls auf den Host ausweichen: `mcp__windows_mcp__PowerShell` und
`mcp__windows_mcp__FileSystem` (Modi read/write/list/info). Damit liessen sich
Wache, Tests und Commits vollstaendig fahren — nur ohne die Bequemlichkeit von
bash.

**Achtung in PowerShell:** Heredocs (`python - <<'EOF'`) gibt es nicht, und ein
Apostroph im Text bricht einen einfachen `-Command`-String (`Unerwartetes Token`).
Skripte als Datei schreiben und mit `-File` aufrufen; lange Commit-Meldungen per
FileSystem-Werkzeug in eine Datei legen und mit `git commit -F <C:/-Pfad>` lesen.

Dazu drei Fallen, die in dieser Lage Zeit gekostet haben:

- **Eine Here-String-Nutzlast in eine `.ps1` legen, nicht in den Aufruf.**
  `$code = @'…'@` mit `$`-Zeichen direkt in `-Command` wird von der bash-Schicht
  vorher expandiert (`Unerwartetes Token "$"`). Skript per `write_file` ablegen,
  dann `& $py <skript>`.
- **Den Interpreter absolut aufrufen.** Das venv-Python eines Fremdordners ist
  unter Windows kein MSYS-Pfad; `/c/Users/...` funktioniert im Terminal, aber ein
  per `-Command` gestarteter Prozess braucht die `C:\`-Form.
- **`docker rm -f` fuer Probe-Container nachziehen.** Die Proben (`probeA`,
  `probeB`, `probeC`) bleiben sonst liegen und tauchen spaeter in jeder
  Container-Liste als Raetsel auf.

### Die drei Zustaende von `cwd` x `mount_cwd` - und welcher die Wurzel zeigt

`terminal.cwd` auf einem Windows-Host ist ein HOST-Pfad. Ob das gutgeht,
entscheidet `docker_mount_cwd_to_workspace` - und der Sichtbereich haengt
daran:

| `cwd` | `docker_mount_cwd_to_workspace` | Terminal | Wurzel sichtbar |
|---|---|---|---|
| Container-Pfad (`/workspace`) | beliebig | laeuft | nein (nur der Mount) |
| Windows-Pfad | `false` | **Exit 125**, jedes Kommando | - |
| Windows-Pfad | `true` | laeuft | nur mit `docker_volumes` |

`terminal.backend: local` ist die vierte, einfachste Antwort: das Terminal
laeuft dann am Host und sieht die ganze Wurzel, ohne `mount_cwd` und ohne
`docker_volumes`. Der Docker-Backend ist die Wahl, wenn Kommandos **isoliert**
laufen sollen - dann braucht es beide Eintraege.

### Backend waehlen: `local` oder `docker` - die Windows-Binaries entscheiden

Die Frage ist nicht, ob Docker gerade erreichbar ist, sondern **was die Arbeit
ausfuehren muss**. Der Container ist Linux; alles, was ein Windows-Programm
braucht, laeuft dort nicht:

    file Agenten/Handel/scanner/.venv/Scripts/python.exe
    -> PE32+ executable for MS Windows (console), x86-64

Die Spur-venvs sind Windows-EXEs, `Agenten/Routinen/handel-tests.ps1` sucht
`.venv\Scripts\python.exe`, und die `Routinen/*.ps1` sind PowerShell. Im Container
ist davon nichts ausfuehrbar - also entscheidet die **Arbeitslast**, nicht die
Verfuegbarkeit:

| Arbeitslast | Backend |
|---|---|
| BrainFiles selbst: Spur-venvs, `.ps1`-Routinen, Git an der Wurzel | `local` |
| reines Python/Node ohne Windows-Programme, isolierte Laeufe | `docker` |

`local` laeuft als derselbe Benutzer **ohne Rueckfrage bei destruktiven
Kommandos** - das ist die eigentliche Kostenstelle, nicht „der Agent loescht
alles". Sie wird mit einer Sicherung bezahlt, nicht mit einem Container (`.git`
an der Wurzel, die drei Kopien, `Wissen/Schutzregeln.md`), und die greift
unabhaengig vom Backend.

**Wenn „Docker faellt staendig aus" als Argument kommt: erst messen.** Gemessen
am 08.10.2026: **10** Docker-Abstuerze in 30 Tagen, **alle an einem Tag** (der
Commit-Erschoepfungstag mit 31 App-Abstuerzen), an den uebrigen 29 Tagen null.
Die Wahrnehmung stimmt nicht mit der Rate ueberein - jeder Ausfall trifft, weil
er das Terminal mitnimmt, aber er ist selten. Messweg:

    # Abstuerze (Application Error) je Tag, 30 Tage
    Get-WinEvent -FilterHashtable @{LogName='Application';
      ProviderName='Application Error'; StartTime=(Get-Date).AddDays(-30)} \
      -MaxEvents 5000 | Where-Object { $_.Message -match 'docker' } |
      Group-Object { $_.TimeCreated.ToString('yyyy-MM-dd') }

    # Wie oft hat eine Wache geheilt? Agenten/Hermes/cron/output/<job-id>/
    #   '**Status:** silent (empty output)' = gesund, nichts gesendet
    #   Statuszeile FEHLT                   = gemeldet (Heilung/Erholung)

Der zweite Punkt ist der wichtigere: die Wache schreibt fuer **jeden** Lauf eine
Datei, auch die stillen. „Wie viele Meldungen" ist deshalb eine Zaehlung ueber
`Status`, nicht ueber die Dateizahl (50 Laeufe, 49 still, 1 gemeldet).

Der Docker-Pfad laesst sich vollstaendig einrichten und **liegen lassen** -
er ist dann nicht kaputt, nur nicht aktiv, und ein spaeterer Wechsel kostet
keine zweite Einrichtung.

Einen `docker_volumes`-Eintrag erkennt man an zwei Regeln: er ist ein
**roher `-v`-Spec** und braucht deshalb den **Doppelpunkt** (ohne ihn: `Docker
volume '...' missing colon, skipping`), und ein Nicht-String wird ebenso
verworfen. Der gebundene Pfad ist der einzige Weg an den `cwd` heran -
`_existing_host_mount()` vergleicht ueber `_host_path_key` und findet einen
Mount nur, wenn **derselbe Host-Pfad** dort noch einmal steht.

### Nachgemessen am 06.10.2026: der Container-Test ist BLOCKIERT

Der Eintrag steht in der Config, aber der Beleg am echten Container fehlt - der
Docker-Daemon ist beschaedigt und kann **keinen** Container mehr starten:

    docker run ... -> Exit 125
      write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db:
      read-only file system
    docker image ls -> rpc error: ... input/output error (Content-Blob)

**Die Gegenprobe, die den Verdacht entkraeftet:** derselbe `docker run` **ohne
jeden Volume-Eintrag** scheitert exakt gleich. Der Schaden liegt also nicht am
`docker_volumes`-Eintrag. Wer hier „der Eintrag hat es kaputtgemacht" liest,
liest eine unbelegte Ursache.

Was sich trotzdem belegen laesst:

- Der Spec ist formal gueltig: `_split_volume_spec` (in
  `tools/environments/docker.py`, NICHT in `remote_common`) zerlegt beide
  Schreibweisen zu `('C:\Users\...\BrainFiles', '/brainfiles')`.
- Der Host-Pfad existiert.
- Der Eintrag selbst: `git diff --numstat` 2/0, `terminal` 12 -> 13 Schluessel,
  `yaml.safe_load` liest ihn zurueck, CRLF 1377 -> 1379, bareLF 0.

**Beleg erbracht am 06.10.2026** (nach einem Neustart von Docker Desktop, der
den read-only-Metadaten-Store geheilt hat):

    docker run -d --name probeBF -v 'C:\Users\faupe\Documents\BrainFiles:/brainfiles' \
        nikolaik/python-nodejs:python3.11-nodejs20 sleep infinity
    docker exec probeBF ls /brainfiles
    -> AENDERUNGSPLAN-TASKS-2026-10-04.md  AGENTS.md  Agenten  MaxHirn  Modelle  Werkstatt ...
    docker exec probeBF ls -d /brainfiles/.git && cd /brainfiles && git log --oneline -1
    -> /brainfiles/.git / 0c68b4d2 Wiki-Lektion 5: ...
    docker exec probeBF sh -c 'touch /brainfiles/.__probe && rm /brainfiles/.__probe'
    -> schreiben-OK

**Image-Falle beim Nachstellen:** `nousresearch/hermes-sandbox:desktop` startet in
dieser Umgebung nicht - der Container endet sofort mit Exit 255 und
`exec /usr/bin/sleep: exec format error` (Architektur). Fuer die Mount-Gegenprobe
ein passendes Image nehmen (`nikolaik/python-nodejs:python3.11-nodejs20`); die
Bindung selbst wird von Docker angelegt und ist am `hermes-sandbox`-Image mit
`docker inspect --format '{{range .Mounts}}...'` genauso zu sehen.
