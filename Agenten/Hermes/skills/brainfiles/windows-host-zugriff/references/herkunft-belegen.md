# Sonden: welcher Prozess hat dieses Artefakt erzeugt

Rezepte fuer die Frage "woher kommt diese Datei / dieses Fenster". Alle
Host-Aufrufe ueber `mcp__windows_mcp__PowerShell`, Pfade absolut. Die Regeln
stehen in SKILL.md ("Eine Datei erscheint immer wieder").

## 1. Verknuepfung (.lnk) lesen: Ziel und Arbeitsverzeichnis

`strings` gibt es in der MSYS-Bash nicht. Die `.lnk`-Bytes lesen und die
druckbaren Laeufe herausziehen — Ziel, Arbeitsverzeichnis und Relativpfade
stehen dort im Klartext:

```python
import re
d = open(r"C:\Users\faupe\Desktop\Hermes.lnk", 'rb').read()
for r in re.findall(rb'[\x20-\x7e]{6,}', d):
    print(r.decode('latin1'))
```

Ausgabe nennt das Ziel (`...\release\win-unpacked\Hermes.exe`) und daneben die
Relativform mit `%USERPROFILE%` — fehlt ein echtes Arbeitsverzeichnis, startet
der Prozess im ORDNER DER VERKNUEPFUNG.

Ein Heredoc durch die Terminal-Schicht loest Fluchtfolgen auf — bei Mustern mit
`\x`/`\r` das Skript mit `write_file` ablegen und starten.

## 2. Haelt noch jemand die Datei? (Schreiber tot oder lebendig)

```powershell
$f = '<absoluter pfad>'
$i = Get-Item -LiteralPath $f
'{0} B  angelegt {1}  zuletzt {2}' -f $i.Length, $i.CreationTime, $i.LastWriteTime
try   { $fs=[IO.File]::Open($f,'Open','ReadWrite','None'); $fs.Close(); 'frei -> kein lebender Schreiber' }
catch { 'GESPERRT -> ein Prozess haelt sie: ' + $_.Exception.Message }
```

- **Frei** = der Schreiber ist fertig. Ein Prozess-Schnappschuss JETZT findet ihn
  nicht mehr — die Frage muss beim NAECHSTEN Auftauchen beantwortet werden
  (Abschnitt 4).
- **Gesperrt** = ein lebender Prozess hat sie offen (typisch: umgeleitetes
  stdout). Prozessliste sofort einfrieren, nicht spaeter.
- Anlege- und Schreibzeitpunkt liegen oft Sekunden auseinander: der Schreiber hat
  in EINEM Zug geschrieben und geschlossen. Die letzten Zeilen IM Artefakt
  datieren den Vorgang — ein Startbanner mit Zeitstempel ist ein guter Anker.
- `Get-Process -Id <pid>` auf eine PID aus einem Minuten alten Schnappschuss
  liefert leer: Dienste auf diesem Rechner starten haeufig neu. Eine
  Prozessliste ist ein Zeitpunkt, kein Zustand.

## 3. Prozesse: nach Kommandozeile, mit Eltern und Startzeit

```powershell
$o = @()
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match '<suchwort>' -or $_.Name -in @('cmd.exe','wscript.exe') } |
  ForEach-Object { $o += ('{0}`t{1}`t{2}`t{3}' -f $_.ProcessId, $_.ParentProcessId, $_.Name, ($_.CommandLine -replace '\s+',' ')) }
