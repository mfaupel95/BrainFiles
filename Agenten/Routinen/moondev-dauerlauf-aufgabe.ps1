# Startet den MoonDev-Dauerlauf (Agenten/Handel/moondev_dauerlauf.py) als
# eigene geplante Aufgabe - er faehrt die geklonten Moon-Dev-Agenten
# (new_or_top, kraken) als langlebige Kindprozesse mit Wiederstart-Garantie.
#
# Registrierung (braucht Elevation, wie alle geplanten Aufgaben):
#   powershell -ExecutionPolicy Bypass -File Agenten\Routinen\moondev-dauerlauf-aufgabe.ps1

$ErrorActionPreference = 'Stop'
$name   = 'MaxHirn-MoonDev-Dauerlauf'
$wrapper = Join-Path $PSScriptRoot 'moondev-dauerlauf.ps1'
if (-not (Test-Path $wrapper)) { throw "Wrapper fehlt: $wrapper" }

$aktion  = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '"')
$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = 'PT2M'
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$task = New-ScheduledTask -Action $aktion -Trigger $trigger -Settings $settings `
  -Description 'MoonDev-Dauerlauf: faehrt die geklonten Moon-Dev-Agenten (new_or_top, kraken) als Kindprozesse mit Wiederstart-Garantie. Treiber: Agenten/Handel/moondev_dauerlauf.py'

Register-ScheduledTask -TaskName $name -InputObject $task -Force | Out-Null
Get-ScheduledTask -TaskName $name | Select-Object TaskName, State | Format-Table -AutoSize
Write-Output "Aufgabe '$name' angelegt."