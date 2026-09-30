<#
  probe-stiller-start.ps1 - welcher Startweg wirkt wirklich?

  Faehrt EINE Kommandozeile mit mehreren Fensterstilen ueber einen
  Skriptwirt (WScript.Shell.Run) und meldet je Stil, ob tatsaechlich ein
  passender Prozess entstanden ist. Damit wird aus "der Dienst startet
  nicht" eine Wahrheitstabelle mit genau einem unterscheidenden Faktor.

  Gemessen am 30.09.2026 (cscript, Windows 11 26200):
      Ziel                     Stil 0  Stil 1  Stil 2  Stil 3  Stil 7  Stil 8
      cmd /c echo ...          nein    ja      nein    ja      nein    ja
      python.exe (Konsole)     nein    ja       -       -       -       -
      pythonw.exe (GUI)        JA      ja       -       -       -       -
  Stil 0 startet ein KONSOLENprogramm GAR NICHT - ohne Fehlermeldung.

  Aufruf ueber das terminal-Werkzeug:
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:/.../probe-stiller-start.ps1" `
        -Zeile "C:\...\python.exe -c \"open(r'C:\...\marke.txt','w').write('ok')\"" `
        -ProzessMuster 'python'

  ACHTUNG: startet wirklich das angegebene Programm. Fuer einen Dienst erst
  mit einer harmlosen Zeile (cmd /c echo) eichen, dann mit der echten Zeile.
#>
param(
  [Parameter(Mandatory = $true)][string]$Zeile,
  [string]$ProzessMuster = '',
  [int[]]$Stile = @(0, 1, 2, 3, 7, 8),
  [int]$WarteSekunden = 8,
  [string]$Ordner = "$env:TEMP\probe-stiller-start"
)

$ErrorActionPreference = 'Continue'
if (-not (Test-Path $Ordner)) { New-Item -ItemType Directory -Path $Ordner -Force | Out-Null }
$Ordner = (Resolve-Path $Ordner).Path
$vbs = Join-Path $Ordner 'probe.vbs'

function Prozesse([string]$muster) {
  $alle = Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe' or Name='cmd.exe'" -ErrorAction SilentlyContinue
  if ([string]::IsNullOrWhiteSpace($muster)) { return @() }
  return @($alle | Where-Object { $_.CommandLine -and $_.CommandLine -match $muster })
}

"=== Probe: $Zeile"
"=== Muster: $ProzessMuster   Stile: $($Stile -join ',')   Wartezeit: $WarteSekunden s"
""
$ergebnis = @()

foreach ($stil in $Stile) {
  $vorher = @(Prozesse $ProzessMuster | Select-Object -ExpandProperty ProcessId)

  # VBS, das genau diese Zeile mit genau diesem Stil startet (nicht warten)
  $inhalt = @(
    'Option Explicit',
    'Dim sh',
    'Set sh = CreateObject("WScript.Shell")',
    'sh.Run "' + ($Zeile -replace '"', '""') + '", ' + $stil + ', False'
  ) -join "`r`n"
  [System.IO.File]::WriteAllText($vbs, $inhalt, [System.Text.Encoding]::ASCII)

  & cscript.exe //nologo $vbs | Out-Null
  $cscriptExit = $LASTEXITCODE
  Start-Sleep -Seconds $WarteSekunden

  $nachher = @(Prozesse $ProzessMuster)
  $neue = @($nachher | Where-Object { $vorher -notcontains $_.ProcessId })

  $ergebnis += [pscustomobject]@{
    Stil     = $stil
    cscript  = $cscriptExit
    Prozess  = if ($neue.Count -gt 0) { 'JA' } else { 'nein' }
    PIDs     = ($neue | Select-Object -ExpandProperty ProcessId) -join ','
    Name     = ($neue | Select-Object -ExpandProperty Name | Select-Object -Unique) -join ','
  }

  # Aufraeumen: nur die eben entstandenen Prozesse beenden
  foreach ($p in $neue) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 1
}

""
$ergebnis | Format-Table -AutoSize | Out-String
"cscript-Exitcode 0 in ALLEN Zeilen ist normal - er beweist nichts."
"Massgeblich ist die Spalte Prozess. Genau EIN Faktor darf sich unterscheiden."