$o -join "`n"
```

- **Ergebnis in ein Array sammeln und `-join`.** Eine Pipeline, die auf
  `Select-Object … | Format-List` endet, kam durch die Bruecke leer zurueck,
  waehrend derselbe Aufruf als Textliste vollstaendig ankam.
- Der Suchtext muss den EIGENEN Aufruf ausschliessen (Muster aus Teilen bauen,
  eigenen PID filtern) — sonst findet sich der Suchende selbst.
- Ein Redirect (`... > datei`) steht beim ELTERNprozess, nicht beim Kind. Findet
  die Suche den Zielnamen in keiner Kommandozeile, ist der Starter beendet —
  kein Beweis, dass niemand schreibt.
- Bei Diensten mit eigenem Bundle (Electron-`app.asar`) auch dort nach dem
  Erzeuger suchen, nicht nur im Quelltext: der Nulltreffer im Quellbaum
  beweist nur, dass der Erzeuger nicht dort liegt.

## 4. Den Schreiber beim NAECHSTEN Auftauchen fangen

`FileSystemWatcher` auf den Fundort, der im `Created`-Ereignis sofort die
Prozessliste mit Eltern und Startzeit mitschreibt. Der Schreiber lebt oft nur
Sekunden — deshalb IM Ereignis messen, nicht danach.

```powershell
$ziel = 'C:\Users\faupe\Desktop'
$log  = 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\cache\scratch\wache-schreiber.log'
$w = New-Object IO.FileSystemWatcher $ziel, '*'
$w.EnableRaisingEvents = $true
Register-ObjectEvent $w Created -Action {
  Add-Content -LiteralPath $log -Value ("== " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $Event.SourceEventArgs.Name)
  Get-CimInstance Win32_Process |
    Where-Object { $_.CreationDate -gt (Get-Date).AddSeconds(-60) } |
    ForEach-Object { Add-Content -LiteralPath $log -Value ('   {0} {1} parent={2} {3}' -f $_.ProcessId, $_.Name, $_.ParentProcessId, ($_.CommandLine -replace '\s+',' ')) }
}
```

- Die Wache **schreibt nur** und beendet nichts — sie ist eine Messung.
- Aktionsbloecke laufen in einem eigenen Runspace: Pfade im Block absolut halten.
- Soll sie laenger laufen, gehoert sie in einen Cron mit leerer Ausgabe
  ("nichts senden") und Merkdatei, nicht in einen Dialog.
- Liegt der Fundort auf dem Desktop, zusaetzlich den CWD des Starters
  geradeziehen (Verknuepfung -> Eigenschaften -> "Ausfuehren in":
  Startverzeichnis des Dienstes). Der Mechanismus (CWD) ist damit belegt, der
  Schreiber selbst nicht — beides so benennen.

## 5. Grep auf Windows: begrenzen, sonst stirbt der Aufruf

Ein `grep -r` ueber `BrainFiles` oder `apps/desktop` laeuft in `node_modules`,
`.hermes-runtime`, `venv`/`.venv`, `dist` und die `.claude/worktrees` und
reisst das 180-s-Limit der Terminal-Schicht — der Aufruf kommt ohne Ausgabe
zurueck, und die ganze Suche war umsonst.

```bash
cd /c/Users/faupe/Documents/BrainFiles
timeout 120 grep -rIn --include=*.py --include=*.ps1 --include=*.ts \
  -e '<muster>' . 2>/dev/null \
  | grep -vE 'node_modules|/\.git/|site-packages|\.hermes-runtime|/venv/|\.venv|/dist/|worktrees' | head -20
```

- `--include` setzen UND nachfiltern; `timeout` voranstellen, damit der Aufruf
  mit Teilergebnis zurueckkommt statt zu sterben.
- Feste Suchtexte mit `grep -F` suchen. Eine `for`-Schleife mit Mustern aus
  Backslash-Klammern bricht die Bash mit "unexpected EOF" ab — Muster einzeln
  und einfach-quotiert aufrufen.
- Verbotene Zeichen in Windows-Dateinamen sind `< > : " / \ | ? *` und die
  Steuerzeichen. Ein Name, in dem genau diese FEHLEN, wurde mit einem
  Dateinamen-Reiniger gebaut (Node `sanitize-filename` entfernt sie ohne
  Ersatz); Hermes' eigener Reiniger `hermes_cli/gateway_windows._sanitize_filename`
  ERSETZT sie durch `_` und kommt damit als Quelle nicht in Frage.
