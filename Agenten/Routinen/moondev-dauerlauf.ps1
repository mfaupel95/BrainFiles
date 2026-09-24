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

if (-not (Test-Path $py))      { throw "venv-Python fehlt: $py" }
if (-not (Test-Path $treiber)) { throw "Treiber fehlt: $treiber" }

$p = Start-Process -FilePath $py -ArgumentList $treiber, '--stumm' `
                   -WorkingDirectory $handel -WindowStyle Hidden -PassThru

"$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))  gestartet als PID $($p.Id)" |
  Add-Content $log -Encoding UTF8
Write-Output "MoonDev-Dauerlauf gestartet PID $($p.Id)"