# Docker-Sandbox: Umgebungsvariablen hineinreichen

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
## Sonderfall Windows-Host: `terminal.cwd` im Docker-Backend

Auf einem Windows-Host ist `terminal.cwd` ein **Host**-Pfad
(`C:\Users\...`), im Container existiert er nicht. Drei Zustaende:

| Zustand | was passiert |
|---|---|
| `docker_mount_cwd_to_workspace: true` | Host-Pfad wird gebunden, `cwd` auf `/workspace` umgeschrieben - laeuft |
| `false` **und** `cwd` ein Container-Pfad (`/workspace`) | laeuft |
| `false` **und** `cwd` ein Windows-Pfad | **Exit 125** |

**Symptom des kaputten Zustands:** JEDES `terminal`-Kommando scheitert
("Terminal environment unavailable"), im Traceback steht
`docker: Error response from daemon: the working directory 'C:\Users\...' is
invalid, it needs to be an absolute path`, Rueckgabecode 125.

**Beleg:** `_resolve_config_cwd()` in `hermes-agent/tools/terminal_tool.py`.
Mit `mount_docker_cwd=True` (Zeilen 685-692) wird `host_cwd = candidate` und
`cwd = "/workspace"` gesetzt. Mit `False` greift der Windows-Zweig (Zeilen
693-702) und setzt `cwd = candidate` - der Windows-Pfad geht roh in
`docker run -w`.

Gegenprobe ohne Hermes (am schnellsten):

    docker run -d --name probe -w 'C:\Users\...\Agenten\Hermes' <image> sleep infinity   # Exit 125
    docker run -d --name probe -w /workspace <image> sleep infinity                          # Exit 0

**Zweiter Faktor - warum es lange unauffaellig bleibt:** der Container wird beim
ERSTEN Kommando gebaut und danach **wiederverwendet**
(`persist_across_processes` + `container_persistent: true`). Solange einer laeuft,
faellt nichts auf; erst nach dem Idle-Reaper (`terminal.lifetime_seconds`) oder
einem Docker-Neustart bricht jedes Kommando auf. Deshalb nie "laeuft doch" als
Entwarnung nehmen.

**Wirkt erst nach dem Neuladen der Config** durch den Hermes-Prozess
(Gateway/Desktop) - kein Live-Schalter.

**Aendern NIE per `hermes config set`:** das schneidet den Kommentar-Schwanz der
`config.yaml` ab und schreibt die Datei mit LF (Falle vom 29.09.2026).
Byte-genau ersetzen, Zeilenenden vorher/nachher zaehlen, danach `Compare-Object`
Sicherung <-> Datei: genau ein Zeilenpaar.
