# Dauerlauf nach Spur-Verdrahtung neu starten

Eine SPUREN-Aenderung (neue Spur) sieht der LAUFENDE Dauerlauf nicht - er hat
die alte Liste im Speicher. Neustart noetig, und der Neustart hat ein paar
Token-fressende Fallen, die sich mit dem richtigen Befehlssatz erledigen.

## Identifikation (nicht raten)

Die PID-Dateien (`dauerlauf.pid`, `dauerlauf.mittel.pid`) nennen den Treiber,
aber der Waechter kann schon einen Neustart gemacht haben - die Dateien sind
nicht zuverlaessig. Laufende Instanzen wirklich auflisten mit einem
PowerShell-Einzeiler in einer .ps1-Datei (im bash scheitert `-Filter` mit
verschachtelten Anfuehrungszeichen und `$_` wird von bash verschluckt):

```powershell
Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq "python.exe" -and $_.CommandLine -match "handel\\dauerlauf.py"
} | Select-Object ProcessId,ParentProcessId,CreationDate | Format-List
```

- CommandLine auf die EXAKTE Skriptdatei (`handel\\dauerlauf.py`) filtern -
  `-match "dauerlauf"` erwischt auch `moondev_dauerlauf.py` (eigener Task,
  kein Handelslauefer) und faelscht den Bestand.
- Es laufen ZWEI: Basis (ohne `--risiko`) und Mittel (`--risiko mittel`);
  beide neu starten.

## Beenden und starten

- `taskkill //F //T //PID <nr>` scheitert im bash (MSYS-Pfadkonvertierung ist
  dort abgeschaltet, `//` bleibt doppelt) - EINFACHER Slash:
  `taskkill /F /T /PID <treiber-pid>` (beendet den Baum inkl. Kind).
- Nach dem Beenden `Start-ScheduledTask MaxHirn-Handel-Dauerlauf` UND
  `MaxHirn-Handel-Dauerlauf-Mittel-Waechter`. Der Wrapper startet und kehrt
  sofort zurueck - der Task-State springt damit zurueck auf "Ready", obwohl
  der Prozess laeuft. **Den Prozess pruefen, nicht den Task-State.**
- Falle: Solange die alte PID noch in der pid-Datei steht und der Task
  gestartet wird, kann der Wrapper ohne Laeufer enden (er sieht "laeuft
  schon"). Erst die Instanzen wirklich beenden, dann starten.

## Nachweis

1. Neue PIDs in `dauerlauf.pid`/`dauerlauf.mittel.pid` (Mittel-Nr. in der
   mittel-Datei).
2. Erster Zyklus liegt im Journal; Zyklusalter < Takt.
3. `scanner/.venv/Scripts/python.exe spiegelstand.py` -> `N von N Spuren
   byte-gleich (Q:)`, mit N = neuer SPUREN-Stand - die Neue ist dabei.
