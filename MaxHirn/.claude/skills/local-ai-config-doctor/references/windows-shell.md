# Shell-Mechanik auf Windows-Geräten

Diese Notizen betreffen Befehle, die du über `device_bash`, `desktop-commander/start_process` oder `windows-mcp/PowerShell` auf dem Rechner des Nutzers ausführst.

## Das Quoting-Problem — und die Lösung

Der Aufruf geht durch mehrere Schichten (MCP-Argument → `powershell -Command` → PowerShell-Parser). Anführungszeichen und `$`-Zeichen werden dabei mehrfach interpretiert. Typische Fehlermeldungen:

```
Die Zeichenfolge hat kein Abschlusszeichen: ".
Schließende ")" fehlt in einem Ausdruck.
FINDSTR: ... kann nicht geöffnet werden.
```

Das ist kein Rechteproblem und keine kaputte Umgebung, sondern zerlegtes Quoting. Zwei bis drei Fehlversuche pro Sitzung sind dadurch normal — es sei denn, du gehst gleich anders vor.

**Die verlässliche Methode:** Skript in eine Datei schreiben, dann die Datei ausführen.

```
write_file  →  C:\Users\<user>\AppData\Local\Temp\check.ps1
start_process →  powershell -NoProfile -ExecutionPolicy Bypass -File C:\...\Temp\check.ps1
```

Im Skript kannst du normal quoten, mehrzeilig arbeiten, Schleifen und `try/catch` nutzen. Für alles, was länger als ein einzelner kurzer Befehl ist, ist das der Standardweg, nicht die Ausnahme.

## Wenn du doch inline arbeitest

- Pfade **literal** schreiben (`C:\Users\faupe\...`) statt über `$env:USERPROFILE` — die Variable wird in der Inline-Form regelmäßig zerlegt.
- `Join-Path $w 'unterordner'` statt `"$w\unterordner"`.
- Einfache Anführungszeichen innen, doppelte außen — nie umgekehrt.
- `findstr` mit mehreren `/C:`-Mustern funktioniert über diese Schichten praktisch nie. Nutze stattdessen `Select-String` in einer Skriptdatei.
- Umgebungsvariablen für einen einzelnen `cmd /c`-Aufruf: `cmd /c "set VAR=wert&& programm"` — das `&&` folgt direkt auf den Wert, ohne Leerzeichen davor, sonst landet es im Wert.

## Suchen und Lesen

- Dateisuche: `Get-ChildItem -Path <root> -Filter '*name*' -Recurse -Depth 3 -ErrorAction SilentlyContinue`. **Immer mit `-Depth`** — eine ungebremste Suche über das Benutzerprofil läuft in den Timeout.
- Inhaltssuche: `rg` (ripgrep) ist auf Entwicklerrechnern meist vorhanden und um Größenordnungen schneller als `Select-String` über Verzeichnisbäume. Bei Treffern in `node_modules`/`venv` gezielt ausschließen (`-g '!node_modules' -g '!venv'`), sonst ertrinkst du in Fundstellen.
- Ein MCP-gestütztes `start_search` mit `searchType: content` liefert Treffer paginiert — bei sehr breiten Mustern kommen leicht tausende Zeilen zurück. Muster eng fassen, `maxResults` setzen.
- Dateien lesen: `read_file` mit `offset`/`length` statt `cat` über große Dateien.

## Rechte und Neustarts

- **User-Umgebungsvariable** setzen: `[Environment]::SetEnvironmentVariable('NAME','wert','User')` — funktioniert ohne Adminrechte.
- **System-Variable** (`'Machine'`) braucht Administratorrechte. Ohne sie kommt „Der angeforderte Registrierungszugriff ist unzulässig." Das ist kein Grund, die Aufgabe abzubrechen: die User-Variable erfüllt in aller Regel denselben Zweck. Gib dem Nutzer den Einzeiler für eine Administrator-PowerShell mit, falls er es systemweit will.
- **Wichtig:** Neu gesetzte Variablen erreichen **keinen laufenden Prozess**. Ein MCP-Server, der vor dem Setzen gestartet wurde, sieht sie nicht — auch nicht in Shells, die er neu startet, weil er sein eigenes Environment weitergibt. Wenn eine Prüfung eine gerade gesetzte Variable trotzdem als fehlend meldet, ist das erwartetes Verhalten und kein neuer Befund. Verifizieren kannst du es, indem du die Variable für den Testaufruf explizit mitgibst.
- Löschen von Dateien ist über `device_bash` standardmäßig gesperrt (`Operation not permitted`). Dann `device_request_delete_permission` für den betroffenen Ordner anfragen; bei Ablehnung die Dateien nach `_to_delete/` verschieben und dem Nutzer sagen, wo sie liegen.

## Python auf dem Gerät

Viele Werkzeuge bringen ein eigenes venv mit. Das ist der richtige Interpreter, wenn du Interna eines Werkzeugs prüfen willst — nicht das System-Python:

```
<tool-home>\<repo>\venv\Scripts\python.exe <skript.py>
```

Auch hier gilt: Python-Einzeiler mit `-c` über die Quoting-Schichten scheitern zuverlässig. Schreib eine `.py`-Datei nach `Temp` und ruf sie auf.
