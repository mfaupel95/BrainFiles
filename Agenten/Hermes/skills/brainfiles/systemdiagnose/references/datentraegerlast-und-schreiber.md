# Datentraegerlast: welcher Prozess schreibt auf welcher Platte

Eigene Messdimension neben RAM und CPU. Ein Rechner kann 20 GB freien RAM,
16 GB freien Commit und 0 % CPU haben und trotzdem unbrauchbar sein, weil
**eine** Platte ihre Warteschlange nicht abarbeitet. Die Anzeige friert, die
Programme reagieren träge, kein Speicher- oder CPU-Befund ist sichtbar.

## 1. Je Platte messen, nicht „die Platte“

`Win32_PerfFormattedData_PerfDisk_PhysicalDisk` liefert je Volume eine Zeile
(„0 C:“, „1 O:“, zusammengefasste Pools „2 I: G: H:“). Der entscheidende
Wert ist `CurrentDiskQueueLength` — `PercentDiskTime > 100` ist normal bei
NVMe und heisst nur „Auslastung ueber 100 % der Zeitmessung“.

```powershell
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk |
  Where-Object { $_.Name -ne '_Total' } |
  Select-Object Name,PercentDiskTime,CurrentDiskQueueLength,
    @{n='MBps';e={[math]::Round($_.DiskBytesPersec/1MB,1)}}
```

Merksatz: **eine Platte mit Queue > 5 bei ansonsten leerem Feld erzeugt genau
das Symptom „haengt“, das sonst an CPU oder Speicher gesucht wird.** Das Feld
`Get-Counter '\\PhysicalDisk(_Total)\\...'` ist lokalisiert und liefert auf
deutschem Windows still — `Win32_PerfFormattedData_*` ist der Weg. Der Pool-Eintrag
„2 I: G: H:“ ist eine Messung fuer mehrere Volumen, nicht fuer eines: bei hohem
Wert dort einzeln je Volume nachmessen, bevor ein Laufwerk verdaechtigt wird.

## 2. Den Schreiber finden: IO-Rate je Prozess, nicht CPU-Lebenszeit

`Sort-Object CPU` sortiert nach aufsummierter Prozessorzeit seit Start. Ein
Dauerprozess mit 20 000 s CPU kann seit Stunden mit 0,1 % Last laufen und
trotzdem 116 MB/s auf die Platte schreiben — die CPU-Sortierung fuehrt dann
weg vom Schuldigen. Richtig ist die aktuelle I/O-Rate je PID, zweimal
abgelesen (die erste Ablesung etabliert nur die Prozessmenge):

```powershell
$seen=@{}
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { $_.Name -notin '_Total','Idle' } |
  ForEach-Object { $seen[$_.IDProcess]=$_.Name }
Start-Sleep -Seconds 5
Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
  Where-Object { $_.Name -notin '_Total','Idle' } |
  ForEach-Object {
    [pscustomobject]@{ Name=$_.Name; PID=$_.IDProcess
      KBps=[math]::Round($_.IODataBytesPersec/1024,0); CPU=$_.PercentProcessorTime }
  } | Sort-Object KBps -Descending | Select-Object -First 12
```

Den PID **mit der vollstaendigen Kommandozeile** nachziehen; erst dann ist der
Befund belegt. Eine belegte Kette ist: Warteschlange nennt die Platte →
hoechste KB/s nennt den Prozess → `CommandLine` nennt sein Arbeitsverzeichnis
→ dort liegen die Dateien mit der passenden Alters-/Groessen-Spur.

## 3. Der haeufigste Einzelfall: ein Indexer/Watcher auf SQLite

Ein Datei-Watcher mit kurzem Poll-Intervall (`watch --poll-seconds 2`) auf
einem Projektordner schreibt seine Datenbank (`.projectatlas/projectatlas.db`
plus `-wal`) bei jeder Aenderung neu. Die Spur im Bild: DB und **WAL** mit
den juengsten Zeitstempeln, `KB/s` zweistellig, Warteschlange auf genau dieser
Platte, CPU des Prozesses niedrig.

Belege im Bild sammeln, dann beenden:

```powershell
Get-ChildItem <projekt>\.projectatlas -File | Select-Object Name,Length,LastWriteTime
Stop-Process -Id <pid> -Force
Start-Sleep -Seconds 8   # dann Queue und % erneut messen
```

Der Nachmess-Schritt ist Teil des Befunds: `PercentDiskTime` und
`CurrentDiskQueueLength` **nach** dem Beenden auf 0 gehen lassen. Sonst ist
„ich habe den Schuldigen beendet" eine Behauptung.

## 4. Waisen derselben Binary bleiben liegen

Ein Watcher-Launcher, der pro Anfrage einen Serverprozess startet und nicht
freigibt, hinterlaesst Dutzende gleicher Kommandozeile mit **0 s CPU**. Sie
sind nach dem Beenden des Vorgaengers weiter zu sehen und werden beim
Gruppieren faelschlich als „Ursache" mitgezaehlt — nach dem Beenden des einen
Schuldigen also die Restliste erneut ausgeben und getrennt melden.

Auch hier gilt: Sortierbegrenz (`Select-Object -First N`) verdeckt die
waechstende Zahl. Die Gesamtzahl je Gruppe separat ausgeben.

## 5. Volumensuche begrenzen, sonst laeuft die Diagnose in den Timeout

`Get-ChildItem O:\ -Recurse` ueber ein 550-GB-Volume ueber eine MCP-Sitzung
laeuft in den Timeout und liefert NICHTS — auch nicht teilweise, auch nicht
 fuer die oberste Ebene. Drei Begrenzungen, jede fuer sich noetig:

* `-Depth 2` statt `-Recurse` (Tiefe zaehlt Ordner, nicht Ebenen beliebig)
* Reparse-Points aussortieren: `Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }` — Junctionen und Symlinks duplizieren sonst den ganzen Baum und verschieben die Summe
* je Unterordner **einzeln** messen und in einer Schleife sammeln, statt
  alles in einem Aufruf

Fuer „welche Datei auf dieser Platte ist heute gewachsen“ ist die Form
`Get-ChildItem <laufwerk>\ -Recurse -File -Depth 3 | Where-Object { $_.Length -gt 200MB -and $_.LastWriteTime -gt $cut }`
belastbar: eine Liste konkreter Pfade mit Groesse und Zeitstempel, aus der
sich die Quelle ohne weitere Messung ablesen laesst. Aus `.vhdx`-, `pagefile.sys`-
und Modellblob-Grossen laesst sich zudem direkt ablesen, welche Last die
Platte trägt, bevor man einen Prozess sucht.

## 6. Freier Plattenplatz ist Teil des Befunds, nicht ein Nebensatz

Bei 1–2 % freiem Platz ist jeder schreibende Dienst (Watcher, Sicherung,
Datenbank, Modell-Download) selbst eine Gefahr, und der Rechner traegt die
2004-Ereignisse (virtueller Speicher unzureichend) aus dem Vor-Nacht-Zeitfenster.
Nach dem Beenden des Schuldigen deshalb **die Empfehlung auf den Plattenplatz
legen** und den Dienst ausdruecklich nicht neu starten, bis Luft da ist — sonst
holt man den Befund binnen Minuten zurueck.

Was nicht angefasst wurde (Modelle, Docker-VHDX, pagefile.sys, Kopien) am
Ende nennen: das sind Loeschkandidaten, aber keine Diagnoseaktion.
