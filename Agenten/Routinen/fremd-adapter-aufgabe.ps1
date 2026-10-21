# Registriert MaxHirn-Fremd-Adapter (alle 2 Minuten). NICHT AUTOMATISCH AUSGEFUEHRT.
# Das Signal-Fenster ist 180 s (expiry_s); ein Takt von 2 Minuten erwischt jedes Signal.
# Aufruf: powershell -ExecutionPolicy Bypass -File Agenten\Routinen\fremd-adapter-aufgabe.ps1
# Entfernen: Unregister-ScheduledTask -TaskName 'MaxHirn-Fremd-Adapter' -Confirm:$false
$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'fremd-adapter.ps1'
$aktion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date '00:00') -RepetitionInterval (New-TimeSpan -Minutes 2)
$einst = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$prin = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'MaxHirn-Fremd-Adapter' -Action $aktion -Trigger $trigger -Settings $einst -Principal $prin -Force | Out-Null
"Aufgabe eingerichtet: " + (Get-ScheduledTask -TaskName 'MaxHirn-Fremd-Adapter').State
