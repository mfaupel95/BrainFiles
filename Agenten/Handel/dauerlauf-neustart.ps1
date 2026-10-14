# Startet den BASIS-Dauerlauf neu - erst wenn der laufende Zyklus vorbei ist.
#
# Warum das Warten Pflicht ist: laeuft gerade eine Spur (z. B. eine LIVE-Spur an
# der Boerse), wuerde ein Restart sie als Waise weiterlaufen lassen UND sofort
# einen neuen Zyklus starten - bei einem Live-Pfad ist das ein Doppelorder-
# Risiko. Erst wenn der Loop keine Kinder mehr hat, wird getauscht.
#
# Aufruf (wartet bis 10 Minuten):
#   powershell -NoProfile -ExecutionPolicy Bypass -File dauerlauf-neustart.ps1
param(
  [int]$WarteSekunden = 600,
  [switch]$NurPruefen,
  [string]$Stufe = 'basis'          # basis | mittel | hoch (eigene PID/Log-Dateien)
)

$ErrorActionPreference = 'Stop'
$handel = Split-Path $PSScriptRoot -Parent
$handel = Join-Path $handel 'Handel'
# Je Stufe eigene Sperre: dauerlauf.pid (Basis), dauerlauf.mittel.pid, dauerlauf.hoch.pid
# Der Startbefehl traegt -Risiko, weil dieselben drei Wrapper je Stufe starten.
$sperreName = 'dauerlauf.pid'
$risikoArgs = @()
if ($Stufe -ne 'basis') { $sperreName = "dauerlauf.$Stufe.pid"; $risikoArgs = @('-Risiko', $Stufe) }
$sperre = Join-Path $handel $sperreName
$log    = Join-Path $handel 'dauerlauf-neustart.log'

function Schreib($t) {
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  $t" | Add-Content $log -Encoding UTF8
}

$root = (Get-Content $sperre -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $root) { Schreib 'keine Sperre - kein laufender Basislauf'; exit 1 }
# Die Sperre traegt PID und Startzeit ("72484 1790854541.93") - nur das ERSTE
# Feld ist die PID; ein [int]-Cast auf den ganzen Text bricht mit
# Formatfehler ab (01.10.2026 erlebt: alle drei Stufen brachen ungeschaltet ab).
$root = [int]($root -split '\s+')[0]
$kind = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $root -and $_.Name -like 'python*' })
if (-not $kind) { Schreib "Wurzel $root hat keinen Loop - nichts zu tauschen"; exit 1 }
$loop = $kind[0].ProcessId
Schreib "Basis: Wurzel $root, Loop $loop - warte auf das Zyklusende"

$frist = (Get-Date).AddSeconds($WarteSekunden)
$frei = $false
while ((Get-Date) -lt $frist) {
  $laeuft = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $loop -and $_.Name -like 'python*' })
  if ($laeuft.Count -eq 0) { $frei = $true; break }
  Start-Sleep -Seconds 5
}
# Zweite Messung, damit ein Sekundenloch zwischen zwei Spuren nicht reicht.
if ($frei) {
  Start-Sleep -Seconds 3
  $laeuft = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $loop -and $_.Name -like 'python*' })
  if ($laeuft.Count -ne 0) { $frei = $false }
}
if (-not $frei) { Schreib 'Zyklus laeuft noch - NICHT getauscht (spaeter erneut)'; exit 2 }
Schreib "Zyklusende erreicht (keine Kindprozesse) - tausche PID $loop/$root"

if ($NurPruefen) { Schreib 'NurPruefen: kein Eingriff'; exit 0 }

# Reihenfolge: ERST das Kind (der Loop), dann die Wurzel. Die Wurzel ist nur ein
# Startprogramm und endet mit dem Kind - ein Stop-Process darauf wirft dann
# "kein Prozess mit dieser ID" und haette mit ErrorActionPreference='Stop' den
# ganzen Rest (inkl. Neustart) abgebrochen (am 24.09.2026 passiert: der Loop war
# danach tot und wurde erst von Hand neu gestartet). Deshalb hier ausdruecklich
# fehlertolerant beenden und den Erfolg MESSEN statt zu hoffen.
Stop-Process -Id $loop -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Stop-Process -Id $root -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$weg = @(Get-Process -Id @($loop, $root) -ErrorAction SilentlyContinue)
if ($weg.Count -ne 0) {
  Schreib ("Prozesse leben noch: " + (($weg | ForEach-Object { $_.Id }) -join ', ') +
           " - Abbruch, kein Doppelstart")
  exit 3
}
Schreib "alte Prozesse beendet (Loop $loop, Wurzel $root)"

Remove-Item $sperre -Force -ErrorAction SilentlyContinue
# Der Start-Skript liegt NICHT hier (Agenten/Handel), sondern in Routinen/ -
# bis 14.10.2026 zeigte dieser Aufruf auf 'handel-dauerlauf.ps1' im eigenen
# Ordner, der dort nicht existiert, und der Neustart liess den Dauerlauf tot
# (gemessen 12.10.2026 beim ersten orb/orbk-Neustart).
$routinen = Join-Path (Split-Path $PSScriptRoot -Parent) 'Routinen'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $routinen 'handel-dauerlauf.ps1') @risikoArgs
Start-Sleep -Seconds 5
$neu = (Get-Content $sperre -ErrorAction SilentlyContinue | Select-Object -First 1)
Schreib "neu gestartet, Sperre zeigt PID $neu"
exit 0