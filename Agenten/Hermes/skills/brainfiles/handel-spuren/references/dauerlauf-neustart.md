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
  $_.Name -eq "python.exe" -and $_.CommandLine -match "dauerlauf.py" -and $_.CommandLine -notmatch "moondev"
} | Select-Object ProcessId,ParentProcessId,CreationDate | Format-List
```

- Der Treiber laeuft mit der RELATIVEN Datei `dauerlauf.py` (der Wrapper
  startet ihn mit `-WorkingDirectory $handel` und ArgumentList `'dauerlauf.py'`)
  - ein Filter auf den Vollpfad `handel\dauerlauf.py` findet 0 Prozesse.
  `-match "dauerlauf.py"` allein erwischt auch `moondev_dauerlauf.py` (eigener
  Task, kein Handelslauefer) und faelscht den Bestand - deshalb das
  `-notmatch "moondev"` obendrauf.
- Es laufen DREI Stufen: Basis/niedrig (`MaxHirn-Handel-Dauerlauf`, Wrapper
  ohne `-Risiko` = Parameter-Default, Sperre `dauerlauf.pid`), mittel
  (`MaxHirn-Handel-Dauerlauf-Mittel-Waechter`, `-Risiko mittel`,
  `dauerlauf.mittel.pid`) und hoch (`MaxHirn-Handel-Dauerlauf-Hoch-Waechter`,
  `-Risiko hoch`, `dauerlauf.hoch.pid`). Alle drei neu starten.

## Beenden und starten

- `taskkill //F //T //PID <nr>` scheitert im bash (MSYS-Pfadkonvertierung ist
  dort abgeschaltet, `//` bleibt doppelt) - EINFACHER Slash:
  `taskkill /F /T /PID <treiber-pid>` (beendet den Baum inkl. Kind).
- Nach dem Beenden `Start-ScheduledTask` auf alle drei -
  `MaxHirn-Handel-Dauerlauf`, `MaxHirn-Handel-Dauerlauf-Mittel-Waechter` und
  `MaxHirn-Handel-Dauerlauf-Hoch-Waechter`. Der Wrapper startet und kehrt
  sofort zurueck - der Task-State springt damit zurueck auf "Ready", obwohl
  der Prozess laeuft. **Den Prozess pruefen, nicht den Task-State.**
- Falle: Solange die alte PID noch in der pid-Datei steht und der Task
  gestartet wird, kann der Wrapper ohne Laeufer enden (er sieht "laeuft
  schon"). Erst die Instanzen wirklich beenden, dann starten.

## Aus einer Agenten-/MCP-Shell starten (windows-mcp)

- Den Wrapper DIREKT aufrufen: `& 'Agenten\Routinen\handel-dauerlauf.ps1'
  -Risiko <niedrig|mittel|hoch>` - die Basis ist `-Risiko niedrig`
  (Parameter-Default, `ValidateSet`). Einen `Start-Process powershell
  -WindowStyle Hidden` davorzuschalten startete aus einem Kontext ohne
  interaktiven Desktop NICHTS (kein Prozess, keine Fehlermeldung) - der
  direkte Aufruf ist der Weg.
- Der direkte Aufruf kann trotzdem HANGEN (die aufrufende Shell wartet auf
  das Kind, oder die Bus-Melde-Ende-Meldung des Wrappers blockiert) und in
  einen Timeout laufen. Der Start passiert VORHER: das Wrapper-Log
  (Agenten/Routinen/logs/handel-dauerlauf-letzter-lauf[.stufe].log) schreibt
  "Start (Stufe X)" und "gestartet als PID ...", die Sperrdatei ist danach
  neu. Wahrheit IMMER in einem SEPARATEN Aufruf messen (Prozesse mit
  CreationDate, Sperrdateien, Wrapper-Log) - nie aus dem Rueckkehrstatus des
  Wrapper-Aufrufs schliessen.
- Vor dem Kill: `freigabe_fenster.json` pruefen und offene Fenster notieren.
  Sie sind DATEIBASIERT und bleiben ueber den Neustart gueltig - der neue
  Dauerlauf liest dieselbe Datei; ein Neustart ist deshalb kein
  Freigabe-Verlust.

## Nachweis

1. Neue PIDs in den drei Sperrdateien je Stufe (`dauerlauf.pid`,
   `dauerlauf.mittel.pid`, `dauerlauf.hoch.pid`).
2. Erster Zyklus liegt im Journal; Zyklusalter < Takt.
3. `scanner/.venv/Scripts/python.exe spiegelstand.py` -> `N von N Spuren
   byte-gleich (Q:)`, mit N = neuer SPUREN-Stand - die Neue ist dabei.

## Spur-Subprozesse fensterlos halten

Der Dauerlauf startet je Spur `handeln.py` als `subprocess.run`. Jeder
Konsolen-Subprozess, den ein HINTERGRUND-/Task-Prozess auf Windows startet,
bekommt OHNE Sicherheits-Flag ein eigenes Konsolenfenster, das aufblitzt und
den Fokus stiehlt - `-WindowStyle Hidden` in der Task-Action ERBT das Kind
nicht. Unter `if os.name == "nt":` `creationflags=subprocess.CREATE_NO_WINDOW`
setzen - fuer die Spur-Kinder und fuer jeden CLI-Aufruf aus einem
Hintergrundprozess (onchainos u. a.). Der Linux-Zweig bleibt unveraendert.
Nach so einem Patch den Lauf am Aufgabe-Task pruefen: das verdeckte
Hintergrundfenster sonst wieder sichtbar heraus.
