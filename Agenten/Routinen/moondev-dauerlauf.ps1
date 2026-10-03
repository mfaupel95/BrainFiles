# Startet den MoonDev-Dauerlauf (Agenten/Handel/moondev_dauerlauf.py) fensterlos:
# python.exe mit verstecktem Fenster statt pythonw.exe.
#
# WARUM: Nur ein Elternprozess MIT eigener Konsole (python.exe) vererbt sie als
# eine versteckte Konsole an alle Kinder (die geklonten Agenten, onchainos.exe,
# powershell.exe ...). pythonw.exe ist ein GUI-Subsystem-Prozess ohne Konsole,
# dort legt jedes Konsolen-Kind sein eigenes SICHTBARES an - aufblitzende
# Fenster rauben den Fokus (Hermes main.ts:2986). -WindowStyle Hidden versteckt
# genau diese eine vererbte Konsole; der eigentliche Treiber laeuft ohnehin
# --stumm und braucht kein Fenster.
#
# Von der Aufgabenplanung (MaxHirn-MoonDev-Dauerlauf) bei der Anmeldung
# aufgerufen (+2 Minuten). Doppelstart verhindert die Aufgabe selbst
# (MultipleInstances IgnoreNew), der Treiber traegt bei Bedarf seine eigene
# Wiederstart-Garantie.

$ErrorActionPreference = 'Stop'
$wurzel  = Split-Path $PSScriptRoot -Parent                 # Agenten
$handel  = Join-Path $wurzel 'Handel'
$py      = Join-Path $handel 'scanner\.venv\Scripts\python.exe'
$treiber = Join-Path $handel 'moondev_dauerlauf.py'
$logs    = Join-Path $PSScriptRoot 'logs'
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
$log = Join-Path $logs 'moondev-dauerlauf-letzter-lauf.log'

# Bus-Anbindung: eine Routine, die nur bei Erfolg meldet, sieht im Journal wie
# eine nicht existierende aus - genau daran war der Telegram-Bus im September
# vier Tage unbemerkt aus. Deshalb Melde-Start vor der ersten Pruefung und
# Melde-Ende an JEDEM Ausstieg.
. (Join-Path $wurzel 'Bus\Ereignis.ps1')
$marke = Melde-Start -Wer 'routine/moondev-dauerlauf'

if (-not (Test-Path $py))      { Melde-Ende -Marke $marke -Code 1 -Text "venv-Python fehlt: $py"; throw "venv-Python fehlt: $py" }
if (-not (Test-Path $treiber)) { Melde-Ende -Marke $marke -Code 1 -Text "Treiber fehlt: $treiber"; throw "Treiber fehlt: $treiber" }

# Einzelinstanz-Pruefung. Die Aufgabe selbst kann das nicht leisten: sie ist mit
# IgnoreNew eingestellt, dieser Wrapper kehrt aber sofort zurueck - eine zweite
# Ausloesung (Handstart, Fremdsitzung, Skriptaufruf) startet also einen ZWEITEN
# Treiber samt zweitem Agentensatz. Am 30.09.2026 liefen zwei Paare
# gleichzeitig (15:36 und 16:29). Suchtext aus Teilen bauen, sonst trifft der
# Filter die eigene Kommandozeile.
$muster = 'moondev' + '_dauerlauf'
$laeuft = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' or Name='pythonw.exe'" -EA SilentlyContinue |
            Where-Object { $_.CommandLine -and $_.CommandLine -match $muster })
if ($laeuft.Count -gt 0) {
  $pids = ($laeuft | ForEach-Object ProcessId) -join ', '
  Melde-Ende -Marke $marke -Code 0 -Text "Treiber laeuft schon (PID $pids), kein zweiter Start"
  "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  Treiber laeuft schon (PID $pids) - kein zweiter Start" |
    Add-Content $log -Encoding UTF8
  Write-Output "MoonDev-Dauerlauf laeuft schon (PID $pids)"
  exit 0
}

$p = Start-Process -FilePath $py -ArgumentList $treiber, '--stumm' `
                   -WorkingDirectory $handel -WindowStyle Hidden -PassThru

Melde-Ende -Marke $marke -Code 0 -Text "gestartet als PID $($p.Id)"
"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  gestartet als PID $($p.Id)" |
  Add-Content $log -Encoding UTF8
Write-Output "MoonDev-Dauerlauf gestartet PID $($p.Id)"