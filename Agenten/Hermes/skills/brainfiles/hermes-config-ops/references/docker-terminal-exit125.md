# Docker-Terminal: Exit 125 ist der rohe Windows-Pfad in `-w`

## Das Symptom

Jedes Docker-gestuetzte Werkzeug faellt aus - `terminal`, `write_file`,
`read_file`, `patch`, `execute_code` - mit

```
docker run ... returned non-zero exit status 125
docker: Error response from daemon: the working directory
  'C:\Users\...\Agenten\Hermes' is invalid, it needs to be an absolute path
```

`docker info` laeuft, Docker Desktop laeuft, das Image ist da, ein nacktes
`docker run --rm <image> echo HALLO` gibt Exit 0. Nur Hermes' eigener Aufruf
scheitert.

## Die Ursache (gemessen, zwei Zeugen ohne Hermes)

```
docker run --rm -w 'C:\Users\...\Agenten\Hermes' <image> echo x   -> Exit 125
docker run --rm -w /workspace                        <image> echo x   -> Exit 0
```

`terminal.cwd` traegt einen **Windows-Host-Pfad**. Steht
`terminal.docker_mount_cwd_to_workspace` auf `false`, geht dieser Pfad ROH in
`docker run -w` - und der Linux-Daemon kann ihn nicht aufloesen. Mit `true`
wird das cwd gebunden und `-w` auf `/workspace` umgeschrieben.

Fix in `config.yaml`:

```yaml
terminal:
  docker_mount_cwd_to_workspace: true
```

## Die Falle beim Fixen

**Ein Config-Wert wirkt erst, wenn der GATEWAY ihn gelesen hat.** Die
Docker-Werkzeuge laufen als Kind des Gateways und erben die Einstellung, die
beim Start galt. Nach der Aenderung:

* Auf der Platte verifizieren: `yaml.safe_load` lesen und den Schluessel
  ausgeben (nicht dem Diff glauben - `hermes config set` schneidet den
  Kommentar-Schwanz ab und schreibt LF).
* Dann den Gateway einmal neu starten (Aufgabe `Hermes_Gateway_2ef9d0b7`).
* Erst danach ist das Terminal wieder da. Ein Testlauf VOR dem Neustart
  scheitert weiter und sieht wie ein misslungener Fix aus.

## Die Falle beim Diagnostizieren

**Eine selbst gebaute `docker run`-Zeile prueft den eigenen Aufbau, nicht den
Hermes-Weg.** Ich hatte `-v <sandbox>/workspace:/workspace` UND
`-v <cwd>:/workspace` in denselben Aufruf geschrieben, bekam
`Duplicate mount point: /workspace` und meldete das als Ursache. Falsch: diese
Dublette gibt es im Hermes-Weg nicht (die Mount-Liste im Traceback zeigt genau
einen `/workspace`).

Richtig ist, den Aufruf aus dem **Traceback** nachzubauen - Zeile fuer Zeile,
insbesondere die `-w`-Angabe. Erst wenn die eigene Zeile dieselbe Meldung
liefert wie der Traceback, ist es dieselbe Ursache.

## Wenn kein Terminal da ist

`write_file`, `patch` und `read_file` brauchen denselben Container. Fuer die
Dauer des Ausfalls auf den Host ausweichen: `mcp__windows_mcp__PowerShell` und
`mcp__windows_mcp__FileSystem` (Modi read/write/list/info). Damit liessen sich
Wache, Tests und Commits vollstaendig fahren - nur ohne die Bequemlichkeit von
bash.

**Achtung in PowerShell:** Heredocs (`python - <<'EOF'`) gibt es nicht, und ein
Apostroph im Text bricht einen einfachen `-Command`-String (`Unerwartetes Token`).
Skripte als Datei schreiben und mit `-File` aufrufen; lange Commit-Meldungen per
FileSystem-Werkzeug in eine Datei legen und mit `git commit -F <C:/-Pfad>` lesen.
