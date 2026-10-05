# RAM und CPU freigeben

Auftrag: „RAM freigeben“ bzw. „System beschleunigen“. Zwei Fallen, die beide
unter diesem Aufruf zusammenfallen und die Reihenfolge bestimmen, in der
gemessen wird.

## 0. Reihenfolge: erst CPU, dann RAM

Der Auftrag sagt „RAM“, der Befund ist oft die CPU. Ein Rechner kann 21 GB
frei haben, `LoadPercentage` 100 anzeigen und sich trotzdem tot anfuehlen.
Deshalb **vor** jeder Speicher-Aktion eine Momentanlast messen, und zwar als
Differenz zweier Ablesungen — `Sort-Object CPU` zeigt Lebenszeit, nicht Last:

```powershell
$a=@{}; Get-Process | ForEach-Object { $a[$_.Id]=$_.CPU }
Start-Sleep -Seconds 8
Get-Process | ForEach-Object {
  if ($a.ContainsKey($_.Id) -and $null -ne $_.CPU) {
    $d=[double]($_.CPU-$a[$_.Id]); if ($d -gt 0.4) { '{0} {1} {2:N2} Kerne' -f $_.Name,$_.Id,($d/8) }
  }
} | Sort-Object { $d } -Descending
```

`Win32_Processor.LoadPercentage` ist nur ein Momentan-Schnappschuss und kann
dabei dauerhaft 100 zeigen, obwohl die Last woanders liegt — er taugt als
Alarmschwelle, nicht als Beweis.

## 1. Idle-Modell auf CPU: der stille Vollgas-Fresser

Ein lokales Modell, das mit `:cpu` (nicht GPU) geladen ist und **seit Stunden
idle** ist, rechnet auf allen Kernen weiter. Gemessen: 47,6 von 28 Kernen
ueber 8 Sekunden bei 5,2 GB RAM und 10,1 GB Commit — bei *null* offenen
Verbindungen und letztem Logeintrag Stunden alt.

Drei Zeugen, bevor der Prozess als Fresser gilt:

```powershell
# a) wer rechnet wirklich (Differenzmessung wie oben)
# b) hat er überhaupt noch eine Verbindung?
Get-NetTCPConnection -RemotePort 11434 -State Established
# c) wann war die letzte echte Anfrage?
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 20
(Get-Item "$env:LOCALAPPDATA\Ollama\server.log").LastWriteTime
```

`/api/ps` zeigt das geladene Modell mit `size_vram: 0` — das ist das eindeutige
Kennzeichen fuer die CPU-Variante. `expires_at` in der Vergangenheit plus
unveraendertes Log heisst: abgelaufen, nur nicht freigegeben.

Entladen ohne Neustart:

```powershell
Invoke-RestMethod 'http://127.0.0.1:11434/api/generate' -Method Post `
  -Body (@{ model='<name>'; keep_alive=0 } | ConvertTo-Json -Compress)
```

Nach dem Entladen laeuft der Modellprozess weiter (Runner bleibt als Träger
stehen) — **RAM erst nach dem Exit neu messen**, nicht nach dem Aufruf.

## 2. MCP-Knoten: Generationen zaehlen, nicht Prozesse

Ein Gateway, der denselben MCP-Server mehrfach startet, erzeugt 18–24
Knoten derselben Kommandozeile. Sie sind unterscheidbar ueber den Servernamen
im Pfad, und **ohne offene TCP-Verbindung sind sie tot**:

```powershell
$srv = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
       Where-Object { $_.CommandLine -match 'ant\.dir' }
$srv | Group-Object { ($_.CommandLine -split 'ant\.dir\.gh\.')[1] -split '\\' } |
      Sort-Object Count -Descending | Select-Object Count,Name
$ids = $srv.ProcessId
(Get-NetTCPConnection -State Established | Where-Object { $ids -contains $_.OwningProcess }).Count
```

Aufraeumen: je Server die **drei juengsten nach `CreationDate`** behalten,
den Rest per `Stop-Process -Id -Force` beenden (natives Kommando —
`taskkill` aus einer MCP-Session tut still nichts).

Merksatz: **eine bestehende Waechter ist blind, wenn sie den falschen
Prozessnamen zaehlt.** Vor jeder Ueberzahl-Bereinigung die Waechter-Definition
lesen und pruefen, welche Interpreter sie ueberhaupt zaehlt — ein Filter auf
`python` sieht einen `node`-Kreislauf nie.

## 3. Memory Compression ist ein Symptom, kein Fresser

9–10 GB in „Memory Compression“ bei 23 GB freiem RAM sind **kein Leak**. Die
Ursache ist meistens eine Container-Laufzeit (Docker/WSL), die Commit haelt
und Windows zum Komprimieren zwingt. Wer die Zahl sieht und „RAM-Defekt“
ruft, liegt falsch — nach dem Freigeben faellt sie von selbst.

Wer den echten Commit-Fresser sucht: `PM` (`PrivateMemorySize64`) je Prozess
und nach **Gruppen** summieren, nicht nach Einzelprozessen. `com.docker.*`
haelt Commit, obwohl sein RAM-Anteil maessig aussieht.

## 4. PowerShell-Falle beim Gruppieren (kostete eine ganze Runde)

```powershell
# FALSCH -> "CimInstance enthaelt keine Methode op_Addition"
$grp = if ($h.ContainsKey($k)) { $h[$k] } else { $h[$k] = @() }
$grp += $p
```
Der `if`-Ausdruck liefert bei der ersten Iteration ein **CimInstance-Objekt,
kein Array**; `+=` darauf scheitert mit einer Meldung, die nach einem
Prozessproblem klingt, aber ein Skriptfehler ist. Richtig:

```powershell
if (-not $h.ContainsKey($k)) { $h[$k] = New-Object System.Collections.ArrayList }
[void]$h[$k].Add($p)
```

Diagnose-Regel dazu: **eine PowerShell-Fehlerblende, die sich hundertfach
wiederholt, ist fast nie ein Datenproblem, sondern ein Syntax-/Zuweisungsfehler
im Skript.** Die Anzahl gleicher Meldungen ist das Signal — einmal lesen,
Muster suchen, nicht weiterlaufen.

## 5. Der Vorschau-/Anwenden-Lauf

Freigabe-Aktionen als Skript mit `-Anwenden` (Vorschau ist Vorgang) bauen und
**die Vorschau selbst als Beleg nutzen**: sie zeigt, wie viele Prozesse je
Gruppe beendet werden. Ein erster Lauf meldete „beenden 0“ bei tatsaechlich
72 Waisen — das war der Zuweisungsfehler aus Abschnitt 4, kein leeres System.
Nach dem Lauf drei Zahlen erneut messen: RAM frei vorher/nachher, Restzahl der
Knoten, Groesse der Memory Compression.

## Grenzen dieser Diagnose

Freigabe raeumt Symptome. Wenn ein Gateway einen MCP-Server 20-mal startet,
ist die Registrierung die Ursache und bleibt nach dem Kill bestehen — der
Rechner ist dann wieder in derselben Lage. Nach dem Freigeben **pruefen, ob
die Knoten sofort wieder wachsen** (gleiche Gruppierung, ein paar Minuten
spaeter). Wachsen sie, ist der Kreislauf aktiv und die naechste Aufgabe ist
die Server-Registrierung, nicht mehr das Abschalten.