# Registriert MaxHirn-Scanner-Papier (taeglich 08:10). ADMINISTRATOR NOETIG.
# Aufruf (erhoehte PowerShell): powershell -ExecutionPolicy Bypass -File Agenten\Routinen\scanner-papier-aufgabe.ps1
$ErrorActionPreference = 'Stop'
$wrapper = Join-Path $PSScriptRoot 'scanner-papier.ps1'
$aktion = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "{0}"' -f $wrapper)
$trigger = New-ScheduledTaskTrigger -Daily -At '08:10'
$einst = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$prin = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'MaxHirn-Scanner-Papier' -Action $aktion -Trigger $trigger -Settings $einst -Principal $prin -Force | Out-Null
"Aufgabe eingerichtet: " + (Get-ScheduledTask -TaskName 'MaxHirn-Scanner-Papier').State
